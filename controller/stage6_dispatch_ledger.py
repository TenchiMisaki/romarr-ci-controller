"""Offline Stage 6 claim/recovery prototype; no network or test authorization.

Use only a caller-owned private SQLite file. This is not an installed dispatcher
or an accepted distributed lock. A future adapter must independently authenticate
fresh PR snapshots and enforce policy again at its actual dispatch boundary.
"""
from __future__ import annotations

from contextlib import contextmanager
from dataclasses import dataclass
import sqlite3
import uuid

from stage6_pr_branch_v35 import verify_pr_and_base
from stage6_pr_identity_v32 import ExactPR, IdentityRejected, SHA


class LedgerBlocked(RuntimeError):
    """An unknown, stale, duplicate or unavailable state blocks progression."""


@dataclass(frozen=True)
class Ticket:
    """Capability identifying one immutable reservation, never a receipt."""

    source: ExactPR
    controller_sha: str
    generation: int
    nonce: str


def _source(pr, branch, expected):
    """Apply existing exact-source checks plus ordinary-candidate exclusions."""
    verify_pr_and_base(pr_before=pr, pr_after=pr, branch_before=branch,
                       branch_after=branch, expected=expected)
    title = pr.get('title')
    ref = pr['head'].get('ref')
    if (type(title) is not str or type(ref) is not str
            or title.casefold().startswith(('backlog:', 'review:'))
            or ref.casefold().startswith(('notes/', 'review/'))
            or pr['base'].get('ref') != 'main'):
        raise IdentityRejected('DISPATCH_CANDIDATE_EXCLUDED')


class Ledger:
    """Persist local reservations atomically; startup always preserves policy."""

    def __init__(self, path):
        self.path = path

    @contextmanager
    def _transaction(self):
        """Serialize one local operation, rolling back and failing closed."""
        db = None
        try:
            db = sqlite3.connect(self.path, timeout=0.1, isolation_level=None)
            db.execute('BEGIN IMMEDIATE')
            yield db
            db.execute('COMMIT')
        except sqlite3.Error as exc:
            raise LedgerBlocked('LEDGER_UNAVAILABLE') from exc
        finally:
            if db is not None:
                if db.in_transaction:
                    db.rollback()
                db.close()

    def initialize(self):
        """Create an empty disabled ledger; refuse any preexisting schema."""
        with self._transaction() as db:
            if db.execute('SELECT name FROM sqlite_master').fetchone():
                raise LedgerBlocked('LEDGER_ALREADY_INITIALIZED_OR_UNKNOWN')
            db.execute('CREATE TABLE policy (singleton INTEGER PRIMARY KEY CHECK(singleton=1), enabled INTEGER NOT NULL CHECK(enabled IN (0,1)), generation INTEGER NOT NULL)')
            db.execute('INSERT INTO policy VALUES (1,0,0)')
            db.execute('CREATE TABLE claims (pr INTEGER NOT NULL, head TEXT NOT NULL, base TEXT NOT NULL, controller TEXT NOT NULL, generation INTEGER NOT NULL, nonce TEXT NOT NULL UNIQUE, state TEXT NOT NULL CHECK(state IN (\'RESERVED\',\'DISPATCH_UNCERTAIN\')), PRIMARY KEY(pr,head,base))')

    def set_enabled(self, enabled):
        """Model an explicit owner policy action, invalidating older tickets.

        No environment variable, startup path or worker calls this automatically.
        It does not delete claims or authorize a real unattended test.
        """
        if type(enabled) is not bool:
            raise LedgerBlocked('POLICY_MUST_BE_BOOLEAN')
        with self._transaction() as db:
            if db.execute('UPDATE policy SET enabled=?, generation=generation+1 WHERE singleton=1', (int(enabled),)).rowcount != 1:
                raise LedgerBlocked('POLICY_MISSING')

    def reserve(self, expected, controller_sha, *, pr, branch):
        """Reserve one exact revision; existing claims always block duplicates."""
        _source(pr, branch, expected)
        if type(controller_sha) is not str or not SHA.fullmatch(controller_sha):
            raise IdentityRejected('CONTROLLER_SHA_INVALID')
        with self._transaction() as db:
            policy = db.execute('SELECT enabled,generation FROM policy WHERE singleton=1').fetchone()
            if policy is None or policy[0] != 1:
                raise LedgerBlocked('DISARMED')
            if db.execute('SELECT 1 FROM claims').fetchone():
                raise LedgerBlocked('EXISTING_CLAIM_REQUIRES_RECONCILIATION')
            ticket = Ticket(expected, controller_sha, policy[1], uuid.uuid4().hex)
            db.execute('INSERT INTO claims VALUES (?,?,?,?,?,?,?)',
                       (expected.pr_number, expected.head_sha, expected.base_sha,
                        controller_sha, ticket.generation, ticket.nonce, 'RESERVED'))
            return ticket

    def begin_dispatch(self, ticket, *, pr, branch):
        """Persist uncertainty before returning; never retry a returned ticket.

        A crash, timeout, rejected POST or missing run ID needs independent manual
        reconciliation. This prototype deliberately has no claim deletion, reset,
        run binding, completion, automatic retry or network adapter.
        """
        if type(ticket) is not Ticket:
            raise LedgerBlocked('TICKET_INVALID')
        _source(pr, branch, ticket.source)
        with self._transaction() as db:
            policy = db.execute('SELECT enabled,generation FROM policy WHERE singleton=1').fetchone()
            if policy != (1, ticket.generation):
                raise LedgerBlocked('DISARMED_OR_POLICY_CHANGED')
            row = db.execute('SELECT controller,generation,nonce,state FROM claims WHERE pr=? AND head=? AND base=?',
                             (ticket.source.pr_number, ticket.source.head_sha, ticket.source.base_sha)).fetchone()
            if row != (ticket.controller_sha, ticket.generation, ticket.nonce, 'RESERVED'):
                raise LedgerBlocked('CLAIM_CHANGED_OR_DISPATCH_UNCERTAIN')
            db.execute('UPDATE claims SET state=\'DISPATCH_UNCERTAIN\' WHERE nonce=?', (ticket.nonce,))
        return 'DISPATCH_UNCERTAIN_NOT_TEST_ACCEPTED'
