"""Focused offline Stage 6-8 integration; no source tests or API writes."""
import base64
import copy
from concurrent.futures import ThreadPoolExecutor
import hashlib
import threading
import unittest

from controller_cycle import Controller, initial_state, validate, WORKFLOW
from durable_state import GitHubState, StateBlocked, encode, git_sha
from stage6_pr_identity_v32 import CONTROLLER_REPO, ExactPR, IdentityRejected


class MemoryState:
    """Model atomic remote compare-and-swap using independent state copies."""

    def __init__(self):
        self.value, self.version = initial_state(), 0
        self.lock = threading.Lock()
        self.fail = None

    def load(self):
        """Return an isolated snapshot with an immutable version."""
        with self.lock:
            return self.version, copy.deepcopy(self.value)

    def save(self, expected, state):
        """Reject stale writers and model failed/readback-uncertain writes."""
        with self.lock:
            if self.fail == 'before' or expected != self.version:
                raise StateBlocked('TEST_CAS_REJECTED')
            self.version += 1
            self.value = copy.deepcopy(state)
            if self.fail == 'after':
                raise StateBlocked('TEST_RESPONSE_LOST')
            return self.version


class Ports:
    """Fresh synthetic public identities, isolated from network and source."""

    def __init__(self):
        self.pr = dict(number=42, state='open', draft=False, merged=False,
            title='fix: synthetic fixture', html_url='https://github.com/TenchiMisaki/romarr/pull/42',
            head=dict(sha='a'*40, ref='feature/synthetic', repo=dict(full_name='TenchiMisaki/romarr')),
            base=dict(sha='b'*40, ref='main', repo=dict(full_name='TenchiMisaki/romarr')))
        self.branch = dict(name='main', commit=dict(sha='b'*40))
        self.observed = dict(id=123, run_attempt=1, repository=dict(full_name=CONTROLLER_REPO),
            head_sha='c'*40, event='workflow_dispatch', path=WORKFLOW,
            status='queued', conclusion=None,
            html_url=f'https://github.com/{CONTROLLER_REPO}/actions/runs/123')
        self.posts, self.sources, self.legacy = 0, 0, False
        self.after_source = None
        self.response_status = 200
        self.error = False
        self.owner_id = 71314201

    def owner(self):
        """Model independently authenticated user and repository identities."""
        return dict(id=self.owner_id), dict(full_name=CONTROLLER_REPO, owner=dict(id=71314201))

    def source(self, expected):
        """Count source rechecks and support a policy-race hook."""
        self.sources += 1
        if self.after_source:
            callback, self.after_source = self.after_source, None
            callback()
        return copy.deepcopy(self.pr), copy.deepcopy(self.branch)

    def legacy_claim(self, expected):
        """Model the mandatory v1/v2 collision gate."""
        return self.legacy

    def dispatch(self, controller_sha, inputs):
        """Record one exact dispatch request without running source."""
        self.posts += 1
        self.inputs = inputs
        self.observed['display_title'] = (f"Stage 6 PR {inputs['pr_number']} h-{inputs['head_sha']} "
            f"b-{inputs['base_sha']} claim-{inputs['claim_nonce']}")
        if self.error:
            raise TimeoutError('synthetic response loss')
        path = f'{CONTROLLER_REPO}/actions/runs/123'
        return self.response_status, dict(workflow_run_id=123,
            run_url=f'https://api.github.com/repos/{path}', html_url=f'https://github.com/{path}')

    def run(self, run_id):
        """Return a separate run observation; not dispatch response evidence."""
        return copy.deepcopy(self.observed)


class ReviewAPI:
    """Supply the existing review parser's real expected REST shapes."""

    def __init__(self, *, findings=False):
        self.findings = findings

    def request(self, method, path, body=None):
        """Return exact-head coverage and a real bot identity."""
        if '/check-runs' in path:
            return dict(check_runs=[dict(name='CodeRabbit', app=dict(slug='coderabbitai'),
                head_sha='a'*40, status='completed', conclusion='success')])
        if '/comments' in path:
            body = '<!-- final_review_risk_coverage:{"sourceCommitId":"' + 'a'*40 + '","coveredCommitId":"' + 'a'*40 + '","kind":"reviewed"} -->'
            if not self.findings:
                body += '\nNo actionable comments were generated in the recent review.'
            return [dict(user=dict(login='coderabbitai[bot]'), body=body, updated_at='2026-01-01T00:00:00Z')]
        raise AssertionError(path)


class CycleTests(unittest.TestCase):
    """Exercise real coordinator transitions and existing identity/review code."""

    def setUp(self):
        """Provision only a disposable disabled state."""
        self.store, self.ports = MemoryState(), Ports()
        self.source = ExactPR(42, 'a'*40, 'b'*40)
        self.controller = Controller(self.store, self.ports, controller_sha='c'*40,
                                     operational_acceptance=True)

    def arm_reserve(self):
        """Explicitly model owner acceptance/arming in an offline fixture."""
        self.controller.policy(True)
        return self.controller.reserve(self.source, 100)

    def test_default_and_restart_disabled(self):
        for controller in (self.controller, Controller(self.store, self.ports, controller_sha='c'*40)):
            with self.assertRaises(StateBlocked):
                controller.reserve(self.source, 100)
        self.assertEqual(self.ports.posts, 0)

    def test_arming_requires_owner_and_separate_acceptance(self):
        controller = Controller(self.store, self.ports, controller_sha='c'*40)
        with self.assertRaisesRegex(StateBlocked, 'ACCEPTANCE'):
            controller.policy(True)
        self.ports.owner_id = 1
        with self.assertRaisesRegex(StateBlocked, 'OWNER'):
            self.controller.policy(True)
        self.assertFalse(self.store.value['policy']['enabled'])

    def test_exact_dispatch_binds_independent_queued_run(self):
        key, nonce = self.arm_reserve()
        self.assertEqual(self.controller.dispatch(key, nonce), 123)
        self.assertEqual(self.store.value['claims'][key]['state'], 'RUN_BOUND')
        self.assertEqual(self.ports.inputs, dict(pr_number='42', head_sha='a'*40,
            base_sha='b'*40, claim_nonce=nonce))
        self.assertEqual(self.ports.sources, 2)
        self.assertEqual(self.ports.posts, 1)

    def test_uncertain_post_persists_across_restart_and_never_retries(self):
        key, nonce = self.arm_reserve()
        self.ports.error = True
        with self.assertRaises(TimeoutError):
            self.controller.dispatch(key, nonce)
        restarted = Controller(self.store, self.ports, controller_sha='c'*40, operational_acceptance=True)
        with self.assertRaises(StateBlocked):
            restarted.dispatch(key, nonce)
        with self.assertRaises(StateBlocked):
            restarted.reserve(self.source, 200)
        self.assertEqual(self.store.value['claims'][key]['state'], 'DISPATCH_UNCERTAIN')
        self.assertEqual(self.ports.posts, 1)
        restarted.reconcile(key, nonce, 123)
        self.assertEqual(self.store.value['claims'][key]['run_id'], 123)

    def test_missing_direct_id_response_never_retries(self):
        key, nonce = self.arm_reserve()
        self.ports.response_status = 204
        with self.assertRaises(IdentityRejected):
            self.controller.dispatch(key, nonce)
        self.assertEqual(self.store.value['claims'][key]['state'], 'DISPATCH_UNCERTAIN')

    def test_fence_write_failure_before_and_after_commit_prevents_post(self):
        for failure in ('before', 'after'):
            self.setUp()
            key, nonce = self.arm_reserve()
            self.store.fail = failure
            with self.assertRaises(StateBlocked):
                self.controller.dispatch(key, nonce)
            self.assertEqual(self.ports.posts, 0)

    def test_disarm_rearm_invalidates_ticket(self):
        key, nonce = self.arm_reserve()
        self.controller.policy(False)
        self.controller.policy(True)
        with self.assertRaises(StateBlocked):
            self.controller.dispatch(key, nonce)
        self.assertEqual(self.store.value['claims'][key]['state'], 'CANCELED_BEFORE_POST')
        self.assertEqual(self.ports.posts, 0)

    def test_disarm_at_post_boundary_blocks(self):
        key, nonce = self.arm_reserve()
        self.ports.after_source = lambda: self.controller.policy(False)
        with self.assertRaises(StateBlocked):
            self.controller.dispatch(key, nonce)
        self.assertEqual(self.ports.posts, 0)
        self.assertEqual(self.store.value['claims'][key]['state'], 'DISPATCH_UNCERTAIN')

    def test_moved_source_after_reservation_blocks(self):
        key, nonce = self.arm_reserve()
        self.ports.pr['head']['sha'] = 'd'*40
        with self.assertRaises(IdentityRejected):
            self.controller.dispatch(key, nonce)
        self.assertEqual(self.ports.posts, 0)

    def test_draft_review_backlog_and_stale_base_excluded(self):
        for change in ('draft', 'review', 'backlog', 'base'):
            self.setUp()
            self.controller.policy(True)
            if change == 'draft': self.ports.pr['draft'] = True
            if change == 'review': self.ports.pr['head']['ref'] = 'review/fixture'
            if change == 'backlog': self.ports.pr['title'] = 'Backlog: fixture'
            if change == 'base': self.ports.branch['commit']['sha'] = 'd'*40
            with self.assertRaises(IdentityRejected):
                self.controller.reserve(self.source, 100)

    def test_legacy_claim_and_failed_collection_block(self):
        self.controller.policy(True)
        for legacy in (True, None, 'unknown'):
            self.ports.legacy = legacy
            with self.assertRaises(StateBlocked):
                self.controller.reserve(self.source, 100)

    def test_workers_reserve_one_global_outstanding_claim(self):
        self.controller.policy(True)
        barrier = threading.Barrier(8)
        def worker(_):
            """Race independent coordinator operations on one remote model."""
            barrier.wait()
            try:
                self.controller.reserve(self.source, 100)
                return True
            except StateBlocked:
                return False
        with ThreadPoolExecutor(max_workers=8) as pool:
            results = list(pool.map(worker, range(8)))
        self.assertEqual(sum(results), 1)
        self.assertEqual(len(self.store.value['claims']), 1)

    def test_wrong_run_attempt_workflow_repository_and_controller_rejected(self):
        key, nonce = self.arm_reserve()
        self.store.value['claims'][key]['state'] = 'DISPATCH_UNCERTAIN'
        original = copy.deepcopy(self.ports.observed)
        for changes in (dict(id=True), dict(run_attempt=2), dict(path='other.yml'),
                        dict(repository=dict(full_name='foreign/repo')), dict(head_sha='d'*40),
                        dict(event='push'), dict(html_url='https://example.com')):
            self.ports.observed = dict(original, **changes)
            with self.assertRaises(StateBlocked):
                self.controller.reconcile(key, nonce, 123)

    def observe(self, *, findings=False, unresolved=0, collect=None):
        """Exercise the existing CodeRabbit parser through the coordinator."""
        key, nonce = self.arm_reserve()
        self.controller.dispatch(key, nonce)
        self.ports.observed.update(status='completed', conclusion='success')
        result = self.controller.observe(key,
            collect_advisory=collect or (lambda claim: 'ADVISORY_COLLECTED_NOT_TEST_ACCEPTED'),
            review_api=ReviewAPI(findings=findings),
            thread_reader=lambda number, sha: dict(state='VERIFIED', unresolved=unresolved))
        return key, result

    def test_advisory_and_clean_review_never_become_accepted_tests(self):
        key, result = self.observe()
        self.assertEqual(result, 'ADVISORY_COMPLETE')
        self.assertEqual(self.store.value['claims'][key]['review'], 'REVIEW_READY')
        self.assertNotIn('test_accepted', self.store.value['claims'][key])
        with self.assertRaises(StateBlocked):
            self.controller.reserve(self.source, 200)

    def test_review_findings_and_unresolved_threads_remain_visible(self):
        key, _ = self.observe(findings=True, unresolved=2)
        self.assertEqual(self.store.value['claims'][key]['review'], 'UNRESOLVED_THREADS')

    def test_old_run_with_different_claim_nonce_rejected(self):
        key, nonce = self.arm_reserve()
        self.controller.dispatch(key, nonce)
        self.ports.observed['display_title'] += 'different'
        with self.assertRaises(StateBlocked):
            self.controller.reconcile(key, nonce, 123)

    def test_review_refresh_budget_and_source_freshness(self):
        key, _ = self.observe(findings=True, unresolved=1)
        reader = lambda number, sha: dict(state='VERIFIED', unresolved=0)
        self.assertEqual(self.controller.refresh_review(key, 1000,
            review_api=ReviewAPI(), thread_reader=reader), 'REVIEW_READY')
        with self.assertRaises(StateBlocked):
            self.controller.refresh_review(key, 1001, review_api=ReviewAPI(), thread_reader=reader)
        self.ports.pr['head']['sha'] = 'd'*40
        with self.assertRaises(IdentityRejected):
            self.controller.refresh_review(key, 1060, review_api=ReviewAPI(), thread_reader=reader)
        self.assertEqual(self.store.value['claims'][key]['review_checks'], 2)

    def test_bad_advisory_does_not_release_claim(self):
        with self.assertRaises(StateBlocked):
            self.observe(collect=lambda claim: 'unverified')
        self.assertEqual(next(iter(self.store.value['claims'].values()))['state'], 'RUN_BOUND')

    def test_failed_run_recorded_separately_without_collector(self):
        key, nonce = self.arm_reserve()
        self.controller.dispatch(key, nonce)
        self.ports.observed.update(status='completed', conclusion='failure')
        self.assertEqual(self.controller.observe(key, collect_advisory=None,
            review_api=None, thread_reader=None), 'RUN_FAILED')
        self.assertEqual(self.store.value['claims'][key]['review'], 'NOT_TESTED')

    def test_pending_run_never_accepts_or_releases(self):
        key, nonce = self.arm_reserve()
        self.controller.dispatch(key, nonce)
        self.assertEqual(self.controller.observe(key, collect_advisory=None,
            review_api=None, thread_reader=None), 'PENDING_RUN')

    def test_tick_collision_restart_clock_and_cadence(self):
        self.assertEqual(self.controller.tick(1000), 'TICK_RECORDED_NOT_DISPATCH_AUTHORIZED')
        self.assertEqual(self.controller.tick(1001), 'RECENT_TICK_NOOP')
        with self.assertRaises(StateBlocked): self.controller.tick(999)
        self.assertEqual(self.controller.tick(1300), 'TICK_RECORDED_NOT_DISPATCH_AUTHORIZED')
        self.assertEqual(self.ports.posts, 0)

    def test_notification_delivery_dedup_and_private_payload_exclusion(self):
        key, _ = self.arm_reserve()
        sent = []
        def deliver(payload):
            """Require only the fixed code and opaque idempotency key."""
            self.assertEqual(set(payload), {'id', 'code'})
            sent.append(payload)
            return payload['id']
        self.assertEqual(self.controller.notify(key=key, code='FAILED_RUN', now=100,
            deliver=deliver), 'DELIVERY_VERIFIED')
        self.controller.notify(key=key, code='FAILED_RUN', now=500, deliver=deliver)
        self.assertEqual(len(sent), 1)

    def test_unknown_delivery_never_retries_on_restart(self):
        key, _ = self.arm_reserve()
        def timeout(payload):
            """Model a send that may have reached the destination."""
            raise TimeoutError('unknown delivery')
        with self.assertRaises(TimeoutError):
            self.controller.notify(key=key, code='RECOVERY_REQUIRED', now=100, deliver=timeout)
        result = self.controller.notify(key=key, code='RECOVERY_REQUIRED', now=500,
            deliver=lambda payload: self.fail('blind retry'))
        self.assertIn('RECONCILIATION_REQUIRED', result)

    def test_definite_nondelivery_has_finite_spaced_attempts(self):
        key, _ = self.arm_reserve()
        calls = []
        def absent(payload):
            """Return confirmed absence, distinct from unknown delivery."""
            calls.append(payload)
            return None
        for now in (100, 101, 400, 700, 1000):
            self.controller.notify(key=key, code='MISSED_RUN', now=now, deliver=absent)
        self.assertEqual(len(calls), 3)

    def test_corrupt_policy_fails_closed(self):
        for value in (None, {}, dict(enabled='true', generation=0)):
            state = initial_state()
            state['policy'] = value
            with self.assertRaises(StateBlocked): validate(state)

    def test_integrated_cycle_dispatch_pending_failure_and_alert(self):
        self.controller.policy(True)
        self.assertEqual(self.controller.cycle(1000, candidate=self.source), 'DISPATCHED_NOT_TEST_ACCEPTED')
        self.assertEqual(self.controller.cycle(1001, candidate=self.source), 'RECENT_TICK_NOOP')
        self.assertEqual(self.controller.cycle(1300), 'PENDING_RUN')
        self.ports.observed.update(status='completed', conclusion='failure')
        sent = []
        def deliver(payload):
            """Confirm one sanitized failure notification."""
            sent.append(payload)
            return payload['id']
        self.assertEqual(self.controller.cycle(1600, deliver=deliver), 'RUN_FAILED')
        self.assertEqual(len(sent), 1)
        self.assertEqual(self.ports.posts, 1)

    def test_integrated_cycle_retains_uncertainty_and_never_dispatches_again(self):
        key, _ = self.arm_reserve()
        self.assertEqual(self.controller.cycle(1000, candidate=self.source),
                         'RECONCILIATION_REQUIRED_NO_REDISPATCH')
        self.assertEqual(self.store.value['claims'][key]['state'], 'RESERVED')
        self.assertEqual(self.ports.posts, 0)

    def test_review_budget_survives_twenty_checks_and_restart(self):
        key, _ = self.observe()
        reader = lambda number, sha: dict(state='VERIFIED', unresolved=0)
        for index in range(20):
            self.controller.refresh_review(key, 1000+index*60,
                review_api=ReviewAPI(), thread_reader=reader)
        restarted = Controller(self.store, self.ports, controller_sha='c'*40)
        with self.assertRaisesRegex(StateBlocked, 'BUDGET'):
            restarted.refresh_review(key, 3000, review_api=ReviewAPI(), thread_reader=reader)

    def test_cycle_refreshes_completed_pending_review(self):
        key, _ = self.observe(findings=True)
        self.assertEqual(self.store.value['claims'][key]['review_checks'], 0)
        result = self.controller.cycle(1000, review_api=ReviewAPI(),
            thread_reader=lambda number, sha: dict(state='VERIFIED', unresolved=0))
        self.assertEqual(result, 'REVIEW_READY')
        self.assertEqual(self.store.value['claims'][key]['review_checks'], 1)

    def test_failed_observation_persists_alert_intent_before_delivery(self):
        key, nonce = self.arm_reserve()
        self.controller.dispatch(key, nonce)
        self.ports.observed.update(status='completed', conclusion='failure')
        self.controller.observe(key, collect_advisory=None, review_api=None, thread_reader=None)
        self.assertEqual(next(iter(self.store.value['alerts'].values()))['state'], 'PENDING')
        restarted = Controller(self.store, self.ports, controller_sha='c'*40)
        result = restarted.cycle(1000, deliver=lambda payload: payload['id'])
        self.assertEqual(result, 'DELIVERY_VERIFIED')
        self.assertEqual(next(iter(self.store.value['alerts'].values()))['state'], 'DELIVERED')

    def test_terminal_failure_alert_retries_only_confirmed_nondelivery(self):
        key, nonce = self.arm_reserve()
        self.controller.dispatch(key, nonce)
        self.ports.observed.update(status='completed', conclusion='failure')
        calls = []
        def deliver(payload):
            """Confirm absent delivery once, then return a verified receipt."""
            calls.append(payload)
            return None if len(calls) == 1 else payload['id']
        self.assertEqual(self.controller.cycle(1000, deliver=deliver), 'RUN_FAILED')
        self.assertEqual(self.controller.cycle(1300, deliver=deliver), 'DELIVERY_VERIFIED')
        self.assertEqual(len(calls), 2)


class GitAPI:
    """Model immutable Git objects and server-side non-force ref update."""

    def __init__(self):
        self.raw = encode(initial_state())
        self.blob = git_sha('blob', self.raw)
        self.tree, self.head = 'b'*40, 'a'*40
        self.calls = []
        self.fail_patch, self.race = False, False

    def request(self, method, path, body=None):
        """Serve the narrow adapter contract and emulate competing writers."""
        self.calls.append((method, path, body))
        if '/git/ref/' in path:
            return dict(ref='refs/heads/controller-state-v1', object=dict(type='commit', sha=self.head))
        if '/git/commits/' in path:
            return dict(sha=self.head, tree=dict(sha=self.tree))
        if '/git/trees/' in path:
            return dict(sha=self.tree, truncated=False, tree=[dict(path='state.json',
                mode='100644', type='blob', sha=self.blob)])
        if '/git/blobs/' in path:
            return dict(sha=self.blob, encoding='base64', size=len(self.raw),
                content=base64.b64encode(self.raw).decode())
        if method == 'POST' and path.endswith('/git/blobs'):
            self.pending_raw = base64.b64decode(body['content'])
            self.pending_blob = git_sha('blob', self.pending_raw)
            return dict(sha=self.pending_blob)
        if method == 'POST' and path.endswith('/git/trees'):
            return dict(sha='d'*40)
        if method == 'POST' and path.endswith('/git/commits'):
            return dict(sha='e'*40, tree=dict(sha='d'*40), parents=[dict(sha=body['parents'][0])])
        if method == 'PATCH':
            if body['force'] is not False: raise AssertionError('force')
            if self.race: raise StateBlocked('server rejects non-fast-forward')
            self.head, self.tree = 'e'*40, 'd'*40
            self.raw, self.blob = self.pending_raw, self.pending_blob
            if self.fail_patch: raise TimeoutError('lost patch response')
            return dict()
        raise AssertionError((method, path))


class GitStateTests(unittest.TestCase):
    """Test the real Git database adapter without a live mutation."""

    def test_pinned_read_and_verified_write(self):
        api = GitAPI()
        store = GitHubState(api)
        head, state = store.load()
        state['last_tick'] = 100
        self.assertEqual(store.save(head, state), 'e'*40)
        self.assertEqual(store.load()[1], state)
        patches = [c for c in api.calls if c[0] == 'PATCH']
        self.assertEqual(len(patches), 1)
        self.assertEqual(patches[0][2]['force'], False)

    def test_competing_branch_update_rejected(self):
        api = GitAPI()
        store = GitHubState(api)
        head, state = store.load()
        api.head = 'f'*40
        with self.assertRaises(StateBlocked): store.save(head, state)
        self.assertFalse(any(c[0] == 'POST' for c in api.calls))

    def test_server_side_race_never_retried(self):
        api = GitAPI()
        store = GitHubState(api)
        head, state = store.load()
        api.race = True
        with self.assertRaises(StateBlocked): store.save(head, state)
        self.assertEqual(sum(c[0] == 'PATCH' for c in api.calls), 1)

    def test_lost_patch_response_preserves_unknown_without_retry(self):
        api = GitAPI()
        store = GitHubState(api)
        head, state = store.load()
        api.fail_patch = True
        with self.assertRaises(TimeoutError): store.save(head, state)
        self.assertEqual(sum(c[0] == 'PATCH' for c in api.calls), 1)

    def test_corrupt_bytes_and_noncanonical_json_rejected(self):
        for raw in (b'{}', b'{"secret":"unexpected"}', b'[]\n'):
            api = GitAPI()
            api.raw = raw
            with self.assertRaises(StateBlocked): GitHubState(api).load()

    def test_capacity_and_nonfinite_values_block(self):
        for state in (dict(value='x'*1_000_001), dict(value=float('nan'))):
            with self.assertRaises((StateBlocked, ValueError)): encode(state)

    def test_same_parent_same_state_same_second_commits_are_unique(self):
        first, second = GitAPI(), GitAPI()
        for api in (first, second):
            store = GitHubState(api)
            head, state = store.load()
            store.save(head, state)
        messages = [next(c[2]['message'] for c in api.calls if c[0] == 'POST' and c[1].endswith('/git/commits'))
                    for api in (first, second)]
        self.assertNotEqual(messages[0], messages[1])

    def test_identical_concurrent_state_writes_have_exactly_one_winner(self):
        """Model GitHub's same-second object identity and non-force semantics."""
        class AtomicGit:
            """Store immutable objects, with both writers observing one parent."""
            def __init__(inner):
                inner.head = 'a'*40
                raw = encode(initial_state())
                blob = git_sha('blob', raw)
                inner.docs = {
                    'git/commits/'+'a'*40: dict(sha='a'*40, tree=dict(sha='b'*40)),
                    'git/trees/'+'b'*40: dict(sha='b'*40, truncated=False, tree=[
                        dict(path='state.json', mode='100644', type='blob', sha=blob)]),
                    'git/blobs/'+blob: dict(sha=blob, encoding='base64', size=len(raw),
                        content=base64.b64encode(raw).decode())}
                inner.lock = threading.Lock()
                inner.local = threading.local()
                inner.barrier = threading.Barrier(2)

            def request(inner, method, path, body=None):
                """Permit idempotent PATCH to reproduce the old double-success bug."""
                suffix = path.split('romarr-ci-controller/', 1)[1]
                if method == 'GET' and suffix.startswith('git/ref/'):
                    with inner.lock:
                        head = inner.head
                    count = getattr(inner.local, 'reads', 0) + 1
                    inner.local.reads = count
                    if count <= 2:
                        inner.barrier.wait(timeout=5)
                    return dict(ref='refs/heads/controller-state-v1', object=dict(type='commit', sha=head))
                with inner.lock:
                    if method == 'GET':
                        return copy.deepcopy(inner.docs[suffix])
                    if suffix == 'git/blobs':
                        raw = base64.b64decode(body['content']); sha = git_sha('blob', raw)
                        inner.docs['git/blobs/'+sha] = dict(sha=sha, encoding='base64',
                            size=len(raw), content=body['content'])
                        return dict(sha=sha)
                    if suffix == 'git/trees':
                        sha = hashlib.sha1(encode(body)).hexdigest()
                        inner.docs['git/trees/'+sha] = dict(sha=sha, truncated=False, tree=body['tree'])
                        return dict(sha=sha)
                    if suffix == 'git/commits':
                        # Fixed timestamp: only parent/tree/message distinguish writes.
                        sha = hashlib.sha1(encode(dict(body, timestamp=1000))).hexdigest()
                        value = dict(sha=sha, tree=dict(sha=body['tree']),
                                     parents=[dict(sha=p) for p in body['parents']])
                        inner.docs['git/commits/'+sha] = value
                        return copy.deepcopy(value)
                    if method == 'PATCH':
                        target = body['sha']; parent = inner.docs['git/commits/'+target]['parents'][0]['sha']
                        if target != inner.head and parent != inner.head:
                            raise StateBlocked('NON_FAST_FORWARD')
                        inner.head = target
                        return dict()
                    raise AssertionError((method, path))
        api = AtomicGit()
        def worker(_):
            """Attempt the identical fenced state from independent API clients."""
            try:
                GitHubState(api).save('a'*40, initial_state())
                return True
            except StateBlocked:
                return False
        with ThreadPoolExecutor(max_workers=2) as pool:
            results = list(pool.map(worker, range(2)))
        self.assertEqual(sum(results), 1)


if __name__ == '__main__':
    unittest.main()
