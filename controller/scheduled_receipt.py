"""Offline Stage 5 candidate: inspect one claimed ROMarr receipt per monitor run.

Not deployed. Source-independent selection and rendering only; the live CLI
reuses controller.receipt_collector's existing read-only, final-freshness gates.
No claim creation, dispatch, GitHub mutation, or pytest is implemented here.
"""
from __future__ import annotations

import json
import os
from pathlib import Path
import re
import sys

SOURCE = "TenchiMisaki/romarr"
SCHEMA = "romarr-ci-scheduled-receipt-v01"
SHA = re.compile(r"[0-9a-f]{40}\Z")
STATUS = re.compile(r"[A-Z0-9_]{1,80}\Z")
CLAIMED_READY = "WORKFLOW_SUCCESS_ARTIFACT_PRESENT_CONTENTS_UNVERIFIED"
VERIFIED = frozenset(("RECEIPT_VERIFIED_NO_SKIPS", "RECEIPT_VERIFIED_SKIPS_REQUIRE_POLICY"))
MAX_REPORT_BYTES = 250_000
MAX_RECORDS = 1000


class ScheduleError(ValueError):
    """The pre-existing monitor input does not safely select a receipt."""


def is_sha(value):
    """Return true only for a lowercase full Git SHA-1 identifier."""
    return isinstance(value, str) and SHA.fullmatch(value) is not None


def choose(report, run_number):
    """Select at most one existing v2 receipt with fair, deterministic rotation.

    Global metadata collection gaps suppress all selections. This routine has
    no network access and never uses metadata as evidence of receipt success.
    """
    if not isinstance(report, dict) or report.get("mode") != "read_only" or report.get("source") != SOURCE:
        raise ScheduleError("Invalid report identity")
    rows = report.get("results")
    excluded = report.get("excluded_count")
    if not isinstance(rows, list) or len(rows) > MAX_RECORDS:
        raise ScheduleError("Invalid report row count")
    if type(excluded) is not int or excluded < 0:
        raise ScheduleError("Invalid excluded count")
    if type(run_number) is not int or not 1 <= run_number <= 10**12:
        raise ScheduleError("Invalid monitor run number")

    seen = set()
    candidates = []
    collection_incomplete = False
    for row in rows:
        if not isinstance(row, dict):
            raise ScheduleError("Invalid report record")
        number = row.get("number")
        if type(number) is not int or not 1 <= number <= 999999 or number in seen:
            raise ScheduleError("Invalid or duplicate PR number")
        seen.add(number)
        state = row.get("status")
        if not isinstance(state, str) or not STATUS.fullmatch(state):
            raise ScheduleError("Invalid PR state")
        if state in ("COLLECTION_FAILED", "STALE"):
            collection_incomplete = True
            continue
        if state != "CURRENT_METADATA_ONLY":
            raise ScheduleError("Unsupported PR state")
        head, base = row.get("sha"), row.get("base_sha")
        if not is_sha(head) or not is_sha(base):
            raise ScheduleError("Invalid PR commit identity")
        pytest = row.get("pytest")
        if not isinstance(pytest, dict):
            raise ScheduleError("Missing pytest metadata")
        test_status = pytest.get("status")
        if not isinstance(test_status, str) or not STATUS.fullmatch(test_status):
            raise ScheduleError("Invalid pytest metadata status")
        if test_status == CLAIMED_READY:
            run_id = pytest.get("run_id")
            if type(run_id) is not int or not 1 <= run_id <= 10**19 - 1:
                raise ScheduleError("Missing or invalid run-ID ledger")
            candidates.append((number, head, base, run_id))

    if collection_incomplete:
        return {"schema": SCHEMA, "status": "COLLECTION_INCOMPLETE", "candidate_count": 0}
    if not candidates:
        return {"schema": SCHEMA, "status": "NO_CLAIMED_RECEIPT_CANDIDATE", "candidate_count": 0}
    candidates.sort(key=lambda x: x[0])
    number, head, base, run_id = candidates[(run_number - 1) % len(candidates)]
    return {"schema": SCHEMA, "status": "SELECTED_METADATA_ONLY",
            "candidate_count": len(candidates), "pr_number": number,
            "head_sha": head, "base_sha": base, "run_id": run_id}


def inspect_once(report, run_number, collector, client):
    """Run the existing independent collector once and return sanitized status.

    The collector must independently re-read the PR, claim, run, artifact and
    final freshness; selection metadata alone never establishes acceptance.
    """
    choice = choose(report, run_number)
    if choice["status"] != "SELECTED_METADATA_ONLY":
        return choice
    number, head, base, run_id = (choice[k] for k in ("pr_number", "head_sha", "base_sha", "run_id"))
    common = {"schema": SCHEMA, "pr_number": number,
              "head_sha": head, "base_sha": base, "run_id": run_id,
              "candidate_count": choice["candidate_count"]}
    try:
        result = collector(pr_number=number, expected_head=head, expected_base=base, client=client)
    except ValueError:
        # CollectionError and ReceiptError are both ValueError subclasses;
        # untrusted exception messages must never appear in public output.
        return {**common, "status": "COLLECTION_FAILED"}
    if not isinstance(result, dict):
        return {**common, "status": "COLLECTION_FAILED"}
    verdict = result.get("status")
    counts = result.get("counts")
    if (verdict not in VERIFIED or result.get("pr_number") != number
        or result.get("tested_sha") != head or result.get("base_sha") != base
        or result.get("run_id") != run_id or result.get("public_evidence") != "PASS"
        or result.get("unattended_actions_authorized") is not False
        or not isinstance(counts, dict)
        or any(type(counts.get(k)) is not int or not 0 <= counts[k] <= 1_000_000
               for k in ("passed", "skipped", "failed", "errors"))
        or counts["failed"] != 0 or counts["errors"] != 0 or counts["passed"] == 0
        or (counts["skipped"] > 0) != (verdict == "RECEIPT_VERIFIED_SKIPS_REQUIRE_POLICY")
        or result.get("skip_policy") != ("UNVERIFIED" if counts["skipped"] else "NOT_APPLICABLE")):
        return {**common, "status": "COLLECTION_FAILED"}
    return {**common, "status": verdict,
            "counts": {k: counts[k] for k in ("passed", "skipped", "failed", "errors")},
            "skip_policy": result["skip_policy"]}


def render(result):
    """Render only allowlisted machine statuses and public identity fields."""
    if not isinstance(result, dict) or result.get("schema") != SCHEMA:
        raise ScheduleError("Invalid receipt report schema")
    status = result.get("status")
    allowed = VERIFIED | {"COLLECTION_INCOMPLETE", "COLLECTION_FAILED", "NO_CLAIMED_RECEIPT_CANDIDATE"}
    if not isinstance(status, str) or status not in allowed:
        raise ScheduleError("Invalid receipt report status")
    lines = ["", "### One existing pytest receipt — independently checked (read-only)", ""]
    if status == "COLLECTION_INCOMPLETE":
        lines.append("**COLLECTION INCOMPLETE:** PR metadata is incomplete; no receipt was selected.")
    elif status == "NO_CLAIMED_RECEIPT_CANDIDATE":
        lines.append("No completed claimed receipt is eligible for inspection this run. This does not imply all PRs have passing tests.")
    else:
        n, head, base, run_id = (result.get(k) for k in ("pr_number", "head_sha", "base_sha", "run_id"))
        if (type(n) is not int or not 1 <= n <= 999999 or
            type(run_id) is not int or not 1 <= run_id <= 10**19 - 1 or
            not is_sha(head) or not is_sha(base)):
            raise ScheduleError("Invalid selected receipt identity")
        lines.append(f"ROMarr PR #{n}, head `{head[:8]}`, base `{base[:8]}`, pytest run `{run_id}`.")
        if status == "COLLECTION_FAILED":
            lines.append("**COLLECTION FAILED:** The receipt is not independently accepted; inspect the private job diagnostics.")
        else:
            c = result.get("counts")
            if (not isinstance(c, dict) or
                any(type(c.get(k)) is not int or not 0 <= c[k] <= 1_000_000
                    for k in ("passed", "skipped", "failed", "errors")) or
                c["failed"] != 0 or c["errors"] != 0 or c["passed"] == 0 or
                (c["skipped"] > 0) != (status == "RECEIPT_VERIFIED_SKIPS_REQUIRE_POLICY")):
                raise ScheduleError("Invalid accepted counts")
            lines.append(f"**{status}** — {c['passed']} passed, {c['skipped']} skipped, 0 failed/errors.")
            if c["skipped"]:
                lines.append("**Skip-policy review remains required.** This is not a release, merge or deploy acceptance.")
            else:
                lines.append("This is receipt verification only, not code-review, Docker or release acceptance.")
    return "\n".join(lines) + "\n"


def _unique_keys(pairs):
    """Reject duplicate JSON object keys instead of allowing last-key wins."""
    obj = {}
    for key, value in pairs:
        if key in obj:
            raise ScheduleError("Duplicate report JSON field")
        obj[key] = value
    return obj


def safe_json(path):
    """Read a single, regular, bounded locally produced status JSON file."""
    p = Path(path)
    if not p.is_file() or p.is_symlink() or p.stat().st_size > MAX_REPORT_BYTES:
        raise ScheduleError("Missing, linked or oversized local report")
    try:
        return json.loads(p.read_text(encoding="utf-8"), object_pairs_hook=_unique_keys)
    except (OSError, UnicodeError, ValueError) as exc:
        raise ScheduleError("Invalid local JSON report") from exc



def finalize(status_path, receipt_path, output_path, metadata_renderer):
    """Produce a bounded, sanitized step summary even when prior steps failed.

    The only permitted data from the monitor is its allowlist-rendered status,
    and from the receipt audit its validated machine verdict. Never publish
    raw GitHub API responses, exception text, signed URLs or internal logs.
    An absent/malformed status report suppresses any apparent receipt success.
    """
    try:
        status_report = safe_json(status_path)
        monitor_text = metadata_renderer(status_report)
        if not isinstance(monitor_text, str) or len(monitor_text) > 400_000:
            raise ScheduleError("Invalid sanitized monitor rendering")
        metadata_ok = True
    except Exception:
        # Includes monitor_summary.SummaryError (not a ValueError).
        # Never expose untrusted collector/renderer exception strings.
        monitor_text = ("## ROMarr PR monitor — read-only metadata\n\n"
                        "**METADATA COLLECTION: NOT VERIFIED.** The preceding monitor "
                        "steps did not produce a valid complete report.\n")
        metadata_ok = False

    receipt_acceptable = False
    if metadata_ok:
        try:
            receipt_report = safe_json(receipt_path)
            receipt_text = render(receipt_report)
            receipt_acceptable = receipt_report.get("status") in (VERIFIED | {"NO_CLAIMED_RECEIPT_CANDIDATE"})
        except Exception:
            receipt_text = ("\n### One existing pytest receipt — independently checked (read-only)\n\n"
                            "**RECEIPT COLLECTION: NOT VERIFIED.** No valid complete "
                            "receipt result is available from this run.\n")
    else:
        receipt_text = ("\n### One existing pytest receipt — independently checked (read-only)\n\n"
                        "**RECEIPT COLLECTION: NOT VERIFIED.** Metadata validation "
                        "did not complete.\n")

    destination = Path(output_path)
    if (not destination.parent.is_dir() or destination.is_symlink() or
        destination.exists()):
        raise ScheduleError("Unsafe summary destination")
    combined = monitor_text.rstrip("\n") + "\n" + receipt_text
    if len(combined.encode("utf-8")) > 500_000:
        raise ScheduleError("Sanitized summary exceeds size limit")
    with destination.open("x", encoding="utf-8") as fh:
        fh.write(combined)
    return metadata_ok and receipt_acceptable


def main(argv):
    """Run only one read-only audit or render existing sanitized results."""
    if len(argv) == 5 and argv[1] == "finalize":
        from monitor_summary import render as render_metadata
        # Summary finalization is intentionally nonblocking so that a failed
        # earlier step remains a failed job but the sanitized artifact remains.
        result_acceptable = finalize(argv[2], argv[3], argv[4], render_metadata)
        return 0 if result_acceptable else 2
    if len(argv) != 3 or argv[1] not in ("audit", "render"):
        raise ScheduleError("Expected audit/render or finalize and required file paths")
    data = safe_json(argv[2])
    if argv[1] == "render":
        sys.stdout.write(render(data))
        return 0
    raw_number = os.environ.get("GITHUB_RUN_NUMBER", "")
    if re.fullmatch(r"[1-9][0-9]{0,11}", raw_number) is None:
        raise ScheduleError("Missing verified GitHub run number")
    token = os.environ.get("GH_TOKEN", "")
    if not token:
        raise ScheduleError("GitHub read-only token unavailable")
    # Import only for audit. This file is intended to be installed next to the
    # existing, unchanged and independently tested receipt_collector.py.
    from receipt_collector import GitHubReadClient, collect_once
    result = inspect_once(data, int(raw_number), collect_once, GitHubReadClient(token))
    print(json.dumps(result, sort_keys=True))
    return 2 if result["status"] in ("COLLECTION_INCOMPLETE", "COLLECTION_FAILED") else 0


if __name__ == "__main__":
    try:
        raise SystemExit(main(sys.argv))
    except (ScheduleError, OSError, ImportError, ValueError, TypeError):
        print("SCHEDULED RECEIPT: BLOCKED — invalid or incomplete read-only check", file=sys.stderr)
        raise SystemExit(2) from None
