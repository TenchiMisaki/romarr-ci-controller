"""Synthetic runner-layout CLI smoke; no network, GitHub token or source tests."""
from __future__ import annotations

import json
import os
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[1]
HEAD = "a" * 40
BASE = "b" * 40


class SyntheticRunnerLayout(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        self.ctl = self.root / "controller"
        self.ctl.mkdir()
        shutil.copy2(ROOT / "controller/scheduled_receipt.py", self.ctl / "scheduled_receipt.py")
        (self.ctl / "monitor_summary.py").write_text('''
class SummaryError(Exception):
    pass

def render(report):
    if report.get("mode") != "read_only" or report.get("source") != "TenchiMisaki/romarr":
        raise SummaryError("Invalid producer report")
    return "## Synthetic sanitized monitor summary\\n"
''', encoding="utf-8")
        (self.ctl / "receipt_collector.py").write_text('''
class GitHubReadClient:
    def __init__(self, token):
        if token != "x":
            raise ValueError("Missing synthetic test token")


def collect_once(*, pr_number, expected_head, expected_base, client):
    return {"status": "RECEIPT_VERIFIED_SKIPS_REQUIRE_POLICY",
            "pr_number": pr_number, "tested_sha": expected_head,
            "base_sha": expected_base, "run_id": 43676714571,
            "public_evidence": "PASS", "unattended_actions_authorized": False,
            "skip_policy": "UNVERIFIED",
            "counts": {"passed": 4029, "skipped": 4, "failed": 0, "errors": 0}}
''', encoding="utf-8")
        self.data = self.root / "status.json"
        self.data.write_text(json.dumps({
            "mode": "read_only", "source": "TenchiMisaki/romarr", "excluded_count": 1,
            "results": [{"number": 28, "status": "CURRENT_METADATA_ONLY", "sha": HEAD,
                         "base_sha": BASE, "pytest": {
                            "status": "WORKFLOW_SUCCESS_ARTIFACT_PRESENT_CONTENTS_UNVERIFIED",
                            "run_id": 43676714571}}]}), encoding="utf-8")

    def run_cli(self, *args, **env):
        extra = {"GITHUB_RUN_NUMBER": "1", "GH_TOKEN": "x"}
        extra.update(env)
        return subprocess.run([sys.executable, "controller/scheduled_receipt.py", *map(str, args)],
                              cwd=self.root, capture_output=True, text=True,
                              env={**os.environ, **extra}, timeout=15)

    def test_exact_action_style_audit_and_finalize(self):
        receipt = self.root / "receipt.json"
        out = self.run_cli("audit", self.data)
        self.assertEqual(out.returncode, 0, out.stderr)
        receipt.write_text(out.stdout, encoding="utf-8")
        result = json.loads(out.stdout)
        self.assertEqual(result["pr_number"], 28)
        self.assertEqual(result["status"], "RECEIPT_VERIFIED_SKIPS_REQUIRE_POLICY")
        output = self.root / "monitor-summary.md"
        second = self.run_cli("finalize", self.data, receipt, output)
        self.assertEqual(second.returncode, 0, second.stderr)
        self.assertIn("4029 passed, 4 skipped", output.read_text(encoding="utf-8"))

    def test_missing_audit_input_still_finalizes_safe_result(self):
        output = self.root / "monitor-summary.md"
        done = self.run_cli("finalize", self.root / "nonexistent.json",
                            self.root / "nonexistent-receipt.json", output)
        self.assertEqual(done.returncode, 2, done.stderr)
        rendered = output.read_text(encoding="utf-8")
        self.assertIn("METADATA COLLECTION: NOT VERIFIED", rendered)
        self.assertIn("RECEIPT COLLECTION: NOT VERIFIED", rendered)

    def test_invalid_metadata_with_successful_audit_output_blocks_green(self):
        self.data.write_text('{"mode":"invalid"}', encoding="utf-8")
        receipt = self.root / "receipt.json"
        receipt.write_text(json.dumps({"schema":"romarr-ci-scheduled-receipt-v01",
                                       "status":"NO_CLAIMED_RECEIPT_CANDIDATE"}), encoding="utf-8")
        output = self.root / "monitor-summary.md"
        result = self.run_cli("finalize", self.data, receipt, output)
        self.assertEqual(result.returncode, 2)
        self.assertIn("METADATA COLLECTION: NOT VERIFIED", output.read_text(encoding="utf-8"))

    def test_no_existing_receipts_is_legitimate_noop(self):
        receipt = self.root / "receipt.json"
        receipt.write_text(json.dumps({"schema":"romarr-ci-scheduled-receipt-v01",
                                       "status":"NO_CLAIMED_RECEIPT_CANDIDATE"}), encoding="utf-8")
        outpath = self.root / "monitor-summary.md"
        result = self.run_cli("finalize", self.data, receipt, outpath)
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertIn("No completed claimed receipt", outpath.read_text(encoding="utf-8"))

    def test_missing_read_token_blocks_audit_without_printing_token(self):
        out = self.run_cli("audit", self.data, GH_TOKEN="")
        self.assertEqual(out.returncode, 2)
        self.assertIn("SCHEDULED RECEIPT: BLOCKED", out.stderr)
        self.assertNotIn("x", out.stdout)
