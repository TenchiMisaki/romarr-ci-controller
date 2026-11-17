"""Synthetic offline negative and positive cases for read-only HTTP boundary."""
import hashlib
import io
import json
from email.message import Message
from urllib.error import HTTPError, URLError

import pytest

from stage6_pr_identity_v32 import IdentityRejected
from stage6_pr_transport_v38 import (
    ReadOnlyGitHubTransport, _known_api_url, _storage_url, _bounded_response, _parse_json,
)

ROOT = 'https://api.github.com/repos/TenchiMisaki/romarr-ci-controller/actions/artifacts/14202822767/zip'
META = 'https://api.github.com/repos/TenchiMisaki/romarr-ci-controller/actions/runs/43817942953'
STORAGE = 'https://productionresultssa4.blob.core.windows.net/results/f.zip?sig=abc123'


class Response:
    def __init__(self, status, body=b'', headers=None):
        self.status = status
        self._reader = io.BytesIO(body)
        self.headers = Message()
        for k, v in (headers or {}).items():
            self.headers[k] = v
        self.closed = False
    def read(self, n=-1): return self._reader.read(n)
    def close(self): self.closed = True


class FakeOpener:
    def __init__(self, responses):
        self.responses = list(responses)
        self.requests = []
    def open(self, request, timeout):
        self.requests.append(request)
        r = self.responses.pop(0)
        if isinstance(r, BaseException): raise r
        return r


def make_response(body):
    return Response(200, body, {'Content-Length':str(len(body))})


def test_valid_metadata_only():
    fake = FakeOpener([make_response(b'{"ok":true}')])
    assert ReadOnlyGitHubTransport('fake-readonly-token', opener=fake).get_json(META) == {'ok':True}
    assert fake.requests[0].get_method() == 'GET'
    assert fake.requests[0].get_header('Authorization') == 'Bearer fake-readonly-token'


def test_storage_auth_separation_hash_and_exact_url():
    content = b'fixed-public-advisory-zip-bytes'
    fake = FakeOpener([Response(302, headers={'Location':STORAGE}), make_response(content)])
    got = ReadOnlyGitHubTransport('fake-readonly-token', opener=fake).get_artifact_bytes(ROOT, 65536, hashlib.sha256(content).hexdigest())
    assert got == content
    assert len(fake.requests) == 2
    assert fake.requests[0].get_header('Authorization') == 'Bearer fake-readonly-token'
    assert fake.requests[1].get_header('Authorization') is None
    assert fake.requests[1].full_url == STORAGE


@pytest.mark.parametrize('url', [
    'http://api.github.com/repos/TenchiMisaki/romarr/pulls/2',
    'https://api.github.com/repos/Other/romarr/pulls/2',
    'https://api.github.com/repos/TenchiMisaki/romarr/pulls/2?token=a',
    'https://api.github.com/repos/TenchiMisaki/romarr/pulls/0',
    'https://api.github.com/repos/TenchiMisaki/romarr/pulls/2/commits',
    'https://api.github.com/repos/TenchiMisaki/romarr/branches/secret',
    'https://api.github.com/repos/TenchiMisaki/romarr-ci-controller/actions/artifacts/2/zip?x=1',
    'https://api.github.com/repos/TenchiMisaki/romarr-ci-controller/actions/runs/2/jobs?per_page=100&page=2',
])
def test_api_rejects_unknown_routes(url):
    assert not _known_api_url(url)


@pytest.mark.parametrize('url', [
    'http://productionresultssa4.blob.core.windows.net/x',
    'https://storage.googleapis.com/x',
    'https://fake.blob.core.windows.net.attacker.invalid/x',
    'https://user:secret@abc.blob.core.windows.net/x',
    'https://abc.blob.core.windows.net:8443/x',
    'https://abc.blob.core.windows.net/x#fragment',
    'https://abc.blob.core.windows.net',
    'https://abc.blob.core.windows.net/x\nAuthorization: Bearer fake',
])
def test_redirect_rejected(url):
    assert not _storage_url(url)


def test_rotating_storage_host_is_syntactically_accepted():
    assert _storage_url(STORAGE)


def test_wrong_redirect_fails_before_storage_get():
    fake = FakeOpener([Response(302, headers={'Location':'https://attacker.invalid/zip'})])
    with pytest.raises(IdentityRejected):
        ReadOnlyGitHubTransport('fake-token', opener=fake).get_artifact_bytes(ROOT, 65536, '1'*64)
    assert len(fake.requests) == 1


def test_missing_redirect_fails_closed():
    fake = FakeOpener([Response(302)])
    with pytest.raises(IdentityRejected):
        ReadOnlyGitHubTransport('fake-token', opener=fake).get_artifact_bytes(ROOT, 65536, '1'*64)


def test_archive_digest_mismatch_fails_closed():
    fake = FakeOpener([Response(302, headers={'Location':STORAGE}),make_response(b'wrong')])
    with pytest.raises(IdentityRejected):
        ReadOnlyGitHubTransport('fake-token', opener=fake).get_artifact_bytes(ROOT, 65536, '1'*64)


def test_archive_too_large_fails_closed():
    fake = FakeOpener([Response(302, headers={'Location':STORAGE}),make_response(b'x'*200)])
    with pytest.raises(IdentityRejected):
        ReadOnlyGitHubTransport('fake-token', opener=fake).get_artifact_bytes(ROOT, 100, '1'*64)


def test_json_rejects_duplicate_keys():
    with pytest.raises(IdentityRejected): _parse_json(b'{"x":1,"x":2}')


@pytest.mark.parametrize('input', [b'[]',b'not json',b'{"a":',b'{"a":NaN}'])
def test_metadata_invalid_json_rejected(input):
    with pytest.raises(IdentityRejected): _parse_json(input)


def test_declared_length_incorrect_rejected():
    with pytest.raises(IdentityRejected):
        _bounded_response(Response(200,b'abc',{'Content-Length':'10'}), 100)


def test_transport_exception_does_not_fabricate_success():
    fake = FakeOpener([URLError('offline')])
    with pytest.raises(IdentityRejected):
        ReadOnlyGitHubTransport('fake-token', opener=fake).get_json(META)


def test_artifact_wrong_endpoint_rejected_before_network():
    fake = FakeOpener([])
    with pytest.raises(IdentityRejected):
        ReadOnlyGitHubTransport('fake-token', opener=fake).get_artifact_bytes(META,65536,'1'*64)
    assert fake.requests == []


def test_ordered_collector_v37_v38_transport_integration_offline():
    from stage6_pr_collector_v37 import collect_ordered
    from test_stage6_pr_collector_v37 import harness
    evidence,_,_,_,ordered = harness()
    replies = []
    for index, (url, data) in enumerate(ordered):
        if index == 7:
            replies += [Response(302, headers={'Location':STORAGE}), make_response(data)]
        else:
            content = json.dumps(data, separators=(',', ':'), allow_nan=False).encode('utf-8')
            replies.append(make_response(content))
    fake = FakeOpener(replies)
    transport = ReadOnlyGitHubTransport('fake-readonly-token', opener=fake)
    result = collect_ordered(evidence=evidence, get_json=transport.get_json,
                             get_artifact_bytes=transport.get_artifact_bytes)
    assert result.state == 'ADVISORY_COLLECTED_NOT_TEST_ACCEPTED'
    assert result.test_accepted is False
    assert len(fake.requests) == 11
    assert [r.full_url for r in fake.requests] == [
        *(x[0] for x in ordered[:7]),ordered[7][0],STORAGE,
        ordered[8][0],ordered[9][0]]
    assert all(req.get_header('Authorization') == 'Bearer fake-readonly-token'
               for req in fake.requests if req.full_url != STORAGE)
    assert fake.requests[8].get_header('Authorization') is None


def test_ordered_collector_v37_v38_transport_rejects_download_corruption_offline():
    from stage6_pr_collector_v37 import collect_ordered
    from test_stage6_pr_collector_v37 import harness
    evidence,_,_,_,ordered = harness()
    replies=[]
    for index, (_, data) in enumerate(ordered):
        if index == 7:
            replies += [Response(302, headers={'Location':STORAGE}), make_response(b'altered')]
        else:
            replies.append(make_response(json.dumps(data, separators=(',', ':'),allow_nan=False).encode()))
    fake = FakeOpener(replies)
    t = ReadOnlyGitHubTransport('fake-readonly-token', opener=fake)
    result = collect_ordered(evidence=evidence, get_json=t.get_json,
                             get_artifact_bytes=t.get_artifact_bytes)
    assert result.state == 'BLOCKED'
    assert not result.test_accepted
    assert len(fake.requests) == 9  # no final freshness reads after corrupt bytes
