"""Private Stage 6 prototype: seal advisory GitHub-job provenance as allowlisted ZIP bytes.

The two-job inspector verifies GitHub run and job metadata through a caller-provided
GET-only adapter. The test case string and source SHA still originate from the
untrusted test job: never claim a trusted test receipt, authorization, or publish
this bundle as an accepted ROMarr result. This module has NO network/write API.
"""
from __future__ import annotations

from dataclasses import dataclass
import hashlib
import io
import json
import zipfile

import stage6_hosted_provenance as provenance

_SCHEMA = 'romarr-stage6-hosted-job-provenance-advisory-v1'
_ALLOWED = frozenset({'advisory.json', 'manifest.json'})
_MAX_BUNDLE = 8192


@dataclass(frozen=True)
class SealedAdvisory:
    state: str
    reason: str = ''
    archive: bytes = b''
    sha256: str = ''
    test_accepted: bool = False
    publication_authorized: bool = False
    unattended_dispatch_enabled: bool = False


def _json_bytes(value: object) -> bytes:
    return (json.dumps(value, sort_keys=True, ensure_ascii=True,
                       separators=(',', ':'), allow_nan=False) + '\n').encode('ascii')


def _payload(expected: provenance.Expectation,
             verified_job_ids: tuple[int, int]) -> dict[str, bytes]:
    data = {
        'schema': _SCHEMA,
        'controller_repository': provenance.CONTROLLER,
        'workflow': provenance.WORKFLOW,
        'controller_sha': expected.controller_sha,
        'declared_source_sha': expected.source_sha,
        'run_id': expected.run_id,
        'run_attempt': expected.attempt,
        'source_job_id': verified_job_ids[0],
        'review_job_id': verified_job_ids[1],
        'declared_passing_cases': expected.case_count,
        'job_provenance': 'GITHUB_RUN_AND_JOB_METADATA_CHECKED',
        'source_test_provenance': 'UNTRUSTED_JOB_CHANNEL_NOT_INDEPENDENTLY_ATTESTED',
        'advisory_only': True,
        'test_accepted': False,
        'publication_authorized': False,
        'unattended_dispatch_enabled': False,
    }
    advisory = _json_bytes(data)
    manifest = _json_bytes({
        'schema': _SCHEMA,
        'files': {'advisory.json': {'bytes': len(advisory),
                                    'sha256': hashlib.sha256(advisory).hexdigest()}},
    })
    return {'advisory.json': advisory, 'manifest.json': manifest}


def _archive(files: dict[str, bytes]) -> bytes:
    sink = io.BytesIO()
    with zipfile.ZipFile(sink, 'w') as z:
        for name in sorted(files):
            member = zipfile.ZipInfo(name, date_time=(2026, 1, 1, 0, 0, 0))
            member.create_system = 3
            member.external_attr = 0o100600 << 16
            member.compress_type = zipfile.ZIP_DEFLATED
            z.writestr(member, files[name])
    return sink.getvalue()


def verify_sealed(archive: bytes, expected: provenance.Expectation,
                  verified_job_ids: tuple[int, int]) -> bool:
    """Independently recompute every allowlisted byte; never trust ZIP manifest alone."""
    if (type(archive) is not bytes or not 1 <= len(archive) <= _MAX_BUNDLE
            or type(verified_job_ids) is not tuple or len(verified_job_ids) != 2
            or any(type(v) is not int or v <= 0 for v in verified_job_ids)
            or verified_job_ids[0] == verified_job_ids[1]):
        return False
    try:
        files = _payload(expected, verified_job_ids)
        with zipfile.ZipFile(io.BytesIO(archive)) as z:
            infos = z.infolist()
            if (len(infos) != 2 or set(x.filename for x in infos) != _ALLOWED
                    or any(x.file_size > 4096 or x.compress_size > 4096
                           or x.flag_bits & 0x01 for x in infos)):
                return False
            # Never call testzip()/read() before bounding decompressed sizes.
            if z.testzip() is not None:
                return False
            for item in infos:
                if (item.is_dir() or item.flag_bits & 0x01
                        or item.file_size != len(files[item.filename])
                        or item.file_size > 4096
                        or item.compress_type != zipfile.ZIP_DEFLATED
                        or item.external_attr >> 16 != 0o100600
                        or z.read(item) != files[item.filename]):
                    return False
        # Canonical archive bytes reject trailing data, order and metadata tampering.
        return archive == _archive(files)
    except (ValueError, KeyError, TypeError, OverflowError, RuntimeError,
            zipfile.BadZipFile, OSError, EOFError, MemoryError):
        return False


def prepare_private_advisory(api: object, expected: provenance.Expectation,
                             untrusted: object) -> SealedAdvisory:
    """Read-only metadata validation and in-memory sealing; never upload/publish."""
    result = provenance.inspect(api, expected, untrusted)
    if result.state != 'ADVISORY_JOB_PROVENANCE_VERIFIED':
        return SealedAdvisory(result.state, result.reason)
    try:
        content = _archive(_payload(expected, result.verified_job_ids))
        if not verify_sealed(content, expected, result.verified_job_ids):
            return SealedAdvisory('BLOCKED', 'ADVISORY_SEAL_INVALID')
        return SealedAdvisory('PRIVATE_ADVISORY_SEALED', archive=content,
                             sha256=hashlib.sha256(content).hexdigest())
    except (ValueError, KeyError, TypeError, RuntimeError, OSError):
        return SealedAdvisory('BLOCKED', 'ADVISORY_SEAL_INVALID')
