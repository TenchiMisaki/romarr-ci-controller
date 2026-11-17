"""Offline, fail-closed metadata attestation for a future isolated PR canary.

Only checks supplied snapshots. They MUST come from a trusted authenticated
collector, independently of source-job outputs. No HTTP, writes, test acceptance
or permission to schedule/dispatch is implemented.
"""
from __future__ import annotations

from dataclasses import dataclass
import re

from stage6_pr_identity_v32 import ExactPR, IdentityRejected, verify_stable_pr, verify_controller_run
from stage6_pr_live_run_v41 import verify_advisory_run

CONTROLLER = "TenchiMisaki/romarr-ci-controller"
API = f"https://api.github.com/repos/{CONTROLLER}/actions"
HEX64 = re.compile(r"[0-9a-f]{64}\Z")


@dataclass(frozen=True)
class ExpectedArtifact:
    pr: ExactPR
    controller_sha: str
    workflow_path: str
    run_id: int
    run_attempt: int
    source_job_name: str
    required_source_steps: tuple[str, ...]
    artifact_id: int
    artifact_name: str
    artifact_sha256: str
    max_archive_bytes: int = 65536

    def __post_init__(self) -> None:
        if (type(self.pr) is not ExactPR
                or not isinstance(self.controller_sha, str)
                or re.fullmatch(r"[0-9a-f]{40}", self.controller_sha) is None
                or type(self.run_id) is not int or self.run_id < 1
                or type(self.run_attempt) is not int or self.run_attempt < 1
                or type(self.artifact_id) is not int or self.artifact_id < 1
                or type(self.source_job_name) is not str
                or not 1 <= len(self.source_job_name) <= 100
                or type(self.required_source_steps) is not tuple
                or not self.required_source_steps
                or len(set(self.required_source_steps)) != len(self.required_source_steps)
                or any(type(s) is not str or not 1 <= len(s) <= 100 for s in self.required_source_steps)
                or type(self.artifact_name) is not str
                or re.fullmatch(r"[a-z0-9][a-z0-9_-]{0,99}", self.artifact_name) is None
                or type(self.artifact_sha256) is not str
                or HEX64.fullmatch(self.artifact_sha256) is None
                or type(self.max_archive_bytes) is not int
                or not 1 <= self.max_archive_bytes <= 16 * 1024 * 1024):
            raise IdentityRejected("INVALID_ARTIFACT_EXPECTATION")
        # Validate expected workflow path using the existing exact-run checker.
        # It cannot establish that any real run exists; only validates syntax.
        verify_controller_run({"repository": {"full_name": CONTROLLER},
                               "id": self.run_id, "run_attempt": self.run_attempt,
                               "head_sha": self.controller_sha,
                               "path": self.workflow_path,
                               "event": "workflow_dispatch", "status": "completed",
                               "conclusion": "success"},
                              controller_sha=self.controller_sha,
                              run_id=self.run_id, attempt=self.run_attempt,
                              workflow_path=self.workflow_path)


def _dict(value: object) -> dict:
    if type(value) is not dict:
        raise IdentityRejected("METADATA_SHAPE_INVALID")
    return value


def verify_metadata(*, before: object, after: object, run: object,
                    jobs: object, artifact: object, expected: ExpectedArtifact) -> str:
    """Attest identity/producer metadata only, never accept source tests.

    A later trusted downloader MUST separately verify actual ZIP bytes, its
    digest and inner contents; postrun jobs/steps and freshness need further
    checks. Any incomplete, ambiguous, skipped or stale snapshot is rejected.
    """
    if type(expected) is not ExpectedArtifact:
        raise IdentityRejected("EXPECTED_ARTIFACT_TYPE")
    verify_stable_pr(before, after, expected.pr)
    verify_advisory_run(run, controller_sha=expected.controller_sha,
                        run_id=expected.run_id, attempt=expected.run_attempt,
                        workflow_path=expected.workflow_path)

    # Consume the complete authenticated GitHub REST jobs collection, not
    # connector summaries that omit the run_attempt/head_sha fields.
    listing = _dict(jobs)
    source_jobs = listing.get("jobs")
    if (type(source_jobs) is not list or not source_jobs or len(source_jobs) > 100
            or type(listing.get("total_count")) is not int
            or listing["total_count"] != len(source_jobs)):
        raise IdentityRejected("JOB_COLLECTION_INCOMPLETE")
    selected = [job for job in source_jobs
                if type(job) is dict and job.get("name") == expected.source_job_name]
    if len(selected) != 1:
        raise IdentityRejected("SOURCE_JOB_AMBIGUOUS")
    source = selected[0]
    if (type(source.get("id")) is not int or source["id"] < 1
            or source.get("run_id") != expected.run_id
            or source.get("run_url") != f"{API}/runs/{expected.run_id}"
            or source.get("head_branch") != "main"
            or source.get("run_attempt") != expected.run_attempt
            or source.get("head_sha") != expected.controller_sha
            or source.get("status") != "completed"
            or source.get("conclusion") != "success"):
        raise IdentityRejected("SOURCE_JOB_UNVERIFIED")
    steps = source.get("steps")
    if type(steps) is not list or not steps or len(steps) > 100:
        raise IdentityRejected("SOURCE_STEPS_INVALID")
    for required in expected.required_source_steps:
        matches = [step for step in steps
                   if type(step) is dict and step.get("name") == required]
        if (len(matches) != 1 or matches[0].get("status") != "completed"
                or matches[0].get("conclusion") != "success"):
            raise IdentityRejected("REQUIRED_SOURCE_STEP_UNVERIFIED")

    a = _dict(artifact)
    origin = _dict(a.get("workflow_run"))
    base = f"{API}/artifacts/{expected.artifact_id}"
    if (type(a.get("id")) is not int or a["id"] != expected.artifact_id
            or a.get("name") != expected.artifact_name
            or a.get("expired") is not False
            or a.get("digest") != "sha256:" + expected.artifact_sha256
            or type(a.get("size_in_bytes")) is not int
            or not 1 <= a["size_in_bytes"] <= expected.max_archive_bytes
            or a.get("url") != base or a.get("archive_download_url") != base + "/zip"
            or type(origin.get("id")) is not int or origin["id"] != expected.run_id
            or origin.get("head_sha") != expected.controller_sha
            or origin.get("head_branch") != "main"):
        raise IdentityRejected("ARTIFACT_METADATA_MISMATCH")
    return "UNTRUSTED_ARTIFACT_METADATA_IDENTIFIED"


__all__ = ["ExpectedArtifact", "verify_metadata"]
