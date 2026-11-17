"""Preflight classification with synthetic identities and real local Git bytes."""
import copy
import io
import json
import tempfile
import unittest
from urllib.error import HTTPError

from controller_api import ReadNotFound, RestrictedAPI
from controller_cycle import initial_state
from deployment_preflight import ReadOnlyProbe, REPOSITORY_ID, inspect_deployment
from durable_state import PREFIX, STATE_REF, StateBlocked, encode
from stage6_pr_identity_v32 import CONTROLLER_REPO
from test_git_state_integration import LocalGitAPI

SHA = 'c' * 40
TAG = PREFIX + 'git/ref/tags/controller-revision-' + SHA


class ProbeAPI:
    """Provide public-shaped metadata and disposable real state, with fault hooks."""

    def __init__(self, git):
        self.git, self.calls, self.faults = git, [], {}
        self.repo = dict(id=REPOSITORY_ID, full_name=CONTROLLER_REPO,
            private=False, archived=False, disabled=False, owner=dict(id=71314201))
        self.tag = dict(ref='refs/tags/controller-revision-' + SHA,
                        object=dict(type='commit', sha=SHA))
        self.after_state = None

    def request(self, method, path, body=None):
        """Forbid writes and apply deterministic per-path failure observations."""
        self.calls.append((method, path, body))
        if method != 'GET' or body is not None:
            raise AssertionError('Preflight attempted mutation')
        if path in self.faults:
            value = self.faults[path]
            if isinstance(value, Exception):
                raise value
            return copy.deepcopy(value)
        if path == PREFIX.rstrip('/'):
            return copy.deepcopy(self.repo)
        if path == TAG:
            return copy.deepcopy(self.tag)
        result = self.git.request(method, path)
        if '/git/blobs/' in path and self.after_state:
            callback, self.after_state = self.after_state, None
            callback()
        return result


class PreflightTests(unittest.TestCase):
    """Positive identity/storage observations never become activation authority."""

    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.git = LocalGitAPI(self.temp.name)
        self.api = ProbeAPI(self.git)

    def inspect(self):
        """Run the actual collector and enforce zero side effects after each case."""
        before = self.git.head()
        report = inspect_deployment(self.api, controller_sha=SHA)
        self.assertEqual(before, self.git.head())
        self.assertEqual((self.git.created, self.git.patches), ([], 0))
        self.assertTrue(all(method == 'GET' and body is None for method, _, body in self.api.calls))
        self.assertIs(report['activation_allowed'], False)
        self.assertIs(report['dispatch_allowed'], False)
        self.assertEqual(report['operational_acceptance'], 'NOT TESTED')
        return report

    def test_valid_real_git_state_is_observation_only(self):
        report = self.inspect()
        self.assertEqual(report['prerequisites'], 'PASS')
        self.assertEqual(report['checks']['policy']['code'], 'POLICY_DISABLED')
        self.assertEqual(report['checks']['state']['head'], self.git.head())
        self.assertEqual(sum(path == TAG for _, path, _ in self.api.calls), 2)

    def test_wrong_repository_owner_or_visibility_stops_dependent_reads(self):
        for changes in ({'id': 1}, {'id': True}, {'full_name': 'foreign/repo'},
                        {'owner': {'id': 1}}, {'owner': None}, {'private': True},
                        {'archived': True}, {'disabled': True}):
            with self.subTest(changes=changes):
                self.api.repo.update(changes)
                self.assertEqual(self.inspect()['prerequisites'], 'BLOCKED')
                self.assertEqual(len(self.api.calls), 1)
                self.api = ProbeAPI(self.git)

    def test_404_and_collection_failure_are_distinct_neither_proves_absence(self):
        for failure, status, code in (
                (ReadNotFound('private synthetic error'), 'BLOCKED', 'REVISION_NOT_FOUND_OR_NOT_VISIBLE'),
                (StateBlocked('API_HTTP_FAILURE'), 'COLLECTION FAILED', 'REVISION_UNVERIFIED'),
                (TimeoutError('private synthetic error'), 'COLLECTION FAILED', 'REVISION_READ_FAILED')):
            with self.subTest(status=status):
                self.api.faults[TAG] = failure
                report = self.inspect()
                self.assertEqual(report['checks']['revision'], dict(status=status, code=code))
                self.assertNotIn('private synthetic error', json.dumps(report))
                self.assertEqual(report['checks']['state']['status'], 'PASS')
                self.assertNotIn('revision_readback', report['checks'])

    def test_missing_state_does_not_initialize_or_hide_other_observations(self):
        self.api.faults[PREFIX + 'git/ref/' + STATE_REF] = ReadNotFound('synthetic')
        report = self.inspect()
        self.assertEqual(report['checks']['state']['code'], 'STATE_NOT_FOUND_OR_NOT_VISIBLE')
        self.assertNotIn('policy', report['checks'])
        self.assertEqual(report['checks']['revision_readback']['status'], 'PASS')

    def test_wrong_or_malformed_revision_rejected(self):
        for tag in (None, [], {}, dict(ref=self.api.tag['ref'], object=None),
                    dict(ref=self.api.tag['ref'], object=dict(type='tag', sha=SHA)),
                    dict(ref=self.api.tag['ref'], object=dict(type='commit', sha='d'*40))):
            with self.subTest(tag=tag):
                self.api.faults[TAG] = tag
                self.assertEqual(self.inspect()['checks']['revision']['status'], 'FAIL')

    def test_tag_moved_during_state_read_blocks(self):
        self.api.after_state = lambda: self.api.tag['object'].update(sha='d'*40)
        report = self.inspect()
        self.assertEqual(report['checks']['revision']['status'], 'PASS')
        self.assertEqual(report['checks']['revision_readback']['status'], 'FAIL')
        self.assertEqual(report['prerequisites'], 'BLOCKED')

    def test_repository_changed_during_state_read_blocks(self):
        self.api.after_state = lambda: self.api.repo.update(id=1)
        self.assertEqual(self.inspect()['checks']['repository_readback']['status'], 'FAIL')

    def test_state_changed_during_collection_blocks_without_repair(self):
        # The fixture's fixed timestamp/message creates the same object for the
        # same bytes; change the generation to create genuinely different state.
        state = initial_state()
        state['policy']['generation'] = 1
        self.api.after_state = lambda: self.git.publish(encode(state))
        report = inspect_deployment(self.api, controller_sha=SHA)
        self.assertEqual(report['checks']['state']['status'], 'FAIL')
        self.assertEqual(report['prerequisites'], 'BLOCKED')
        self.assertEqual((self.git.created, self.git.patches), ([], 0))

    def test_noncanonical_or_invalid_state_rejected(self):
        for raw in (json.dumps(initial_state()).encode(), encode(dict(schema=1))):
            with self.subTest(raw=raw):
                self.git.publish(raw)
                self.assertEqual(self.inspect()['checks']['state']['status'], 'FAIL')

    def test_enabled_policy_is_reported_never_disarmed(self):
        state = initial_state()
        state['policy'].update(enabled=True, generation=1)
        self.git.publish(encode(state))
        report = self.inspect()
        self.assertEqual(report['checks']['policy']['code'], 'POLICY_ALREADY_ENABLED')
        self.assertEqual(report['prerequisites'], 'BLOCKED')

    def test_invalid_expected_sha_performs_no_reads(self):
        for sha in (None, True, 'C'*40, 'c'*39, SHA + '\n'):
            with self.assertRaises(StateBlocked):
                inspect_deployment(self.api, controller_sha=sha)
        self.assertEqual(self.api.calls, [])

    def test_read_only_wrapper_never_forwards_mutations_or_foreign_targets(self):
        probe = ReadOnlyProbe(self.api)
        for method, path, body in (('POST', PREFIX+'git/blobs', {}),
                                   ('PATCH', PREFIX+'git/refs/'+STATE_REF, {}),
                                   ('GET', 'repos/foreign/repo', None),
                                   ('GET', PREFIX+'../secrets', None),
                                   ('GET', PREFIX+'actions/secrets', None),
                                   ('GET', PREFIX+'git/blobs/'+SHA+'?unexpected=1', None),
                                   ('GET', PREFIX.rstrip('/'), {})):
            with self.assertRaises(StateBlocked):
                probe.request(method, path, body)
        self.assertEqual(self.api.calls, [])


class ReadClassificationTests(unittest.TestCase):
    """The transport retains a sanitized 404 type without weakening retries."""

    def test_404_is_single_attempt_and_only_get_is_not_found(self):
        for method, role, path in (('GET', 'read', PREFIX.rstrip('/')),
                                  ('POST', 'state', PREFIX+'git/blobs')):
            calls = []
            def opener(request, timeout):
                calls.append(request)
                raise HTTPError(request.full_url, 404, 'synthetic', {}, io.BytesIO(b'private'))
            api = RestrictedAPI('synthetic-fixture', role=role, opener=opener,
                                sleep=lambda _: self.fail('Unexpected retry'))
            with self.assertRaises(StateBlocked) as result:
                api.request(method, path)
            self.assertEqual(isinstance(result.exception, ReadNotFound), method == 'GET')
            self.assertNotIn('private', str(result.exception))
            self.assertEqual(len(calls), 1)


if __name__ == '__main__':
    unittest.main()
