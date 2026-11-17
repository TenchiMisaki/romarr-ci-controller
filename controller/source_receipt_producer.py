"""Dormant trusted-host serializer; no source execution or provenance authority.

The host must independently establish full-suite selection, isolated execution,
checkout/toolchain identity and completed collection. JUnit cannot prove those
facts. This module never loads credentials, reads paths or uploads artifacts.
"""
from __future__ import annotations

from dataclasses import dataclass
import hashlib
import io
import re
import stat
import xml.etree.ElementTree as ET
import zipfile

from platform_receipts import (ExpectedPlatform, MAX_MEMBER, MAX_ZIP,
    PlatformRejected, canonical, read_bundle)
from stage6_pr_identity_v32 import CONTROLLER_REPO, SOURCE_REPO

MAX_XML = 8 * 1024 * 1024
OUTCOMES = ('passed', 'failed', 'errors', 'skipped')


@dataclass(frozen=True)
class SourceRun:
    """Host-pinned source execution identity, before artifact ID/digest exist."""
    platform: str
    source_sha: str
    base_sha: str
    controller_sha: str
    workflow: str
    run_id: int
    attempt: int
    job_id: int

    def __post_init__(self):
        """Reuse the consumer's identity grammar without trusting artifact data."""
        ExpectedPlatform(self.platform, SOURCE_REPO, self.source_sha, self.base_sha,
            self.controller_sha, CONTROLLER_REPO, self.controller_sha, self.workflow,
            self.run_id, self.attempt, self.job_id, 'host-pinned', ('host-pinned',),
            1, '0'*64, None, 'source-full')
        if self.platform not in {'source-linux', 'windows-py311', 'windows-py313'}:
            raise PlatformRejected('SOURCE_PRODUCER_PLATFORM_INVALID')


def _counts(node):
    """Require explicit canonical nonnegative suite counters, not guessed totals."""
    keys = ('tests', 'failures', 'errors', 'skipped')
    if any(not re.fullmatch(r'0|[1-9][0-9]{0,4}', node.get(k, '')) for k in keys):
        raise PlatformRejected('SOURCE_PRODUCER_TOTALS_INVALID')
    return {k: int(node.get(k)) for k in keys}


def anonymous_cases(xml):
    """Parse bounded UTF-8 pytest JUnit; strip all names, messages and properties.

    Only the flat pytest testsuite/testsuites dialect is supported. Structural
    ambiguity, nested outcomes and counter disagreement block serialization.
    """
    if type(xml) is not bytes or not 0 < len(xml) <= MAX_XML:
        raise PlatformRejected('SOURCE_PRODUCER_XML_BOUND')
    try:
        text = xml.decode('utf-8')
        if '\x00' in text or re.search(r'<!\s*(?:DOCTYPE|ENTITY)\b', text, re.I):
            raise PlatformRejected('SOURCE_PRODUCER_XML_UNSAFE')
        root = ET.fromstring(text)
    except (UnicodeError, ET.ParseError):
        raise PlatformRejected('SOURCE_PRODUCER_XML_INVALID') from None
    suites = [root] if root.tag == 'testsuite' else list(root) if root.tag == 'testsuites' else []
    if not 1 <= len(suites) <= 100 or any(s.tag != 'testsuite' for s in suites):
        raise PlatformRejected('SOURCE_PRODUCER_SUITE_SHAPE')
    rows, counts = [], dict.fromkeys(OUTCOMES, 0)
    for suite in suites:
        if any(c.tag not in {'testcase', 'properties', 'system-out', 'system-err'} for c in suite):
            raise PlatformRejected('SOURCE_PRODUCER_SUITE_CHILD')
        for child in suite:
            if child.tag in {'system-out', 'system-err'} and list(child):
                raise PlatformRejected('SOURCE_PRODUCER_SUITE_CHILD')
            if child.tag == 'properties' and any(p.tag != 'property' or list(p) for p in child):
                raise PlatformRejected('SOURCE_PRODUCER_PROPERTIES_INVALID')
        cases = [c for c in suite if c.tag == 'testcase']
        actual = dict.fromkeys(OUTCOMES, 0)
        for case in cases:
            if any(c.tag not in {'failure', 'error', 'skipped', 'properties', 'system-out', 'system-err'} for c in case):
                raise PlatformRejected('SOURCE_PRODUCER_CASE_CHILD')
            markers = [c.tag for c in case if c.tag in {'failure', 'error', 'skipped'}]
            # Hidden nested cases/outcomes cannot be silently counted as passes.
            if len(markers) > 1 or any(list(c) for c in case if c.tag != 'properties'):
                raise PlatformRejected('SOURCE_PRODUCER_OUTCOME_AMBIGUOUS')
            if any(p.tag != 'property' or list(p) for c in case if c.tag == 'properties' for p in c):
                raise PlatformRejected('SOURCE_PRODUCER_PROPERTIES_INVALID')
            outcome = {'failure':'failed', 'error':'errors', 'skipped':'skipped'}.get(
                markers[0] if markers else '', 'passed')
            actual[outcome] += 1
            rows.append(dict(ordinal=len(rows)+1, outcome=outcome))
            if len(rows) > 10000:
                raise PlatformRejected('SOURCE_PRODUCER_CASE_BOUND')
        if _counts(suite) != dict(tests=len(cases), failures=actual['failed'],
                                  errors=actual['errors'], skipped=actual['skipped']):
            raise PlatformRejected('SOURCE_PRODUCER_TOTALS_MISMATCH')
        for key in OUTCOMES:
            counts[key] += actual[key]
    if root.tag == 'testsuites' and any(k in root.attrib for k in ('tests','failures','errors','skipped')):
        if _counts(root) != dict(tests=len(rows), failures=counts['failed'],
                                errors=counts['errors'], skipped=counts['skipped']):
            raise PlatformRejected('SOURCE_PRODUCER_ROOT_TOTALS_MISMATCH')
    return counts, rows


def source_bundle(identity, *, xml, pytest_exit, expected_cases):
    """Serialize completed full-suite observations, with no acceptance flags.

    expected_cases is independently pinned by the host, never derived from the
    candidate XML. Matching counts are a consistency check, not full-suite proof.
    Exit/case inconsistencies and empty suites fail closed. Skips/failures remain
    non-PASS. Only the strict anonymous ZIP is returned; raw XML stays private.
    """
    if (type(identity) is not SourceRun or type(pytest_exit) is not int
            or pytest_exit not in {0, 1} or type(expected_cases) is not int
            or not 1 <= expected_cases <= 10000):
        raise PlatformRejected('SOURCE_PRODUCER_INPUT_INVALID')
    counts, rows = anonymous_cases(xml)
    if len(rows) != expected_cases:
        raise PlatformRejected('SOURCE_PRODUCER_SCOPE_COUNT_MISMATCH')
    failed = bool(counts['failed'] or counts['errors'])
    if (pytest_exit == 0) == failed:
        raise PlatformRejected('SOURCE_PRODUCER_EXIT_MISMATCH')
    test = 'FAIL' if failed else 'SKIPPED' if counts['skipped'] else 'PASS'
    receipt = dict(schema='romarr-platform-receipt-v1', platform=identity.platform,
        source_repo=SOURCE_REPO, source_sha=identity.source_sha, base_sha=identity.base_sha,
        controller_sha=identity.controller_sha, producer_repo=CONTROLLER_REPO,
        producer_sha=identity.controller_sha, workflow=identity.workflow,
        run_id=identity.run_id, attempt=identity.attempt, job_id=identity.job_id,
        scope='source-full', subject_sha256=None, counts=counts,
        dimensions=dict(build='NOT_APPLICABLE', startup='NOT_APPLICABLE',
            environment='PASS', test=test, collection='PASS',
            provenance='BLOCKED', freshness='NOT_TESTED'))
    files = {'receipt.json':canonical(receipt), 'cases.json':canonical(
        dict(schema='romarr-platform-cases-v1', cases=rows))}
    files['manifest.json'] = canonical(dict(schema='romarr-platform-manifest-v1',
        files={name:hashlib.sha256(raw).hexdigest() for name,raw in files.items()}))
    if any(len(raw) > MAX_MEMBER for raw in files.values()):
        raise PlatformRejected('SOURCE_PRODUCER_MEMBER_BOUND')
    out = io.BytesIO()
    with zipfile.ZipFile(out, 'w', compression=zipfile.ZIP_STORED) as archive:
        for name, raw in files.items():
            entry = zipfile.ZipInfo(name, date_time=(1980,1,1,0,0,0))
            entry.create_system = 3
            entry.external_attr = (stat.S_IFREG | 0o600) << 16
            archive.writestr(entry, raw)
    raw = out.getvalue()
    if len(raw) > MAX_ZIP:
        raise PlatformRejected('SOURCE_PRODUCER_ARCHIVE_BOUND')
    read_bundle(raw, hashlib.sha256(raw).hexdigest())
    return raw
