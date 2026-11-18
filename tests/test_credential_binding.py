"""Verify controller adapter credential routing using an in-memory transport."""
import io
import unittest

from controller_api import GitHubPorts, RestrictedAPI, WORKFLOW
from durable_state import GitHubState, PREFIX, STATE_REF, StateBlocked


class CredentialBindingTests(unittest.TestCase):
    def setUp(self):
        self.requests = []

        def opener(request, *, timeout):
            self.requests.append((request.method, request.selector,
                                  request.get_header('Authorization')))
            response = io.BytesIO(b'{}')
            response.status = 200
            return response

        self.clients = {
            role: RestrictedAPI(f'fixture-{role}', role=role, opener=opener)
            for role in ('read', 'owner', 'state', 'dispatch')
        }
        self.state = GitHubState(self.clients['state'])
        self.ports = GitHubPorts(reader=self.clients['read'],
                                 dispatcher=self.clients['dispatch'], owner=self.clients['owner'])

    def test_owner_lookup_and_state_read_use_their_own_transport(self):
        self.ports.owner()
        with self.assertRaises(StateBlocked):
            self.state.load()
        self.assertEqual(self.requests, [
            ('GET', '/user', 'Bearer fixture-owner'),
            ('GET', '/' + PREFIX.rstrip('/'), 'Bearer fixture-owner'),
            ('GET', '/' + PREFIX + 'git/ref/' + STATE_REF, 'Bearer fixture-state'),
        ])

    def test_write_routes_use_only_their_designated_credentials(self):
        routes = {
            'state': ('PATCH', PREFIX + 'git/refs/' + STATE_REF),
            'dispatch': ('POST', PREFIX + 'actions/workflows/' + WORKFLOW.rsplit('/', 1)[1] + '/dispatches'),
        }
        for target_role, (method, path) in routes.items():
            for role, client in self.clients.items():
                if role == target_role:
                    client.request(method, path, {})
                else:
                    with self.subTest(role=role, target=target_role), self.assertRaises(StateBlocked):
                        client.request(method, path, {})
        self.assertEqual(self.requests, [
            (method, '/' + path, f'Bearer fixture-{role}')
            for role, (method, path) in routes.items()
        ])
