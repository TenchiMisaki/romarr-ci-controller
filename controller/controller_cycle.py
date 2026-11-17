"""Dormant Stage 6-8 coordination with no installed workflow or test acceptance.

Integrates existing exact-source, dispatch-response and review checks. Trusted
ports must collect authenticated data on isolated infrastructure. The existing
advisory workflow remains advisory; operational activation is separately gated.
"""
from __future__ import annotations

import hashlib
import re
import uuid

from durable_state import StateBlocked, encode, transact
from stage6_dispatch_ledger import _source
from stage6_dispatch_response import dispatch_run_id
from stage6_pr_identity_v32 import CONTROLLER_REPO, ExactPR, SHA
from status import review_status

WORKFLOW = '.github/workflows/stage6-pr-manual-candidate.yml'
OWNER_ID = 71314201
TERMINAL = {'ADVISORY_COMPLETE', 'RUN_FAILED', 'SOURCE_STALE', 'CANCELED_BEFORE_POST'}
STATES = TERMINAL | {'RESERVED', 'DISPATCH_UNCERTAIN', 'RUN_BOUND'}
NONCE = re.compile('[0-9a-f]{32}\\Z')


def initial_state():
    """Return disabled provisioning content; never publish it automatically."""
    return dict(schema=1, policy=dict(enabled=False, generation=0), claims={},
                alerts={}, last_tick=None)


def validate(state):
    """Reject unknown or corrupt durable state before any side effect."""
    if (type(state) is not dict or set(state) != {'schema', 'policy', 'claims', 'alerts', 'last_tick'}
            or type(state['schema']) is not int or state['schema'] != 1):
        raise StateBlocked('STATE_SCHEMA_INVALID')
    p = state['policy']
    if (type(p) is not dict or set(p) != {'enabled', 'generation'}
            or type(p['enabled']) is not bool or type(p['generation']) is not int
            or not 0 <= p['generation'] < 2**63):
        raise StateBlocked('POLICY_INVALID')
    if type(state['claims']) is not dict or type(state['alerts']) is not dict:
        raise StateBlocked('STATE_COLLECTION_INVALID')
    active = 0
    run_ids = set()
    for key, claim in state['claims'].items():
        if type(claim) is not dict or set(claim) != {
                'pr', 'head', 'base', 'controller', 'generation', 'nonce',
                'state', 'run_id', 'created', 'review', 'review_checks', 'last_review'}:
            raise StateBlocked('CLAIM_SCHEMA_INVALID')
        source = ExactPR(claim['pr'], claim['head'], claim['base'])
        if (key != revision_key(source) or claim['state'] not in STATES
                or not SHA.fullmatch(str(claim['controller']))
                or type(claim['generation']) is not int
                or not 0 <= claim['generation'] <= p['generation']
                or not NONCE.fullmatch(str(claim['nonce']))
                or type(claim['created']) is not int or claim['created'] < 0
                or type(claim['review_checks']) is not int or not 0 <= claim['review_checks'] <= 20
                or (claim['last_review'] is not None and (type(claim['last_review']) is not int or claim['last_review'] < 0))
                or claim['review'] not in {'NOT_TESTED', 'REVIEW_READY', 'UNRESOLVED_THREADS', 'REVIEW_NOT_VERIFIED'}):
            raise StateBlocked('CLAIM_INVALID')
        run_id = claim['run_id']
        if run_id is not None:
            if type(run_id) is not int or not 0 < run_id < 2**63 or run_id in run_ids:
                raise StateBlocked('RUN_BINDING_INVALID')
            run_ids.add(run_id)
        if claim['state'] in {'RUN_BOUND', 'ADVISORY_COMPLETE', 'RUN_FAILED', 'SOURCE_STALE'} and run_id is None:
            raise StateBlocked('RUN_BINDING_MISSING')
        active += claim['state'] not in TERMINAL
    if active > 1:
        raise StateBlocked('MULTIPLE_OUTSTANDING_CLAIMS')
    for key, alert in state['alerts'].items():
        if (not re.fullmatch('[0-9a-f]{64}', key) or type(alert) is not dict
                or set(alert) != {'state', 'attempts', 'updated', 'claim_key', 'code'}
                or alert['state'] not in {'PENDING', 'DELIVERY_UNCERTAIN', 'DELIVERED'}
                or type(alert['attempts']) is not int or not 0 <= alert['attempts'] <= 3
                or type(alert['updated']) is not int or alert['updated'] < 0):
            raise StateBlocked('ALERT_INVALID')
        if (alert['claim_key'] not in state['claims'] or alert['code'] not in {
                'MISSED_RUN', 'FAILED_RUN', 'COLLECTION_FAILED', 'REVIEW_FINDING', 'RECOVERY_REQUIRED'}
                or hashlib.sha256((alert['claim_key'] + ':' + alert['code']).encode()).hexdigest() != key):
            raise StateBlocked('ALERT_CLAIM_BINDING_INVALID')
    if state['last_tick'] is not None and (type(state['last_tick']) is not int or state['last_tick'] < 0):
        raise StateBlocked('CLOCK_INVALID')
    encode(state)


def revision_key(source):
    """Deduplicate source revisions independently of controller code changes."""
    return f'{source.pr_number}:{source.head_sha}:{source.base_sha}'


class Controller:
    """One bounded cycle at a time, serialized by the durable state backend.

    Ports: source(ExactPR)->(fresh PR, fresh main branch), legacy_claim(ExactPR)
    ->bool, dispatch(controller_sha, inputs)->(status, body), run(id)->dict.
    Dispatch must use a separately provisioned immutable ref at controller_sha.
    No port may execute selected source with controller credentials.
    """

    def __init__(self, store, ports, *, controller_sha, operational_acceptance=False):
        if not SHA.fullmatch(str(controller_sha)) or type(operational_acceptance) is not bool:
            raise StateBlocked('CONTROLLER_EXPECTATION_INVALID')
        self.store, self.ports = store, ports
        self.sha, self.accepted = controller_sha, operational_acceptance

    def _change(self, operation):
        """Validate both sides of every persisted state transition."""
        def update(state):
            validate(state)
            result = operation(state)
            validate(state)
            return result
        return transact(self.store, update)

    def cycle(self, now, *, candidate=None, collect_advisory=None,
              review_api=None, thread_reader=None, deliver=None):
        """Join scheduling, outstanding work, review and one selected candidate.

        Candidate selection is a separately authenticated read-only operation.
        This cycle never repairs source, retries ambiguous POSTs or accepts a
        test receipt. Delivery remains optional and cannot authorize work.
        """
        tick = self.tick(now)
        if tick == 'RECENT_TICK_NOOP':
            return tick
        _, state = self.store.load()
        validate(state)
        if deliver is not None:
            pending = [(identifier, alert) for identifier, alert in state['alerts'].items()
                if alert['state'] == 'PENDING' and alert['attempts'] < 3
                and (alert['attempts'] == 0 or now - alert['updated'] >= 300)]
            if pending:
                _, alert = sorted(pending)[0]
                return self.notify(key=alert['claim_key'], code=alert['code'], now=now, deliver=deliver)
        active = [(k, c) for k, c in state['claims'].items() if c['state'] not in TERMINAL]
        if active:
            key, claim = active[0]
            if claim['state'] == 'RUN_BOUND':
                result = self.observe(key, collect_advisory=collect_advisory,
                                      review_api=review_api, thread_reader=thread_reader)
                if result == 'RUN_FAILED' and deliver is not None:
                    self.notify(key=key, code='FAILED_RUN', now=now, deliver=deliver)
                return result
            if deliver is not None:
                self.notify(key=key, code='RECOVERY_REQUIRED', now=now, deliver=deliver)
            return 'RECONCILIATION_REQUIRED_NO_REDISPATCH'
        pending_reviews = [(key, claim) for key, claim in state['claims'].items()
            if claim['state'] == 'ADVISORY_COMPLETE' and claim['review'] != 'REVIEW_READY'
            and claim['review_checks'] < 20
            and (claim['last_review'] is None or now - claim['last_review'] >= 60)]
        if pending_reviews and review_api is not None and thread_reader is not None:
            key, _ = min(pending_reviews, key=lambda pair: (pair[1]['last_review'] or pair[1]['created'], pair[0]))
            return self.refresh_review(key, now, review_api=review_api, thread_reader=thread_reader)
        if candidate is None:
            return 'NO_CANDIDATE_NOT_TESTED'
        if type(candidate) is not ExactPR:
            raise StateBlocked('CANDIDATE_TYPE_INVALID')
        key, nonce = self.reserve(candidate, now)
        self.dispatch(key, nonce)
        return 'DISPATCHED_NOT_TEST_ACCEPTED'

    def policy(self, enabled):
        """Require a fresh credential-authenticated owner, never a PR actor.

        ports.owner() must independently GET authenticated user and repository
        owner identity; caller-provided event actor strings are insufficient.
        Arming is additionally impossible without separate operational acceptance.
        """
        user, repository = self.ports.owner()
        if (type(enabled) is not bool or type(user.get('id')) is not int
                or user['id'] != OWNER_ID or repository.get('full_name') != CONTROLLER_REPO
                or repository.get('owner', {}).get('id') != OWNER_ID):
            raise StateBlocked('AUTHENTICATED_OWNER_REQUIRED')
        if enabled and not self.accepted:
            raise StateBlocked('OPERATIONAL_ACCEPTANCE_REQUIRED')
        def update(state):
            state['policy']['enabled'] = enabled
            state['policy']['generation'] += 1
            if not enabled:
                for claim in state['claims'].values():
                    if claim['state'] == 'RESERVED':
                        claim['state'] = 'CANCELED_BEFORE_POST'
        self._change(update)

    def reserve(self, source, now):
        """Select one eligible fresh revision and preserve historical claims."""
        if type(now) is not int or now < 0:
            raise StateBlocked('CLOCK_INVALID')
        pr, branch = self.ports.source(source)
        _source(pr, branch, source)
        legacy = self.ports.legacy_claim(source)
        if legacy is not False:
            raise StateBlocked('LEGACY_CLAIM_OR_COLLECTION_UNCERTAIN')
        def update(state):
            if not self.accepted or not state['policy']['enabled']:
                raise StateBlocked('DISARMED_OR_NOT_ACCEPTED')
            key = revision_key(source)
            if key in state['claims']:
                raise StateBlocked('REVISION_ALREADY_CLAIMED')
            if any(c['state'] not in TERMINAL for c in state['claims'].values()):
                raise StateBlocked('OUTSTANDING_CLAIM')
            nonce = uuid.uuid4().hex
            state['claims'][key] = dict(pr=source.pr_number, head=source.head_sha,
                base=source.base_sha, controller=self.sha,
                generation=state['policy']['generation'], nonce=nonce,
                state='RESERVED', run_id=None, created=now, review='NOT_TESTED',
                review_checks=0, last_review=None)
            return key, nonce
        return self._change(update)

    def dispatch(self, key, nonce):
        """Fence before POST, recheck source/policy, bind only a verified run.

        Any exception after fencing leaves uncertainty. There is no retry,
        deletion, timeout expiry, automatic redispatch or silent claim reset.
        Disarm after the last policy check cannot recall an in-flight request.
        """
        def begin(state):
            claim = state['claims'].get(key)
            if (not self.accepted or not state['policy']['enabled'] or not claim
                    or claim['nonce'] != nonce or claim['state'] != 'RESERVED'
                    or claim['generation'] != state['policy']['generation']
                    or claim['controller'] != self.sha):
                raise StateBlocked('DISPATCH_FENCE_REJECTED')
            claim['state'] = 'DISPATCH_UNCERTAIN'
            return dict(claim)
        claim = self._change(begin)
        source = ExactPR(claim['pr'], claim['head'], claim['base'])
        pr, branch = self.ports.source(source)
        _source(pr, branch, source)
        _, state = self.store.load()
        validate(state)
        if (state['policy'] != dict(enabled=True, generation=claim['generation'])
                or state['claims'].get(key) != claim):
            raise StateBlocked('POLICY_OR_CLAIM_CHANGED_BEFORE_POST')
        status, body = self.ports.dispatch(self.sha, dict(
            pr_number=str(source.pr_number), head_sha=source.head_sha,
            base_sha=source.base_sha, claim_nonce=claim['nonce']))
        run_id = dispatch_run_id(status, body)
        self.reconcile(key, nonce, run_id)
        return run_id

    def reconcile(self, key, nonce, run_id):
        """Authenticate one known run, never guess a run from list ordering.

        Recovery requires a known ID from the direct response or independent
        owner evidence. Run metadata binds the controller/workflow only; source
        outputs still require independent advisory-byte verification later.
        """
        if type(run_id) is not int or not 0 < run_id < 2**63:
            raise StateBlocked('RUN_ID_INVALID')
        run = self.ports.run(run_id)
        def update(state):
            claim = state['claims'].get(key)
            if not claim or claim['nonce'] != nonce or claim['state'] not in {'DISPATCH_UNCERTAIN', 'RUN_BOUND'}:
                raise StateBlocked('RECONCILIATION_CLAIM_INVALID')
            self._run_identity(run, claim, run_id)
            if claim['run_id'] not in (None, run_id):
                raise StateBlocked('RUN_ALREADY_BOUND')
            claim['run_id'], claim['state'] = run_id, 'RUN_BOUND'
        self._change(update)

    @staticmethod
    def _run_identity(run, claim, run_id):
        """Allow queued/failed runs for recovery without implying a test PASS."""
        if (type(run) is not dict or type(run.get('id')) is not int or run['id'] != run_id
                or type(run.get('run_attempt')) is not int or run['run_attempt'] != 1
                or run.get('repository', {}).get('full_name') != CONTROLLER_REPO
                or run.get('head_sha') != claim['controller'] or run.get('event') != 'workflow_dispatch'
                or run.get('path') != WORKFLOW
                or run.get('display_title') != (f"Stage 6 PR {claim['pr']} h-{claim['head']} "
                    f"b-{claim['base']} claim-{claim['nonce']}")
                or run.get('html_url') != f'https://github.com/{CONTROLLER_REPO}/actions/runs/{run_id}'):
            raise StateBlocked('AUTHENTICATED_RUN_IDENTITY_MISMATCH')

    def observe(self, key, *, collect_advisory, review_api, thread_reader):
        """Reconcile source, run, existing advisory collector and CodeRabbit.

        collect_advisory(claim) must call the existing ordered provenance/byte
        collector with expectations pinned to this claim, controller and run ID.
        Its advisory marker never becomes TEST=PASS or receipt acceptance.
        """
        _, snapshot = self.store.load()
        validate(snapshot)
        claim = snapshot['claims'][key]
        if claim['state'] != 'RUN_BOUND':
            raise StateBlocked('RUN_NOT_BOUND')
        run = self.ports.run(claim['run_id'])
        self._run_identity(run, claim, claim['run_id'])
        if run.get('status') != 'completed':
            return 'PENDING_RUN'
        if run.get('conclusion') != 'success':
            result, review = 'RUN_FAILED', 'NOT_TESTED'
        else:
            source = ExactPR(claim['pr'], claim['head'], claim['base'])
            pr, branch = self.ports.source(source)
            _source(pr, branch, source)
            if collect_advisory(dict(claim)) != 'ADVISORY_COLLECTED_NOT_TEST_ACCEPTED':
                raise StateBlocked('ADVISORY_COLLECTION_FAILED')
            review = review_status(review_api, {'number': claim['pr'], 'sha': claim['head']},
                                   thread_reader=thread_reader)['status']
            pr, branch = self.ports.source(source)
            _source(pr, branch, source)
            result = 'ADVISORY_COMPLETE'
        def update(state):
            if state['claims'].get(key) != claim:
                raise StateBlocked('OBSERVATION_CLAIM_CHANGED')
            state['claims'][key]['state'] = result
            state['claims'][key]['review'] = review
            if result == 'RUN_FAILED':
                identifier = hashlib.sha256((key + ':FAILED_RUN').encode()).hexdigest()
                state['alerts'].setdefault(identifier, dict(state='PENDING', attempts=0,
                    updated=0, claim_key=key, code='FAILED_RUN'))
        self._change(update)
        return result

    def refresh_review(self, key, now, *, review_api, thread_reader):
        """Refresh a completed advisory's review with finite persistent budgets.

        Reserve each poll before API collection; restarts do not reset budgets.
        No review comment, code modification, merge or promotion is automatic.
        """
        if type(now) is not int or now < 0:
            raise StateBlocked('CLOCK_INVALID')
        def reserve(state):
            claim = state['claims'].get(key)
            if not claim or claim['state'] != 'ADVISORY_COMPLETE':
                raise StateBlocked('ADVISORY_NOT_COMPLETE')
            last = claim['last_review']
            if claim['review_checks'] >= 20 or last is not None and now - last < 60:
                raise StateBlocked('REVIEW_POLL_BUDGET_OR_INTERVAL')
            claim['review_checks'] += 1
            claim['last_review'] = now
            return dict(claim)
        claim = self._change(reserve)
        source = ExactPR(claim['pr'], claim['head'], claim['base'])
        pr, branch = self.ports.source(source)
        _source(pr, branch, source)
        result = review_status(review_api, {'number': claim['pr'], 'sha': claim['head']},
                               thread_reader=thread_reader)['status']
        pr, branch = self.ports.source(source)
        _source(pr, branch, source)
        def update(state):
            if state['claims'].get(key) != claim:
                raise StateBlocked('REVIEW_CLAIM_CHANGED')
            state['claims'][key]['review'] = result
        self._change(update)
        return result

    def tick(self, now, interval=300):
        """Deduplicate native/fallback ticks; fail closed on time regression."""
        if type(now) is not int or now < 0 or type(interval) is not int or interval < 300:
            raise StateBlocked('CLOCK_OR_INTERVAL_INVALID')
        def update(state):
            last = state['last_tick']
            if last is not None and now < last:
                raise StateBlocked('CLOCK_REGRESSED')
            if last is not None and now - last < interval:
                return 'RECENT_TICK_NOOP'
            state['last_tick'] = now
            return 'TICK_RECORDED_NOT_DISPATCH_AUTHORIZED'
        return self._change(update)

    def notify(self, *, key, code, now, deliver):
        """Reserve a bounded alert attempt before sending a sanitized payload.

        Delivery callback must support the supplied idempotency key and return
        that exact key only after independently verified delivery. Unknown send
        outcomes require receipt reconciliation; never blindly resend.
        """
        if (type(now) is not int or now < 0 or code not in {
                'MISSED_RUN', 'FAILED_RUN', 'COLLECTION_FAILED', 'REVIEW_FINDING', 'RECOVERY_REQUIRED'}):
            raise StateBlocked('ALERT_EXPECTATION_INVALID')
        alert_id = hashlib.sha256((key + ':' + code).encode()).hexdigest()
        def reserve(state):
            if key not in state['claims']:
                raise StateBlocked('ALERT_CLAIM_MISSING')
            prior = state['alerts'].get(alert_id)
            if prior and prior['state'] in {'DELIVERED', 'DELIVERY_UNCERTAIN'}:
                return False
            if prior and (prior['attempts'] >= 3 or prior['attempts'] > 0 and now - prior['updated'] < 300):
                return False
            state['alerts'][alert_id] = dict(state='DELIVERY_UNCERTAIN',
                attempts=1 if prior is None else prior['attempts'] + 1, updated=now,
                claim_key=key, code=code)
            return True
        if not self._change(reserve):
            return 'ALERT_ALREADY_DELIVERED_OR_RECONCILIATION_REQUIRED'
        receipt = deliver({'id': alert_id, 'code': code})
        self.alert_receipt(alert_id, receipt)
        return 'DELIVERY_VERIFIED' if receipt is not None else 'DELIVERY_NOT_SENT_RETRY_PENDING'

    def alert_receipt(self, alert_id, receipt):
        """Resolve uncertain delivery only from an authenticated exact receipt.

        None explicitly means confirmed NOT SENT, permitting a bounded later
        attempt. Exceptions/missing evidence preserve uncertainty across restart.
        """
        if receipt is not None and receipt != alert_id:
            raise StateBlocked('ALERT_RECEIPT_MISMATCH')
        def update(state):
            alert = state['alerts'].get(alert_id)
            if not alert or alert['state'] != 'DELIVERY_UNCERTAIN':
                raise StateBlocked('ALERT_NOT_UNCERTAIN')
            alert['state'] = 'PENDING' if receipt is None else 'DELIVERED'
        self._change(update)
