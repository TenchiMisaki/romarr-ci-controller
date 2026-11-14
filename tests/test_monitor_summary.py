"""Read-only scheduled monitor must render truthfully and reject unsafe metadata."""
import unittest

from controller import monitor_summary as m


def report(rows=None, excluded=2):
    """Build one canonical metadata-only status report."""
    return {"mode": "read_only", "source": "TenchiMisaki/romarr",
            "excluded_count": excluded,
            "results": [] if rows is None else rows}


def record(number=21, review_status="REVIEW_READY", findings="NO_NEW_ACTIONABLE", threads=0):
    """Provide a valid current-head PR status without claiming test execution."""
    return {
        "number": number, "sha": "a" * 40, "base_sha": "b" * 40,
        "status": "CURRENT_METADATA_ONLY",
        "pytest": {"status": "LEGACY_BASE_ATTESTED_HISTORICAL"},
        "coderabbit": {"status": review_status, "new_findings": findings,
                       "unresolved_threads": threads},
    }


class Render(unittest.TestCase):
    """Preserve evidence and refuse fabricated clean/PASS statuses."""

    def test_empty_report_does_not_claim_test_pass(self):
        rendered = m.render(report())
        self.assertIn("No eligible PRs", rendered)
        self.assertIn("does **not** re-run pytest", rendered)
        self.assertNotIn("TEST=PASS", rendered)

    def test_verified_metadata_is_not_test_execution(self):
        rendered = m.render(report([record()]))
        self.assertIn("LEGACY_BASE_ATTESTED_HISTORICAL", rendered)
        self.assertIn("REVIEW_READY", rendered)
        self.assertIn("None from metadata", rendered)
        self.assertIn("`aaaaaaaa` / `bbbbbbbb`", rendered)

    def test_unresolved_threads_need_attention(self):
        rendered = m.render(report([record(review_status="UNRESOLVED_THREADS",
                                           findings="UNKNOWN_OR_ACTIONABLE", threads=2)]))
        self.assertIn("Review findings/threads", rendered)
        self.assertNotIn("None from metadata", rendered)

    def test_unverified_review_is_not_reported_ready(self):
        rendered = m.render(report([record(review_status="REVIEW_NOT_VERIFIED",
                                           findings="NOT_VERIFIED", threads=None)]))
        self.assertIn("Verify review", rendered)

    def test_collection_failure_is_not_hidden(self):
        broken = {"number": 25, "status": "COLLECTION_FAILED",
                  "reason": "Do not publish raw collector error or secrets"}
        rendered = m.render(report([broken]))
        self.assertIn("COLLECTION FAILED", rendered)
        self.assertNotIn("secrets", rendered)

    def test_bad_source_blocks(self):
        data = report()
        data["source"] = "OtherOwner/romarr"
        with self.assertRaises(m.SummaryError):
            m.render(data)

    def test_wrong_mode_blocks(self):
        data = report()
        data["mode"] = "dispatch"
        with self.assertRaises(m.SummaryError):
            m.render(data)

    def test_duplicate_pr_blocks(self):
        with self.assertRaises(m.SummaryError):
            m.render(report([record(21), record(21)]))

    def test_untrusted_status_injection_blocks(self):
        data = record()
        data["coderabbit"]["status"] = "REVIEW_READY|spoof"
        with self.assertRaises(m.SummaryError):
            m.render(report([data]))

    def test_missing_source_sha_blocks(self):
        data = record()
        data["base_sha"] = "short"
        with self.assertRaises(m.SummaryError):
            m.render(report([data]))

    def test_boolean_or_negative_thread_count_blocks(self):
        for invalid in (True, -1):
            data = record(threads=invalid)
            with self.subTest(value=invalid):
                with self.assertRaises(m.SummaryError):
                    m.render(report([data]))

    def test_unknown_pr_status_blocks(self):
        data = record()
        data["status"] = "SUCCESS"
        with self.assertRaises(m.SummaryError):
            m.render(report([data]))

    def test_invalid_excluded_count_blocks(self):
        for value in (-1, True, "5"):
            with self.subTest(value=value):
                with self.assertRaises(m.SummaryError):
                    m.render(report(excluded=value))


if __name__ == "__main__":
    unittest.main()
