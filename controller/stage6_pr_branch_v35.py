"""Offline PR base-tip freshness gate; no network, dispatch or authorization.

Only use authenticated snapshots from the same intended GitHub repository.
The trusted caller remains responsible for retrieving the snapshots and for
rechecking after the test and before accepting any run-bound evidence.
"""
from __future__ import annotations

from stage6_pr_identity_v32 import ExactPR, IdentityRejected, verify_stable_pr

SOURCE = 'TenchiMisaki/romarr'
BASE_REF = 'main'


def verify_base_branch(*, before: object, after: object, expected: ExactPR,
                       repository: str = SOURCE, branch: str = BASE_REF) -> str:
    """Require the GitHub branch tip to equal the exact expected PR base SHA.

    This deliberately blocks older open PRs whose recorded base SHA lags the
    current destination branch. It does not silently redefine their tested
    base. A separate source selection/reconciliation stage must happen first.
    """
    if (type(expected) is not ExactPR or type(repository) is not str
            or repository != SOURCE or type(branch) is not str
            or branch != BASE_REF):
        raise IdentityRejected('BASE_BRANCH_EXPECTATION_INVALID')
    for snapshot in (before, after):
        if type(snapshot) is not dict:
            raise IdentityRejected('BRANCH_RESPONSE_SHAPE_INVALID')
        commit = snapshot.get('commit')
        if (snapshot.get('name') != branch or type(commit) is not dict
                or commit.get('sha') != expected.base_sha):
            raise IdentityRejected('BASE_BRANCH_TIP_CHANGED_OR_STALE')
    return 'BASE_BRANCH_TIP_STABLE'


def verify_pr_and_base(*, pr_before: object, pr_after: object,
                       branch_before: object, branch_after: object,
                       expected: ExactPR) -> str:
    """Combine PR snapshot consistency and independently read branch-tip parity."""
    verify_stable_pr(pr_before, pr_after, expected)
    verify_base_branch(before=branch_before, after=branch_after, expected=expected)
    return 'PR_AND_BASE_SNAPSHOT_IDENTITIES_STABLE_NOT_TEST_ACCEPTED'


__all__ = ['verify_base_branch', 'verify_pr_and_base']
