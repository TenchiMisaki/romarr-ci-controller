"""Private v24 GitHub REST artifact compatibility and nested ZIP readback.

Offline only: no network adapter, upload, token, workflow dispatch, or receipt
acceptance. The caller supplies independently trusted artifact ID, outer and
inner SHA-256 digests and verified source/run/job expectations. The GitHub REST
artifact metadata and downloaded outer ZIP are always treated as untrusted.
"""
from __future__ import annotations

from dataclasses import dataclass
import hashlib
import io
import re
import stat
import zipfile

import stage6_artifact_readback as readback
import stage6_hosted_provenance as provenance

CONTROLLER = 'TenchiMisaki/romarr-ci-controller'
ARTIFACT = 'stage6-advisory-provenance-v1'
MEMBER = 'stage6-advisory-sealed.zip'
MAX_OUTER = 16384
MAX_INNER = 8192
SHA = re.compile(r'[0-9a-f]{64}\Z')


@dataclass(frozen=True)
class EnvelopeResult:
    state: str
    reason: str = ''
    outer_sha256: str = ''
    inner_sha256: str = ''
    test_accepted: bool = False
    publication_authorized: bool = False
    unattended_dispatch_enabled: bool = False


def _blocked(reason: str) -> EnvelopeResult:
    return EnvelopeResult('BLOCKED', reason)


def verify_github_artifact(raw: object, outer: object,
                           expected: provenance.Expectation,
                           verified_job_ids: tuple[int, int], *,
                           expected_artifact_id: int,
                           independent_outer_digest: str,
                           independent_inner_digest: str) -> EnvelopeResult:
    """Verify documented REST metadata, outer artifact ZIP, then sealed ZIP.

    Trust prerequisites are NOT established here: independent digest and ID
    values must come from an authenticated trusted path, not raw metadata or
    the producer's untrusted output. The caller must independently recheck the
    workflow run and job provenance/freshness before relying on this advisory.
    """
    if not isinstance(expected, provenance.Expectation):
        return _blocked('INDEPENDENT_EXPECTATION_INVALID')
    if (type(expected_artifact_id) is not int or expected_artifact_id <= 0
            or type(independent_outer_digest) is not str
            or not SHA.fullmatch(independent_outer_digest)
            or type(independent_inner_digest) is not str
            or not SHA.fullmatch(independent_inner_digest)):
        return _blocked('INDEPENDENT_EXPECTATION_INVALID')
    if (type(outer) is not bytes or not 1 <= len(outer) <= MAX_OUTER):
        return _blocked('OUTER_ARCHIVE_SIZE_OR_TYPE_INVALID')
    if not isinstance(raw, dict) or not isinstance(raw.get('workflow_run'), dict):
        return _blocked('GITHUB_METADATA_INVALID')
    item_url = (f'https://api.github.com/repos/{CONTROLLER}/actions/artifacts/'
                f'{expected_artifact_id}')
    linked = raw['workflow_run']
    if (type(raw.get('id')) is not int or raw['id'] != expected_artifact_id
            or raw.get('name') != ARTIFACT
            or type(raw.get('size_in_bytes')) is not int
            or raw['size_in_bytes'] != len(outer)
            or raw.get('expired') is not False
            or raw.get('url') != item_url
            or raw.get('archive_download_url') != item_url + '/zip'
            or type(linked.get('id')) is not int or linked['id'] != expected.run_id
            or linked.get('head_sha') != expected.controller_sha):
        return _blocked('GITHUB_METADATA_IDENTITY_MISMATCH')
    outer_sha = hashlib.sha256(outer).hexdigest()
    if (raw.get('digest') != 'sha256:' + outer_sha
            or outer_sha != independent_outer_digest):
        return _blocked('OUTER_DIGEST_MISMATCH')
    try:
        with zipfile.ZipFile(io.BytesIO(outer)) as archive:
            files = archive.infolist()
            if len(files) != 1 or files[0].filename != MEMBER:
                return _blocked('OUTER_MEMBERS_NOT_ALLOWLISTED')
            item = files[0]
            if (item.is_dir() or item.flag_bits & 0x01
                    or item.file_size < 1 or item.file_size > MAX_INNER
                    or item.compress_size > MAX_OUTER
                    or item.compress_type not in (zipfile.ZIP_STORED, zipfile.ZIP_DEFLATED)):
                return _blocked('OUTER_MEMBER_UNSAFE')
            mode = item.external_attr >> 16
            if mode and stat.S_IFMT(mode) not in (0, stat.S_IFREG):
                return _blocked('OUTER_MEMBER_UNSAFE')
            inner = archive.read(item)
            # Reject trailers/zip overlays, which can hide unreviewed bytes.
            if not _no_outer_trailing_data(outer):
                return _blocked('OUTER_TRAILING_DATA')
    except (zipfile.BadZipFile, RuntimeError, ValueError, OSError, EOFError, MemoryError):
        return _blocked('OUTER_ARCHIVE_INVALID')
    inner_sha = hashlib.sha256(inner).hexdigest()
    if inner_sha != independent_inner_digest:
        return _blocked('INNER_DIGEST_MISMATCH')
    normalized = {
        'id': expected_artifact_id, 'name': ARTIFACT,
        'size_in_bytes': len(inner), 'expired': False,
        'workflow_run': {'id': expected.run_id, 'head_sha': expected.controller_sha},
        'digest': 'sha256:' + inner_sha, 'state': 'completed',
    }
    result = readback.verify_downloaded_advisory(
        normalized, inner, expected, verified_job_ids, independent_inner_digest,
        expected_artifact_id=expected_artifact_id)
    if result.state != 'ADVISORY_ARTIFACT_READBACK_VERIFIED':
        return _blocked('SEALED_ADVISORY_' + result.reason)
    return EnvelopeResult('GITHUB_ADVISORY_ENVELOPE_VERIFIED',
                          outer_sha256=outer_sha, inner_sha256=inner_sha)


def _no_outer_trailing_data(payload: bytes) -> bool:
    """Bounded structural check: ZIP EOCD must end at the final byte."""
    # EOCD minimum 22 bytes; comment length stored in the final two EOCD fields.
    off = payload.rfind(b'PK\x05\x06')
    if off < 0 or off + 22 > len(payload):
        return False
    count = int.from_bytes(payload[off + 20:off + 22], 'little')
    return off + 22 + count == len(payload)
