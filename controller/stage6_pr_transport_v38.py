"""Read-only, fail-closed transport for the PRIVATE Stage 6 offline candidate.

The caller owns the independently verified expected run/PR/artifact identities.
Only fixed public GitHub REST endpoints may be requested. The authenticated
GitHub API's artifact ZIP endpoint may return one 302 redirect; no GitHub token
is ever forwarded to the isolated storage request. There are no write verbs,
implicit redirects, ambient proxies, disk writes, or retries.

This is NOT a test receipt or an accepted live workflow implementation.
"""
from __future__ import annotations

import hashlib
import json
import re
import ssl
from urllib.error import HTTPError, URLError
from urllib.parse import urlsplit
from urllib.request import (
    HTTPSHandler, HTTPRedirectHandler, ProxyHandler, Request, build_opener,
)

from stage6_pr_identity_v32 import IdentityRejected

_API = 'https://api.github.com'
_REPO = 'TenchiMisaki/romarr'
_CONTROLLER = 'TenchiMisaki/romarr-ci-controller'
_API_VERSION = '2026-03-10'
_MAX_META = 1024 * 1024  # jobs collection may include many bounded steps
_MAX_ARCHIVE = 65536
_SHA = re.compile(r'[0-9a-f]{64}\Z')
_RUN = re.compile(r'[1-9][0-9]{0,18}\Z')
_BLOB_HOST = re.compile(r'[a-z0-9]{3,24}\.blob\.core\.windows\.net\Z')


class _NoRedirect(HTTPRedirectHandler):
    def redirect_request(self, request, fp, code, msg, headers, newurl):
        return None


def _new_opener():
    """Disable inherited HTTP proxies and require certificate-validating TLS."""
    return build_opener(ProxyHandler({}), HTTPSHandler(context=ssl.create_default_context()), _NoRedirect())


def _valid_token(token):
    return (type(token) is str and 1 <= len(token) <= 1024 and
            all(33 <= ord(x) <= 126 for x in token))


def _known_api_url(url: str) -> bool:
    """Allow precisely one PR, branch, run, jobs, artifact, or artifact ZIP API."""
    if type(url) is not str:
        return False
    prefix = re.escape(_API)
    source = re.escape(_REPO)
    controller = re.escape(_CONTROLLER)
    patterns = (
        rf'{prefix}/repos/{source}/pulls/[1-9][0-9]{{0,6}}',
        rf'{prefix}/repos/{source}/branches/main',
        rf'{prefix}/repos/{controller}/actions/runs/[1-9][0-9]{{0,18}}',
        rf'{prefix}/repos/{controller}/actions/runs/[1-9][0-9]{{0,18}}/jobs\?per_page=100',
        rf'{prefix}/repos/{controller}/actions/artifacts/[1-9][0-9]{{0,18}}',
        rf'{prefix}/repos/{controller}/actions/artifacts/[1-9][0-9]{{0,18}}/zip',
    )
    return any(re.fullmatch(p, url) for p in patterns)


def _storage_url(url):
    if type(url) is not str or not 1 <= len(url) <= 4096 or any(ord(c) < 33 or ord(c) == 127 for c in url):
        return False
    try:
        p = urlsplit(url)
        host = p.hostname
        return (p.scheme == 'https' and type(host) is str and
                _BLOB_HOST.fullmatch(host) is not None and
                p.port in (None, 443) and not p.username and not p.password and
                p.netloc == host + (':443' if p.port == 443 else '') and
                p.path.startswith('/') and not p.fragment)
    except ValueError:
        return False


def _bounded_response(response, limit: int):
    if type(limit) is not int or limit < 1:
        raise IdentityRejected('BAD_LIMIT')
    length = response.headers.get('Content-Length')
    if length is not None and (not length.isascii() or not length.isdecimal() or int(length) > limit):
        raise IdentityRejected('BODY_LENGTH_INVALID')
    parts = []
    total = 0
    while True:
        block = response.read(min(8192, limit - total + 1))
        if type(block) is not bytes:
            raise IdentityRejected('BODY_INVALID')
        if not block:
            break
        total += len(block)
        if total > limit:
            raise IdentityRejected('BODY_TOO_LARGE')
        parts.append(block)
    if length is not None and total != int(length):
        raise IdentityRejected('BODY_LENGTH_MISMATCH')
    return b''.join(parts)


def _get(opener, url: str, token: str | None, *, expected_status: int, limit: int, accept: str):
    headers = {
        'Accept': accept, 'User-Agent': 'romarr-stage6-offline-v38',
        'X-GitHub-Api-Version': _API_VERSION,
    }
    if token is not None:
        headers['Authorization'] = 'Bearer ' + token
    request = Request(url, headers=headers, method='GET')
    try:
        response = opener.open(request, timeout=12)
    except HTTPError as exc:
        # Redirect-blocking handlers raise HTTPError(302), which may be expected.
        if exc.code != expected_status:
            exc.close()
            raise IdentityRejected('HTTP_STATUS_INVALID') from None
        response = exc
    except (URLError, TimeoutError, OSError):
        raise IdentityRejected('HTTP_TRANSPORT_FAILED') from None
    try:
        if response.status != expected_status:
            raise IdentityRejected('HTTP_STATUS_INVALID')
        if expected_status == 302:
            location = response.headers.get('Location')
            if not _storage_url(location):
                raise IdentityRejected('ARTIFACT_REDIRECT_INVALID')
            return location
        return _bounded_response(response, limit)
    finally:
        response.close()


def _parse_json(raw):
    def no_duplicates(items):
        value = {}
        for key, val in items:
            if key in value:
                raise IdentityRejected('DUPLICATE_JSON_KEY')
            value[key] = val
        return value
    try:
        result = json.loads(raw, object_pairs_hook=no_duplicates,
                            parse_constant=lambda value: (_ for _ in ()).throw(IdentityRejected('NONFINITE_JSON')))
    except (ValueError, UnicodeDecodeError, TypeError):
        raise IdentityRejected('JSON_UNVERIFIED') from None
    if type(result) is not dict:
        raise IdentityRejected('JSON_SHAPE_INVALID')
    return result


class ReadOnlyGitHubTransport:
    """Bind strict API/redirect policy to two callbacks consumed by v37.

    Supply one independently obtained, ephemeral, read-only GitHub token.
    The injected opener exists for offline unit testing; production callers
    must use the default opener and verify runner/token provenance separately.
    """
    def __init__(self, token: str, *, opener=None):
        if not _valid_token(token):
            raise IdentityRejected('GITHUB_TOKEN_INVALID')
        self._token = token
        self._opener = opener if opener is not None else _new_opener()

    def get_json(self, url: str) -> object:
        if not _known_api_url(url) or url.endswith('/zip'):
            raise IdentityRejected('API_URL_NOT_ALLOWLISTED')
        raw = _get(self._opener, url, self._token, expected_status=200,
                   limit=_MAX_META, accept='application/vnd.github+json')
        return _parse_json(raw)

    def get_artifact_bytes(self, url: str, max_bytes: int, expected_sha256: str) -> bytes:
        if (not _known_api_url(url) or not url.endswith('/zip') or
                type(max_bytes) is not int or not 1 <= max_bytes <= _MAX_ARCHIVE or
                type(expected_sha256) is not str or not _SHA.fullmatch(expected_sha256)):
            raise IdentityRejected('ARTIFACT_EXPECTATION_INVALID')
        location = _get(self._opener, url, self._token, expected_status=302,
                        limit=1, accept='application/vnd.github+json')
        # IMPORTANT: the signed storage URL is only fetched with NO token.
        raw = _get(self._opener, location, None, expected_status=200,
                   limit=max_bytes, accept='application/octet-stream')
        if len(raw) == 0 or hashlib.sha256(raw).hexdigest() != expected_sha256:
            raise IdentityRejected('ARTIFACT_DIGEST_MISMATCH')
        return raw


__all__ = ['ReadOnlyGitHubTransport']
