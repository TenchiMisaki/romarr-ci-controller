"""Private, fail-closed GitHub Actions artifact HTTP transport candidate.

No workflow dispatch, write method, credential persistence, or receipt acceptance.
The caller supplies a verified artifact ID and independent digest expectations.
No HTTP operation occurs on import. The storage host allowlist must be chosen
from a separately reviewed GitHub redirect target; it is never inferred from
untrusted Location metadata.
"""
from __future__ import annotations

from dataclasses import dataclass
import hashlib
import json
import re
import ssl
from urllib.parse import urlsplit
from urllib.request import (
    build_opener, HTTPSHandler, HTTPRedirectHandler, ProxyHandler, Request,
)
from urllib.error import HTTPError, URLError

import stage6_github_artifact_envelope as envelope

API = 'https://api.github.com'
VERSION = '2026-03-10'
MAX_METADATA = 8192
SHA = re.compile(r'[0-9a-f]{64}\Z')


@dataclass(frozen=True)
class FetchResult:
    state: str
    reason: str = ''
    metadata: dict | None = None
    archive: bytes = b''
    archive_sha256: str = ''
    test_accepted: bool = False
    publication_authorized: bool = False
    unattended_dispatch_enabled: bool = False


class _NoRedirect(HTTPRedirectHandler):
    def redirect_request(self, req, fp, code, msg, headers, newurl):
        """Never follow a redirect or transfer authorization automatically."""
        return None


def _opener():
    """TLS verification on; disable environment proxy and HTTP redirects."""
    return build_opener(ProxyHandler({}), HTTPSHandler(context=ssl.create_default_context()), _NoRedirect())


def _host_allowed(url: str, allowed: frozenset[str]) -> bool:
    """Require strict HTTPS URL, exact hostname allowlist, and no userinfo."""
    if type(url) is not str or len(url) > 4096 or any(ord(c) < 33 or ord(c) == 127 for c in url):
        return False
    try:
        u = urlsplit(url)
        return (u.scheme == 'https' and bool(u.hostname) and
                u.hostname in allowed and u.port in (None, 443) and
                not u.username and not u.password and not u.fragment and
                u.path.startswith('/') and bool(u.path) and
                u.netloc == u.hostname + (':443' if u.port == 443 else ''))
    except ValueError:
        return False


def _bounded(response, limit: int) -> bytes:
    """Read streams in chunks, refusing inaccurate and oversized bodies."""
    declared = response.headers.get('Content-Length')
    if declared is not None:
        if not declared.isascii() or not declared.isdecimal() or int(declared) > limit:
            raise ValueError('SIZE_INVALID')
    parts = []
    total = 0
    while True:
        data = response.read(min(4096, limit + 1 - total))
        if not isinstance(data, bytes):
            raise ValueError('BODY_INVALID')
        if not data:
            break
        total += len(data)
        if total > limit:
            raise ValueError('SIZE_INVALID')
        parts.append(data)
    if declared is not None and total != int(declared):
        raise ValueError('SIZE_INVALID')
    return b''.join(parts)


def _request(opener, url: str, token: str | None, *, max_bytes: int,
             accept: str, expected_status: int, require_location: bool = False):
    headers = {'Accept': accept, 'X-GitHub-Api-Version': VERSION,
               'User-Agent': 'romarr-stage6-private-v25'}
    if token:
        headers['Authorization'] = 'Bearer ' + token
    request = Request(url, headers=headers, method='GET')
    try:
        response = opener.open(request, timeout=10)
    except HTTPError as exc:
        # urllib deliberately raises HTTPError for a 302 blocked by our
        # redirect handler. Treat it as the response, not a retry signal.
        if exc.code != expected_status:
            exc.close()
            raise ValueError('HTTP_STATUS_UNEXPECTED') from None
        response = exc
    except (URLError, TimeoutError, OSError):
        raise ValueError('TRANSPORT_FAILED') from None
    try:
        if response.status != expected_status:
            raise ValueError('HTTP_STATUS_UNEXPECTED')
        if require_location:
            return response.headers.get('Location')
        return _bounded(response, max_bytes)
    finally:
        response.close()


def fetch_artifact(*, artifact_id: int, token: str,
                   expected_outer_sha256: str,
                   expected_run_id: int, expected_controller_sha: str,
                   permitted_storage_hosts: frozenset[str], opener=None) -> FetchResult:
    """Fetch one immutable expected artifact, without trusting its verdict.

    `permitted_storage_hosts` MUST be a verified exact-host configuration,
    never constructed from the received Location. No writes or retries.
    A fresh trusted provenance and inner-digest check is required after fetch.
    """
    if (type(artifact_id) is not int or artifact_id < 1 or
            type(expected_run_id) is not int or expected_run_id < 1 or
            type(expected_controller_sha) is not str or
            not re.fullmatch(r'[0-9a-f]{40}', expected_controller_sha) or
            type(expected_outer_sha256) is not str or
            not SHA.fullmatch(expected_outer_sha256) or
            type(token) is not str or not 1 <= len(token) <= 1024 or
            any(ord(c) < 33 or ord(c) > 126 for c in token) or
            type(permitted_storage_hosts) is not frozenset or
            not permitted_storage_hosts or any(
                type(h) is not str or not re.fullmatch(r'[a-z0-9.-]{1,253}', h)
                or h == 'api.github.com' for h in permitted_storage_hosts)):
        return FetchResult('BLOCKED', 'TRUSTED_INPUT_INVALID')
    opener = _opener() if opener is None else opener
    base = f'{API}/repos/{envelope.CONTROLLER}/actions/artifacts/{artifact_id}'
    try:
        metadata_bytes = _request(opener, base, token, max_bytes=MAX_METADATA,
                                  accept='application/vnd.github+json', expected_status=200)
        raw = json.loads(metadata_bytes)
        if (type(raw) is not dict or type(raw.get('id')) is not int or
                raw['id'] != artifact_id or raw.get('name') != envelope.ARTIFACT or
                raw.get('expired') is not False or
                raw.get('url') != base or raw.get('archive_download_url') != base + '/zip' or
                type(raw.get('workflow_run')) is not dict or
                raw['workflow_run'].get('id') != expected_run_id or
                raw['workflow_run'].get('head_sha') != expected_controller_sha or
                raw.get('digest') != 'sha256:' + expected_outer_sha256 or
                type(raw.get('size_in_bytes')) is not int or
                not 1 <= raw['size_in_bytes'] <= envelope.MAX_OUTER):
            return FetchResult('BLOCKED', 'METADATA_MISMATCH')
        location = _request(opener, base + '/zip', token, max_bytes=0,
                            accept='application/vnd.github+json', expected_status=302,
                            require_location=True)
        if not _host_allowed(location, permitted_storage_hosts):
            return FetchResult('BLOCKED', 'REDIRECT_NOT_ALLOWLISTED')
        archive = _request(opener, location, None, max_bytes=envelope.MAX_OUTER,
                           accept='application/octet-stream', expected_status=200)
        actual = hashlib.sha256(archive).hexdigest()
        if (len(archive) != raw['size_in_bytes'] or actual != expected_outer_sha256):
            return FetchResult('BLOCKED', 'DOWNLOADED_BYTES_MISMATCH')
        return FetchResult('DOWNLOADED_UNTRUSTED', metadata=raw,
                           archive=archive, archive_sha256=actual)
    except (ValueError, UnicodeError, json.JSONDecodeError) as exc:
        reason = str(exc)
        return FetchResult('BLOCKED', reason if reason in {
            'SIZE_INVALID', 'BODY_INVALID', 'HTTP_STATUS_UNEXPECTED',
            'TRANSPORT_FAILED'} else 'METADATA_OR_TRANSPORT_INVALID')


def fetch_and_verify(*, expected, verified_job_ids: tuple[int, int],
                     independent_inner_digest: str, **kwargs) -> FetchResult:
    """Combine untrusted download with the existing offline envelope verifier."""
    fetched = fetch_artifact(**kwargs)
    if fetched.state != 'DOWNLOADED_UNTRUSTED':
        return fetched
    result = envelope.verify_github_artifact(
        fetched.metadata, fetched.archive, expected, verified_job_ids,
        expected_artifact_id=kwargs['artifact_id'],
        independent_outer_digest=kwargs['expected_outer_sha256'],
        independent_inner_digest=independent_inner_digest)
    if result.state != 'GITHUB_ADVISORY_ENVELOPE_VERIFIED':
        return FetchResult('BLOCKED', 'ENVELOPE_' + result.reason)
    return FetchResult('ADVISORY_READBACK_VERIFIED', archive_sha256=fetched.archive_sha256)
