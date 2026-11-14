#!/usr/bin/env python3
"""Read-only ROMarr PR status: exact base/head pytest receipt and CodeRabbit review.

Neither a green check nor an Actions success is a verified artifact or a clean
CodeRabbit review. Missing GraphQL thread evidence remains NOT VERIFIED.
"""
from __future__ import annotations

import json
import os
from pathlib import Path
import re
import sys
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen

sys.path.insert(0, str(Path(__file__).resolve().parent))
import watch  # noqa: E402

COVERAGE = re.compile(r"<!-- final_review_risk_coverage:(\{[^\n]*\}) -->")
RUN_ID = re.compile(r"[1-9][0-9]{0,18}\Z")
GRAPHQL_QUERY = """query($owner:String!, $repo:String!, $number:Int!, $cursor:String) {
  repository(owner:$owner, name:$repo) {
    pullRequest(number:$number) {
      headRefOid
      reviewThreads(first:100, after:$cursor) {
        pageInfo { hasNextPage endCursor }
        nodes { isResolved isOutdated path }
      }
    }
  }
}"""


def pages(api, suffix):
    """Fetch all bounded REST pages; no silently truncated reviews or checks."""
    all_items = []
    for page in range(1, 11):
        payload = api.request("GET", f"repos/{watch.SOURCE}/{suffix}?per_page=100&page={page}")
        # GitHub checks use a wrapped {total_count, check_runs} collection;
        # pull-request reviews and issue comments are bare arrays.
        rows = payload.get("check_runs") if suffix.endswith("/check-runs") and isinstance(payload, dict) else payload
        if not isinstance(rows, list):
            raise watch.WatchError("Invalid paginated REST collection")
        all_items.extend(rows)
        if len(rows) < 100:
            return all_items
    raise watch.WatchError("REST collection exceeds 1000 rows; status unverified")


def graphql_threads(number, sha, token, opener=urlopen):
    """Read all review-thread resolution states using GitHub's read-only query."""
    if not token:
        raise watch.WatchError("GraphQL authentication unavailable; threads not verified")
    cursor = None
    unresolved = 0
    total = 0
    for _ in range(10):
        payload = {"query": GRAPHQL_QUERY,
                   "variables": {"owner": "TenchiMisaki", "repo": "romarr",
                                 "number": number, "cursor": cursor}}
        request = Request("https://api.github.com/graphql",
                          data=json.dumps(payload).encode("utf-8"), method="POST",
                          headers={"Accept": "application/vnd.github+json",
                                   "Content-Type": "application/json",
                                   "Authorization": "Bearer " + token,
                                   "X-GitHub-Api-Version": "2026-03-10",
                                   "User-Agent": "romarr-ci-controller-status"})
        try:
            with opener(request, timeout=15) as response:
                if response.status != 200:
                    raise watch.WatchError("GraphQL did not return HTTP 200")
                raw = json.loads(response.read().decode("utf-8"))
        except (HTTPError, URLError, TimeoutError, ValueError, UnicodeError) as exc:
            raise watch.WatchError("GraphQL review-thread collection failed: " +
                                   type(exc).__name__) from None
        if not isinstance(raw, dict) or raw.get("errors"):
            raise watch.WatchError("GraphQL review-thread data missing or errors")
        pr = (((raw.get("data") or {}).get("repository") or {}).get("pullRequest") or {})
        if pr.get("headRefOid", "").lower() != sha:
            raise watch.WatchError("GraphQL PR head differs from expected source SHA")
        connection = pr.get("reviewThreads") or {}
        nodes = connection.get("nodes")
        page = connection.get("pageInfo") or {}
        if not isinstance(nodes, list) or not isinstance(page.get("hasNextPage"), bool):
            raise watch.WatchError("Invalid GraphQL review-thread pagination")
        for node in nodes:
            if not isinstance(node, dict) or not isinstance(node.get("isResolved"), bool):
                raise watch.WatchError("Missing review-thread resolution state")
            total += 1
            unresolved += int(not node["isResolved"])
        if not page["hasNextPage"]:
            return {"state": "VERIFIED", "total": total, "unresolved": unresolved}
        next_cursor = page.get("endCursor")
        if not isinstance(next_cursor, str) or not next_cursor or next_cursor == cursor:
            raise watch.WatchError("Invalid GraphQL review-thread cursor")
        cursor = next_cursor
    raise watch.WatchError("GraphQL threads exceed 1000; status unverified")


def review_status(api, pr, *, thread_reader):
    """Separate check execution, current-head review coverage and thread state."""
    sha = pr["sha"]
    number = pr["number"]
    result = {"check": "NOT_FOUND", "coverage": "NOT_VERIFIED",
              "new_findings": "NOT_VERIFIED", "threads": "NOT_VERIFIED",
              "unresolved_threads": None, "status": "REVIEW_NOT_VERIFIED"}
    checks = pages(api, f"commits/{sha}/check-runs")
    selected = [item for item in checks if isinstance(item, dict) and
                item.get("name") == "CodeRabbit" and
                (item.get("app") or {}).get("slug") == "coderabbitai" and
                item.get("head_sha") == sha]
    if selected:
        check = selected[-1]
        result["check"] = ("SUCCESS" if check.get("status") == "completed" and
                           check.get("conclusion") == "success" else
                           str(check.get("conclusion") or check.get("status") or "UNKNOWN").upper())
    comments = pages(api, f"issues/{number}/comments")
    summaries = [c for c in comments if isinstance(c, dict) and
                 (c.get("user") or {}).get("login") == "coderabbitai[bot]" and
                 COVERAGE.search(str(c.get("body") or ""))]
    if summaries:
        latest = max(summaries, key=lambda c: c.get("updated_at") or "")
        body = str(latest.get("body") or "")
        try:
            coverage = json.loads(COVERAGE.search(body).group(1))
        except (json.JSONDecodeError, AttributeError):
            coverage = {}
        if (coverage.get("sourceCommitId") == sha and
            coverage.get("coveredCommitId") == sha and coverage.get("kind") == "reviewed"):
            result["coverage"] = "CURRENT_HEAD_REVIEWED"
            result["new_findings"] = ("NO_NEW_ACTIONABLE" if
                "No actionable comments were generated in the recent review." in body else
                "UNKNOWN_OR_ACTIONABLE")
        else:
            result["coverage"] = "STALE_OR_INCOMPLETE"
    try:
        th = thread_reader(number, sha)
        if th.get("state") != "VERIFIED" or not isinstance(th.get("unresolved"), int):
            raise watch.WatchError("Unverified thread collector")
        result["threads"] = "VERIFIED"
        result["unresolved_threads"] = th["unresolved"]
    except watch.WatchError:
        result["threads"] = "COLLECTION_FAILED"
    if (result["check"] == "SUCCESS" and result["coverage"] == "CURRENT_HEAD_REVIEWED"
        and result["new_findings"] == "NO_NEW_ACTIONABLE" and
        result["threads"] == "VERIFIED" and result["unresolved_threads"] == 0):
        result["status"] = "REVIEW_READY"
    elif result["threads"] == "VERIFIED" and result["unresolved_threads"] > 0:
        result["status"] = "UNRESOLVED_THREADS"
    return result


def pytest_status(api, pr):
    """Read metadata only; artifact contents/hashes require separate inspection."""
    if watch.claim_exists(api, pr):
        matches = api.request("GET", f"repos/{watch.CONTROLLER}/git/matching-refs/tags/{watch.claim_name(pr)}-run-")
        if not isinstance(matches, list):
            raise watch.WatchError("Invalid dispatch ledger collection")
        prefix = "refs/tags/" + watch.claim_name(pr) + "-run-"
        valid = [m for m in matches if isinstance(m, dict) and
                 str(m.get("ref", "")).startswith(prefix) and
                 RUN_ID.fullmatch(str(m["ref"])[len(prefix):])]
        if len(valid) != len(matches) or len(valid) != 1:
            return {"status": "CLAIM_WITHOUT_UNIQUE_RUN", "run_id": None}
        run_id = int(valid[0]["ref"][len(prefix):])
        run = api.request("GET", f"repos/{watch.CONTROLLER}/actions/runs/{run_id}")
        if not isinstance(run, dict) or run.get("id") != run_id or run.get("event") != "workflow_dispatch":
            raise watch.WatchError("Dispatch run identity differs from ledger")
        if run.get("status") != "completed":
            status = "IN_PROGRESS" if run.get("status") in ("queued", "in_progress", "waiting") else "UNKNOWN"
        elif run.get("conclusion") != "success":
            status = "WORKFLOW_" + str(run.get("conclusion") or "UNKNOWN").upper()
        else:
            status = "WORKFLOW_SUCCESS_EVIDENCE_NOT_INDEPENDENTLY_CHECKED"
        return {"status": status, "run_id": run_id}
    return {"status": ("LEGACY_CLAIM_RECONCILE" if watch.claim_exists(api, pr, legacy=True)
                       else "NOT_DISPATCHED"), "run_id": None}


def report(api, pr, *, token, thread_reader=None):
    """Revalidate PR identity after all metadata reads; do not return stale PASS."""
    if thread_reader is None:
        thread_reader = lambda n, sha: graphql_threads(n, sha, token)
    current = api.request("GET", f"repos/{watch.SOURCE}/pulls/{pr['number']}")
    now, reason = watch.classify(current)
    if reason != "eligible" or now != pr:
        return {"number": pr["number"], "status": "STALE", "reason": "PR identity changed"}
    pytest_info = pytest_status(api, pr)
    review = review_status(api, pr, thread_reader=thread_reader)
    watch.verify_fresh(api, pr)
    return {"number": pr["number"], "sha": pr["sha"], "base_sha": pr["base_sha"],
            "pytest": pytest_info, "coderabbit": review,
            "status": "CURRENT_METADATA_ONLY"}


def main():
    if len(sys.argv) != 2 or sys.argv[1] != "audit":
        raise watch.WatchError("Usage: status.py audit (read-only)")
    api = watch.API(token=os.environ.get("GH_TOKEN", ""))
    candidates, excluded = watch.discover(api)
    records = []
    for candidate in candidates:
        try:
            records.append(report(api, candidate, token=os.environ.get("GH_TOKEN", "")))
        except watch.WatchError as exc:
            records.append({"number": candidate["number"], "status": "COLLECTION_FAILED",
                            "reason": str(exc)})
    print(json.dumps({"mode": "read_only", "source": watch.SOURCE,
                      "results": records, "excluded_count": len(excluded)},
                     indent=2, sort_keys=True))


if __name__ == "__main__":
    try:
        main()
    except (watch.WatchError, ValueError, TypeError) as exc:
        print("VERIFICATION GATE: BLOCKED — " + str(exc), file=sys.stderr)
        raise SystemExit(2)
