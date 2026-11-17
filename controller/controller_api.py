"""Dormant credential-isolated API adapters for the Stage 6-8 coordinator.

No token loading, service, workflow, scheduler or privileged entrypoint. Each
role receives its own least-privilege credential from a separately accepted
trusted host. Selected ROMarr code never runs in this process.
"""
from __future__ import annotations

import json
import re
import time
from urllib.error import HTTPError, URLError
from urllib.request import HTTPRedirectHandler, Request, build_opener

from controller_cycle import WORKFLOW
from durable_state import MAX_BYTES, PREFIX, STATE_REF, StateBlocked
from stage6_pr_identity_v32 import CONTROLLER_REPO, SOURCE_REPO, SHA
from watch import claim_name, legacy_claim_name


class NoRedirect(HTTPRedirectHandler):
    """Never send a credential to a redirect destination."""

    def redirect_request(self, req, fp, code, msg, headers, newurl):
        """Reject all API redirects, including same-host redirects."""
        return None


class RestrictedAPI:
    """Role-restricted, bounded JSON transport; GET retries only.

    progress receives fixed retry metadata, never payload, URL, token or server
    exception text. Authentication/authorization/shape/identity errors are not
    retried. The default has normal TLS verification and no proxy override.
    """

    def __init__(self, token, *, role='read', opener=None, sleep=time.sleep, progress=None):
        if type(token) is not str or not token or token != token.strip() or role not in {'read', 'state', 'dispatch', 'owner'}:
            raise StateBlocked('API_CREDENTIAL_OR_ROLE_INVALID')
        self._token, self.role = token, role
        self.opener = opener or build_opener(NoRedirect()).open
        self.sleep, self.progress = sleep, progress or (lambda info: None)

    def _allowed(self, method, path):
        """Match complete paths; arbitrary URLs and repository input are rejected."""
        if type(path) is not str or method not in {'GET', 'POST', 'PATCH'}:
            return False
        if self.role == 'owner':
            return method == 'GET' and path in {'user', PREFIX.rstrip('/')}
        if method == 'GET':
            if path == PREFIX.rstrip('/'):
                return True
            if path in {f'repos/{SOURCE_REPO}/branches/main', PREFIX + 'git/ref/' + STATE_REF}:
                return True
            if re.fullmatch(re.escape(f'repos/{SOURCE_REPO}/pulls/') + r'[1-9][0-9]{0,5}', path):
                return True
            if re.fullmatch(re.escape(PREFIX) + r'git/(?:commits|trees|blobs)/[0-9a-f]{40}', path):
                return True
            if re.fullmatch(re.escape(PREFIX) + r'actions/runs/[1-9][0-9]{0,18}', path):
                return True
            if re.fullmatch(re.escape(PREFIX) + r'git/ref/tags/controller-revision-[0-9a-f]{40}', path):
                return True
            return bool(re.fullmatch(re.escape(PREFIX) + r'git/matching-refs/tags/romarr-ci-v[12]/pr-[1-9][0-9]{0,5}[-a-z0-9]+', path))
        if self.role == 'state':
            return (method == 'POST' and path in {PREFIX + 'git/' + x for x in ('blobs', 'trees', 'commits')}
                    or method == 'PATCH' and path == PREFIX + 'git/refs/' + STATE_REF)
        return (self.role == 'dispatch' and method == 'POST'
                and path == PREFIX + 'actions/workflows/' + WORKFLOW.rsplit('/', 1)[1] + '/dispatches')

    def request(self, method, path, body=None):
        """Perform bounded reads or exactly one write, with sanitized failures."""
        if not self._allowed(method, path) or method == 'GET' and body is not None:
            raise StateBlocked('API_TARGET_OR_METHOD_REJECTED')
        raw = None if body is None else json.dumps(body, allow_nan=False, separators=(',', ':')).encode()
        if raw is not None and len(raw) > MAX_BYTES * 2:
            raise StateBlocked('API_REQUEST_TOO_LARGE')
        req = Request('https://api.github.com/' + path, data=raw, method=method, headers={
            'Authorization': 'Bearer ' + self._token, 'Accept': 'application/vnd.github+json',
            'Content-Type': 'application/json', 'X-GitHub-Api-Version': '2026-03-10',
            'User-Agent': 'romarr-controller-candidate'})
        started = time.monotonic()
        for attempt in range(1, 4 if method == 'GET' else 2):
            try:
                with self.opener(req, timeout=15) as response:
                    expected = 200 if method in {'GET', 'PATCH'} or path.endswith('/dispatches') else 201
                    if response.status != expected:
                        raise StateBlocked('API_STATUS_UNVERIFIED')
                    payload = response.read(MAX_BYTES * 2 + 1)
                    if len(payload) > MAX_BYTES * 2:
                        raise StateBlocked('API_RESPONSE_TOO_LARGE')
                    try:
                        return json.loads(payload)
                    except (ValueError, UnicodeError):
                        raise StateBlocked('API_JSON_INVALID') from None
            except HTTPError as exc:
                transient = exc.code in {408, 429, 500, 502, 503, 504}
                exc.close()
                if method != 'GET' or not transient or attempt == 3:
                    raise StateBlocked('API_HTTP_FAILURE') from None
            except (URLError, TimeoutError, ConnectionError, OSError):
                if method != 'GET' or attempt == 3:
                    raise StateBlocked('API_TRANSPORT_UNCERTAIN') from None
            interval = 2 * attempt
            self.progress(dict(state='TRANSIENT_READ_RETRY', attempt=attempt, limit=3,
                               interval=interval, elapsed=round(time.monotonic()-started, 2)))
            self.sleep(interval)
        raise StateBlocked('API_READ_EXHAUSTED')


class GitHubPorts:
    """Connect the coordinator to explicit read/dispatch/owner API roles.

    State writer credentials stay in GitHubState. Dispatch requires a separately
    provisioned lightweight immutable revision tag verified before and after POST.
    Tags, state storage and credentials are never provisioned here.
    """

    def __init__(self, *, reader, dispatcher, owner):
        self.reader, self.dispatcher, self.owner_api = reader, dispatcher, owner

    def owner(self):
        """Independently authenticate the caller and public repository owner."""
        return (self.owner_api.request('GET', 'user'),
                self.owner_api.request('GET', PREFIX.rstrip('/')))

    def source(self, expected):
        """Fetch fresh PR and base branch snapshots with the read credential."""
        return (self.reader.request('GET', f'repos/{SOURCE_REPO}/pulls/{expected.pr_number}'),
                self.reader.request('GET', f'repos/{SOURCE_REPO}/branches/main'))

    def legacy_claim(self, expected):
        """Block any existing/ambiguous v1/v2 tag rather than replacing it."""
        pr = dict(number=expected.pr_number, sha=expected.head_sha, base_sha=expected.base_sha)
        for name in (claim_name(pr), legacy_claim_name(pr)):
            rows = self.reader.request('GET', PREFIX + 'git/matching-refs/tags/' + name)
            if type(rows) is not list:
                raise StateBlocked('LEGACY_COLLECTION_INVALID')
            if rows:
                return True
        return False

    def run(self, run_id):
        """Read one independently identified run, never choose newest by time."""
        if type(run_id) is not int or not 0 < run_id < 2**63:
            raise StateBlocked('RUN_ID_INVALID')
        return self.reader.request('GET', PREFIX + f'actions/runs/{run_id}')

    def _revision(self, sha):
        """Require a lightweight tag pointing directly to the pinned controller."""
        ref = 'tags/controller-revision-' + sha
        tag = self.reader.request('GET', PREFIX + 'git/ref/' + ref)
        if (type(tag) is not dict or tag.get('ref') != 'refs/' + ref
                or tag.get('object', {}).get('type') != 'commit'
                or tag['object'].get('sha') != sha):
            raise StateBlocked('IMMUTABLE_CONTROLLER_REF_UNVERIFIED')

    def dispatch(self, controller_sha, inputs):
        """Request direct run details once, keeping missing response uncertain."""
        if not SHA.fullmatch(str(controller_sha)):
            raise StateBlocked('CONTROLLER_SHA_INVALID')
        self._revision(controller_sha)
        body = self.dispatcher.request('POST', PREFIX + 'actions/workflows/'
            + WORKFLOW.rsplit('/', 1)[1] + '/dispatches', dict(
                ref='controller-revision-' + controller_sha, inputs=inputs, return_run_details=True))
        self._revision(controller_sha)
        return 200, body
