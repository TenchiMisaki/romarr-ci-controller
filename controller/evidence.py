#!/usr/bin/env python3
"""Execute bounded ROMarr pytest, retain private raw evidence, publish only safe counts.

This is a first-release, GitHub-hosted *manual* pilot. No Docker services,
real-world infrastructure, or GitHub source branches are modified.
"""
from __future__ import annotations

from datetime import datetime
import hashlib
import importlib.util
import json
import os
from pathlib import Path
import re
import signal
import subprocess
import sys
import time
import xml.etree.ElementTree as ET

from target import atomic_json, require_sha, TargetError

REPORT_SCHEMA = "romarr-ci-result-v1"
CASE_SCHEMA = "pr-pytest-cases-v1"
OUTCOMES = ("passed", "failed", "errors", "skipped")
STRUCTURAL = (
    "tests/test_wired.py", "tests/test_ui_pages.py", "tests/test_openapi.py",
    "tests/test_security_claims.py", "tests/test_brand.py",
    "tests/test_docker_install.py", "tests/test_repo_hygiene.py",
)
MAX_SECONDS = 1200
HEARTBEAT = 20


class CollectionError(RuntimeError):
    pass


def digest(path: Path):
    if not path.is_file():
        return None
    h = hashlib.sha256()
    with path.open("rb") as handle:
        for data in iter(lambda: handle.read(131072), b""):
            h.update(data)
    return h.hexdigest()


def collect_junit(path: Path):
    """Fail closed if pytest's declared tests do not equal the emitted cases."""
    if not path.is_file():
        raise CollectionError("JUNIT_MISSING")
    try:
        root = ET.parse(path).getroot()
    except ET.ParseError as error:
        raise CollectionError("JUNIT_MALFORMED") from error
    if root.tag == "testsuite":
        suite = root
    elif root.tag == "testsuites" and len(root) == 1 and root[0].tag == "testsuite":
        suite = root[0]
    else:
        raise CollectionError("JUNIT_UNSUPPORTED_STRUCTURE")
    if suite.findall("testsuite"):
        raise CollectionError("JUNIT_NESTED_SUITES_UNSUPPORTED")
    try:
        declared = {key: int(suite.attrib[key]) for key in ("tests", "errors", "failures", "skipped")}
    except (KeyError, ValueError):
        raise CollectionError("JUNIT_MISSING_OR_INVALID_TOTALS") from None
    if any(n < 0 for n in declared.values()) or sum(declared[k] for k in ("errors", "failures", "skipped")) > declared["tests"]:
        raise CollectionError("JUNIT_INVALID_TOTALS")
    cases = suite.findall("testcase")
    observed = {key: 0 for key in OUTCOMES}
    anonymous = []
    for index, case in enumerate(cases, start=1):
        states = [name for tag, name in (("failure", "failed"), ("error", "errors"), ("skipped", "skipped")) if case.find(tag) is not None]
        if len(states) > 1:
            raise CollectionError("JUNIT_CONFLICTING_CASE_OUTCOMES")
        state = states[0] if states else "passed"
        observed[state] += 1
        anonymous.append({"id": f"case-{index:06d}", "outcome": state})
    if declared["tests"] != len(cases):
        diff = declared["tests"] - len(cases)
        raise CollectionError(f"JUNIT_TOTAL_CASE_MISMATCH declared={declared['tests']} serialized={len(cases)} delta={diff}")
    for node_attr, outcome in (("errors", "errors"), ("failures", "failed"), ("skipped", "skipped")):
        if declared[node_attr] != observed[outcome]:
            raise CollectionError(f"JUNIT_{node_attr.upper()}_CASE_MISMATCH declared={declared[node_attr]} serialized={observed[outcome]}")
    if declared["tests"] <= 0:
        raise CollectionError("JUNIT_NO_TESTS")
    if len({x["id"] for x in anonymous}) != len(anonymous):
        raise CollectionError("JUNIT_DUPLICATE_ANONYMOUS_ID")
    return observed, anonymous


def now():
    return datetime.now().astimezone().isoformat(timespec="seconds")


def verify_runtime(source: Path, target: dict):
    if os.environ.get("GITHUB_ACTIONS") != "true" or os.environ.get("GITHUB_REPOSITORY") != "TenchiMisaki/romarr-ci-controller":
        raise TargetError("Unexpected GitHub Actions controller identity")
    if sys.version_info[:2] != (3, 13):
        raise TargetError("Runner must use Python 3.13")
    node = subprocess.run(["node", "--version"], capture_output=True, text=True, timeout=10, check=False)
    if node.returncode != 0 or not re.fullmatch(r"v24\.[0-9]+\.[0-9]+", node.stdout.strip()):
        raise TargetError("Required Node.js 24 is unavailable")
    for dependency in ("pytest", "requests", "rom_hub"):
        if importlib.util.find_spec(dependency) is None:
            raise TargetError(f"Required Python dependency unavailable: {dependency}")
    if not (source / ".git").exists() or not (source / "pytest.ini").is_file():
        raise TargetError("ROMarr Git checkout or pytest.ini is missing")
    if not (source.parent / ".archive-org-proof").is_dir():
        raise TargetError("Official ROMarr Archive.org test fixture is missing")
    for arguments in (("rev-parse", "HEAD"), ("status", "--porcelain", "--untracked-files=all")):
        process = subprocess.run(["git", "-C", str(source), *arguments], capture_output=True, text=True, timeout=15, check=False)
        if process.returncode != 0:
            raise TargetError("Git source identity/status command failed")
        if arguments[0] == "rev-parse" and process.stdout.strip().lower() != target["sha"]:
            raise TargetError("Checked-out ROMarr commit differs from pinned SHA")
        if arguments[0] == "status" and process.stdout.strip():
            raise TargetError("ROMarr worktree is dirty before testing")
    return node.stdout.strip()


def launch_pytest(source: Path, private: Path, args: list[str]):
    raw_log = private / "pytest.log"
    junit = private / "junit.xml"
    env = dict(os.environ)
    # Never pass any API, artifact, OIDC, or checkout credentials into PR code.
    for name in tuple(env):
        if name in ("GH_TOKEN", "GITHUB_TOKEN", "ACTIONS_RUNTIME_TOKEN", "ACTIONS_ID_TOKEN_REQUEST_TOKEN"):
            env.pop(name, None)
    started = time.monotonic()
    timed_out = False
    command = [sys.executable, "-m", "pytest", *args, "-q", f"--junitxml={junit}"]
    with raw_log.open("wb") as log:
        process = subprocess.Popen(command, cwd=source, env=env, stdout=log, stderr=subprocess.STDOUT, start_new_session=True)
        while True:
            remaining = MAX_SECONDS - (time.monotonic() - started)
            if remaining <= 0:
                timed_out = True
                break
            try:
                process.wait(timeout=min(HEARTBEAT, remaining))
                break
            except subprocess.TimeoutExpired:
                print(f"PYTEST RUNNING: elapsed={round(time.monotonic() - started)}s, limit={MAX_SECONDS}s", flush=True)
        if timed_out:
            try:
                os.killpg(process.pid, signal.SIGTERM)
            except ProcessLookupError:
                pass
            try:
                process.wait(timeout=10)
            except subprocess.TimeoutExpired:
                try:
                    os.killpg(process.pid, signal.SIGKILL)
                except ProcessLookupError:
                    pass
                process.wait(timeout=10)
    return process.returncode, timed_out, round(time.monotonic() - started, 2), raw_log, junit


def run():
    temp = Path(os.environ["RUNNER_TEMP"])
    private, public = temp / "romarr-ci-private", temp / "romarr-ci-public"
    private.mkdir(parents=True, exist_ok=True)
    public.mkdir(parents=True, exist_ok=True)
    target = json.loads((private / "target.json").read_text(encoding="utf-8"))
    require_sha(target["sha"], "pinned target")
    scope = os.environ.get("INPUT_SCOPE", "full")
    if scope not in ("full", "structural"):
        raise TargetError("Only full or structural scope is supported")
    source = Path(os.environ["GITHUB_WORKSPACE"]) / "romarr"
    summary = {
        "schema": REPORT_SCHEMA, "runner_version": "v01", "repository": target["repository"],
        "pr_number": target["number"], "pr_url": target["pr_url"],
        "tested_sha": target["sha"], "base_sha": target["base_sha"],
        "scope": scope, "run_id": os.environ.get("GITHUB_RUN_ID", "local"),
        "run_attempt": os.environ.get("GITHUB_RUN_ATTEMPT", "1"),
        "started_at": now(), "finished_at": None,
        "python_version": sys.version.split()[0], "node_version": None,
        "pytest_exit_code": None, "elapsed_seconds": None,
        "test_status": "NOT_TESTED", "collection_status": "BLOCKED",
        "environment_status": "NOT_VERIFIED", "counts": None,
        "private_junit_sha256": None, "private_log_sha256": None,
        "first_error": None,
    }
    print("================ PREFLIGHT CHECK ================", flush=True)
    print(f"Script: ROMarr GitHub Pytest Controller v01; expected repo: {target['repository']}; SHA: {target['sha']}", flush=True)
    print(f"Detected runner: {os.environ.get('RUNNER_NAME', 'unknown')}; timestamp: {summary['started_at']}", flush=True)
    try:
        summary["node_version"] = verify_runtime(source, target)
        summary["environment_status"] = "PASS"
        print("ENVIRONMENT PASS: Python 3.13, Node.js 24, required packages, SHA and clean source", flush=True)
        args = ["tests/"] if scope == "full" else list(STRUCTURAL)
        code, timeout, elapsed, log, junit = launch_pytest(source, private, args)
        summary["pytest_exit_code"] = code
        summary["elapsed_seconds"] = elapsed
        summary["private_log_sha256"] = digest(log)
        summary["private_junit_sha256"] = digest(junit)
        summary["test_status"] = "TIMED_OUT" if timeout else ("PASS" if code == 0 else "FAIL")
        if timeout:
            summary["first_error"] = "PYTEST_TIMEOUT"
        elif code != 0:
            summary["first_error"] = f"PYTEST_EXIT_{code}"
        try:
            counts, cases = collect_junit(junit)
            summary["counts"] = counts
            if code == 0 and (counts["failed"] or counts["errors"]):
                # A zero process exit paired with recorded case failures is not
                # a trustworthy success. Never hide it behind a green gate.
                summary["test_status"] = "UNCONFIRMED"
                summary["first_error"] = "PYTEST_EXIT_JUNIT_VERDICT_CONFLICT"
            anonymous = {
                "schema": CASE_SCHEMA, "repository": target["repository"],
                "pr_number": target["number"], "pr_url": target["pr_url"],
                "tested_sha": target["sha"], "scope": scope,
                "run_id": summary["run_id"], "run_attempt": summary["run_attempt"],
                "privacy": "Anonymous ordinal and result only; no test names or arguments",
                "counts": counts, "cases": cases,
            }
            atomic_json(public / "testcases.json", anonymous)
            summary["collection_status"] = "PASS"
        except CollectionError as error:
            summary["collection_status"] = "FAILED"
            summary["first_error"] = str(error) if summary["first_error"] is None else summary["first_error"] + "; " + str(error)
    except (TargetError, FileNotFoundError, OSError, subprocess.SubprocessError, ValueError) as error:
        summary["environment_status"] = "FAILED" if summary["environment_status"] == "NOT_VERIFIED" else summary["environment_status"]
        summary["collection_status"] = "FAILED"
        summary["first_error"] = f"ENV_OR_RUN_ERROR_{type(error).__name__}" if summary["first_error"] is None else summary["first_error"]
    finally:
        summary["finished_at"] = now()
        atomic_json(public / "summary.json", summary)
        print("================ DIAGNOSTIC FINISH ================", flush=True)
        print(f"Finished: {summary['finished_at']}; TEST={summary['test_status']}; COLLECTION={summary['collection_status']}; first_error={summary['first_error']}", flush=True)
    # Final gate handles statuses after artifact upload, including real test failures.


def report_and_manifest():
    temp = Path(os.environ["RUNNER_TEMP"])
    private, public = temp / "romarr-ci-private", temp / "romarr-ci-public"
    public.mkdir(parents=True, exist_ok=True)
    try:
        target = json.loads((private / "target.json").read_text(encoding="utf-8"))
    except (OSError, ValueError):
        raise TargetError("No verified source target exists") from None
    summary_path = public / "summary.json"
    if not summary_path.is_file():
        atomic_json(summary_path, {
            "schema": REPORT_SCHEMA, "repository": target["repository"],
            "pr_number": target["number"], "pr_url": target["pr_url"],
            "tested_sha": target["sha"], "test_status": "NOT_TESTED",
            "collection_status": "FAILED", "environment_status": "FAILED",
            "first_error": "PYTEST_NOT_EXECUTED_OR_EVIDENCE_MISSING",
            "counts": None, "scope": os.environ.get("INPUT_SCOPE", "unknown"),
        })
    post_path = public / "postcheck.json"
    if not post_path.is_file():
        atomic_json(post_path, {"status": "COLLECTION_FAILED", "details": ["Live source postcheck not available"]})
    summary = json.loads(summary_path.read_text(encoding="utf-8"))
    post = json.loads(post_path.read_text(encoding="utf-8"))
    counts = summary.get("counts")
    totals = "NOT AVAILABLE" if not isinstance(counts, dict) else ", ".join(f"{key}={counts.get(key)}" for key in OUTCOMES)
    name = summary.get("pr_url") or f"https://github.com/{target['repository']}/tree/main"
    details = [
        "# ROMarr pytest controller — ChatGPT handoff",
        "", f"Source: {name}", f"Immutable tested commit: `{target['sha']}`",
        f"Scope: {summary.get('scope')}",
        f"Test: **{summary.get('test_status')}** (raw pytest exit: {summary.get('pytest_exit_code', 'not available')})",
        f"Collection: **{summary.get('collection_status')}**",
        f"Environment: **{summary.get('environment_status')}**",
        f"Live source check: **{post.get('status')}**",
        f"Individual cases: {totals}",
        f"First sanitized error: {summary.get('first_error') or 'None'}",
        "", "Private raw pytest log and JUnit XML were not uploaded; their checksums are in summary.json only when generated.",
        "Node-dependent regressions require Node.js 24; the run is not a Docker build, browser acceptance, CodeRabbit review or deployed behavior proof.",
        "", "Ask ChatGPT to review this run's summary.json, testcases.json, postcheck.json, and current ROMarr PR/CodeRabbit findings.",
    ]
    (public / "HANDOFF.md").write_text("\n".join(details) + "\n", encoding="utf-8")
    required = ["summary.json", "postcheck.json", "HANDOFF.md"]
    if (public / "testcases.json").is_file():
        required.append("testcases.json")
    manifest = {"schema": "romarr-ci-manifest-v1", "files": {key: digest(public / key) for key in required}}
    atomic_json(public / "manifest.json", manifest)
    if not all(digest(public / key) == value for key, value in manifest["files"].items()):
        raise CollectionError("MANIFEST_READBACK_FAILED")
    print("EVIDENCE: sanitized report, manifest, and optional case export read-back verified")


def final_gate():
    public = Path(os.environ["RUNNER_TEMP"]) / "romarr-ci-public"
    try:
        summary = json.loads((public / "summary.json").read_text(encoding="utf-8"))
        post = json.loads((public / "postcheck.json").read_text(encoding="utf-8"))
        manifest = json.loads((public / "manifest.json").read_text(encoding="utf-8"))
        if manifest.get("schema") != "romarr-ci-manifest-v1" or not manifest.get("files"):
            raise CollectionError("MANIFEST_INVALID")
        for name, recorded in manifest["files"].items():
            if name != Path(name).name or digest(public / name) != recorded:
                raise CollectionError("MANIFEST_INVALID_OR_MISMATCHED")
        if summary.get("collection_status") == "PASS":
            cases = json.loads((public / "testcases.json").read_text(encoding="utf-8"))
            if cases.get("schema") != CASE_SCHEMA or cases.get("tested_sha") != summary.get("tested_sha"):
                raise CollectionError("CASE_SCHEMA_OR_SHA_MISMATCH")
            observed = {key: 0 for key in OUTCOMES}
            identifiers = set()
            for index, case in enumerate(cases.get("cases", []), 1):
                if case.get("id") != f"case-{index:06d}" or case.get("outcome") not in OUTCOMES or case.get("id") in identifiers or set(case) != {"id", "outcome"}:
                    raise CollectionError("CASE_INVALID_OR_DUPLICATED")
                identifiers.add(case["id"])
                observed[case["outcome"]] += 1
            if observed != summary.get("counts") or cases.get("counts") != observed:
                raise CollectionError("CASE_COUNTS_MISMATCH")
        trustworthy_counts = isinstance(summary.get("counts"), dict) and sum(summary["counts"].values()) > 0 and summary["counts"].get("failed") == 0 and summary["counts"].get("errors") == 0
        passed = (summary.get("test_status") == "PASS" and summary.get("pytest_exit_code") == 0
                  and summary.get("environment_status") == "PASS" and summary.get("collection_status") == "PASS"
                  and post.get("status") == "UNCHANGED" and trustworthy_counts
                  and os.environ.get("ARTIFACT_STATUS") == "success")
        status = "PASS" if passed else "FAIL_OR_BLOCKED"
        print(f"FINAL GATE: {status}; TEST={summary.get('test_status')}; COLLECTION={summary.get('collection_status')}; SOURCE={post.get('status')}")
        step_summary = os.environ.get("GITHUB_STEP_SUMMARY")
        if step_summary:
            with open(step_summary, "a", encoding="utf-8") as stream:
                stream.write((public / "HANDOFF.md").read_text(encoding="utf-8"))
        if not passed:
            raise SystemExit(1)
    except (OSError, ValueError, KeyError, CollectionError) as exc:
        print(f"FINAL GATE BLOCKED: {type(exc).__name__}", file=sys.stderr)
        raise SystemExit(2)


def main():
    if len(sys.argv) != 2 or sys.argv[1] not in ("run", "finalize", "gate"):
        raise SystemExit("Usage: evidence.py run|finalize|gate")
    mode = sys.argv[1]
    if mode == "run":
        run()
    elif mode == "finalize":
        report_and_manifest()
    else:
        final_gate()


if __name__ == "__main__":
    try:
        main()
    except (TargetError, CollectionError) as error:
        print(f"EVIDENCE BLOCKED: {error}", file=sys.stderr)
        raise SystemExit(2)
