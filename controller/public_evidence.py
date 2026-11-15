"""Inspect sanitized ROMarr CI artifact ZIPs without trusting their test claims.

This verifies self-consistency only. GitHub run identity, current PR head/base,
workflow conclusion, review, and skip acceptability need separate checks.
"""

from __future__ import annotations

from collections import Counter
import hashlib
import json
import re
import zipfile
import zlib


SHA = re.compile(r"[0-9a-f]{40}\Z")
DIGEST = re.compile(r"[0-9a-f]{64}\Z")
LIMIT = 16 * 1024 * 1024
SCOPES = {"full", "structural"}
UPSTREAM = {"summary.json", "cases.json", "manifest.json"}
CONTROLLER = {"HANDOFF.md", "summary.json", "postcheck.json", "testcases.json", "manifest.json"}


class EvidenceError(ValueError):
    """An artifact was malformed, inconsistent, or inconsistent with its target."""


def _unique_pairs(pairs):
    data = {}
    for key, value in pairs:
        if key in data:
            raise EvidenceError("Duplicate JSON key")
        data[key] = value
    return data


def _json(data):
    try:
        return json.loads(data.decode("utf-8"), object_pairs_hook=_unique_pairs)
    except (UnicodeDecodeError, json.JSONDecodeError) as exc:
        raise EvidenceError("Invalid artifact JSON") from exc


def _cases(cases, *, official):
    if not isinstance(cases, list) or not 0 < len(cases) <= 100_000:
        raise EvidenceError("Missing or excessive anonymous cases")
    counts = Counter()
    for index, case in enumerate(cases, 1):
        identifier = index if official else f"case-{index:06d}"
        if (not isinstance(case, dict) or set(case) != {"id", "outcome"}
                or type(case["id"]) is not type(identifier) or case["id"] != identifier
                or case["outcome"] not in ("passed", "failed", "error" if official else "errors", "skipped")):
            raise EvidenceError("Invalid or non-anonymous case")
        counts[case["outcome"]] += 1
    return {key: counts[key] for key in ("passed", "failed", "error" if official else "errors", "skipped")}


def _counts_match(recorded, observed):
    return (isinstance(recorded, dict) and set(recorded) == set(observed)
            and all(type(recorded[key]) is int and recorded[key] == value
                    for key, value in observed.items()))


def inspect(path, *, repository: str, head: str, base: str, scope: str):
    """Check an artifact against explicit expected source identity; never run code."""
    if repository not in ("BlizzHacker/romarr", "TenchiMisaki/romarr"):
        raise EvidenceError("Unrecognized source repository")
    if not SHA.fullmatch(head) or not SHA.fullmatch(base) or scope not in SCOPES:
        raise EvidenceError("Invalid expected source or scope")
    official = repository == "BlizzHacker/romarr"
    allowed = UPSTREAM if official else CONTROLLER
    try:
        with zipfile.ZipFile(path) as archive:
            entries = archive.infolist()
            names = [item.filename for item in entries]
            if len(names) != len(allowed) or set(names) != allowed:
                raise EvidenceError("Archive members differ from expected schema")
            if any(item.is_dir() or item.file_size > LIMIT
                   or item.file_size > max(item.compress_size, 1) * 200 for item in entries):
                raise EvidenceError("Unsafe, oversized, or excessively compressed member")
            data = {name: archive.read(name) for name in names}
    except (OSError, zipfile.BadZipFile, RuntimeError, EOFError, zlib.error) as exc:
        raise EvidenceError("Unreadable artifact ZIP") from exc

    manifest = _json(data["manifest.json"])
    if not official:
        if not isinstance(manifest, dict) or manifest.get("schema") != "romarr-ci-manifest-v1":
            raise EvidenceError("Unknown controller manifest schema")
        manifest = manifest.get("files")
    if not isinstance(manifest, dict) or set(manifest) != allowed - {"manifest.json"}:
        raise EvidenceError("Missing or unexpected manifest entries")
    for name, digest in manifest.items():
        if not isinstance(digest, str) or not DIGEST.fullmatch(digest) or hashlib.sha256(data[name]).hexdigest() != digest:
            raise EvidenceError("Artifact SHA-256 mismatch")

    summary = _json(data["summary.json"])
    if not isinstance(summary, dict) or summary.get("repository") != repository or summary.get("scope") != scope:
        raise EvidenceError("Artifact repository or scope mismatch")
    if official:
        if (type(summary.get("schema")) is not int or summary["schema"] != 1
                or type(summary.get("exit")) is not int or summary["exit"] != 0
                or summary.get("tested_head") != head
                or summary.get("tested_base") != base):
            raise EvidenceError("Upstream source identity mismatch")
        cases = _json(data["cases.json"])
        observed = _cases(cases, official=True)
        if (not _counts_match(summary.get("counts"), observed) or summary.get("exit") != 0
                or any(summary.get(key) != "PASS" for key in ("test", "environment", "collection"))
                or summary.get("source") != "UNCHANGED"):
            raise EvidenceError("Upstream test, source, or case gate incomplete")
    else:
        if (type(summary.get("pytest_exit_code")) is not int
                or summary["pytest_exit_code"] != 0
                or summary.get("schema") != "romarr-ci-result-v1" or summary.get("tested_sha") != head
                or summary.get("base_sha") != base):
            raise EvidenceError("Controller source identity mismatch")
        post = _json(data["postcheck.json"])
        cases_doc = _json(data["testcases.json"])
        if (not isinstance(post, dict) or post.get("status") != "UNCHANGED"
                or post.get("tested_sha") != head or not isinstance(cases_doc, dict)
                or cases_doc.get("schema") != "pr-pytest-cases-v1"
                or cases_doc.get("repository") != repository or cases_doc.get("tested_sha") != head
                or cases_doc.get("scope") != scope):
            raise EvidenceError("Controller source or case identity mismatch")
        observed = _cases(cases_doc.get("cases"), official=False)
        if (not _counts_match(cases_doc.get("counts"), observed) or not _counts_match(summary.get("counts"), observed)
                or cases_doc.get("run_id") != summary.get("run_id")
                or cases_doc.get("run_attempt") != summary.get("run_attempt")
                or summary.get("pytest_exit_code") != 0
                or any(summary.get(key) != "PASS" for key in ("test_status", "environment_status", "collection_status"))):
            raise EvidenceError("Controller test or case gate incomplete")

    return {
        "artifact_integrity": "PASS", "case_reconciliation": "PASS",
        "repository": repository, "head": head, "base": base, "scope": scope,
        "counts": observed, "skips_require_review": observed["skipped"] > 0,
        "github_run_identity": "EXTERNAL_VERIFICATION_REQUIRED",
        "current_revision": "EXTERNAL_VERIFICATION_REQUIRED",
        "runtime_and_review": "NOT_TESTED_BY_ARTIFACT",
    }
