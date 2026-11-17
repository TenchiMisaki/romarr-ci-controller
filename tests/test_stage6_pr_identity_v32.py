"""Offline negative and positive tests for Stage 6 PR identity prototype."""
import copy
import pytest

from stage6_pr_identity_v32 import (
    ExactPR, IdentityRejected, verify_pr, verify_stable_pr, verify_controller_run,
)

H = "a" * 40
B = "b" * 40
C = "c" * 40
EX = ExactPR(29, H, B)
PATH = ".github/workflows/stage6-manual-artifact-readback-v28-CANDIDATE.yml"


def fresh_pr():
    repo = {"full_name": "TenchiMisaki/romarr"}
    return {"number": 29, "state": "open", "draft": False, "merged": False,
            "html_url": "https://github.com/TenchiMisaki/romarr/pull/29",
            "head": {"sha": H, "repo": copy.deepcopy(repo)},
            "base": {"sha": B, "repo": copy.deepcopy(repo)}}


def fresh_run():
    return {"id": 123, "run_attempt": 1, "head_sha": C,
            "repository": {"full_name": "TenchiMisaki/romarr-ci-controller"},
            "path": PATH, "event": "workflow_dispatch", "status": "completed",
            "conclusion": "success"}


def test_positive_exact_pr():
    verify_pr(fresh_pr(), EX)
    verify_stable_pr(fresh_pr(), fresh_pr(), EX)


@pytest.mark.parametrize("field,value", [
    ("number", True), ("number", 30), ("state", "closed"),
    ("draft", True), ("merged", True), ("html_url", "https://evil.invalid"),
])
def test_bad_pr_root_rejected(field, value):
    p = fresh_pr()
    p[field] = value
    with pytest.raises(IdentityRejected):
        verify_pr(p, EX)


@pytest.mark.parametrize("field,value", [
    ("head", "f" * 40), ("base", "f" * 40),
])
def test_moving_source_rejected(field, value):
    p = fresh_pr()
    p[field]["sha"] = value
    with pytest.raises(IdentityRejected):
        verify_pr(p, EX)


def test_changed_base_during_execution_rejected():
    p = fresh_pr()
    q = fresh_pr()
    q["base"]["sha"] = "f" * 40
    with pytest.raises(IdentityRejected):
        verify_stable_pr(p, q, EX)


@pytest.mark.parametrize("side", ["head", "base"])
def test_foreign_repo_rejected(side):
    p = fresh_pr()
    p[side]["repo"]["full_name"] = "BlizzHacker/romarr"
    with pytest.raises(IdentityRejected):
        verify_pr(p, EX)


def test_missing_identity_rejected():
    p = fresh_pr()
    del p["head"]["repo"]
    with pytest.raises(IdentityRejected):
        verify_pr(p, EX)


def test_invalid_expected_identity_rejected():
    with pytest.raises(IdentityRejected):
        ExactPR(True, H, B)
    with pytest.raises(IdentityRejected):
        ExactPR(29, "not-a-sha", B)


def test_positive_run_identity():
    verify_controller_run(fresh_run(), controller_sha=C, run_id=123, attempt=1, workflow_path=PATH)


@pytest.mark.parametrize("field,value", [
    ("id", True), ("id", 124), ("run_attempt", 2),
    ("head_sha", "f" * 40), ("event", "pull_request"),
    ("status", "in_progress"), ("conclusion", "failure"),
    ("path", ".github/workflows/another.yml"),
])
def test_bad_run_rejected(field, value):
    r = fresh_run()
    r[field] = value
    with pytest.raises(IdentityRejected):
        verify_controller_run(r, controller_sha=C, run_id=123, attempt=1, workflow_path=PATH)


def test_foreign_controller_repo_rejected():
    r = fresh_run()
    r["repository"]["full_name"] = "other/repo"
    with pytest.raises(IdentityRejected):
        verify_controller_run(r, controller_sha=C, run_id=123, attempt=1, workflow_path=PATH)


def test_path_traversal_expectation_rejected():
    with pytest.raises(IdentityRejected):
        verify_controller_run(fresh_run(), controller_sha=C, run_id=123, attempt=1,
                              workflow_path=".github/workflows/../evil.yml")
