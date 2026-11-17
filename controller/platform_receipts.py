"""Independent advisory platform receipts; never release or deployment approval.

Provider metadata and build attestations must be collected independently by a
trusted verifier. Artifact self-reports alone cannot establish provenance.
"""
from __future__ import annotations

from dataclasses import dataclass
import hashlib
import io
import json
import re
import stat
import struct
import zipfile

SHA40 = re.compile(r'[0-9a-f]{40}\Z')
SHA256 = re.compile(r'[0-9a-f]{64}\Z')
REPO = re.compile(r'[A-Za-z0-9_.-]+/[A-Za-z0-9_.-]+\Z')
PLATFORMS = {'source-linux', 'docker-standard', 'docker-browser',
             'windows-py311', 'windows-py313', 'windows-exe', 'android'}
DIMENSIONS = {'build', 'environment', 'startup', 'test', 'collection', 'provenance', 'freshness'}
STATES = {'PASS', 'FAIL', 'NOT_TESTED', 'NOT_CONFIGURED', 'UNSUPPORTED',
          'SKIPPED', 'INCOMPLETE', 'COLLECTION_FAILED', 'STALE', 'BLOCKED', 'NOT_APPLICABLE'}
MEMBERS = {'receipt.json', 'cases.json', 'manifest.json'}
MAX_ZIP = 4 * 1024 * 1024
MAX_MEMBER = 1024 * 1024


class PlatformRejected(ValueError):
    """Platform evidence is missing, malformed, stale or unauthenticated."""


def canonical(value):
    """Deterministic JSON with no nonfinite numbers or alternate encodings."""
    return (json.dumps(value, sort_keys=True, separators=(',', ':'), allow_nan=False)+'\n').encode()


def positive(value):
    """Exclude booleans from IDs and enforce bounded positive integers."""
    return type(value) is int and 0 < value < 2**63


@dataclass(frozen=True)
class ExpectedPlatform:
    """Trusted immutable expectations, never populated from the candidate ZIP."""
    platform: str
    source_repo: str
    source_sha: str
    base_sha: str
    controller_sha: str
    producer_repo: str
    producer_sha: str
    workflow: str
    run_id: int
    attempt: int
    job_id: int
    job_name: str
    required_steps: tuple[str, ...]
    artifact_id: int
    artifact_sha256: str
    subject_sha256: str | None
    scope: str

    def __post_init__(self):
        """Reject unbounded, foreign-shaped or incomplete expectation fields."""
        if (self.platform not in PLATFORMS or self.platform == 'android'
                or any(type(x) is not str or not REPO.fullmatch(x) for x in (self.source_repo, self.producer_repo))
                or any(type(x) is not str or not SHA40.fullmatch(x) for x in (
                    self.source_sha, self.base_sha, self.controller_sha, self.producer_sha))
                or any(not positive(x) for x in (self.run_id, self.attempt, self.job_id, self.artifact_id))
                or type(self.workflow) is not str
                or not re.fullmatch(r'\.github/workflows/[A-Za-z0-9_-]+\.yml', self.workflow)
                or type(self.job_name) is not str or not 1 <= len(self.job_name) <= 120
                or type(self.required_steps) is not tuple or not self.required_steps
                or len(set(self.required_steps)) != len(self.required_steps)
                or any(type(x) is not str or not 1 <= len(x) <= 120 for x in self.required_steps)
                or type(self.artifact_sha256) is not str or not SHA256.fullmatch(self.artifact_sha256)
                or self.scope not in {'source-full', 'source-focused', 'runtime-smoke', 'native-smoke'}):
            raise PlatformRejected('PLATFORM_EXPECTATION_INVALID')
        packaged = self.platform.startswith('docker-') or self.platform == 'windows-exe'
        if packaged != (type(self.subject_sha256) is str and bool(SHA256.fullmatch(self.subject_sha256))):
            raise PlatformRejected('PACKAGED_SUBJECT_DIGEST_REQUIRED')
        if not packaged and self.subject_sha256 is not None:
            raise PlatformRejected('SOURCE_SUBJECT_NOT_APPLICABLE')


@dataclass(frozen=True)
class PlatformResult:
    """Advisory evidence outcome; every authorization flag stays false."""
    platform: str
    source_repo: str
    source_sha: str
    base_sha: str
    controller_sha: str
    dimensions: dict
    case_counts: dict
    state: str
    release_authorized: bool = False
    unattended_enabled: bool = False


def read_bundle(raw, digest):
    """Accept only three canonical, bounded regular JSON files with hashes."""
    if (type(raw) is not bytes or not 22 <= len(raw) <= MAX_ZIP
            or hashlib.sha256(raw).hexdigest() != digest
            or raw[:4] != b'PK\x03\x04' or raw[-22:-18] != b'PK\x05\x06'):
        raise PlatformRejected('PLATFORM_ARCHIVE_DIGEST_OR_SIZE')
    try:
        with zipfile.ZipFile(io.BytesIO(raw)) as archive:
            rows = archive.infolist()
            if archive.comment or len(rows) != 3 or {x.filename for x in rows} != MEMBERS:
                raise PlatformRejected('PLATFORM_MEMBER_ALLOWLIST')
            content = {}
            cursor = 0
            for row in rows:
                mode = row.external_attr >> 16
                if (row.is_dir() or row.comment or row.extra or row.flag_bits & 1 or row.file_size > MAX_MEMBER
                        or row.file_size <= 0 or row.compress_type not in {zipfile.ZIP_STORED, zipfile.ZIP_DEFLATED}
                        or stat.S_ISLNK(mode) or stat.S_IFMT(mode) not in {0, stat.S_IFREG}
                        or row.file_size > max(1, row.compress_size) * 100):
                    raise PlatformRejected('PLATFORM_MEMBER_UNSAFE')
                # The central directory does not authenticate local-only fields.
                # Require contiguous ordinary headers and compressed data, with
                # no descriptors, prefixes, padding or unaccounted bytes.
                if row.header_offset != cursor or cursor + 30 > len(raw):
                    raise PlatformRejected('PLATFORM_LOCAL_HEADER_LAYOUT')
                fields = struct.unpack_from('<4s5H3I2H', raw, cursor)
                signature, version, flags, method, _, _, crc, packed, size, namesize, extra = fields
                name = row.filename.encode('utf-8' if flags & 0x800 else 'cp437')
                if (signature != b'PK\x03\x04' or version != row.extract_version
                        or flags != row.flag_bits or flags & ~0x800 or method != row.compress_type
                        or crc != row.CRC or packed != row.compress_size or size != row.file_size
                        or extra or namesize != len(name)
                        or raw[cursor+30:cursor+30+namesize] != name):
                    raise PlatformRejected('PLATFORM_LOCAL_HEADER_METADATA')
                cursor += 30 + namesize + packed
                data = archive.read(row)
                value = json.loads(data)
                if canonical(value) != data:
                    raise PlatformRejected('PLATFORM_JSON_NOT_CANONICAL')
                content[row.filename] = (data, value)
            # Account for each central header and the single terminal EOCD.
            central_start = cursor
            for row in rows:
                if raw[cursor:cursor+4] != b'PK\x01\x02' or cursor + 46 > len(raw):
                    raise PlatformRejected('PLATFORM_CENTRAL_LAYOUT')
                namesize, extrasize, commentsize = struct.unpack_from('<3H', raw, cursor+28)
                if extrasize or commentsize:
                    raise PlatformRejected('PLATFORM_CENTRAL_METADATA')
                cursor += 46 + namesize
            if (cursor != len(raw)-22 or struct.unpack_from('<4s4H2IH', raw, cursor)
                    != (b'PK\x05\x06', 0, 0, 3, 3, cursor-central_start, central_start, 0)):
                raise PlatformRejected('PLATFORM_UNACCOUNTED_ARCHIVE_BYTES')
            manifest = content['manifest.json'][1]
            expected = {name: hashlib.sha256(content[name][0]).hexdigest()
                        for name in ('receipt.json', 'cases.json')}
            if manifest != {'schema': 'romarr-platform-manifest-v1', 'files': expected}:
                raise PlatformRejected('PLATFORM_MANIFEST_INVALID')
            return content['receipt.json'][1], content['cases.json'][1]
    except (zipfile.BadZipFile, ValueError, UnicodeError, RuntimeError, OSError) as exc:
        if isinstance(exc, PlatformRejected):
            raise
        raise PlatformRejected('PLATFORM_ARCHIVE_INVALID') from None


def github_metadata(expected, *, run, jobs, artifact):
    """Bind authenticated GitHub run, exact job/steps and artifact metadata.

    This is a provider-specific adapter. Other providers must implement their
    own authenticated metadata contract, not impersonate GitHub data fields.
    """
    e = expected
    if (type(run) is not dict or run.get('repository', {}).get('full_name') != e.producer_repo
            or type(run.get('id')) is not int or run['id'] != e.run_id
            or type(run.get('run_attempt')) is not int or run['run_attempt'] != e.attempt
            or run.get('head_sha') != e.producer_sha or run.get('path') != e.workflow
            or run.get('status') != 'completed' or run.get('conclusion') != 'success'
            or run.get('html_url') != f'https://github.com/{e.producer_repo}/actions/runs/{e.run_id}'):
        raise PlatformRejected('PLATFORM_RUN_IDENTITY')
    if (type(jobs) is not dict or type(jobs.get('total_count')) is not int
            or type(jobs.get('jobs')) is not list or jobs['total_count'] != len(jobs['jobs'])
            or not 0 < len(jobs['jobs']) <= 100):
        raise PlatformRejected('PLATFORM_JOBS_INCOMPLETE')
    matches = [j for j in jobs['jobs'] if type(j) is dict and j.get('id') == e.job_id]
    if len(matches) != 1:
        raise PlatformRejected('PLATFORM_JOB_NOT_UNIQUE')
    job = matches[0]
    if (type(job.get('id')) is not int or job.get('name') != e.job_name
            or type(job.get('run_id')) is not int or job['run_id'] != e.run_id
            or type(job.get('run_attempt')) is not int or job['run_attempt'] != e.attempt
            or job.get('head_sha') != e.producer_sha
            or job.get('status') != 'completed' or job.get('conclusion') != 'success'
            or type(job.get('steps')) is not list):
        raise PlatformRejected('PLATFORM_JOB_IDENTITY')
    for name in e.required_steps:
        steps = [s for s in job['steps'] if type(s) is dict and s.get('name') == name]
        if len(steps) != 1 or steps[0].get('status') != 'completed' or steps[0].get('conclusion') != 'success':
            raise PlatformRejected('PLATFORM_REQUIRED_STEP_NOT_SUCCESSFUL')
    if (type(artifact) is not dict or type(artifact.get('id')) is not int
            or artifact['id'] != e.artifact_id or artifact.get('expired') is not False
            or type(artifact.get('size_in_bytes')) is not int
            or not 0 < artifact['size_in_bytes'] <= MAX_ZIP
            or artifact.get('digest') != 'sha256:' + e.artifact_sha256
            or artifact.get('workflow_run', {}).get('id') != e.run_id
            or artifact.get('workflow_run', {}).get('head_sha') != e.producer_sha):
        raise PlatformRejected('PLATFORM_ARTIFACT_IDENTITY')


def verify_platform(expected, *, raw, run, jobs, artifact, source_before,
                    source_after, verify_subject=None):
    """Reconcile a typed receipt without trusting its provenance PASS flag.

    Source snapshots contain independently authenticated repo/head/base values.
    For packages, verify_subject(expected) must use an independently authenticated
    build/attestation verifier and return the exact (repo, source SHA, digest).
    No default attestation implementation is assumed. Missing proof is BLOCKED.
    """
    if type(expected) is not ExpectedPlatform:
        raise PlatformRejected('PLATFORM_EXPECTATION_TYPE')
    e = expected
    identity = dict(repo=e.source_repo, head=e.source_sha, base=e.base_sha)
    if source_before != identity or source_after != identity:
        raise PlatformRejected('PLATFORM_SOURCE_STALE')
    github_metadata(e, run=run, jobs=jobs, artifact=artifact)
    receipt, cases = read_bundle(raw, e.artifact_sha256)
    wanted = dict(schema='romarr-platform-receipt-v1', platform=e.platform,
                  source_repo=e.source_repo, source_sha=e.source_sha, base_sha=e.base_sha,
                  controller_sha=e.controller_sha, producer_repo=e.producer_repo,
                  producer_sha=e.producer_sha, workflow=e.workflow, run_id=e.run_id,
                  attempt=e.attempt, job_id=e.job_id, scope=e.scope, subject_sha256=e.subject_sha256)
    if type(receipt) is not dict or set(receipt) != set(wanted) | {'dimensions', 'counts'}:
        raise PlatformRejected('PLATFORM_RECEIPT_SCHEMA')
    if any(type(receipt[k]) is not type(v) or receipt[k] != v for k, v in wanted.items()):
        raise PlatformRejected('PLATFORM_RECEIPT_IDENTITY')
    dims, counts = receipt['dimensions'], receipt['counts']
    if type(dims) is not dict or set(dims) != DIMENSIONS or any(type(v) is not str or v not in STATES for v in dims.values()):
        raise PlatformRejected('PLATFORM_DIMENSIONS_INVALID')
    outcomes = {'passed', 'failed', 'errors', 'skipped'}
    if type(counts) is not dict or set(counts) != outcomes or any(type(v) is not int or v < 0 for v in counts.values()):
        raise PlatformRejected('PLATFORM_COUNTS_INVALID')
    if type(cases) is not dict or set(cases) != {'schema', 'cases'} or cases['schema'] != 'romarr-platform-cases-v1':
        raise PlatformRejected('PLATFORM_CASE_SCHEMA')
    rows = cases['cases']
    if type(rows) is not list or len(rows) > 10000:
        raise PlatformRejected('PLATFORM_CASE_BOUND')
    actual = dict.fromkeys(outcomes, 0)
    for index, case in enumerate(rows, 1):
        if (type(case) is not dict or set(case) != {'ordinal', 'outcome'}
                or type(case['ordinal']) is not int or case['ordinal'] != index or case['outcome'] not in outcomes):
            raise PlatformRejected('PLATFORM_CASE_PRIVACY_OR_ORDER')
        actual[case['outcome']] += 1
    if actual != counts or dims['test'] == 'PASS' and (not rows or counts['failed'] or counts['errors'] or counts['skipped']):
        raise PlatformRejected('PLATFORM_CASE_ACCOUNTING_OR_SKIP_POLICY')
    result_dims = dict(dims)
    # Producer assertions are not provenance evidence, even in canonical JSON.
    if verify_subject is None:
        result_dims['provenance'] = 'BLOCKED'
    else:
        proof = verify_subject(e)
        if proof != (e.source_repo, e.source_sha, e.subject_sha256):
            raise PlatformRejected('INDEPENDENT_PROVENANCE_MISMATCH')
        result_dims['provenance'] = 'PASS'
    # Internal count consistency cannot establish completed producer collection.
    result_dims['freshness'] = 'PASS'
    required = {'environment', 'test', 'collection', 'provenance', 'freshness'}
    if e.subject_sha256 is not None:
        required |= {'build', 'startup'}
    state = 'ADVISORY_VERIFIED' if all(result_dims[k] == 'PASS' for k in required) else 'ADVISORY_BLOCKED'
    return PlatformResult(e.platform, e.source_repo, e.source_sha, e.base_sha,
                          e.controller_sha, result_dims, counts, state)


def readiness(*, policy, identity, results):
    """Aggregate one revision under explicit versioned required/optional policy."""
    if (type(policy) is not dict or set(policy) != {'schema', 'required', 'optional'}
            or policy['schema'] != 'romarr-platform-policy-v1'
            or any(type(policy[k]) is not list for k in ('required', 'optional'))):
        raise PlatformRejected('PLATFORM_POLICY_INVALID')
    required, optional = policy['required'], policy['optional']
    platforms = required + optional
    if (not required or len(set(platforms)) != len(platforms)
            or any(p not in PLATFORMS for p in platforms) or type(results) is not list
            or type(identity) is not tuple or len(identity) != 4):
        raise PlatformRejected('PLATFORM_POLICY_OR_IDENTITY_INVALID')
    indexed = {}
    for result in results:
        if (type(result) is not PlatformResult or result.platform not in platforms or result.platform in indexed
                or (result.source_repo, result.source_sha, result.base_sha, result.controller_sha) != identity
                or result.release_authorized or result.unattended_enabled):
            raise PlatformRejected('PLATFORM_AGGREGATE_STALE_OR_DUPLICATE')
        indexed[result.platform] = result.state
    states = {p: indexed.get(p, 'NOT_TESTED') for p in platforms}
    return dict(schema='romarr-platform-readiness-v1', platforms=states,
                state='ADVISORY_READY' if all(states[p] == 'ADVISORY_VERIFIED' for p in required) else 'ADVISORY_INCOMPLETE',
                release_authorized=False, unattended_enabled=False)
