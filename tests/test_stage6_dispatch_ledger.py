"""Offline durable-claim, disarm, interruption and real worker-race checks."""
import copy
from contextlib import closing
from concurrent.futures import ThreadPoolExecutor
from dataclasses import replace
from pathlib import Path
import sqlite3
import tempfile
import threading
import unittest

from stage6_dispatch_ledger import Ledger, LedgerBlocked
from stage6_pr_identity_v32 import ExactPR, IdentityRejected


class DispatchLedgerTests(unittest.TestCase):
    """Exercise a private disposable database without invoking any dispatcher."""

    def setUp(self):
        """Build one exact synthetic public-source identity and disabled ledger."""
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.path = str(Path(self.temp.name) / 'ledger.sqlite')
        self.ledger = Ledger(self.path)
        self.ledger.initialize()
        self.expected = ExactPR(42, 'a' * 40, 'b' * 40)
        self.controller = 'c' * 40
        self.pr = {'number': 42, 'state': 'open', 'draft': False, 'merged': False,
                   'title': 'fix: synthetic fixture',
                   'html_url': 'https://github.com/TenchiMisaki/romarr/pull/42',
                   'head': {'sha': 'a' * 40, 'ref': 'fix/synthetic', 'repo': {'full_name': 'TenchiMisaki/romarr'}},
                   'base': {'sha': 'b' * 40, 'ref': 'main', 'repo': {'full_name': 'TenchiMisaki/romarr'}}}
        self.branch = {'name': 'main', 'commit': {'sha': 'b' * 40}}

    def reserve(self, ledger=None):
        """Reserve the fixture using the real ledger implementation."""
        return (ledger or self.ledger).reserve(self.expected, self.controller,
                                              pr=self.pr, branch=self.branch)

    def arm(self):
        """Model the separate explicit owner action in an offline fixture."""
        self.ledger.set_enabled(True)

    def test_default_and_restart_remain_disabled(self):
        for ledger in (self.ledger, Ledger(self.path)):
            with self.assertRaisesRegex(LedgerBlocked, 'DISARMED'):
                self.reserve(ledger)

    def test_success_records_uncertainty_before_return(self):
        self.arm()
        ticket = self.reserve()
        self.assertEqual(self.ledger.begin_dispatch(ticket, pr=self.pr, branch=self.branch),
                         'DISPATCH_UNCERTAIN_NOT_TEST_ACCEPTED')
        with closing(sqlite3.connect(self.path)) as db:
            self.assertEqual(db.execute('SELECT state FROM claims').fetchone(), ('DISPATCH_UNCERTAIN',))

    def test_duplicate_and_restart_after_reservation_block(self):
        self.arm()
        self.reserve()
        with self.assertRaises(LedgerBlocked):
            self.reserve(Ledger(self.path))

    def test_interrupted_or_uncertain_post_never_retries(self):
        self.arm()
        ticket = self.reserve()
        self.ledger.begin_dispatch(ticket, pr=self.pr, branch=self.branch)
        restarted = Ledger(self.path)
        with self.assertRaises(LedgerBlocked):
            restarted.begin_dispatch(ticket, pr=self.pr, branch=self.branch)
        with self.assertRaises(LedgerBlocked):
            self.reserve(restarted)

    def test_disarm_blocks_reserved_work_and_rearm_does_not_revive_it(self):
        self.arm()
        ticket = self.reserve()
        self.ledger.set_enabled(False)
        for rearm in (False, True):
            if rearm:
                self.arm()
            with self.assertRaisesRegex(LedgerBlocked, 'POLICY_CHANGED'):
                self.ledger.begin_dispatch(ticket, pr=self.pr, branch=self.branch)

    def test_disarm_preserves_uncertain_claim(self):
        self.arm()
        ticket = self.reserve()
        self.ledger.begin_dispatch(ticket, pr=self.pr, branch=self.branch)
        self.ledger.set_enabled(False)
        self.arm()
        with self.assertRaises(LedgerBlocked):
            self.reserve()

    def test_real_concurrent_workers_reserve_at_most_once(self):
        self.arm()
        barrier = threading.Barrier(8)
        def worker(_):
            """Race independent database connections without mocked locks."""
            barrier.wait(timeout=10)
            try:
                self.reserve(Ledger(self.path))
                return True
            except LedgerBlocked:
                return False
        with ThreadPoolExecutor(max_workers=8) as pool:
            self.assertEqual(sum(pool.map(worker, range(8))), 1)

    def test_changed_source_after_reservation_is_rejected(self):
        self.arm()
        ticket = self.reserve()
        changed = copy.deepcopy(self.pr)
        changed['head']['sha'] = 'd' * 40
        with self.assertRaises(IdentityRejected):
            self.ledger.begin_dispatch(ticket, pr=changed, branch=self.branch)
        with closing(sqlite3.connect(self.path)) as db:
            self.assertEqual(db.execute('SELECT state FROM claims').fetchone(), ('RESERVED',))

    def test_changed_base_and_stale_branch_are_rejected(self):
        self.arm()
        changed = copy.deepcopy(self.pr)
        changed['base']['sha'] = 'd' * 40
        with self.assertRaises(IdentityRejected):
            self.ledger.reserve(self.expected, self.controller, pr=changed, branch=self.branch)
        with self.assertRaises(IdentityRejected):
            self.ledger.reserve(self.expected, self.controller, pr=self.pr,
                                branch={'name': 'main', 'commit': {'sha': 'd' * 40}})

    def test_draft_backlog_review_closed_foreign_candidates_rejected(self):
        self.arm()
        for field, value in [('draft', True), ('state', 'closed'), ('title', 'Backlog: deferred'), ('title', 'Review: isolated')]:
            changed = copy.deepcopy(self.pr)
            changed[field] = value
            with self.subTest(field=field, value=value), self.assertRaises(IdentityRejected):
                self.ledger.reserve(self.expected, self.controller, pr=changed, branch=self.branch)
        for ref in ('review/candidate', 'notes/deferred'):
            changed = copy.deepcopy(self.pr)
            changed['head']['ref'] = ref
            with self.assertRaises(IdentityRejected):
                self.ledger.reserve(self.expected, self.controller, pr=changed, branch=self.branch)
        changed = copy.deepcopy(self.pr)
        changed['head']['repo']['full_name'] = 'example/other'
        with self.assertRaises(IdentityRejected):
            self.ledger.reserve(self.expected, self.controller, pr=changed, branch=self.branch)

    def test_forged_ticket_and_duplicate_begin_are_rejected(self):
        self.arm()
        ticket = self.reserve()
        for forged in (replace(ticket, nonce='0' * 32), replace(ticket, controller_sha='d' * 40)):
            with self.assertRaises(LedgerBlocked):
                self.ledger.begin_dispatch(forged, pr=self.pr, branch=self.branch)
        self.ledger.begin_dispatch(ticket, pr=self.pr, branch=self.branch)
        with self.assertRaises(LedgerBlocked):
            self.ledger.begin_dispatch(ticket, pr=self.pr, branch=self.branch)

    def test_existing_unknown_and_corrupt_databases_are_preserved(self):
        with self.assertRaises(LedgerBlocked):
            self.ledger.initialize()
        other = Path(self.temp.name) / 'corrupt.sqlite'
        other.write_bytes(b'not a database')
        with self.assertRaises(LedgerBlocked):
            Ledger(str(other)).initialize()
        self.assertEqual(other.read_bytes(), b'not a database')

    def test_invalid_policy_and_controller_identity_block(self):
        for value in (1, 'true', None):
            with self.assertRaises(LedgerBlocked):
                self.ledger.set_enabled(value)
        self.arm()
        with self.assertRaises(IdentityRejected):
            self.ledger.reserve(self.expected, 'main', pr=self.pr, branch=self.branch)


if __name__ == '__main__':
    unittest.main()
