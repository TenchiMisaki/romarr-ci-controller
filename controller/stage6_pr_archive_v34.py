"""Offline byte verifier for a future exact-PR *advisory*, never a test receipt.

The trusted caller must first validate current PR/run/job/artifact provenance via
v32/v33, then obtain the bytes through the credential-separated transport.
No network access, credentials, dispatch, job execution, or authorization here.
"""
from __future__ import annotations
import hashlib
import io
import json
import re
import stat
import zipfile
from dataclasses import dataclass
from stage6_pr_identity_v32 import IdentityRejected

MAX_OUTER = 65536
MAX_INNER = 8192
FILES = frozenset({'advisory.json', 'manifest.json'})
SCHEMA = 'romarr-stage6-pr-advisory-v34'
HEX40 = re.compile(r'[0-9a-f]{40}\Z')
HEX64 = re.compile(r'[0-9a-f]{64}\Z')

@dataclass(frozen=True)
class AdvisoryBytes:
    state: str
    archive_sha256: str
    passing_cases: int
    test_accepted: bool = False
    publication_authorized: bool = False
    unattended_dispatch_enabled: bool = False


def _canonical(value):
    try:
        return (json.dumps(value, sort_keys=True, separators=(',', ':'), ensure_ascii=True, allow_nan=False) + '\n').encode('ascii')
    except (TypeError, ValueError, UnicodeError) as exc:
        raise IdentityRejected('JSON_INVALID') from exc


def _strict_json(blob):
    def no_dupes(items):
        d = {}
        for key, value in items:
            if key in d:
                raise IdentityRejected('JSON_DUPLICATE_KEY')
            d[key] = value
        return d
    try:
        value = json.loads(blob, object_pairs_hook=no_dupes)
    except (ValueError, UnicodeError, TypeError, OverflowError) as exc:
        raise IdentityRejected('JSON_INVALID') from exc
    if type(value) is not dict or _canonical(value) != blob:
        raise IdentityRejected('JSON_NONCANONICAL')
    return value


def _eof(blob):
    pos = blob.rfind(b'PK\x05\x06')
    if pos < 0 or pos + 22 > len(blob):
        return False
    comment = int.from_bytes(blob[pos+20:pos+22], 'little')
    return pos + 22 + comment == len(blob)


def verify_advisory_bytes(archive: bytes, *, expected_archive_sha256: str,
                          expected_run_id: int, expected_head_sha: str,
                          expected_base_sha: str) -> AdvisoryBytes:
    """Reject malformed byte evidence; never promote it to trusted pytest PASS.

    The outer digest MUST be from independently authenticated GitHub metadata,
    not merely the artifact producer's untrusted reported output.
    """
    if (type(archive) is not bytes or not 1 <= len(archive) <= MAX_OUTER
            or type(expected_archive_sha256) is not str or not HEX64.fullmatch(expected_archive_sha256)
            or type(expected_run_id) is not int or expected_run_id < 1
            or type(expected_head_sha) is not str or not HEX40.fullmatch(expected_head_sha)
            or type(expected_base_sha) is not str or not HEX40.fullmatch(expected_base_sha)):
        raise IdentityRejected('BYTE_EXPECTATION_INVALID')
    outer = hashlib.sha256(archive).hexdigest()
    if outer != expected_archive_sha256:
        raise IdentityRejected('OUTER_SHA256_MISMATCH')
    if not archive.startswith(b'PK\x03\x04') or not _eof(archive):
        raise IdentityRejected('ARCHIVE_TRAILING_DATA')
    try:
        with zipfile.ZipFile(io.BytesIO(archive), 'r') as z:
            members = z.infolist()
            if len(members) != 2 or {m.filename for m in members} != FILES:
                raise IdentityRejected('UNEXPECTED_MEMBERS')
            raw = {}
            for m in members:
                mode = m.external_attr >> 16
                if (m.is_dir() or m.flag_bits & 1 or not 0 < m.file_size <= MAX_INNER
                    or m.compress_size > MAX_OUTER or m.compress_type not in (0, 8)
                    or (mode and stat.S_IFMT(mode) not in (0, stat.S_IFREG))):
                    raise IdentityRejected('UNSAFE_ZIP_MEMBER')
                payload = z.read(m)
                if len(payload) != m.file_size:
                    raise IdentityRejected('ZIP_MEMBER_LENGTH_MISMATCH')
                raw[m.filename] = payload
    except (zipfile.BadZipFile, RuntimeError, OSError, EOFError, ValueError, MemoryError) as exc:
        if isinstance(exc, IdentityRejected):
            raise
        raise IdentityRejected('ZIP_INVALID') from exc
    record = _strict_json(raw['advisory.json'])
    manifest = _strict_json(raw['manifest.json'])
    if (set(record) != {'schema','run_id','head_sha','base_sha','passing_cases','pytest_exit','test_accepted','publication_authorized','unattended_dispatch_enabled'}
            or record.get('schema') != SCHEMA or type(record.get('run_id')) is not int
            or record['run_id'] != expected_run_id
            or record.get('head_sha') != expected_head_sha
            or record.get('base_sha') != expected_base_sha
            or type(record.get('passing_cases')) is not int
            or not 1 <= record['passing_cases'] <= 10000
            or type(record.get('pytest_exit')) is not int or record['pytest_exit'] != 0
            or any(record.get(k) is not False for k in ('test_accepted','publication_authorized','unattended_dispatch_enabled'))):
        raise IdentityRejected('ADVISORY_SCHEMA_MISMATCH')
    if manifest != {'schema': SCHEMA, 'files': {'advisory.json': {
            'sha256': hashlib.sha256(raw['advisory.json']).hexdigest(),
            'bytes': len(raw['advisory.json'])}}}:
        raise IdentityRejected('MANIFEST_MISMATCH')
    return AdvisoryBytes('ADVISORY_BYTES_VERIFIED_NOT_ACCEPTED', outer, record['passing_cases'])
