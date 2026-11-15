"""Offline synthetic contract tests for Stage 5 candidate (not live GitHub)."""
from __future__ import annotations

import sys
from pathlib import Path
import unittest
from unittest.mock import patch
import json
import tempfile
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "controller"))
import scheduled_receipt as s

H1 = "a" * 40
B1 = "b" * 40
H2 = "c" * 40
B2 = "d" * 40


def row(number=28, head=H1, base=B1, status=s.CLAIMED_READY, run_id=43676714571):
    return {"number": number, "status": "CURRENT_METADATA_ONLY", "sha": head,
            "base_sha": base, "pytest": {"status": status, "run_id": run_id},
            "coderabbit": {"status": "REVIEW_NOT_VERIFIED"}}


def report(*rows):
    return {"mode": "read_only", "source": s.SOURCE, "excluded_count": 2, "results": list(rows)}


def accepted(*, pr_number, expected_head, expected_base, client):
    assert client == "offline-injected-fake"
    return {"status": "RECEIPT_VERIFIED_SKIPS_REQUIRE_POLICY",
            "pr_number": pr_number, "tested_sha": expected_head,
            "base_sha": expected_base, "run_id": 43676714571,
            "public_evidence": "PASS", "unattended_actions_authorized": False,
            "skip_policy": "UNVERIFIED",
            "counts": {"passed": 4029, "skipped": 4, "failed": 0, "errors": 0}}


class Stage5OfflineContract(unittest.TestCase):
    def test_one_existing_claim_selection(self):
        c = s.choose(report(row()), 1)
        self.assertEqual(c["status"], "SELECTED_METADATA_ONLY")
        self.assertEqual(c["pr_number"], 28)
        self.assertEqual(c["run_id"], 43676714571)

    def test_no_claim_preserves_not_dispatched(self):
        c = s.choose(report(row(status="NOT_DISPATCHED", run_id=None)), 2)
        self.assertEqual(c["status"], "NO_CLAIMED_RECEIPT_CANDIDATE")

    def test_no_candidate_when_in_progress(self):
        self.assertEqual(s.choose(report(row(status="IN_PROGRESS")), 1)["status"],
                         "NO_CLAIMED_RECEIPT_CANDIDATE")

    def test_round_robin_without_mutating_any_claim(self):
        rows = report(row(35, H2, B2, run_id=44), row(28, H1, B1))
        self.assertEqual(s.choose(rows, 1)["pr_number"], 28)
        self.assertEqual(s.choose(rows, 2)["pr_number"], 35)
        self.assertEqual(s.choose(rows, 3)["pr_number"], 28)

    def test_incomplete_metadata_suppresses_all(self):
        x = report(row(), {"number": 29, "status": "COLLECTION_FAILED", "reason": "private detail"})
        self.assertEqual(s.choose(x, 2)["status"], "COLLECTION_INCOMPLETE")

    def test_stale_metadata_suppresses_all(self):
        x = report(row(), {"number": 30, "status": "STALE"})
        self.assertEqual(s.choose(x, 3)["status"], "COLLECTION_INCOMPLETE")

    def test_duplicate_pr_fails_closed(self):
        with self.assertRaises(s.ScheduleError):
            s.choose(report(row(), row()), 1)

    def test_wrong_repository_fails_closed(self):
        x = report(row())
        x["source"] = "SomeoneElse/romarr"
        with self.assertRaises(s.ScheduleError):
            s.choose(x, 1)

    def test_invalid_head_and_base_fails_closed(self):
        for bad in ("deadbeef", "A" * 40, 123, None):
            with self.subTest(bad=bad), self.assertRaises(s.ScheduleError):
                s.choose(report(row(head=bad)), 1)

    def test_invalid_run_ledger_fails_closed(self):
        for bad in (None, 0, True, "9", -3):
            with self.subTest(bad=bad), self.assertRaises(s.ScheduleError):
                s.choose(report(row(run_id=bad)), 1)

    def test_invalid_run_number_fails_closed(self):
        for bad in (None, False, 0, -1, 10**13, "1"):
            with self.subTest(bad=bad), self.assertRaises(s.ScheduleError):
                s.choose(report(row()), bad)

    def test_skip_policy_preserved_for_real_recorded_counts(self):
        c = s.inspect_once(report(row()), 1, accepted, "offline-injected-fake")
        self.assertEqual(c["status"], "RECEIPT_VERIFIED_SKIPS_REQUIRE_POLICY")
        self.assertEqual(c["counts"]["skipped"], 4)
        self.assertIn("Skip-policy review remains required", s.render(c))

    def test_collector_failure_never_prints_untrusted_error(self):
        def fail(**kwargs):
            raise ValueError("https://signed-url.example/private-token")
        c = s.inspect_once(report(row()), 1, fail, "fake")
        self.assertEqual(c["status"], "COLLECTION_FAILED")
        self.assertNotIn("signed-url", str(c) + s.render(c))

    def test_reject_wrong_run_identity(self):
        def fail(**kwargs):
            r = accepted(**kwargs)
            r["run_id"] += 1
            return r
        self.assertEqual(s.inspect_once(report(row()), 1, fail, "offline-injected-fake")["status"],
                         "COLLECTION_FAILED")

    def test_reject_changed_source_identity_after_fake_collection(self):
        def fail(**kwargs):
            r = accepted(**kwargs)
            r["tested_sha"] = H2
            return r
        self.assertEqual(s.inspect_once(report(row()), 1, fail, "offline-injected-fake")["status"],
                         "COLLECTION_FAILED")

    def test_reject_lying_skip_policy(self):
        def fail(**kwargs):
            r = accepted(**kwargs)
            r["skip_policy"] = "NOT_APPLICABLE"
            return r
        self.assertEqual(s.inspect_once(report(row()), 1, fail, "offline-injected-fake")["status"],
                         "COLLECTION_FAILED")

    def test_reject_claimed_green_with_failed_test(self):
        def fail(**kwargs):
            r = accepted(**kwargs)
            r["counts"]["failed"] = 1
            return r
        self.assertEqual(s.inspect_once(report(row()), 1, fail, "offline-injected-fake")["status"],
                         "COLLECTION_FAILED")

    def test_zero_skips_reported_separately(self):
        def no_skips(**kwargs):
            r = accepted(**kwargs)
            r["counts"]["skipped"] = 0
            r["status"] = "RECEIPT_VERIFIED_NO_SKIPS"
            r["skip_policy"] = "NOT_APPLICABLE"
            return r
        c = s.inspect_once(report(row()), 1, no_skips, "offline-injected-fake")
        self.assertEqual(c["status"], "RECEIPT_VERIFIED_NO_SKIPS")
        self.assertNotIn("Skip-policy review remains required", s.render(c))

    def test_unknown_verdict_never_renders(self):
        with self.assertRaises(s.ScheduleError):
            s.render({"schema": s.SCHEMA, "status": "PASS_AND_DEPLOY"})

    def test_untrusted_raw_metadata_is_not_rendered(self):
        c = s.choose(report(row(status="NOT_DISPATCHED", run_id=None)), 1)
        self.assertNotIn("PASS", s.render(c))



class FinalizationRecovery(unittest.TestCase):
    """Exercise positive and fail-closed summary recovery without GitHub access."""

    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.root = Path(self.tmp.name)
        self.status = self.root / "status.json"
        self.receipt = self.root / "receipt.json"
        self.output = self.root / "summary.md"
        self.status.write_text(json.dumps(report(row())), encoding="utf-8")
        self.receipt.write_text(json.dumps(s.inspect_once(report(row()), 1, accepted,
                                                          "offline-injected-fake")), encoding="utf-8")

    def renderer(self, data):
        if data.get("source") != s.SOURCE:
            raise ValueError("No raw source text should be printed")
        return "## Verified sanitized metadata table\n"

    def test_valid_status_and_receipt_keeps_skip_flag(self):
        ok = s.finalize(self.status, self.receipt, self.output, self.renderer)
        text = self.output.read_text(encoding="utf-8")
        self.assertTrue(ok)
        self.assertIn("4 skipped", text)
        self.assertIn("Skip-policy review remains required", text)
        self.assertNotIn("METADATA COLLECTION: NOT VERIFIED", text)

    def test_missing_metadata_suppresses_even_valid_receipt(self):
        self.status.unlink()
        self.assertFalse(s.finalize(self.status, self.receipt, self.output, self.renderer))
        result = self.output.read_text(encoding="utf-8")
        self.assertIn("METADATA COLLECTION: NOT VERIFIED", result)
        self.assertIn("RECEIPT COLLECTION: NOT VERIFIED", result)
        self.assertNotIn("4029", result)

    def test_corrupt_metadata_cannot_echo_secret(self):
        self.status.write_text('{"secret":"do-not-publish", invalid}', encoding="utf-8")
        self.assertFalse(s.finalize(self.status, self.receipt, self.output, self.renderer))
        self.assertNotIn("do-not-publish", self.output.read_text(encoding="utf-8"))

    def test_missing_receipt_produces_sanitized_incomplete_section(self):
        self.receipt.unlink()
        self.assertFalse(s.finalize(self.status, self.receipt, self.output, self.renderer))
        result = self.output.read_text(encoding="utf-8")
        self.assertIn("Verified sanitized metadata table", result)
        self.assertIn("RECEIPT COLLECTION: NOT VERIFIED", result)

    def test_corrupt_receipt_never_leaks_url(self):
        self.receipt.write_text('{"url":"https://private.example/signed?key=secret",}', encoding="utf-8")
        self.assertFalse(s.finalize(self.status, self.receipt, self.output, self.renderer))
        result = self.output.read_text(encoding="utf-8")
        self.assertNotIn("private.example", result)
        self.assertNotIn("secret", result)

    def test_collector_reported_failure_never_returns_verified(self):
        self.receipt.write_text(json.dumps({"schema": s.SCHEMA,
            "status": "COLLECTION_FAILED", "pr_number": 28,
            "head_sha": H1, "base_sha": B1, "run_id": 43676714571}), encoding="utf-8")
        self.assertFalse(s.finalize(self.status, self.receipt, self.output, self.renderer))
        self.assertIn("COLLECTION FAILED", self.output.read_text(encoding="utf-8"))

    def test_invalid_receipt_schema_never_claims_pass(self):
        self.receipt.write_text(json.dumps({"schema":"invalid", "status":"RECEIPT_VERIFIED_NO_SKIPS"}), encoding="utf-8")
        self.assertFalse(s.finalize(self.status, self.receipt, self.output, self.renderer))
        self.assertNotIn("RECEIPT_VERIFIED_NO_SKIPS", self.output.read_text(encoding="utf-8"))

    def test_never_overwrites_existing_result(self):
        """An already-present result must never be replaced on any OS."""
        self.output.write_text("previous run protected", encoding="utf-8")
        with self.assertRaises(s.ScheduleError):
            s.finalize(self.status, self.receipt, self.output, self.renderer)
        self.assertEqual(self.output.read_text(encoding="utf-8"), "previous run protected")

    def test_never_overwrites_real_symlink(self):
        """Exercise the filesystem symlink branch when OS permissions permit."""
        try:
            self.output.symlink_to(self.status)
        except OSError as exc:
            if getattr(exc, "winerror", None) == 1314:
                self.skipTest("Native symlink creation not permitted on this Windows account (WinError 1314)")
            raise
        self.assertTrue(self.output.is_symlink())
        with self.assertRaises(s.ScheduleError):
            s.finalize(self.status, self.receipt, self.output, self.renderer)
        self.assertEqual(json.loads(self.status.read_text(encoding="utf-8"))["source"], s.SOURCE)
        self.assertTrue(self.output.is_symlink())

    def test_rejects_simulated_symlink_without_os_privilege(self):
        """Always verify fail-closed logic even when Windows cannot make links."""
        with patch.object(type(self.output), "is_symlink", autospec=True,
                          side_effect=lambda path: path == self.output) as probe:
            with self.assertRaises(s.ScheduleError):
                s.finalize(self.status, self.receipt, self.output, self.renderer)
            self.assertTrue(any(call.args[0] == self.output for call in probe.call_args_list))
        self.assertFalse(self.output.exists())
        self.assertEqual(json.loads(self.status.read_text(encoding="utf-8"))["source"], s.SOURCE)

    def test_symlink_permission_denied_is_explicitly_skipped(self):
        """Negative test for the Windows 1314 collector classification path."""
        denied = OSError("A required privilege is not held by the client")
        denied.winerror = 1314
        with patch.object(type(self.output), "symlink_to", side_effect=denied):
            with self.assertRaisesRegex(unittest.SkipTest, "WinError 1314"):
                self.test_never_overwrites_real_symlink()
        self.assertFalse(self.output.exists())

    def test_renderer_custom_exception_yields_safe_fallback(self):
        class RendererError(Exception):
            pass
        def broken(_):
            raise RendererError("private signed URL and credentials")
        self.assertFalse(s.finalize(self.status, self.receipt, self.output, broken))
        rendered = self.output.read_text(encoding="utf-8")
        self.assertIn("METADATA COLLECTION: NOT VERIFIED", rendered)
        self.assertNotIn("credentials", rendered)

    def test_duplicate_json_fields_rejected_without_leaking(self):
        self.status.write_text('{"source":"one","source":"two","token":"secret"}', encoding="utf-8")
        self.assertFalse(s.finalize(self.status, self.receipt, self.output, self.renderer))
        self.assertIn("METADATA COLLECTION: NOT VERIFIED", self.output.read_text(encoding="utf-8"))
        self.assertNotIn("secret", self.output.read_text(encoding="utf-8"))

    def test_renderer_rejects_untrusted_source_without_leaking(self):
        self.status.write_text(json.dumps({"source":"unexpected"}), encoding="utf-8")
        self.assertFalse(s.finalize(self.status, self.receipt, self.output, self.renderer))
        self.assertIn("METADATA COLLECTION: NOT VERIFIED", self.output.read_text(encoding="utf-8"))

    def test_rejects_oversized_rendering(self):
        self.assertFalse(s.finalize(self.status, self.receipt, self.output,
                                    lambda data: "do-not-publish" * 30000))
        self.assertNotIn("do-not-publish", self.output.read_text(encoding="utf-8"))


if __name__ == "__main__":
    unittest.main()
