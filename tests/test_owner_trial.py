"""Scoped owner-trial authority, expiry and recovery with no source execution."""
from dataclasses import FrozenInstanceError
import hashlib
import json
import tempfile
import unittest

from controller_cycle import Controller, WORKFLOW
from controller_api import GitHubPorts
from durable_state import GitHubState, StateBlocked, encode
from owner_trial import OwnerTrialController, OwnerTrialEntrypoint, SCOPE, TrialApproval
from stage6_pr_identity_v32 import CONTROLLER_REPO, ExactPR, SOURCE_REPO
from test_controller_cycle import MemoryState, Ports
from test_git_state_integration import LocalGitAPI

SHA = 'c' * 40


def approval_record():
    """Return ancient synthetic fixture authority, never a live accepted record."""
    return dict(schema=1, scope=SCOPE, repository=CONTROLLER_REPO, owner_id=71314201,
        controller=SHA, workflow=WORKFLOW, source_repository=SOURCE_REPO,
        pr=42, head='a'*40, base='b'*40, issued=100, expires=200)


class TrialTests(unittest.TestCase):
    """Exercise the unchanged coordinator through its scope-bound acceptance hook."""

    def setUp(self):
        self.now = 150
        self.store, self.ports = MemoryState(), Ports()
        self.source = ExactPR(42, 'a'*40, 'b'*40)
        self.approval = self.make_approval()
        self.controller = OwnerTrialController(self.store, self.ports,
            controller_sha=SHA, approval=self.approval)

    def make_approval(self, record=None, raw=None, **kwargs):
        """Pin fixture bytes independently of their embedded content fields."""
        if raw is None:
            raw = encode(approval_record() if record is None else record)
        args = dict(expected_digest=hashlib.sha256(raw).hexdigest(),
                    controller_sha=SHA, clock=lambda: self.now)
        args.update(kwargs)
        return TrialApproval(raw, **args)

    def arm_reserve(self):
        """Use the real owner policy and durable reservation transitions."""
        self.controller.policy(True)
        return self.controller.reserve(self.source, self.now)

    def owner_entrypoint(self, *, raw=None):
        """Take the approved hash from the synthetic deployment configuration."""
        approved = encode(approval_record())
        return OwnerTrialEntrypoint(self.store, self.ports, controller_sha=SHA,
            approval_digest=hashlib.sha256(approved).hexdigest(),
            approval_bytes=approved if raw is None else raw, clock=lambda: self.now)

    def test_owner_entrypoint_refuses_different_approval_bytes(self):
        other_source = dict(approval_record(), pr=43)
        with self.assertRaisesRegex(StateBlocked, 'TRIAL_APPROVAL_IDENTITY_INVALID'):
            self.owner_entrypoint(raw=encode(other_source))
        self.assertEqual(self.store.version, 0)
        self.assertEqual(self.ports.posts, 0)

    def test_owner_entrypoint_blocks_wrong_repository_and_expired_arm(self):
        entrypoint = self.owner_entrypoint()
        owner = self.ports.owner
        self.ports.owner = lambda: (owner()[0], dict(owner()[1], full_name='other/repo'))
        with self.assertRaisesRegex(StateBlocked, 'AUTHENTICATED_OWNER_REQUIRED'):
            entrypoint.arm()
        self.ports.owner = owner
        self.now = 200
        with self.assertRaisesRegex(StateBlocked, 'OPERATIONAL_ACCEPTANCE_REQUIRED'):
            entrypoint.arm()
        self.assertEqual(self.store.version, 0)
        self.assertEqual(self.ports.posts, 0)

    def test_owner_entrypoint_rejects_malformed_or_boolean_owner_identity(self):
        entrypoint = self.owner_entrypoint()
        user, repository = self.ports.owner()
        invalid = [(None, repository), (user, None), (user, dict(repository, owner=None)),
                   (user, dict(repository, owner={'id': True})),
                   (dict(user, id=True), repository)]
        for identity in invalid:
            with self.subTest(identity=identity):
                self.ports.owner = lambda: identity
                with self.assertRaisesRegex(StateBlocked, 'AUTHENTICATED_OWNER_REQUIRED'):
                    entrypoint.arm()
                with self.assertRaisesRegex(StateBlocked, 'AUTHENTICATED_OWNER_REQUIRED'):
                    entrypoint.recover_known_run('unknown', 'unknown', 123)
        self.assertEqual(self.store.version, 0)
        self.assertEqual(self.ports.posts, 0)

    def test_owner_entrypoint_reauthenticates_recovery_after_expiry(self):
        entrypoint = self.owner_entrypoint()
        entrypoint.arm()
        key, nonce = self.controller.reserve(self.source, self.now)
        self.ports.error = True
        with self.assertRaises(TimeoutError):
            self.controller.dispatch(key, nonce)
        self.now = 200
        self.ports.owner_id = 1
        before = self.store.load()
        with self.assertRaisesRegex(StateBlocked, 'AUTHENTICATED_OWNER_REQUIRED'):
            entrypoint.recover_known_run(key, nonce, 123)
        self.assertEqual(self.store.load(), before)
        self.ports.owner_id = approval_record()['owner_id']
        entrypoint.disarm()
        entrypoint.recover_known_run(key, nonce, 123)
        self.assertFalse(self.store.value['policy']['enabled'])
        self.assertEqual(self.store.value['claims'][key]['run_id'], 123)
        self.assertEqual(self.ports.posts, 1)

    def test_exact_approved_trial_dispatches_once_and_does_not_accept_tests(self):
        key, nonce = self.arm_reserve()
        self.assertEqual(self.controller.dispatch(key, nonce), 123)
        with self.assertRaises(StateBlocked):
            self.controller.reserve(self.source, 151)
        self.assertEqual(self.ports.posts, 1)
        self.assertEqual(self.store.value['claims'][key]['state'], 'RUN_BOUND')
        self.assertEqual(self.store.value['claims'][key]['review'], 'NOT_TESTED')

    def test_approval_does_not_replace_authenticated_owner(self):
        self.ports.owner_id = 1
        with self.assertRaisesRegex(StateBlocked, 'AUTHENTICATED_OWNER_REQUIRED'):
            self.controller.policy(True)
        self.assertEqual(self.store.version, 0)
        self.assertEqual(self.ports.posts, 0)

    def test_default_coordinator_remains_disarmed(self):
        with self.assertRaisesRegex(StateBlocked, 'OPERATIONAL_ACCEPTANCE_REQUIRED'):
            Controller(self.store, self.ports, controller_sha=SHA).policy(True)
        self.assertEqual(self.store.version, 0)

    def test_not_yet_valid_expired_and_invalid_clock_never_arm(self):
        for now in (99, 200, 201, True, None, 150.0, -1, 2**63):
            with self.subTest(now=now), self.assertRaises(StateBlocked):
                self.now = now
                self.controller.policy(True)
        self.assertEqual(self.store.version, 0)

    def test_expiry_before_reservation_leaves_policy_and_claims_unchanged(self):
        self.controller.policy(True)
        before = self.store.load()
        self.now = 200
        with self.assertRaisesRegex(StateBlocked, 'DISARMED_OR_NOT_ACCEPTED'):
            self.controller.reserve(self.source, 200)
        self.assertEqual(self.store.load(), before)
        self.assertEqual(self.ports.posts, 0)

    def test_expiry_before_fence_preserves_reservation(self):
        key, nonce = self.arm_reserve()
        before = self.store.load()
        self.now = 200
        with self.assertRaisesRegex(StateBlocked, 'DISPATCH_FENCE_REJECTED'):
            self.controller.dispatch(key, nonce)
        self.assertEqual(self.store.load(), before)
        self.assertEqual(self.ports.posts, 0)

    def test_expiry_after_fence_prevents_post_and_preserves_uncertainty(self):
        key, nonce = self.arm_reserve()
        self.ports.after_source = lambda: setattr(self, 'now', 200)
        with self.assertRaisesRegex(StateBlocked, 'ACCEPTANCE_CHANGED_BEFORE_POST'):
            self.controller.dispatch(key, nonce)
        self.assertEqual(self.store.value['claims'][key]['state'], 'DISPATCH_UNCERTAIN')
        self.assertEqual(self.ports.posts, 0)

    def test_actual_adapter_rechecks_expiry_after_network_tag_lookup(self):
        case = self
        class Reader:
            """Model the tag GET spanning the approval deadline."""
            def request(self, method, path, body=None):
                case.assertEqual(method, 'GET')
                case.now = 200
                return dict(ref='refs/tags/controller-revision-'+SHA,
                            object=dict(type='commit', sha=SHA))
        class Dispatcher:
            """No POST may reach this adapter after the delayed tag read."""
            def request(self, method, path, body=None):
                case.fail('POST attempted after approval expired')
        adapter = GitHubPorts(reader=Reader(), dispatcher=Dispatcher(), owner=None)
        self.ports.dispatch = adapter.dispatch
        key, nonce = self.arm_reserve()
        with self.assertRaisesRegex(StateBlocked, 'DISPATCH_APPROVAL_REJECTED_BEFORE_POST'):
            self.controller.dispatch(key, nonce)
        self.assertEqual(self.store.value['claims'][key]['state'], 'DISPATCH_UNCERTAIN')
        self.assertEqual(self.ports.posts, 0)

    def test_other_pr_head_or_base_cannot_reserve(self):
        self.controller.policy(True)
        for changes in ({'number': 43}, {'head': 'd'*40}, {'base': 'e'*40}):
            with self.subTest(changes=changes):
                source = ExactPR(changes.get('number', 42), changes.get('head', 'a'*40), changes.get('base', 'b'*40))
                self.ports.pr['number'] = source.pr_number
                self.ports.pr['html_url'] = f'https://github.com/{SOURCE_REPO}/pull/{source.pr_number}'
                self.ports.pr['head']['sha'], self.ports.pr['base']['sha'] = source.head_sha, source.base_sha
                self.ports.branch['commit']['sha'] = source.base_sha
                with self.assertRaisesRegex(StateBlocked, 'DISARMED_OR_NOT_ACCEPTED'):
                    self.controller.reserve(source, 150)
        self.assertEqual(self.store.value['claims'], {})
        self.assertEqual(self.ports.posts, 0)

    def test_different_controller_or_unvalidated_approval_cannot_bind(self):
        for sha, approval in (('d'*40, self.approval), (SHA, True), (SHA, approval_record())):
            with self.assertRaisesRegex(StateBlocked, 'TRIAL_APPROVAL_BINDING_INVALID'):
                OwnerTrialController(self.store, self.ports, controller_sha=sha, approval=approval)

    def test_hash_pin_must_match_exact_approved_bytes(self):
        for raw, pin in ((encode(approval_record()), '0'*64),
                         (b'', '0'*64), (b'x'*8193, '0'*64),
                         (encode(approval_record()), True)):
            with self.assertRaisesRegex(StateBlocked, 'TRIAL_APPROVAL_IDENTITY_INVALID'):
                self.make_approval(raw=raw, expected_digest=pin)

    def test_canonical_json_and_unique_fields_required(self):
        raw = encode(approval_record())
        for invalid in (raw.rstrip(), json.dumps(approval_record()).encode(),
                        raw.replace(b'"schema":1', b'"schema":1,"schema":1'), b'{}\n', b'[]\n', b'null\n'):
            with self.subTest(raw=invalid), self.assertRaisesRegex(StateBlocked, 'TRIAL_APPROVAL_CONTENT_INVALID'):
                self.make_approval(raw=invalid)

    def test_record_target_scope_types_and_dates_are_strict(self):
        for field, value in (('schema', True), ('scope', 'unattended'),
                ('repository', 'foreign/repo'), ('owner_id', True), ('owner_id', 1),
                ('controller', 'd'*40), ('workflow', '.github/workflows/other.yml'),
                ('source_repository', 'foreign/repo'), ('pr', True),
                ('head', 'd'*39), ('base', 'e'*39), ('issued', True),
                ('issued', -1), ('expires', 100), ('expires', 2**63)):
            record = approval_record()
            record[field] = value
            with self.subTest(field=field, value=value), self.assertRaises(StateBlocked):
                self.make_approval(record)

    def test_approval_scope_is_immutable(self):
        with self.assertRaises(FrozenInstanceError):
            self.approval.expires = 300
        with self.assertRaises(FrozenInstanceError):
            self.approval.source = ExactPR(43, 'a'*40, 'b'*40)

    def test_expired_approval_still_permits_owner_disarm_and_known_run_recovery(self):
        key, nonce = self.arm_reserve()
        self.ports.error = True
        with self.assertRaises(TimeoutError):
            self.controller.dispatch(key, nonce)
        self.now = 200
        self.controller.policy(False)
        self.controller.reconcile(key, nonce, 123)
        self.assertFalse(self.store.value['policy']['enabled'])
        self.assertEqual(self.store.value['claims'][key]['run_id'], 123)
        self.assertEqual(self.ports.posts, 1)

    def test_wrong_owner_cannot_disarm_then_owner_cancels_only_reservation(self):
        key, nonce = self.arm_reserve()
        self.now = 200
        self.ports.owner_id = 1
        before = self.store.load()
        with self.assertRaises(StateBlocked):
            self.controller.policy(False)
        self.assertEqual(self.store.load(), before)
        self.ports.owner_id = 71314201
        self.controller.policy(False)
        self.assertEqual(self.store.value['claims'][key]['state'], 'CANCELED_BEFORE_POST')
        self.assertEqual(self.ports.posts, 0)

    def test_real_git_state_survives_expiry_and_restart_without_post(self):
        with tempfile.TemporaryDirectory() as root:
            git = LocalGitAPI(root)
            controller = OwnerTrialController(GitHubState(git), self.ports,
                controller_sha=SHA, approval=self.approval)
            controller.policy(True)
            key, nonce = controller.reserve(self.source, 150)
            self.now = 200
            before = git.head()
            restarted = OwnerTrialController(GitHubState(LocalGitAPI(root, initialize=False)),
                self.ports, controller_sha=SHA, approval=self.approval)
            with self.assertRaisesRegex(StateBlocked, 'DISPATCH_FENCE_REJECTED'):
                restarted.dispatch(key, nonce)
            self.assertEqual(git.head(), before)
            restarted.policy(False)
            self.assertNotEqual(git.head(), before)
            self.assertEqual(self.ports.posts, 0)


if __name__ == '__main__':
    unittest.main()
