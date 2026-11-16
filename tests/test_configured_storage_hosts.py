"""Stage 6 GitHub-hosted artifact redirect safety checks (offline unittest).

The documented *.blob.core.windows.net family rotates storage-account names.
This must not weaken token separation, provenance, digest or archive checks.
"""
import hashlib
import io
import json
import sys
import unittest
import zipfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'controller'))
import stage6_manual_readback_v28 as m  # noqa: E402
import stage6_artifact_http as transport  # noqa: E402

A = 'productionresultssa32.blob.core.windows.net'
B = 'productionresultssa31.blob.core.windows.net'
C = 'productionresultssa4.blob.core.windows.net'
TEST_RUN = 3000123
TEST_ARTIFACT = 5000123
TEST_HEAD = 'a' * 40
TEST_TOKEN = 'offline-dummy-token-not-real'


def canon(data):
    return (json.dumps(data, sort_keys=True, separators=(',', ':'), allow_nan=False) + '\n').encode('ascii')


def advisory_zip():
    record = {'schema': m.SCHEMA, 'run_id': TEST_RUN,
              'source_sha': m.EXPECTED_SOURCE, 'passing_cases': 3,
              'pytest_exit': 0, 'test_accepted': False,
              'publication_authorized': False, 'unattended_dispatch_enabled': False}
    adv = canon(record)
    manifest = canon({'schema': m.SCHEMA, 'files': {
        'advisory.json': {'sha256': hashlib.sha256(adv).hexdigest(), 'bytes': len(adv)}}})
    stream = io.BytesIO()
    with zipfile.ZipFile(stream, mode='w', compression=zipfile.ZIP_STORED) as z:
        z.writestr('advisory.json', adv)
        z.writestr('manifest.json', manifest)
    return stream.getvalue()


class FakeResponse:
    def __init__(self, status=200, data=b'', location=None):
        self.status = status
        self.headers = {'Content-Length': str(len(data))}
        if location is not None:
            self.headers['Location'] = location
        self.body = io.BytesIO(data)
    def read(self, n=-1):
        return self.body.read(n)
    def close(self):
        self.body.close()


class FakeOpener:
    def __init__(self, archive, redirect):
        self.archive = archive
        self.redirect = redirect
        self.calls = []
    def open(self, request, timeout):
        self.calls.append((request.full_url, request.headers.get('Authorization')))
        if request.full_url == f'https://api.github.com/repos/TenchiMisaki/romarr-ci-controller/actions/artifacts/{TEST_ARTIFACT}/zip':
            return FakeResponse(302, location=self.redirect)
        if request.full_url == self.redirect:
            return FakeResponse(200, data=self.archive)
        raise AssertionError('unexpected URL')


def attested_metadata(archive):
    digest = hashlib.sha256(archive).hexdigest()
    base = f'https://api.github.com/repos/TenchiMisaki/romarr-ci-controller/actions/artifacts/{TEST_ARTIFACT}'
    run = {'id': TEST_RUN, 'run_attempt': 1, 'head_sha': TEST_HEAD,
           'event': 'workflow_dispatch', 'status': 'in_progress', 'conclusion': None,
           'repository': {'full_name': 'TenchiMisaki/romarr-ci-controller'}}
    source_steps = [{'name': 'Set up job', 'conclusion': 'success'},
                    {'name': 'Fetch immutable public ROMarr source and test without credentials', 'conclusion': 'success'},
                    {'name': 'Upload only sanitized advisory and manifest', 'conclusion': 'success'}]
    jobs = {'total_count': 2, 'jobs': [
        {'id': 44, 'name': 'Run one real ROMarr test file in offline container', 'run_id': TEST_RUN,
         'run_attempt': 1, 'head_sha': TEST_HEAD, 'status': 'completed', 'conclusion': 'success', 'steps': source_steps},
        {'id': 45, 'name': 'Separate runner validates advisory source outcome', 'run_id': TEST_RUN,
         'run_attempt': 1, 'head_sha': TEST_HEAD, 'status': 'in_progress', 'conclusion': None,
         'steps': [{'name': 'Set up job', 'conclusion': 'success'}]}
    ]}
    artifact = {'id': TEST_ARTIFACT, 'name': 'romarr-stage6-v26-advisory', 'expired': False,
                'size_in_bytes': len(archive), 'digest': 'sha256:' + digest,
                'url': base, 'archive_download_url': base + '/zip',
                'workflow_run': {'id': TEST_RUN, 'head_sha': TEST_HEAD}}
    return run, jobs, artifact


def invoke(redirect, digest=None, mutation=None):
    archive = advisory_zip()
    triple = list(attested_metadata(archive))
    if mutation:
        mutation(triple)
    opener = FakeOpener(archive, redirect)
    expected = digest if digest is not None else hashlib.sha256(archive).hexdigest()
    result = m.run(run_id=TEST_RUN, run_attempt=1, controller_sha=TEST_HEAD,
                   artifact_id=TEST_ARTIFACT, producer_digest=expected, token=TEST_TOKEN,
                   producer_sha=m.EXPECTED_SOURCE, producer_cases='PPP',
                   producer_exit='0', producer_state='success', opener=opener,
                   fetch_snapshots=lambda **_: triple)
    return result, opener


class StorageDomainTests(unittest.TestCase):
    def test_allowed_hosts_rotate(self):
        for host in (A, B, C, 'abc.blob.core.windows.net',
                     'a' * 24 + '.blob.core.windows.net'):
            with self.subTest(host=host):
                self.assertTrue(m.github_artifact_redirect_allowed('https://' + host + '/download?sig=synthetic'))

    def test_syntactically_allowed_urls(self):
        for url in ('https://' + A + '/download',
                    'https://' + B + ':443/download?signature=synthetic',
                    'https://' + C + '/download?sig=%2F'):
            with self.subTest(url=url):
                self.assertTrue(m.github_artifact_redirect_allowed(url))

    def test_reject_unapproved_urls(self):
        bad = [
            None, b'https://'+A.encode()+b'/a', '',
            'http://'+A+'/file', 'ftp://'+A+'/file',
            'https://'+A+'.attacker.invalid/file',
            'https://'+A.rstrip('net')+'nett/file',
            'https://'+A+'/file#fragment',
            'https://attacker.invalid@'+A+'/file',
            'https://user:pass@'+A+'/file',
            'https://'+A+':444/file',
            'https://'+A+'/file\n',
            'https://'+A+'/file\t',
            'https://'+A+'/file\r',
            'https://'+A+'@attacker.invalid/file',
            'https://'+A+'/file#',
            'https://a.blob.core.windows.net/file',
            'https://ab.blob.core.windows.net/file',
            'https://' + 'a'*25 + '.blob.core.windows.net/file',
            'https://ab-c.blob.core.windows.net/file',
            'https://ABCD.blob.core.windows.net/file',
            'https://'+A+'.evil/file',
            'https://'+A+'./file',
            'https://'+A.replace('.blob.', '.blob.evil.')+'/file',
            'https://'+A+'/file\x00',
            'https://'+A+'/file\x7f',
            'https://'+A+'/file ' + 'a'*4100,
            'https://[::1]/file',
            'https://api.github.com/file',
            '//'+A+'/file',
            'https://'+A+':bad/file',
        ]
        # Empty URL fragment marker is allowed by the shared transport helper;
        # it does not carry a fragment value and cannot redirect away.
        bad.remove('https://'+A+'/file#')
        # Uppercase host canonicalizes in urlsplit(), but strict transport rejects
        # noncanonical netloc. Confirm independently rather than normalizing.
        for index, url in enumerate(bad):
            with self.subTest(i=index):
                self.assertFalse(m.github_artifact_redirect_allowed(url))

    def test_shared_exact_host_helper_is_unchanged(self):
        self.assertTrue(transport._host_allowed('https://'+A+'/file', frozenset({A})))
        self.assertFalse(transport._host_allowed('https://'+C+'/file', frozenset({A})))

    def test_integrated_rotating_host_token_separation_and_digest(self):
        for host in (A, B, C):
            with self.subTest(host=host):
                result, opener = invoke('https://'+host+'/download?sig=synthetic')
                self.assertEqual(result.state, 'ADVISORY_BYTES_VERIFIED')
                self.assertEqual(result.passing_cases, 3)
                self.assertFalse(result.test_accepted)
                self.assertFalse(result.publication_authorized)
                self.assertFalse(result.unattended_dispatch_enabled)
                self.assertEqual(len(opener.calls), 2)
                self.assertTrue(opener.calls[0][0].startswith('https://api.github.com'))
                self.assertEqual(opener.calls[0][1], 'Bearer '+TEST_TOKEN)
                self.assertEqual(opener.calls[1][1], None)

    def test_integrated_invalid_redirect_stops_before_storage(self):
        for url in ('https://attacker.invalid/file', 'https://'+C+'.evil.invalid/file',
                    'http://'+C+'/file', 'https://user@'+C+'/file'):
            with self.subTest(url=url):
                result, opener = invoke(url)
                self.assertEqual(result.reason, 'REDIRECT_NOT_ALLOWLISTED')
                self.assertEqual(len(opener.calls), 1)

    def test_integrated_digest_mismatch_rejected_before_network(self):
        result, opener = invoke('https://'+C+'/file', digest='0'*64)
        self.assertEqual(result.state, 'BLOCKED')
        self.assertEqual(len(opener.calls), 0)

    def test_integrated_provenance_mismatch_rejected_before_network(self):
        result, opener = invoke('https://'+C+'/file', mutation=lambda x: x[0].update({'event': 'push'}))
        self.assertEqual(result.state, 'BLOCKED')
        self.assertEqual(len(opener.calls), 0)


if __name__ == '__main__':
    unittest.main()
