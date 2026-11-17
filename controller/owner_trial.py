"""Dormant owner-controlled, one-source advisory trial; no installed caller.

The trusted host must obtain approval independently and protect its expected
digest, controller revision, clock and API roles from PR/source influence.
Hashing arbitrary caller JSON does not authenticate approval. This module loads
no credentials, reads no environment variables and accepts no workflow inputs.
"""
from __future__ import annotations

import hashlib
import json
import re
import time
from dataclasses import dataclass

from controller_cycle import Controller, OWNER_ID, WORKFLOW
from durable_state import StateBlocked, encode
from stage6_pr_identity_v32 import CONTROLLER_REPO, ExactPR, SOURCE_REPO, SHA

SCOPE = 'single-revision-advisory-trial-v1'
MAX_APPROVAL_BYTES = 8192


@dataclass(frozen=True, init=False)
class TrialApproval:
    """Check canonical owner-approved bytes against an independently pinned hash.

    The pin is a trusted deployment input, not a field inside the approval.
    Fresh authenticated owner checks still happen in Controller.policy. Approval
    covers one source/controller and time window, not unattended automation,
    source-test acceptance, publication, merge, deployment or fallback retirement.
    """

    controller_sha: str
    source: ExactPR
    issued: int
    expires: int
    clock: object

    def __init__(self, raw, *, expected_digest, controller_sha, clock=None):
        if (type(raw) is not bytes or not 0 < len(raw) <= MAX_APPROVAL_BYTES
                or type(expected_digest) is not str
                or not re.fullmatch('[0-9a-f]{64}', expected_digest)
                or type(controller_sha) is not str or not SHA.fullmatch(controller_sha)
                or hashlib.sha256(raw).hexdigest() != expected_digest):
            raise StateBlocked('TRIAL_APPROVAL_IDENTITY_INVALID')
        try:
            record = json.loads(raw)
            if encode(record) != raw:
                raise ValueError('Noncanonical approval')
            if (set(record) != {'schema', 'scope', 'repository', 'owner_id',
                    'controller', 'workflow', 'source_repository', 'pr', 'head',
                    'base', 'issued', 'expires'}
                    or type(record['schema']) is not int or record['schema'] != 1
                    or record['scope'] != SCOPE or record['repository'] != CONTROLLER_REPO
                    or type(record['owner_id']) is not int or record['owner_id'] != OWNER_ID
                    or record['controller'] != controller_sha or record['workflow'] != WORKFLOW
                    or record['source_repository'] != SOURCE_REPO
                    or type(record['issued']) is not int or type(record['expires']) is not int
                    or not 0 <= record['issued'] < record['expires'] < 2**63):
                raise ValueError('Invalid approval')
            source = ExactPR(record['pr'], record['head'], record['base'])
        except (ValueError, TypeError, KeyError, StateBlocked):
            raise StateBlocked('TRIAL_APPROVAL_CONTENT_INVALID') from None
        trusted_clock = clock if clock is not None else lambda: int(time.time())
        if not callable(trusted_clock):
            raise StateBlocked('TRIAL_CLOCK_INVALID')
        for name, value in dict(controller_sha=controller_sha, source=source,
                issued=record['issued'], expires=record['expires'], clock=trusted_clock).items():
            object.__setattr__(self, name, value)

    def permits(self, *, controller_sha, source=None):
        """Recheck the trusted clock and exact scope at every authority boundary."""
        now = self.clock()
        if type(now) is not int or not 0 <= now < 2**63:
            raise StateBlocked('TRIAL_CLOCK_INVALID')
        return (controller_sha == self.controller_sha and self.issued <= now < self.expires
                and (source is None or type(source) is ExactPR and source == self.source))


class OwnerTrialController(Controller):
    """Bind the existing coordinator to one separately approved advisory trial.

    Arming still requires fresh authenticated owner/repository reads and durable
    CAS/readback. Expiry blocks new reservations and dispatch but never deletes
    unknown claims or prevents authenticated disarm/run reconciliation. No source
    execution, scheduler, credential service or owner entrypoint is installed.
    """

    def __init__(self, store, ports, *, controller_sha, approval):
        if type(approval) is not TrialApproval or approval.controller_sha != controller_sha:
            raise StateBlocked('TRIAL_APPROVAL_BINDING_INVALID')
        super().__init__(store, ports, controller_sha=controller_sha)
        self.approval = approval

    def _accepted(self, source=None):
        """Require the pinned trial scope before arming, reserving and POST."""
        return self.approval.permits(controller_sha=self.sha, source=source)

    def _dispatch(self, source, inputs):
        """Recheck after the adapter's last tag lookup, before its POST request."""
        return self.ports.dispatch(self.sha, inputs, pre_post=lambda: self._accepted(source))
