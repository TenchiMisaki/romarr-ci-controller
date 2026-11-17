"""Synthetic negative-path checks for branch-tip freshness, never hosted tests."""
import copy
import pytest
from stage6_pr_identity_v32 import ExactPR, IdentityRejected
from stage6_pr_branch_v35 import verify_base_branch, verify_pr_and_base

H = 'a' * 40
B = 'b' * 40
OTHER = 'c' * 40


def identity():
    return ExactPR(29, H, B)


def branch(sha=B):
    return {'name': 'main', 'commit': {'sha': sha}}


def pr():
    return {
        'number': 29, 'state': 'open', 'draft': False, 'merged': False,
        'html_url': 'https://github.com/TenchiMisaki/romarr/pull/29',
        'head': {'sha': H, 'repo': {'full_name': 'TenchiMisaki/romarr'}},
        'base': {'sha': B, 'repo': {'full_name': 'TenchiMisaki/romarr'}},
    }


def test_stable_branch_and_pr():
    assert verify_pr_and_base(pr_before=pr(), pr_after=copy.deepcopy(pr()),
        branch_before=branch(), branch_after=branch(), expected=identity()) \
        == 'PR_AND_BASE_SNAPSHOT_IDENTITIES_STABLE_NOT_TEST_ACCEPTED'


@pytest.mark.parametrize('before,after', [(B,OTHER), (OTHER,B), (OTHER,OTHER)])
def test_branch_drift_and_stale_base_fail(before,after):
    with pytest.raises(IdentityRejected, match='BASE_BRANCH_TIP_CHANGED_OR_STALE'):
        verify_base_branch(before=branch(before), after=branch(after), expected=identity())


@pytest.mark.parametrize('bad', [None, {}, {'name':'main'},
                                  {'name':'feature','commit':{'sha':B}},
                                  {'name':'main','commit':[]},
                                  {'name':'main','commit':{'sha':123}},
                                  {'name':'main','commit':{'sha':B.upper()}}])
def test_incomplete_or_malformed_branch_fails(bad):
    with pytest.raises(IdentityRejected):
        verify_base_branch(before=branch(), after=bad, expected=identity())


def test_wrong_repository_and_branch_expectation_fail():
    for overrides in ({'repository':'BlizzHacker/romarr'},{'branch':'master'}):
        with pytest.raises(IdentityRejected, match='BASE_BRANCH_EXPECTATION_INVALID'):
            verify_base_branch(before=branch(), after=branch(),expected=identity(),**overrides)


def test_pr_changed_while_branch_stable_fails():
    after=pr()
    after['head']['sha']=OTHER
    with pytest.raises(IdentityRejected, match='PR_SOURCE_IDENTITY_MISMATCH'):
        verify_pr_and_base(pr_before=pr(), pr_after=after,
                           branch_before=branch(), branch_after=branch(), expected=identity())


def test_live_observed_pr29_base_drift_rejection():
    # Exact REST-derived values observed during the November 16 audit.
    expected=ExactPR(29,'d62d00778aa5bd2dbce9a862774522083ebae7a9',
                       '29f52812ff53b58c2f21e910ba267a87acb922a3')
    current=branch('74755b337a8bb4364e533cfab25b0d6377b5c86f')
    with pytest.raises(IdentityRejected, match='BASE_BRANCH_TIP_CHANGED_OR_STALE'):
        verify_base_branch(before=current,after=current,expected=expected)
