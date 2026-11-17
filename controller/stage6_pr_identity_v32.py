"""Fail-closed, offline snapshot identity checks for a future Stage 6 PR canary.

Candidate only. No network, GitHub credentials, dispatches, claims, or acceptance
receipts. A trusted caller must retrieve fresh authenticated snapshots, ensure
collections are complete, and perform separate source, job and artifact checks.
"""
from __future__ import annotations

from dataclasses import dataclass
import re

SOURCE_REPO = "TenchiMisaki/romarr"
CONTROLLER_REPO = "TenchiMisaki/romarr-ci-controller"
SHA = re.compile(r"[0-9a-f]{40}\Z")


class IdentityRejected(ValueError):
    """The supplied identity or an observed GitHub snapshot is inconsistent."""


def _sha(value: object) -> bool:
    return type(value) is str and SHA.fullmatch(value) is not None


def _positive(value: object) -> bool:
    return type(value) is int and value > 0


def _obj(value: object) -> dict:
    if type(value) is not dict:
        raise IdentityRejected("INVALID_SNAPSHOT_SHAPE")
    return value


@dataclass(frozen=True)
class ExactPR:
    pr_number: int
    head_sha: str
    base_sha: str

    def __post_init__(self) -> None:
        if not _positive(self.pr_number) or not _sha(self.head_sha) or not _sha(self.base_sha):
            raise IdentityRejected("INVALID_EXPECTED_IDENTITY")


def verify_pr(pr: object, expected: ExactPR) -> None:
    """Verify an authenticated, fresh public fork PR snapshot against both SHAs.

    Any missing, changed, draft, closed, foreign-repository, or merged PR rejects.
    This does not independently establish git object ancestry or source safety.
    """
    if type(expected) is not ExactPR:
        raise IdentityRejected("EXPECTED_IDENTITY_TYPE")
    p = _obj(pr)
    head = _obj(p.get("head"))
    base = _obj(p.get("base"))
    head_repo = _obj(head.get("repo"))
    base_repo = _obj(base.get("repo"))
    if (
        type(p.get("number")) is not int or p["number"] != expected.pr_number
        or p.get("state") != "open"
        or p.get("draft") is not False
        or p.get("merged") is not False
        or p.get("html_url") != f"https://github.com/{SOURCE_REPO}/pull/{expected.pr_number}"
        or head_repo.get("full_name") != SOURCE_REPO
        or base_repo.get("full_name") != SOURCE_REPO
        or head.get("sha") != expected.head_sha
        or base.get("sha") != expected.base_sha
        or not _sha(head.get("sha"))
        or not _sha(base.get("sha"))
    ):
        raise IdentityRejected("PR_SOURCE_IDENTITY_MISMATCH")


def verify_stable_pr(before: object, after: object, expected: ExactPR) -> None:
    """Require the same exact open PR identity before and after a test job."""
    verify_pr(before, expected)
    verify_pr(after, expected)


def verify_controller_run(
    run: object, *, controller_sha: str, run_id: int, attempt: int,
    workflow_path: str,
) -> None:
    """Validate a known controller run without treating the run as a PR receipt.

    The caller must independently verify jobs, steps, source output, artifact and
    authorized workflow identity. A successful top-level run is insufficient.
    """
    if (
        not _sha(controller_sha) or not _positive(run_id)
        or not _positive(attempt) or type(workflow_path) is not str
        or not workflow_path.startswith(".github/workflows/")
        or not workflow_path.endswith(".yml")
        or ".." in workflow_path or "//" in workflow_path
    ):
        raise IdentityRejected("INVALID_RUN_EXPECTATION")
    r = _obj(run)
    repo = _obj(r.get("repository"))
    if (
        repo.get("full_name") != CONTROLLER_REPO
        or type(r.get("id")) is not int or r["id"] != run_id
        or type(r.get("run_attempt")) is not int or r["run_attempt"] != attempt
        or r.get("head_sha") != controller_sha
        or r.get("path") != workflow_path
        or r.get("event") != "workflow_dispatch"
        or r.get("status") != "completed"
        or r.get("conclusion") != "success"
    ):
        raise IdentityRejected("CONTROLLER_RUN_IDENTITY_MISMATCH")


__all__ = ["ExactPR", "IdentityRejected", "verify_pr", "verify_stable_pr", "verify_controller_run"]
