"""Ordered, injectable read-only Stage 6 collector (OFFLINE CANDIDATE).

The supplied callbacks MUST be implemented by a separately authenticated, TLS-
validated collector. This module makes no HTTP calls itself, does not dispatch,
and never authorizes tests, publication, or unattended behavior.
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Callable

from stage6_pr_final_gate_v36 import FinalEvidence, verify_final_candidate
from stage6_pr_identity_v32 import IdentityRejected

PR_REPO = "TenchiMisaki/romarr"
CONTROLLER = "TenchiMisaki/romarr-ci-controller"
API = "https://api.github.com"


@dataclass(frozen=True)
class CollectionResult:
    state: str
    reason: str = ""
    test_accepted: bool = False
    publication_authorized: bool = False
    unattended_dispatch_enabled: bool = False


def collect_ordered(*, evidence: FinalEvidence,
                    get_json: Callable[[str], object],
                    get_artifact_bytes: Callable[[str, int, str], bytes]) -> CollectionResult:
    """Sequence independent PR, branch, run, jobs, artifact and ZIP reads.

    The artifact callback receives the exact API ZIP endpoint, strict max-byte
    bound and expected SHA-256. It MUST independently enforce HTTP redirects,
    credential isolation and TLS; the callback output is NOT automatically
    authenticated by being supplied here. Do not translate unknown errors to
    positive evidence. No retries or writes.
    """
    if (type(evidence) is not FinalEvidence or not callable(get_json)
            or not callable(get_artifact_bytes)):
        return CollectionResult("BLOCKED", "COLLECTOR_INPUT_INVALID")
    e = evidence.expected
    pr_path = f"{API}/repos/{PR_REPO}/pulls/{e.pr.pr_number}"
    branch_path = f"{API}/repos/{PR_REPO}/branches/main"
    run_path = f"{API}/repos/{CONTROLLER}/actions/runs/{e.run_id}"
    jobs_path = f"{run_path}/jobs?per_page=100"
    artifact_path = f"{API}/repos/{CONTROLLER}/actions/artifacts/{e.artifact_id}"
    zip_path = f"{artifact_path}/zip"
    try:
        # Ordering is a security-relevant contract: final reads happen only
        # after the download, and are not accepted from initial cached objects.
        pr_before = get_json(pr_path)
        branch_before = get_json(branch_path)
        run = get_json(run_path)
        jobs = get_json(jobs_path)
        artifact = get_json(artifact_path)
        pr_after = get_json(pr_path)
        branch_after = get_json(branch_path)
        raw = get_artifact_bytes(zip_path, e.max_archive_bytes, e.artifact_sha256)
        if type(raw) is not bytes or not 1 <= len(raw) <= e.max_archive_bytes:
            raise IdentityRejected("ARTIFACT_DOWNLOAD_INVALID")
        pr_final = get_json(pr_path)
        branch_final = get_json(branch_path)
        status = verify_final_candidate(evidence=evidence, pr_before=pr_before,
            pr_after=pr_after, pr_final=pr_final, branch_before=branch_before,
            branch_after=branch_after, branch_final=branch_final, run=run,
            jobs=jobs, artifact=artifact, raw_zip=raw)
        if status != "FINAL_PR_ADVISORY_IDENTITIES_AND_BYTES_VERIFIED_NOT_TEST_ACCEPTED":
            raise IdentityRejected("FINAL_ADVISORY_STATUS_UNEXPECTED")
        return CollectionResult("ADVISORY_COLLECTED_NOT_TEST_ACCEPTED")
    except (IdentityRejected, ValueError, TypeError, KeyError, OSError,
            RuntimeError, TimeoutError) as exc:
        # Do not echo exception messages from untrusted GitHub responses or
        # callback internals, which may contain tokens/signed URLs.
        return CollectionResult("BLOCKED", "INDEPENDENT_COLLECTION_OR_VALIDATION_FAILED")


__all__ = ["CollectionResult", "collect_ordered"]
