"""Host-only JUnit sanitizer for Stage 6 manual PR advisory; never executes source code.

Test source runs in a separate credential-free offline container, and can only
write a private JUnit XML to an isolated mount. This trusted host process parses
that output and writes two fixed, anonymous, canonical advisory files.
"""
from __future__ import annotations
import hashlib
import json
import os
from pathlib import Path
import re
import stat
import xml.etree.ElementTree as ET
from stage6_pr_archive_v34 import SCHEMA

SHA = re.compile(r'[0-9a-f]{40}\Z')
DECIMAL = re.compile(r'[1-9][0-9]{0,18}\Z')

class SourceBlocked(ValueError):
    """Do not publish when source evidence is invalid."""


def _canonical(obj):
    return (json.dumps(obj, sort_keys=True, separators=(',', ':'),
                       ensure_ascii=True, allow_nan=False) + '\n').encode('ascii')


def sanitize_junit(xml: bytes, *, run_id: int, head_sha: str, base_sha: str,
                   pytest_exit: int) -> tuple[bytes, bytes]:
    """Parse strict JUnit, reject skips/errors/structural ambiguity, output anonymous bytes."""
    if (type(xml) is not bytes or not 0 < len(xml) <= 500_000
            or type(run_id) is not int or run_id < 1
            or type(head_sha) is not str or SHA.fullmatch(head_sha) is None
            or type(base_sha) is not str or SHA.fullmatch(base_sha) is None
            or type(pytest_exit) is not int or pytest_exit != 0
            or re.search(rb'<!\s*(?:DOCTYPE|ENTITY)\b', xml, flags=re.I)):
        raise SourceBlocked('INPUT_INVALID')
    try:
        document = ET.fromstring(xml)
    except ET.ParseError as exc:
        raise SourceBlocked('XML_INVALID') from exc
    if document.tag == 'testsuite':
        suites = [document]
    elif document.tag == 'testsuites':
        suites = list(document)
    else:
        raise SourceBlocked('SUITE_SHAPE_INVALID')
    if not suites or len(suites) > 20:
        raise SourceBlocked('SUITE_COUNT_INVALID')
    count = 0
    for suite in suites:
        if suite.tag != 'testsuite':
            raise SourceBlocked('SUITE_SHAPE_INVALID')
        cases = [c for c in suite if c.tag == 'testcase']
        if any(c.tag not in ('testcase', 'properties', 'system-out', 'system-err') for c in suite):
            raise SourceBlocked('SUITE_CHILD_INVALID')
        try:
            totals = {k: int(suite.attrib[k]) for k in ('tests', 'failures', 'errors', 'skipped')}
        except (ValueError, KeyError) as exc:
            raise SourceBlocked('TOTALS_INVALID') from exc
        if (totals != {'tests': len(cases), 'failures': 0, 'errors': 0, 'skipped': 0}
                or len(cases) < 1 or count + len(cases) > 256):
            raise SourceBlocked('TOTALS_MISMATCH_OR_NONPASS')
        if any(sub.tag in ('failure','error','skipped') for c in cases for sub in c):
            raise SourceBlocked('CASE_NONPASS')
        count += len(cases)
    record = {'schema': SCHEMA, 'run_id': run_id, 'head_sha': head_sha,
              'base_sha': base_sha, 'passing_cases': count, 'pytest_exit': 0,
              'test_accepted': False, 'publication_authorized': False,
              'unattended_dispatch_enabled': False}
    advisory = _canonical(record)
    manifest = _canonical({'schema': SCHEMA, 'files': {'advisory.json': {
        'sha256': hashlib.sha256(advisory).hexdigest(), 'bytes': len(advisory)}}})
    return advisory, manifest


def _private_file(root: Path) -> bytes:
    if root.is_symlink() or not root.is_dir():
        raise SourceBlocked('RESULT_DIR_INVALID')
    f = root / 'private.xml'
    if f.is_symlink() or not f.is_file():
        raise SourceBlocked('RESULT_FILE_INVALID')
    mode = f.lstat()
    if (not stat.S_ISREG(mode.st_mode) or mode.st_nlink != 1
            or mode.st_mode & 0o077 or not 0 < mode.st_size <= 500_000):
        raise SourceBlocked('RESULT_FILE_UNSAFE')
    return f.read_bytes()


def main():
    """Entrypoint for the source job's trusted host-side sanitizer."""
    env = os.environ
    if (type(env.get('GITHUB_RUN_ID')) is not str
            or not DECIMAL.fullmatch(env['GITHUB_RUN_ID'])
            or env.get('RAW_PYTEST_EXIT') != '0'):
        raise SystemExit('BLOCKED: source result identity/exit invalid')
    try:
        raw = _private_file(Path(env['RESULT_DIR']))
        advisory, manifest = sanitize_junit(raw, run_id=int(env['GITHUB_RUN_ID']),
            head_sha=env['EXPECTED_PR_HEAD_SHA'], base_sha=env['EXPECTED_PR_BASE_SHA'],
            pytest_exit=0)
        target = Path(env['HANDOFF_DIR'])
        if target.is_symlink() or not target.is_dir() or list(target.iterdir()):
            raise SourceBlocked('HANDOFF_DIR_UNSAFE')
        for name, data in (('advisory.json', advisory), ('manifest.json', manifest)):
            f = target / name
            with f.open('xb') as out:
                out.write(data)
            f.chmod(0o600)
    except (KeyError, OSError, ValueError, SourceBlocked):
        raise SystemExit('BLOCKED: safe anonymous source evidence unavailable') from None
    print('SOURCE_ADVISORY_GENERATED_NO_TEST_ACCEPTANCE')


if __name__ == '__main__':
    main()
