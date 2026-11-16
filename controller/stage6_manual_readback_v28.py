"""Private manual-only v28 GitHub artifact download and advisory readback.

Run in a separate, token-bearing verification job only. The producer's result
channel is never a trusted pytest receipt. No side effects other than GET.
"""
from __future__ import annotations

from dataclasses import dataclass
import hashlib
import io
import json
import os
import re
import stat
import zipfile

import stage6_artifact_http as transport
import stage6_hosted_api_v27 as provenance

MAX_OUTER = 65536
MAX_MEMBER = 4096
SHA = re.compile(r'[0-9a-f]{64}\Z')
HEX40 = re.compile(r'[0-9a-f]{40}\Z')
EXPECTED_SOURCE = '3c9896d2406d331c4f25c8a9f661c711ffe51745'
FILES = frozenset({'advisory.json', 'manifest.json'})
SCHEMA = 'romarr-stage6-v26-anonymous-advisory-v1'


@dataclass(frozen=True)
class AdvisoryResult:
    state: str
    reason: str = ''
    archive_sha256: str = ''
    passing_cases: int = 0
    test_accepted: bool = False
    publication_authorized: bool = False
    unattended_dispatch_enabled: bool = False


def _block(reason):
    return AdvisoryResult('BLOCKED', reason)


def _canonical(value):
    return (json.dumps(value, sort_keys=True, separators=(',', ':'), allow_nan=False) + '\n').encode('ascii')


def _json_no_duplicates(data):
    def pairs(items):
        obj = {}
        for key, value in items:
            if key in obj:
                raise ValueError('JSON_DUPLICATE_KEY')
            obj[key] = value
        return obj
    result = json.loads(data, object_pairs_hook=pairs)
    if type(result) is not dict or _canonical(result) != data:
        raise ValueError('JSON_NONCANONICAL')
    return result


def verify_archive(archive: bytes, *, run_id: int, source_sha: str,
                   producer_sha: str, producer_cases: str,
                   producer_exit: str, producer_state: str) -> AdvisoryResult:
    """Verify exact raw outer artifact and canonical two-file inner format."""
    if (type(run_id) is not int or run_id < 1 or source_sha != EXPECTED_SOURCE
            or producer_sha != source_sha or type(producer_cases) is not str
            or re.fullmatch(r'P{1,256}', producer_cases) is None
            or producer_exit != '0' or producer_state != 'success'):
        return _block('SOURCE_CHANNEL_MISMATCH')
    if type(archive) is not bytes or not 1 <= len(archive) <= MAX_OUTER:
        return _block('ARCHIVE_SIZE_INVALID')
    if not _zip_ends_at_eof(archive):
        return _block('ARCHIVE_TRAILING_DATA')
    try:
        with zipfile.ZipFile(io.BytesIO(archive)) as z:
            members = z.infolist()
            if len(members) != 2 or {m.filename for m in members} != FILES:
                return _block('MEMBERS_NOT_ALLOWLISTED')
            raw = {}
            for member in members:
                mode = member.external_attr >> 16
                if (member.is_dir() or member.flag_bits & 1
                        or not 0 < member.file_size <= MAX_MEMBER
                        or member.compress_size > MAX_OUTER
                        or member.compress_type not in (zipfile.ZIP_STORED, zipfile.ZIP_DEFLATED)
                        or mode and stat.S_IFMT(mode) not in (0, stat.S_IFREG)):
                    return _block('MEMBER_UNSAFE')
                payload = z.read(member)
                if len(payload) != member.file_size:
                    return _block('MEMBER_SIZE_MISMATCH')
                raw[member.filename] = payload
        record = _json_no_duplicates(raw['advisory.json'])
        manifest = _json_no_duplicates(raw['manifest.json'])
    except (zipfile.BadZipFile, ValueError, OSError, RuntimeError, EOFError,
            UnicodeError, MemoryError, TypeError):
        return _block('ARCHIVE_OR_JSON_INVALID')
    if (set(record) != {'schema','run_id','source_sha','passing_cases',
                        'pytest_exit','test_accepted','publication_authorized',
                        'unattended_dispatch_enabled'}
            or record.get('schema') != SCHEMA
            or type(record.get('run_id')) is not int or record['run_id'] != run_id
            or record.get('source_sha') != source_sha
            or type(record.get('passing_cases')) is not int
            or not 1 <= record['passing_cases'] <= 256
            or len(producer_cases) != record['passing_cases']
            or type(record.get('pytest_exit')) is not int or record['pytest_exit'] != 0
            or any(record.get(k) is not False for k in (
                'test_accepted', 'publication_authorized', 'unattended_dispatch_enabled'))):
        return _block('ADVISORY_SCHEMA_MISMATCH')
    expected_manifest = {'schema': SCHEMA, 'files': {
        'advisory.json': {'sha256': hashlib.sha256(raw['advisory.json']).hexdigest(),
                          'bytes': len(raw['advisory.json'])}}}
    if manifest != expected_manifest:
        return _block('MANIFEST_MISMATCH')
    return AdvisoryResult('ADVISORY_BYTES_VERIFIED',
                          archive_sha256=hashlib.sha256(archive).hexdigest(),
                          passing_cases=record['passing_cases'])


def _zip_ends_at_eof(data):
    pos = data.rfind(b'PK\x05\x06')
    if pos < 0 or pos + 22 > len(data):
        return False
    comment = int.from_bytes(data[pos + 20:pos + 22], 'little')
    return pos + 22 + comment == len(data)


def configured_storage_hosts(primary: str, secondary: str = '') -> frozenset[str]:
    """Only accept one or two independently configured exact Azure artifact hosts.

    An unset secondary entry preserves the old single-host behavior. Never
    discover trusted hosts from the received GitHub redirect Location.
    """
    if type(primary) is not str or type(secondary) is not str:
        raise ValueError('STORAGE_HOST_CONFIGURATION_INVALID')
    hosts = [primary] + ([secondary] if secondary else [])
    if (len(hosts) != len(set(hosts)) or not 1 <= len(hosts) <= 2 or
            any(re.fullmatch(r'[a-z0-9-]{1,64}\.blob\.core\.windows\.net', h) is None
                for h in hosts)):
        raise ValueError('STORAGE_HOST_CONFIGURATION_INVALID')
    return frozenset(hosts)


def run(*, run_id: int, run_attempt: int, controller_sha: str,
        artifact_id: int, producer_digest: str, token: str,
        storage_hosts: frozenset[str], producer_sha: str,
        producer_cases: str, producer_exit: str, producer_state: str,
        opener=None, fetch_snapshots=None) -> AdvisoryResult:
    """Recheck authenticated API provenance, then hash raw signed-storage bytes."""
    if (type(run_id) is not int or run_id < 1 or type(run_attempt) is not int
            or run_attempt < 1 or type(artifact_id) is not int or artifact_id < 1
            or type(controller_sha) is not str or HEX40.fullmatch(controller_sha) is None
            or type(producer_digest) is not str or SHA.fullmatch(producer_digest) is None
            or type(token) is not str or not 1 <= len(token) <= 1024
            or any(ord(c) < 33 or ord(c) > 126 for c in token)
            or type(storage_hosts) is not frozenset or not 1 <= len(storage_hosts) <= 2
            or any(type(h) is not str or not re.fullmatch(r'[a-z0-9.-]{1,253}', h)
                   or h == 'api.github.com' for h in storage_hosts)):
        return _block('INDEPENDENT_INPUT_INVALID')
    if opener is None:
        opener = transport._opener()
    if fetch_snapshots is None:
        fetch_snapshots = provenance.fetch_snapshots
    try:
        run_data, jobs_data, artifact = fetch_snapshots(
            run_id=run_id, artifact_id=artifact_id, token=token, opener=opener)
        provenance.attest(run_data, jobs_data, artifact,
                          run_id=run_id, run_attempt=run_attempt,
                          controller_sha=controller_sha, artifact_id=artifact_id,
                          uploaded_digest=producer_digest)
        outer_digest = artifact['digest'][7:]
        size = artifact['size_in_bytes']
        if (type(size) is not int or not 1 <= size <= MAX_OUTER or
                not SHA.fullmatch(outer_digest)):
            return _block('ARTIFACT_SIZE_OR_DIGEST_INVALID')
        base = f'{provenance.API}/artifacts/{artifact_id}/zip'
        location = transport._request(opener, base, token, max_bytes=0,
                                      accept='application/vnd.github+json',
                                      expected_status=302, require_location=True)
        if not transport._host_allowed(location, storage_hosts):
            return _block('REDIRECT_NOT_ALLOWLISTED')
        raw = transport._request(opener, location, None, max_bytes=MAX_OUTER,
                                 accept='application/octet-stream', expected_status=200)
        if (len(raw) != size or hashlib.sha256(raw).hexdigest() != outer_digest
                or outer_digest != producer_digest):
            return _block('DOWNLOADED_DIGEST_OR_SIZE_MISMATCH')
        result = verify_archive(raw, run_id=run_id, source_sha=EXPECTED_SOURCE,
                                producer_sha=producer_sha, producer_cases=producer_cases,
                                producer_exit=producer_exit, producer_state=producer_state)
        return result
    except (KeyError, ValueError, TypeError, OSError, RuntimeError,
            UnicodeError, json.JSONDecodeError):
        return _block('API_OR_DOWNLOAD_UNVERIFIED')


def main():
    """Run from the manual-only verifier step, never from the isolated source job."""
    try:
        outcome = run(
            run_id=int(os.environ['EXPECTED_RUN_ID']),
            run_attempt=int(os.environ['EXPECTED_RUN_ATTEMPT']),
            controller_sha=os.environ['EXPECTED_CONTROLLER_SHA'],
            artifact_id=int(os.environ['EXPECTED_ARTIFACT_ID']),
            producer_digest=os.environ['UPLOADED_ARTIFACT_DIGEST'],
            token=os.environ['GITHUB_TOKEN'],
            storage_hosts=configured_storage_hosts(
                os.environ['APPROVED_STORAGE_HOST'],
                os.environ.get('ADDITIONAL_APPROVED_STORAGE_HOST', '')),
            producer_sha=os.environ['UNTRUSTED_SOURCE_SHA'],
            producer_cases=os.environ['UNTRUSTED_CASES'],
            producer_exit=os.environ['UNTRUSTED_EXIT'],
            producer_state=os.environ['SOURCE_JOB_RESULT'],
        )
    except (KeyError, ValueError, TypeError):
        outcome = _block('MISSING_OR_INVALID_INPUT')
    if outcome.state != 'ADVISORY_BYTES_VERIFIED':
        print('BLOCKED: manual advisory download/integrity unverified (' + outcome.reason + ')')
        raise SystemExit(1)
    print(f'ADVISORY_DOWNLOADED_BYTES_VERIFIED: {outcome.passing_cases} anonymous cases')
    print('GITHUB_TEST_RECEIPT_ACCEPTED: false')
    print('TEST_ACCEPTED: false')
    print('PUBLICATION_AUTHORIZED: false')
    print('UNATTENDED_DISPATCH_ENABLED: false')
    print('PR_SOURCE_TESTED: false')


if __name__ == '__main__':
    main()
