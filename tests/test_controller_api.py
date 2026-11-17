"""Exercise role, credential, redirect, retry and immutable-ref contracts."""
import io
import json
import unittest
from urllib.error import HTTPError

from controller_api import GitHubPorts, NoRedirect, RestrictedAPI
from durable_state import PREFIX, StateBlocked
from stage6_pr_identity_v32 import ExactPR


class Response(io.BytesIO):
    """Bounded in-memory HTTP response fixture."""

    def __init__(self, payload, status=200):
        super().__init__(json.dumps(payload).encode())
        self.status = status


class APITests(unittest.TestCase):
    """No real credentials or network calls are used."""

    def test_role_and_target_negative_matrix(self):
        for role in ('read', 'state', 'dispatch', 'owner'):
            api = RestrictedAPI('synthetic-fixture', role=role)
            for path in ('https://example.com', 'repos/foreign/repo/git/refs',
                         PREFIX + '../secrets', PREFIX + 'actions/secrets', 'user/token'):
                self.assertFalse(api._allowed('POST', path))
            self.assertFalse(api._allowed('DELETE', PREFIX + 'git/refs/heads/controller-state-v1'))
        self.assertFalse(RestrictedAPI('synthetic-fixture')._allowed('POST', PREFIX + 'git/blobs'))
        self.assertFalse(RestrictedAPI('synthetic-fixture', role='state')._allowed('POST', PREFIX + 'actions/workflows/stage6-pr-manual-candidate.yml/dispatches'))
        self.assertFalse(RestrictedAPI('synthetic-fixture', role='dispatch')._allowed('POST', PREFIX + 'git/blobs'))

    def test_redirect_handler_never_forwards_credentials(self):
        self.assertIsNone(NoRedirect().redirect_request(None, None, 302, '', {}, 'https://example.com'))

    def test_authorized_read_and_bounded_transient_retries(self):
        calls, delays, progress = [], [], []
        def opener(request, timeout):
            """Fail two reads then return one independent API result."""
            calls.append(request)
            if len(calls) < 3:
                raise HTTPError(request.full_url, 503, 'synthetic', {}, None)
            return Response(dict(ok=True))
        api = RestrictedAPI('synthetic-fixture', opener=opener, sleep=delays.append, progress=progress.append)
        self.assertEqual(api.request('GET', PREFIX.rstrip('/')), dict(ok=True))
        self.assertEqual(delays, [2, 4])
        self.assertEqual(len(progress), 2)
        self.assertEqual(calls[-1].get_header('Authorization'), 'Bearer synthetic-fixture')
        self.assertNotIn('synthetic-fixture', str(progress))

    def test_auth_redirect_and_mutation_failure_never_retry(self):
        for role, method, path, status in (
                ('read', 'GET', PREFIX.rstrip('/'), 401),
                ('read', 'GET', PREFIX.rstrip('/'), 403),
                ('read', 'GET', PREFIX.rstrip('/'), 302),
                ('state', 'POST', PREFIX + 'git/blobs', 503)):
            calls = []
            def opener(request, timeout):
                """Return a nonretryable or ambiguous synthetic HTTP failure."""
                calls.append(request)
                raise HTTPError(request.full_url, status, 'synthetic', {}, None)
            api = RestrictedAPI('synthetic-fixture', role=role, opener=opener,
                                sleep=lambda delay: self.fail('retry'))
            with self.assertRaises(StateBlocked): api.request(method, path)
            self.assertEqual(len(calls), 1)

    def test_dispatch_204_and_oversized_response_fail_closed(self):
        api = RestrictedAPI('synthetic-fixture', role='dispatch',
                            opener=lambda *a, **k: Response(None, 204))
        with self.assertRaises(StateBlocked):
            api.request('POST', PREFIX + 'actions/workflows/stage6-pr-manual-candidate.yml/dispatches', {})
        api = RestrictedAPI('synthetic-fixture', opener=lambda *a, **k: Response('x'*2_000_001))
        with self.assertRaises(StateBlocked): api.request('GET', PREFIX.rstrip('/'))

    def test_ports_dispatch_pins_ref_and_direct_id(self):
        calls = []
        class API:
            """Record adapter traffic and provide a fixed immutable tag."""
            def request(inner, method, path, body=None):
                calls.append((method, path, body))
                if method == 'GET':
                    return dict(ref='refs/tags/controller-revision-'+'c'*40,
                                object=dict(type='commit', sha='c'*40))
                return dict(workflow_run_id=123)
        api = API()
        ports = GitHubPorts(reader=api, dispatcher=api, owner=api)
        status, body = ports.dispatch('c'*40, dict(pr_number='42'))
        self.assertEqual((status, body['workflow_run_id']), (200, 123))
        self.assertEqual([c[0] for c in calls], ['GET', 'POST', 'GET'])
        self.assertTrue(calls[1][2]['return_run_details'])
        self.assertEqual(calls[1][2]['ref'], 'controller-revision-'+'c'*40)

    def test_existing_legacy_claim_stops_new_backend(self):
        class API:
            """Return an existing v2 tag collection."""
            def request(inner, method, path, body=None):
                return [dict(ref='historical')]
        api = API()
        ports = GitHubPorts(reader=api, dispatcher=api, owner=api)
        self.assertTrue(ports.legacy_claim(ExactPR(42, 'a'*40, 'b'*40)))

    def test_dispatch_approval_guard_runs_between_tag_lookup_and_post(self):
        calls = []
        class API:
            """Record the actual guarded adapter's request order."""
            def request(self, method, path, body=None):
                calls.append(method)
                if method == 'GET':
                    return dict(ref='refs/tags/controller-revision-'+'c'*40,
                                object=dict(type='commit', sha='c'*40))
                return dict(workflow_run_id=123)
        api = API()
        ports = GitHubPorts(reader=api, dispatcher=api, owner=None)
        def approve():
            calls.append('GUARD')
            return True
        ports.dispatch('c'*40, {}, pre_post=approve)
        self.assertEqual(calls, ['GET','GUARD','POST','GET'])
        for value in (False, None, 1):
            calls.clear()
            with self.assertRaises(StateBlocked):
                ports.dispatch('c'*40, {}, pre_post=lambda: value)
            self.assertEqual(calls, ['GET'])
        calls.clear()
        with self.assertRaisesRegex(StateBlocked, 'CALLBACK_INVALID'):
            ports.dispatch('c'*40, {}, pre_post=True)
        self.assertEqual(calls, [])


if __name__ == '__main__':
    unittest.main()
