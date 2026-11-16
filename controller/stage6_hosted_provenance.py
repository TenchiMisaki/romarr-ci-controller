"""Offline Stage 6 provenance validator for the *completed manual* source pilot.

This module checks independently fetched GitHub Actions run/job metadata, never
claims that a reported test count proves correct execution, and never uploads.
It has no HTTP client, token handling, shell command or mutating operation.
The caller supplies a GET-only adapter and independent expectations.
"""
from __future__ import annotations

from dataclasses import dataclass
import re
from typing import Any

CONTROLLER = "TenchiMisaki/romarr-ci-controller"
WORKFLOW = ".github/workflows/stage6-source-manual-pilot.yml"
WORKFLOW_NAME = "ROMarr Stage 6 - Pinned source isolation pilot (MANUAL, ADVISORY)"
JOB_SOURCE = "Run one real ROMarr test file in offline container"
JOB_REVIEWER = "Separate runner validates advisory source outcome"
SHA_PATTERN = re.compile(r"[0-9a-f]{40}\Z")
POSITIVE = re.compile(r"[1-9][0-9]{0,14}\Z")
OUTCOMES = re.compile(r"P{1,256}\Z")


class ProvenanceBlocked(Exception):
    """Fixed public-safe reason; never include raw API response or private logs."""


@dataclass(frozen=True)
class Expectation:
    controller_sha: str
    source_sha: str
    run_id: int
    attempt: int
    case_count: int


@dataclass(frozen=True)
class Result:
    state: str
    reason: str = ""
    verified_job_ids: tuple[int, int] = ()
    test_accepted: bool = False
    publication_authorized: bool = False
    unattended_dispatch_enabled: bool = False


def _positive(value: Any, maximum: int = 999_999_999_999_999) -> bool:
    return type(value) is int and 1 <= value <= maximum


def _expect(e: Expectation) -> None:
    if (not isinstance(e, Expectation)
            or not isinstance(e.controller_sha, str) or not SHA_PATTERN.fullmatch(e.controller_sha)
            or not isinstance(e.source_sha, str) or not SHA_PATTERN.fullmatch(e.source_sha)
            or not _positive(e.run_id) or not _positive(e.attempt, 100)
            or not _positive(e.case_count, 256)):
        raise ProvenanceBlocked("EXPECTED_IDENTITY_INVALID")


def _read(api: Any, path: str, allowed: set[str]) -> dict:
    if path not in allowed:
        raise ProvenanceBlocked("READ_PATH_DENIED")
    result = api.request("GET", path)
    if not isinstance(result, dict):
        raise ProvenanceBlocked("METADATA_NOT_OBJECT")
    return result


def _run(run: dict, e: Expectation) -> None:
    if (type(run.get("id")) is not int or run["id"] != e.run_id
            or type(run.get("run_attempt")) is not int or run["run_attempt"] != e.attempt
            or run.get("path") != WORKFLOW or run.get("name") != WORKFLOW_NAME
            or run.get("event") != "workflow_dispatch"
            or run.get("head_branch") != "main" or run.get("head_sha") != e.controller_sha
            or run.get("status") != "completed" or run.get("conclusion") != "success"
            or not isinstance(run.get("repository"), dict)
            or run["repository"].get("full_name") != CONTROLLER
            or not isinstance(run.get("head_repository"), dict)
            or run["head_repository"].get("full_name") != CONTROLLER):
        raise ProvenanceBlocked("RUN_IDENTITY_MISMATCH")


def _jobs(data: dict, e: Expectation) -> tuple[int, int]:
    jobs = data.get("jobs")
    if (type(data.get("total_count")) is not int or data["total_count"] != 2
            or not isinstance(jobs, list) or len(jobs) != 2
            or not all(isinstance(j, dict) for j in jobs)):
        raise ProvenanceBlocked("JOB_INVENTORY_INVALID")
    names = [j.get("name") for j in jobs]
    if set(names) != {JOB_SOURCE, JOB_REVIEWER} or len(set(names)) != 2:
        raise ProvenanceBlocked("JOB_NAMES_INVALID")
    ids: list[int] = []
    runners: list[str] = []
    for j in jobs:
        if (not _positive(j.get("id")) or type(j.get("run_id")) is not int
                or j["run_id"] != e.run_id
                or type(j.get("run_attempt")) is not int or j["run_attempt"] != e.attempt
                or j.get("head_sha") != e.controller_sha
                or j.get("head_branch") != "main"
                or j.get("workflow_name") != WORKFLOW_NAME
                or j.get("status") != "completed" or j.get("conclusion") != "success"
                or j.get("runner_group_name") != "GitHub Actions"
                or not isinstance(j.get("runner_name"), str) or not j["runner_name"].startswith("GitHub Actions ")
                or not isinstance(j.get("steps"), list) or len(j["steps"]) != 3
                or any(not isinstance(s, dict) or s.get("status") != "completed"
                       or s.get("conclusion") != "success" for s in j["steps"])):
            raise ProvenanceBlocked("JOB_METADATA_INVALID")
        actual_names = [s.get("name") for s in j["steps"]]
        expected_middle = ("Fetch immutable public ROMarr source and test without credentials"
                           if j["name"] == JOB_SOURCE else
                           "Reject malformed or inconsistent untrusted result channel")
        if actual_names != ["Set up job", expected_middle, "Complete job"]:
            raise ProvenanceBlocked("JOB_STEPS_INVALID")
        ids.append(j["id"])
        runners.append(j["runner_name"])
    if len(set(ids)) != 2 or len(set(runners)) != 2:
        raise ProvenanceBlocked("JOB_SEPARATION_UNVERIFIED")
    return (ids[names.index(JOB_SOURCE)], ids[names.index(JOB_REVIEWER)])


def inspect(api: Any, expected: Expectation, untrusted: object) -> Result:
    """Read only strict GitHub API run and jobs; no artifact or source-test acceptance.

    The source SHA is only compared to the *untrusted* handoff field here. Real
    source attestation demands a separate independently trusted verification.
    """
    try:
        _expect(expected)
        if (not isinstance(untrusted, dict) or set(untrusted) != {"source_sha", "cases", "pytest_exit"}
                or untrusted["source_sha"] != expected.source_sha
                or untrusted["pytest_exit"] != "0"
                or not isinstance(untrusted["cases"], str)
                or not OUTCOMES.fullmatch(untrusted["cases"])
                or len(untrusted["cases"]) != expected.case_count):
            raise ProvenanceBlocked("UNTRUSTED_CHANNEL_INVALID")
        run_path = f"repos/{CONTROLLER}/actions/runs/{expected.run_id}"
        jobs_path = f"{run_path}/jobs?per_page=100&page=1"
        allowed = {run_path, jobs_path}
        run = _read(api, run_path, allowed)
        _run(run, expected)
        ids = _jobs(_read(api, jobs_path, allowed), expected)
        # Recheck mutable REST run metadata after the jobs were read.
        _run(_read(api, run_path, allowed), expected)
        return Result("ADVISORY_JOB_PROVENANCE_VERIFIED", verified_job_ids=ids)
    except ProvenanceBlocked as e:
        return Result("BLOCKED", reason=str(e))
    except (AttributeError, KeyError, TypeError, ValueError, OSError):
        return Result("COLLECTION_FAILED", reason="API_COLLECTION_FAILED")
    except Exception:
        return Result("COLLECTION_FAILED", reason="API_COLLECTION_FAILED")
