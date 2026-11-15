"""Read-only GitHub Actions receipt acceptance, after trusted artifact retrieval.

This module performs NO HTTP calls and NO mutations. The caller must collect
PR, tag, workflow, job, and artifact metadata from verified GitHub API targets
and obtain the archive from the exact GitHub artifact ID. A proven ZIP inspector
(e.g., controller/public_evidence.py::inspect) must be supplied by the caller.

A verified receipt is NOT authorization to dispatch, merge, publish, or deploy.
"""
from __future__ import annotations

import hashlib
import json
from pathlib import Path
import re
from zipfile import BadZipFile, ZipFile

SOURCE = "TenchiMisaki/romarr"
CONTROLLER = "TenchiMisaki/romarr-ci-controller"
WORKFLOW_PATH = ".github/workflows/romarr-pytest.yml"
_SHA = re.compile(r"[0-9a-f]{40}\Z")
_DIGEST = re.compile(r"sha256:[0-9a-f]{64}\Z")
_MAX_ARCHIVE_BYTES = 16 * 1024 * 1024
_REQUIRED_STEPS = (
    "Resolve and pin source on GitHub",
    "Checkout pinned public ROMarr source (read-only)",
    "Run exact-source pytest and collect anonymous case outcomes",
    "Independently recheck the live source head and local checkout",
    "Finalize sanitized evidence and checksum manifest",
    "Upload sanitized evidence (never raw JUnit or test logs)",
    "Final evidence acceptance gate",
)


class ReceiptError(ValueError):
    """Fail-closed identity, integrity, completeness or receipt mismatch."""


def _require(ok, reason):
    """Reject an incomplete condition with a stable, nonsensitive reason."""
    if not ok:
        raise ReceiptError(reason)


def _positive(value):
    """Require a positive integer and explicitly reject booleans."""
    return type(value) is int and value > 0


def _sha(value):
    """Require a lowercase, full-length immutable Git SHA."""
    return isinstance(value, str) and _SHA.fullmatch(value) is not None


def _ref_matches(ref, name, sha):
    """Match a controller tag and its immutable commit target exactly."""
    obj = ref.get("object") if isinstance(ref, dict) else None
    return (isinstance(ref, dict) and ref.get("ref") == "refs/tags/" + name
            and isinstance(obj, dict) and obj.get("type") == "commit"
            and obj.get("sha") == sha)


def _parse_unique_json(data):
    """Parse mandatory artifact JSON without accepting shadowed keys."""
    def unique(pairs):
        """Raise when JSON contains duplicate keys at any depth."""
        output = {}
        for k, v in pairs:
            if k in output:
                raise ReceiptError("Duplicate artifact JSON key")
            output[k] = v
        return output
    try:
        return json.loads(data.decode("utf-8"), object_pairs_hook=unique)
    except (UnicodeError, ValueError) as exc:
        if isinstance(exc, ReceiptError):
            raise
        raise ReceiptError("Invalid artifact summary JSON") from exc


def verify_receipt(*, pr, run, jobs, artifact_listing, claim_ref, run_ref,
                   expected_pr, expected_head, expected_base, controller_sha,
                   archive_path, inspect_artifact):
    """Validate explicit immutable identity, GitHub metadata and a public ZIP.

    `inspect_artifact` is the already-reviewed `public_evidence.inspect`
    function. Supplying an untrusted or fake function invalidates acceptance.
    The caller must authenticate the GitHub API source separately; copied JSON
    is insufficient evidence of its provenance.
    """
    _require(_positive(expected_pr) and _sha(expected_head) and
             _sha(expected_base) and _sha(controller_sha),
             "Invalid expected identity inputs")
    _require(isinstance(pr, dict) and pr.get("number") == expected_pr
             and pr.get("state") == "open" and pr.get("draft") is False,
             "PR identity/state changed")
    head, base = pr.get("head"), pr.get("base")
    _require(isinstance(head, dict) and isinstance(base, dict)
             and isinstance(head.get("repo"), dict)
             and isinstance(base.get("repo"), dict)
             and head["repo"].get("full_name") == SOURCE
             and base["repo"].get("full_name") == SOURCE
             and head.get("sha") == expected_head
             and base.get("sha") == expected_base,
             "PR repository/head/base mismatch")
    _require(isinstance(run, dict) and _positive(run.get("id"))
             and _positive(run.get("run_attempt"))
             and isinstance(run.get("repository"), dict)
             and isinstance(run.get("head_repository"), dict)
             and run["repository"].get("full_name") == CONTROLLER
             and run["head_repository"].get("full_name") == CONTROLLER
             and run.get("head_sha") == controller_sha
             and run.get("head_branch") == "main"
             and run.get("event") == "workflow_dispatch"
             and run.get("path") == WORKFLOW_PATH
             and run.get("status") == "completed"
             and run.get("conclusion") == "success"
             and run.get("html_url") ==
             f"https://github.com/{CONTROLLER}/actions/runs/{run['id']}",
             "GitHub workflow-run identity or result mismatch")
    run_id, attempt = run["id"], run["run_attempt"]
    claim_name = (f"romarr-ci-v2/pr-{expected_pr}-h-{expected_head}"
                  f"-b-{expected_base}")
    _require(_ref_matches(claim_ref, claim_name, controller_sha)
             and _ref_matches(run_ref, f"{claim_name}-run-{run_id}", controller_sha),
             "Claim or run-ID tag mismatch")

    _require(isinstance(jobs, dict) and isinstance(jobs.get("jobs"), list)
             and jobs.get("total_count") == len(jobs["jobs"])
             and len(jobs["jobs"]) == 1,
             "Incomplete or unexpected job collection")
    job = jobs["jobs"][0]
    _require(isinstance(job, dict) and job.get("name") == "Exact-commit native ROMarr pytest"
             and job.get("run_id") == run_id
             and job.get("run_attempt") == attempt
             and job.get("head_sha") == controller_sha
             and job.get("status") == "completed"
             and job.get("conclusion") == "success",
             "Job identity or result mismatch")
    steps = job.get("steps")
    _require(isinstance(steps, list) and all(isinstance(s, dict) for s in steps),
             "Job steps unavailable")
    for name in _REQUIRED_STEPS:
        matches = [s for s in steps if s.get("name") == name]
        _require(len(matches) == 1 and matches[0].get("status") == "completed"
                 and matches[0].get("conclusion") == "success",
                 "Missing, skipped or failed required job step: " + name)

    _require(isinstance(artifact_listing, dict)
             and isinstance(artifact_listing.get("artifacts"), list)
             and artifact_listing.get("total_count") == len(artifact_listing["artifacts"])
             and len(artifact_listing["artifacts"]) == 1,
             "Incomplete or ambiguous artifact inventory")
    artifact = artifact_listing["artifacts"][0]
    expected_artifact = f"romarr-pytest-handoff-{run_id}-{attempt}"
    workflow_run = artifact.get("workflow_run") if isinstance(artifact, dict) else None
    _require(isinstance(artifact, dict) and _positive(artifact.get("id"))
             and artifact.get("name") == expected_artifact
             and artifact.get("expired") is False
             and _positive(artifact.get("size_in_bytes"))
             and isinstance(artifact.get("digest"), str)
             and _DIGEST.fullmatch(artifact["digest"])
             and isinstance(workflow_run, dict)
             and workflow_run.get("id") == run_id
             and workflow_run.get("head_sha") == controller_sha
             and workflow_run.get("head_branch") == "main"
             and artifact.get("archive_download_url") ==
             f"https://api.github.com/repos/{CONTROLLER}/actions/artifacts/{artifact['id']}/zip",
             "Artifact metadata, producer or digest mismatch")
    path = Path(archive_path)
    _require(path.is_file() and not path.is_symlink(), "Missing or linked archive")
    size = path.stat().st_size
    _require(0 < size <= _MAX_ARCHIVE_BYTES and size == artifact["size_in_bytes"],
             "Downloaded archive size mismatch or unsafe size")
    with path.open("rb") as fh:
        digest = hashlib.file_digest(fh, "sha256").hexdigest()
    _require(artifact["digest"] == "sha256:" + digest,
             "Downloaded archive digest mismatch")

    # This MUST be the vetted upstream inspect function, not only an archive
    # size check or a decoded summary. It validates anonymous cases, CRC and
    # individual manifest member hashes.
    try:
        inspection = inspect_artifact(str(path), repository=SOURCE,
                                      head=expected_head, base=expected_base,
                                      scope="full")
    except Exception as exc:
        raise ReceiptError("Detailed public-artifact inspection failed: " +
                           type(exc).__name__) from exc
    _require(isinstance(inspection, dict)
             and inspection.get("artifact_integrity") == "PASS"
             and inspection.get("case_reconciliation") == "PASS"
             and inspection.get("repository") == SOURCE
             and inspection.get("head") == expected_head
             and inspection.get("base") == expected_base
             and inspection.get("scope") == "full"
             and isinstance(inspection.get("counts"), dict),
             "Detailed artifact inspection incomplete")
    try:
        with ZipFile(path, "r") as z:
            summary = _parse_unique_json(z.read("summary.json"))
            cases_doc = _parse_unique_json(z.read("testcases.json"))
    except (BadZipFile, OSError, KeyError, RuntimeError) as exc:
        raise ReceiptError("Missing mandatory artifact identity fields") from exc
    _require(isinstance(summary, dict) and isinstance(cases_doc, dict)
             and summary.get("pr_number") == expected_pr
             and summary.get("pr_url") == f"https://github.com/{SOURCE}/pull/{expected_pr}"
             and summary.get("run_id") == str(run_id)
             and summary.get("run_attempt") == str(attempt)
             and summary.get("tested_sha") == expected_head
             and summary.get("base_sha") == expected_base
             and summary.get("counts") == inspection["counts"]
             and cases_doc.get("pr_number") == expected_pr
             and cases_doc.get("run_id") == str(run_id)
             and cases_doc.get("run_attempt") == str(attempt),
             "Artifact summary not bound to authenticated PR/run metadata")
    counts = inspection["counts"]
    _require(all(type(counts.get(k)) is int and counts[k] >= 0
                 for k in ("passed", "skipped", "failed", "errors"))
             and counts["failed"] == counts["errors"] == 0
             and counts["passed"] > 0,
             "Failed, empty or unaccounted test outcomes")
    _require(inspection.get("skips_require_review") is (counts["skipped"] > 0),
             "Skip classification disagrees with detailed inspector")
    return {
        "status": ("RECEIPT_VERIFIED_SKIPS_REQUIRE_POLICY" if counts["skipped"]
                   else "RECEIPT_VERIFIED_NO_SKIPS"),
        "pr_number": expected_pr, "tested_sha": expected_head,
        "base_sha": expected_base, "controller_sha": controller_sha,
        "run_id": run_id, "run_attempt": attempt,
        "artifact_id": artifact["id"], "archive_sha256": digest,
        "counts": counts, "public_evidence": "PASS",
        "skip_policy": "UNVERIFIED" if counts["skipped"] else "NOT_APPLICABLE",
        "coderabbit": "NOT_VERIFIED_BY_RECEIPT",
        "other_ci": "NOT_VERIFIED_BY_RECEIPT",
        "unattended_actions_authorized": False,
    }
