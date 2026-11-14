"""Stage 2 candidate: poll the public ROMarr fork, atomically claim PR heads, dispatch CI.

This is not an installed scheduler. It must only run with privileged GitHub
permissions after separate controller-repository authorization and review.
"""
from __future__ import annotations

import datetime as dt
import json
import os
from pathlib import Path
import re
import sys
import time
from urllib.error import HTTPError, URLError
from urllib.parse import quote
from urllib.request import Request, urlopen

CONTROLLER = "TenchiMisaki/romarr-ci-controller"
SOURCE = "TenchiMisaki/romarr"
WORKFLOW = "romarr-pytest.yml"
SHA = re.compile(r"[0-9a-fA-F]{40}\Z")
NUM = re.compile(r"[1-9][0-9]{0,5}\Z")
MAX_PAGES = 10
MAX_DISPATCHES = 1


class WatchError(Exception):
    """An identity, metadata, API or automation safety gate has failed."""


class API:
    """Small standard-library GitHub REST transport with no mutating retries."""

    def __init__(self, token="", opener=urlopen, sleep=time.sleep):
        self.token = token
        self.opener = opener
        self.sleep = sleep

    def request(self, method, path, body=None, allow_missing=False):
        if method not in ("GET", "POST") or not path.startswith("repos/") or ".." in path:
            raise WatchError("Invalid API request target")
        if not (path.startswith("repos/" + CONTROLLER + "/") or
                path.startswith("repos/" + SOURCE + "/")):
            raise WatchError("API repository outside approved scope")
        if method == "POST" and path not in (
            f"repos/{CONTROLLER}/git/refs",
            f"repos/{CONTROLLER}/actions/workflows/{WORKFLOW}/dispatches",
        ):
            raise WatchError("Mutation target outside controller claim/dispatch scope")
        if method == "POST" and not self.token:
            raise WatchError("Authenticated controller token required for mutations")
        data = json.dumps(body, separators=(",", ":")).encode() if body is not None else None
        headers = {"Accept": "application/vnd.github+json",
                   "X-GitHub-Api-Version": "2026-03-10",
                   "User-Agent": "romarr-ci-controller-stage2-candidate"}
        if self.token:
            headers["Authorization"] = "Bearer " + self.token
        req = Request("https://api.github.com/" + path,
                      data=data, method=method, headers=headers)
        # HTTP POST is intentionally never retried: success may be ambiguous.
        for attempt in range(1, 4 if method == "GET" else 2):
            try:
                with self.opener(req, timeout=15) as resp:
                    if method == "POST" and resp.status not in (200, 201):
                        raise WatchError("Mutation returned unexpected HTTP status")
                    if method == "GET" and resp.status != 200:
                        raise WatchError("Read returned unexpected HTTP status")
                    return json.loads(resp.read().decode("utf-8"))
            except HTTPError as exc:
                if allow_missing and method == "GET" and exc.code == 404:
                    return None
                if method != "GET" or exc.code not in (408, 429, 500, 502, 503, 504) or attempt == 3:
                    raise WatchError(f"GitHub API HTTP {exc.code} for {method}") from None
            except (URLError, TimeoutError, ConnectionError):
                if method != "GET" or attempt == 3:
                    raise WatchError(f"GitHub API {method} transport failure") from None
            self.sleep(2 * attempt)
        raise WatchError("GitHub API read exhausted")


def exact_sha(value, name):
    if not isinstance(value, str) or not SHA.fullmatch(value):
        raise WatchError(f"{name} missing or invalid")
    return value.lower()


def classify(pr):
    """Return (candidate, reason) without following PR-provided links or commands."""
    if not isinstance(pr, dict):
        raise WatchError("Invalid PR metadata")
    number = pr.get("number")
    if isinstance(number, bool) or not isinstance(number, int) or not NUM.fullmatch(str(number)):
        raise WatchError("Invalid PR number")
    if pr.get("state") != "open":
        return None, "closed"
    if pr.get("draft") is not False:
        return None, "draft_or_unknown"
    title = pr.get("title")
    if not isinstance(title, str):
        raise WatchError("Missing PR title")
    head, base = pr.get("head"), pr.get("base")
    if not isinstance(head, dict) or not isinstance(base, dict):
        raise WatchError("Missing PR heads")
    head_ref, base_ref = head.get("ref"), base.get("ref")
    if not isinstance(head_ref, str) or not head_ref or not isinstance(base_ref, str) or not base_ref:
        raise WatchError("Missing PR branch")
    if title.lower().startswith(("backlog:", "review:")) or head_ref.startswith(("notes/", "review/")):
        return None, "backlog_or_review"
    head_repo, base_repo = head.get("repo"), base.get("repo")
    if not isinstance(head_repo, dict) or not isinstance(base_repo, dict):
        return None, "unapproved_repository"
    if head_repo.get("full_name") != SOURCE or base_repo.get("full_name") != SOURCE:
        return None, "unapproved_repository"
    return {"number": number, "sha": exact_sha(head.get("sha"), "PR head SHA"),
            "base_sha": exact_sha(base.get("sha"), "PR base SHA"),
            "head_ref": head_ref, "base_ref": base_ref}, "eligible"


def discover(api):
    candidates, exclusions = [], []
    for page in range(1, MAX_PAGES + 1):
        items = api.request("GET", f"repos/{SOURCE}/pulls?state=open&per_page=100&page={page}")
        if not isinstance(items, list):
            raise WatchError("PR list API returned invalid data")
        for pr in items:
            candidate, reason = classify(pr)
            if candidate is not None:
                candidates.append(candidate)
            else:
                exclusions.append({"number": pr.get("number"), "reason": reason})
        if len(items) < 100:
            return sorted(candidates, key=lambda x: x["number"]), exclusions
    raise WatchError("PR pagination exceeded verified 1000-record boundary")


def select_exact(api, environ):
    """Select one explicitly pinned eligible PR without scanning unrelated PRs.

    Dispatch is a privileged operation: absent, malformed or stale user inputs
    must fail before any claim lookup/write or workflow submission. The caller
    also revalidates the same PR immediately before claiming its revision.
    """
    raw_number = environ.get("ROMARR_SELECTED_PR")
    if not isinstance(raw_number, str) or not NUM.fullmatch(raw_number):
        raise WatchError("Dispatch requires one explicit valid PR number")
    number = int(raw_number)
    head_sha = exact_sha(environ.get("ROMARR_SELECTED_HEAD_SHA"), "Selected PR head SHA")
    base_sha = exact_sha(environ.get("ROMARR_SELECTED_BASE_SHA"), "Selected PR base SHA")
    current = api.request("GET", f"repos/{SOURCE}/pulls/{number}")
    candidate, reason = classify(current)
    if reason != "eligible" or candidate is None or candidate["number"] != number:
        raise WatchError(f"Selected PR is not eligible: {reason}")
    if candidate["sha"] != head_sha or candidate["base_sha"] != base_sha:
        raise WatchError("Selected PR head/base SHA changed or does not match")
    return candidate


def claim_name(pr):
    """Version-2 immutable identity: source PR number, head AND base commit."""
    return f"romarr-ci-v2/pr-{pr['number']}-h-{pr['sha']}-b-{pr['base_sha']}"


def legacy_claim_name(pr):
    """Keep the accepted v1 ledger; do not silently reinterpret its unknown base."""
    return f"romarr-ci-v1/pr-{pr['number']}-{pr['sha']}"


def legacy_attestation(pr):
    """Read a reviewed, immutable receipt; never infer a v1 tag's unknown base."""
    path = Path(__file__).with_name("legacy_receipts.json")
    try:
        evidence = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, ValueError) as error:
        raise WatchError("Legacy receipt collection failed: " + type(error).__name__) from None
    if (not isinstance(evidence, dict) or
        evidence.get("schema") != "romarr-ci-legacy-receipts-v1" or
        evidence.get("source_repository") != SOURCE or
        evidence.get("controller_repository") != CONTROLLER):
        raise WatchError("Legacy receipt source identity mismatch")
    items = evidence.get("records")
    if not isinstance(items, list) or len(items) > 100:
        raise WatchError("Invalid legacy receipt count")
    matches = [r for r in items if isinstance(r, dict) and
               r.get("pr_number") == pr["number"] and r.get("head_sha") == pr["sha"]]
    if len(matches) > 1:
        raise WatchError("Conflicting legacy base attestations")
    if not matches:
        return None
    record = matches[0]
    if (not isinstance(record.get("base_sha"), str) or
        not SHA.fullmatch(record["base_sha"]) or
        not isinstance(record.get("controller_sha"), str) or
        not SHA.fullmatch(record["controller_sha"]) or
        not isinstance(record.get("archive_sha256"), str) or
        not re.fullmatch(r"[0-9a-f]{64}", record["archive_sha256"]) or
        not isinstance(record.get("summary_sha256"), str) or
        not re.fullmatch(r"[0-9a-f]{64}", record["summary_sha256"]) or
        isinstance(record.get("run_id"), bool) or
        not isinstance(record.get("run_id"), int) or record["run_id"] < 1 or
        isinstance(record.get("artifact_id"), bool) or
        not isinstance(record.get("artifact_id"), int) or record["artifact_id"] < 1 or
        record.get("source_postcheck") != "UNCHANGED" or
        record.get("pytest") != "PASS" or record.get("collection") != "PASS" or
        record.get("run_url") !=
            f"https://github.com/{CONTROLLER}/actions/runs/{record['run_id']}"):
        raise WatchError("Legacy receipt not an exact verified base/head/run record")
    return record


def claim_path(pr, *, legacy=False):
    name = legacy_claim_name(pr) if legacy else claim_name(pr)
    return f"repos/{CONTROLLER}/git/ref/tags/{name}"


def claim_exists(api, pr, *, legacy=False):
    name = legacy_claim_name(pr) if legacy else claim_name(pr)
    ref = api.request("GET", claim_path(pr, legacy=legacy), allow_missing=True)
    if ref is None:
        return False
    if not isinstance(ref, dict) or ref.get("ref") != "refs/tags/" + name:
        raise WatchError("Claim ref identity mismatch")
    obj = ref.get("object") or {}
    if obj.get("type") != "commit" or not SHA.fullmatch(str(obj.get("sha", ""))):
        raise WatchError("Claim ref does not point to a verified commit format")
    return True


def verify_controller(api, environ):
    if (environ.get("GITHUB_REPOSITORY") != CONTROLLER or
        environ.get("GITHUB_ACTIONS") != "true" or
        environ.get("RUNNER_OS") != "Linux" or
        environ.get("ROMARR_WATCH_DISPATCH") != "YES"):
        raise WatchError("Dispatch requires explicit trusted controller Actions identity and permission gate")
    sha = exact_sha(environ.get("GITHUB_SHA"), "Controller workflow SHA")
    branch = api.request("GET", f"repos/{CONTROLLER}/git/ref/heads/main")
    branch_obj = branch.get("object") if isinstance(branch, dict) else None
    branch_sha = branch_obj.get("sha") if isinstance(branch_obj, dict) else None
    if not isinstance(branch, dict) or branch.get("ref") != "refs/heads/main" or branch_sha != sha:
        raise WatchError("Controller workflow source no longer equals trusted main")
    return sha


def verify_fresh(api, candidate):
    current = api.request("GET", f"repos/{SOURCE}/pulls/{candidate['number']}")
    now, reason = classify(current)
    if reason != "eligible" or now != candidate:
        raise WatchError("PR identity/head/base changed since discovery")


def dispatch_one(api, pr, controller_sha):
    """Claim first, dispatch once, record run ID as a second durable tag."""
    if claim_exists(api, pr):
        return {"number": pr["number"], "sha": pr["sha"], "status": "ALREADY_CLAIMED"}
    if claim_exists(api, pr, legacy=True):
        receipt = legacy_attestation(pr)
        if receipt is None:
            return {"number": pr["number"], "sha": pr["sha"],
                    "status": "LEGACY_CLAIM_RECONCILE"}
        if receipt["base_sha"] == pr["base_sha"]:
            return {"number": pr["number"], "sha": pr["sha"],
                    "status": "LEGACY_BASE_ATTESTED"}
        # A base-only change is new work: v2 claim safely pins the new base.
    verify_fresh(api, pr)
    claim = "refs/tags/" + claim_name(pr)
    try:
        ref = api.request("POST", f"repos/{CONTROLLER}/git/refs", {"ref": claim, "sha": controller_sha})
    except WatchError as exc:
        # A 422 may mean another worker raced this claim. Check once; otherwise
        # fail closed. Do not retry the write or dispatch on uncertain status.
        if claim_exists(api, pr):
            return {"number": pr["number"], "sha": pr["sha"], "status": "ALREADY_CLAIMED"}
        raise WatchError(f"Claim creation inconclusive: {exc}") from None
    if not isinstance(ref, dict) or ref.get("ref") != claim:
        raise WatchError("Claim response cannot be verified; dispatch withheld")
    # The additive Stage 1 base input fails closed if the PR base moves before
    # source resolution. This tests the pinned HEAD, not a synthetic merge commit.
    payload = {"ref": "main", "return_run_details": True,
               "inputs": {"target": "pull_request", "pr_number": str(pr["number"]),
                          "expected_sha": pr["sha"], "expected_base_sha": pr["base_sha"],
                          "scope": "full"}}
    run = api.request("POST", f"repos/{CONTROLLER}/actions/workflows/{WORKFLOW}/dispatches", payload)
    if not isinstance(run, dict) or not isinstance(run.get("workflow_run_id"), int) or run["workflow_run_id"] < 1:
        raise WatchError("Dispatch response has no verified run ID; claim retained; manual reconciliation required")
    run_id = run["workflow_run_id"]
    expected_url = f"https://github.com/{CONTROLLER}/actions/runs/{run_id}"
    if run.get("html_url") != expected_url:
        raise WatchError("Dispatch run URL/repository mismatch; claim retained")
    run_ref = f"refs/tags/{claim_name(pr)}-run-{run_id}"
    ack = api.request("POST", f"repos/{CONTROLLER}/git/refs", {"ref": run_ref, "sha": controller_sha})
    if not isinstance(ack, dict) or ack.get("ref") != run_ref:
        raise WatchError("Dispatch succeeded but run-ID ledger write is inconclusive; reconcile manually")
    return {"number": pr["number"], "sha": pr["sha"], "status": "DISPATCHED", "run_url": expected_url}


def run(mode, api, environ):
    if mode not in ("audit", "dispatch"):
        raise WatchError("Allowed commands: audit, dispatch")
    start = time.time()
    iso = lambda: dt.datetime.now().astimezone().isoformat(timespec="seconds")
    print("================ PREFLIGHT CHECK ================")
    print("Script: ROMarr PR watch Stage 2 candidate")
    print(f"Expected controller: {CONTROLLER}; source: {SOURCE}; mode: {mode}")
    print(f"Detected controller: {environ.get('GITHUB_REPOSITORY', 'NOT SET')}; time: {iso()}")
    print(f"Node/guest: GitHub-hosted Ubuntu job only; no Proxmox or private target")
    try:
        controller_sha = verify_controller(api, environ) if mode == "dispatch" else None
        if mode == "dispatch":
            # One exact-target lookup. Never enumerate eligible PRs for a write.
            candidates, excluded = [select_exact(api, environ)], []
        else:
            candidates, excluded = discover(api)
        report = {"mode": mode, "eligible": candidates, "excluded": excluded, "results": []}
        for pr in candidates:
            try:
                prior = claim_exists(api, pr)
                legacy = claim_exists(api, pr, legacy=True) if not prior else False
                receipt = legacy_attestation(pr) if legacy else None
                legacy_state = ("LEGACY_CLAIM_RECONCILE" if receipt is None else
                                "LEGACY_BASE_ATTESTED" if receipt["base_sha"] == pr["base_sha"] else
                                "BASE_CHANGED_RETEST_REQUIRED")
                if mode == "audit":
                    outcome = {"number": pr["number"], "sha": pr["sha"],
                               "base_sha": pr["base_sha"],
                               "status": ("ALREADY_CLAIMED" if prior else
                                          legacy_state if legacy else "UNCLAIMED")}
                elif prior:
                    outcome = {"number": pr["number"], "sha": pr["sha"], "status": "ALREADY_CLAIMED"}
                elif legacy and legacy_state != "BASE_CHANGED_RETEST_REQUIRED":
                    outcome = {"number": pr["number"], "sha": pr["sha"],
                               "status": legacy_state}
                elif len([z for z in report["results"] if z["status"] == "DISPATCHED"]) >= MAX_DISPATCHES:
                    outcome = {"number": pr["number"], "sha": pr["sha"], "status": "DEFERRED_RATE_BOUND"}
                else:
                    outcome = dispatch_one(api, pr, controller_sha)
                # All outcomes carry both immutable PR identities, including
                # legacy reconciliation, skipped claims and successful dispatch.
                outcome["base_sha"] = pr["base_sha"]
                report["results"].append(outcome)
            except WatchError as exc:
                report["results"].append({"number": pr["number"], "sha": pr["sha"],
                                          "base_sha": pr["base_sha"],
                                          "status": "BLOCKED", "reason": str(exc)})
        print(json.dumps(report, sort_keys=True, indent=2))
        if any(x["status"] == "BLOCKED" for x in report["results"]):
            raise WatchError("One or more PR operations blocked; see per-PR results")
        return report
    finally:
        print("================ DIAGNOSTIC FINISH ================")
        print(f"Local finish: {iso()}; elapsed seconds: {time.time() - start:.1f}")


def main():
    if len(sys.argv) != 2:
        raise WatchError("Usage: watch.py audit|dispatch")
    api = API(token=os.environ.get("GH_TOKEN", ""))
    run(sys.argv[1], api, os.environ)


if __name__ == "__main__":
    try:
        main()
    except (WatchError, ValueError, TypeError) as exc:
        print("VERIFICATION GATE: BLOCKED — " + str(exc), file=sys.stderr)
        raise SystemExit(2)
