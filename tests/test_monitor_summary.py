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
        self.assertIn("Historical pytest; verify required scope", rendered)
        self.assertNotIn("None from metadata", rendered)
        self.assertIn("`aaaaaaaa` / `bbbbbbbb`", rendered)

    def test_unclaimed_revision_is_not_hidden_by_review_ready(self):
        item = record()
        item["pytest"] = {"status": "NOT_DISPATCHED"}
        rendered = m.render(report([item]))
        self.assertIn("New pytest revision (dispatch not authorized)", rendered)
        self.assertNotIn("None from metadata", rendered)

    def test_artifact_metadata_is_not_artifact_verification(self):
        item = record()
        item["pytest"] = {"status": "WORKFLOW_SUCCESS_ARTIFACT_PRESENT_CONTENTS_UNVERIFIED"}
        rendered = m.render(report([item]))
        self.assertIn("Verify pytest artifact contents", rendered)
        self.assertNotIn("None from metadata", rendered)

    def test_claim_without_ledger_is_not_automatically_retried(self):
        item = record()
        item["pytest"] = {"status": "CLAIM_WITHOUT_UNIQUE_RUN"}
        rendered = m.render(report([item]))
        self.assertIn("Reconcile claim/run ledger; no retry", rendered)

    def test_failed_pytest_workflow_is_not_hidden_by_review_ready(self):
        item = record()
        item["pytest"] = {"status": "WORKFLOW_FAILURE"}
        rendered = m.render(report([item]))
        self.assertIn("Investigate pytest workflow outcome", rendered)

    def test_review_findings_and_pytest_gap_both_remain_visible(self):
        item = record(review_status="UNRESOLVED_THREADS",
                      findings="UNKNOWN_OR_ACTIONABLE", threads=2)
        rendered = m.render(report([item]))
        self.assertIn("Review findings/threads; Historical pytest", rendered)

    def test_unknown_pytest_status_never_claims_no_attention(self):
        item = record()
        item["pytest"] = {"status": "UNKNOWN_TEST_STATE"}
        rendered = m.render(report([item]))
        self.assertIn("Verify pytest state", rendered)
        self.assertNotIn("None from metadata", rendered)

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



class AdvisoryNextTest(unittest.TestCase):
    """A proposed revision must never imply approval or duplicate a receipt."""

    def test_no_new_source_when_pr21_has_valid_v1_receipt(self):
        decision = m.next_test_candidate([record()])
        self.assertEqual(decision["status"], "NO_UNCLAIMED_REVISION")
        self.assertIsNone(decision["candidate"])
        self.assertIn("No eligible PR", m.render(report([record()])))

    def test_one_new_pr_selects_full_sha_and_base(self):
        ready = record(number=29)
        ready["pytest"] = {"status": "NOT_DISPATCHED"}
        decision = m.next_test_candidate([ready])
        self.assertEqual(decision["status"], "ADVISORY_CANDIDATE_ONLY")
        self.assertEqual(decision["candidate"]["number"], 29)
        self.assertEqual(decision["candidate"]["sha"], "a" * 40)
        self.assertEqual(decision["candidate"]["base_sha"], "b" * 40)
        summary = m.render(report([ready]))
        self.assertIn("advisory, no writes", summary)
        self.assertIn("Not a dispatch authorization", summary)

    def test_base_only_change_is_potential_new_revision(self):
        changed = record()
        changed["pytest"] = {"status": "BASE_CHANGED_RETEST_REQUIRED"}
        self.assertEqual(m.next_test_candidate([changed])["candidate"]["number"], 21)

    def test_duplicate_candidate_chooses_lowest_number(self):
        late, early = record(number=31), record(number=30)
        late["pytest"] = {"status": "NOT_DISPATCHED"}
        early["pytest"] = {"status": "NOT_DISPATCHED"}
        decision = m.next_test_candidate([late, early])
        self.assertEqual(decision["count"], 2)
        self.assertEqual(decision["candidate"]["number"], 30)

    def test_unknown_legacy_receipt_does_not_retest(self):
        candidate = record()
        candidate["pytest"] = {"status": "LEGACY_CLAIM_RECONCILE"}
        self.assertEqual(m.next_test_candidate([candidate])["status"], "NO_UNCLAIMED_REVISION")

    def test_existing_v2_claim_without_run_never_retries(self):
        candidate = record()
        candidate["pytest"] = {"status": "CLAIM_WITHOUT_UNIQUE_RUN"}
        self.assertIsNone(m.next_test_candidate([candidate])["candidate"])

    def test_workflow_failure_does_not_auto_retry(self):
        candidate = record()
        candidate["pytest"] = {"status": "WORKFLOW_FAILURE"}
        self.assertEqual(m.next_test_candidate([candidate])["status"], "NO_UNCLAIMED_REVISION")

    def test_collection_failure_suppresses_other_ready_candidates(self):
        fresh = record(number=25)
        fresh["pytest"] = {"status": "NOT_DISPATCHED"}
        broken = {"number": 24, "status": "COLLECTION_FAILED",
                  "reason": "untrusted collector detail"}
        decision = m.next_test_candidate([fresh, broken])
        self.assertEqual(decision["status"], "COLLECTION_INCOMPLETE")
        self.assertIsNone(decision["candidate"])
        rendered = m.render(report([fresh, broken]))
        self.assertIn("no candidate is recommended", rendered)
        self.assertNotIn("Potential next PR", rendered)
        self.assertNotIn("untrusted collector detail", rendered)

    def test_missing_head_on_ready_candidate_fails_closed(self):
        fresh = record()
        fresh["pytest"] = {"status": "NOT_DISPATCHED"}
        fresh["sha"] = "abc"
        with self.assertRaises(m.SummaryError):
            m.next_test_candidate([fresh])

    def test_duplicate_pr_numbers_refused_even_with_collection_failure(self):
        fresh = record()
        fresh["pytest"] = {"status": "NOT_DISPATCHED"}
        broken = {"number": 21, "status": "COLLECTION_FAILED"}
        with self.assertRaises(m.SummaryError):
            m.next_test_candidate([fresh, broken])

    def test_status_injection_is_refused(self):
        fresh = record()
        fresh["pytest"] = {"status": "NOT_DISPATCHED|unsafe"}
        with self.assertRaises(m.SummaryError):
            m.next_test_candidate([fresh])

    def test_zero_or_bool_number_refused(self):
        for bad in (0, True):
            fresh = record()
            fresh["number"] = bad
            with self.subTest(value=bad), self.assertRaises(m.SummaryError):
                m.next_test_candidate([fresh])




if __name__ == "__main__":
    unittest.main()
