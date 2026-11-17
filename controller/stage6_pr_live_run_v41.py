"""Stage 6 manual advisory: distinguish active verifier from completed run.

A verifier running within a workflow cannot require the *whole workflow* to
be completed. This accepts in_progress / null only as a NON-ACCEPTANCE advisory
state, and still requires independent successful source-job checks downstream.
"""
from __future__ import annotations
from dataclasses import dataclass
from stage6_pr_identity_v32 import IdentityRejected, verify_controller_run

@dataclass(frozen=True)
class RunState:
    state: str
    test_accepted: bool = False
    publication_authorized: bool = False
    unattended_dispatch_enabled: bool = False


def verify_advisory_run(run: object, *, controller_sha: str, run_id: int,
                        attempt: int, workflow_path: str) -> RunState:
    """Check run identity, allowing an active verifier with no final conclusion.

    Caller must separately establish the source job completed successfully,
    check required steps, artifact, test bytes, final PR freshness and safety.
    This is NOT an overall workflow PASS, even on completed/success evidence.
    """
    if type(run) is not dict:
        raise IdentityRejected('RUN_STATE_INVALID')
    identity = dict(run)
    state = (run.get('status'), run.get('conclusion'))
    if state == ('in_progress', None):
        # Keep strict identity validation in one canonical place; alter ONLY
        # the completion fields of an isolated throwaway copy for that check.
        identity['status'] = 'completed'
        identity['conclusion'] = 'success'
        verify_controller_run(identity, controller_sha=controller_sha,
                              run_id=run_id, attempt=attempt,
                              workflow_path=workflow_path)
        return RunState('ACTIVE_VERIFIER_NOT_TEST_ACCEPTED')
    if state == ('completed', 'success'):
        verify_controller_run(run, controller_sha=controller_sha,
                              run_id=run_id, attempt=attempt,
                              workflow_path=workflow_path)
        return RunState('COMPLETED_RUN_ADVISORY_ONLY')
    raise IdentityRejected('RUN_STATE_UNVERIFIED')
