"""Pure, fail-closed Stage 6 candidate for final PR receipt identity reconciliation.

No network access, dispatch, GitHub writes, scheduling or trusted test approval.
Snapshots must be collected independently by a credential-isolated caller.
"""
from __future__ import annotations

from dataclasses import dataclass

from stage6_pr_archive_v34 import verify_advisory_bytes
from stage6_pr_branch_v35 import verify_base_branch
from stage6_pr_identity_v32 import ExactPR, IdentityRejected, verify_stable_pr
from stage6_pr_receipt_v33 import ExpectedArtifact, verify_metadata


@dataclass(frozen=True)
class FinalEvidence:
    """Caller-supplied immutable expectations; never sourced from the test ZIP."""
    expected: ExpectedArtifact
    source_sha: str

    def __post_init__(self):
        if type(self.expected) is not ExpectedArtifact:
            raise IdentityRejected('FINAL_EXPECTATION_INVALID')
        if type(self.source_sha) is not str or self.source_sha != self.expected.pr.head_sha:
            raise IdentityRejected('TESTED_SOURCE_SHA_MISMATCH')


def verify_final_candidate(*, evidence: FinalEvidence,
                           pr_before: object, pr_after: object, pr_final: object,
                           branch_before: object, branch_after: object, branch_final: object,
                           run: object, jobs: object, artifact: object,
                           raw_zip: bytes) -> str:
    """Reconcile exact PR/base identity, REST metadata, bytes, then final freshness.

    The final checks must occur after byte collection in the trusted caller;
    this pure function does not establish network read order or API authenticity.
    Returns advisory-only status. A separate authorization and acceptance
    implementation is required for any trusted changing-PR pytest receipt.
    """
    if type(evidence) is not FinalEvidence:
        raise IdentityRejected('FINAL_EVIDENCE_TYPE_INVALID')
    expected = evidence.expected
    verify_base_branch(before=branch_before, after=branch_after, expected=expected.pr)
    verify_metadata(before=pr_before, after=pr_after, run=run, jobs=jobs,
                    artifact=artifact, expected=expected)
    if type(raw_zip) is not bytes:
        raise IdentityRejected('ARCHIVE_BYTES_MISSING')
    # v34 returns a non-acceptance marker after verifying canonical content.
    result = verify_advisory_bytes(raw_zip, expected_archive_sha256=expected.artifact_sha256,
                                   expected_run_id=expected.run_id,
                                   expected_head_sha=expected.pr.head_sha,
                                   expected_base_sha=expected.pr.base_sha)
    if result.state != 'ADVISORY_BYTES_VERIFIED_NOT_ACCEPTED':
        raise IdentityRejected('ARCHIVE_NOT_VERIFIED')
    # A final independent PR and base-tip snapshot is mandatory. If these
    # change while bytes are downloaded, do not accept an obsolete head/base.
    verify_stable_pr(pr_after, pr_final, expected.pr)
    verify_base_branch(before=branch_after, after=branch_final, expected=expected.pr)
    return 'FINAL_PR_ADVISORY_IDENTITIES_AND_BYTES_VERIFIED_NOT_TEST_ACCEPTED'


__all__ = ['FinalEvidence', 'verify_final_candidate']
