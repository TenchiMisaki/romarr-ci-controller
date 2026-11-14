"""Render read-only PR/CodeRabbit metadata for GitHub Actions step summaries.

The inputs are untrusted JSON. Accept only known structured fields, never copy
arbitrary reasons, comments, or unverified remote text into public Markdown.
"""
from __future__ import annotations

import json
from pathlib import Path
import re
import sys

SOURCE = "TenchiMisaki/romarr"
SHA = re.compile(r"[0-9a-fA-F]{40}\Z")
STATUS = re.compile(r"[A-Z0-9_]{1,80}\Z")


class SummaryError(Exception):
    """The monitor status producer returned incomplete or invalid metadata."""


def clean_status(value, field):
    """Constrain metadata to safe machine statuses before rendering Markdown."""
    if not isinstance(value, str) or not STATUS.fullmatch(value):
        raise SummaryError(f"{field} is missing or unsafe")
    return value


def render(report):
    """Return a sanitized read-only status table, never a test-pass attestation."""
    if not isinstance(report, dict) or report.get("mode") != "read_only" or report.get("source") != SOURCE:
        raise SummaryError("Wrong source or status mode")
    records = report.get("results")
    excluded = report.get("excluded_count")
    if not isinstance(records, list) or len(records) > 1000:
        raise SummaryError("Invalid result list")
    if isinstance(excluded, bool) or not isinstance(excluded, int) or excluded < 0:
        raise SummaryError("Invalid excluded count")
    lines = [
        "## ROMarr PR monitor — read-only metadata",
        "",
        "This report inspects public PR, claim and CodeRabbit metadata. It does **not** re-run pytest, inspect private test artifacts, create claims, dispatch tests, modify source, or certify a deployed build.",
        "",
        f"Eligible reports: **{len(records)}** · Excluded PRs: **{excluded}**",
        "",
        "| PR | Exact head / base | Pytest receipt metadata | CodeRabbit | Attention |",
        "|---|---|---|---|---|",
    ]
    seen = set()
    for record in records:
        if not isinstance(record, dict):
            raise SummaryError("Invalid PR record")
        number = record.get("number")
        if isinstance(number, bool) or not isinstance(number, int) or number < 1 or number > 999999 or number in seen:
            raise SummaryError("Invalid or duplicate PR number")
        seen.add(number)
        state = clean_status(record.get("status"), "PR status")
        if state == "COLLECTION_FAILED":
            lines.append(f"| #{number} | NOT VERIFIED | COLLECTION FAILED | NOT VERIFIED | Inspect collection |")
            continue
        if state != "CURRENT_METADATA_ONLY":
            raise SummaryError("Unsupported PR report state")
        head, base = record.get("sha"), record.get("base_sha")
        if not isinstance(head, str) or not SHA.fullmatch(head) or not isinstance(base, str) or not SHA.fullmatch(base):
            raise SummaryError("Missing immutable source revision")
        pytest = record.get("pytest")
        review = record.get("coderabbit")
        if not isinstance(pytest, dict) or not isinstance(review, dict):
            raise SummaryError("Missing status components")
        test_status = clean_status(pytest.get("status"), "pytest status")
        review_status = clean_status(review.get("status"), "CodeRabbit status")
        findings = clean_status(review.get("new_findings"), "Review findings status")
        unresolved = review.get("unresolved_threads")
        if unresolved is not None and (isinstance(unresolved, bool) or not isinstance(unresolved, int) or unresolved < 0):
            raise SummaryError("Invalid unresolved thread count")
        attention = ("Review findings/threads" if review_status == "UNRESOLVED_THREADS" or
                     findings == "UNKNOWN_OR_ACTIONABLE" else
                     "Verify review" if review_status != "REVIEW_READY" else
                     "None from metadata")
        lines.append(f"| [#{number}](https://github.com/{SOURCE}/pull/{number}) | `{head[:8]}` / `{base[:8]}` | {test_status} | {review_status} | {attention} |")
    if not records:
        lines.append("| — | — | No eligible PRs | — | — |")
    lines.append("")
    lines.append("A successful monitor job means collection/rendering completed, **not** that each PR passed tests or review. A read-only status with unknown findings requires source/review investigation.")
    return "\n".join(lines) + "\n"


def main(argv):
    """Print a GitHub step summary from one known, local JSON report."""
    if len(argv) != 2:
        raise SummaryError("Usage: monitor_summary.py <local status.json>")
    path = Path(argv[1])
    if not path.is_file() or path.is_symlink() or path.stat().st_size > 250000:
        raise SummaryError("Missing, linked, or oversized local status report")
    try:
        report = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, ValueError, UnicodeError) as error:
        raise SummaryError(f"Unparseable status report: {type(error).__name__}") from None
    print(render(report), end="")


if __name__ == "__main__":
    try:
        main(sys.argv)
    except SummaryError as error:
        print("MONITOR COLLECTION: FAILED — " + str(error), file=sys.stderr)
        raise SystemExit(2)
