"""Offline regression tests of the controller; no GitHub account or ROMarr code used."""
import json
import os
from pathlib import Path
import sys
import tempfile
import unittest
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "controller"))
import target  # noqa: E402
import evidence  # noqa: E402

S1 = "a" * 40
S2 = "b" * 40


def fake_pr(*, head=S1, base=S2, draft=False, state="open", head_repo=target.FORK):
    return {
        "number": 25, "state": state, "draft": draft,
        "head": {"sha": head, "ref": "feature", "repo": {"full_name": head_repo}},
        "base": {"sha": base, "ref": "main", "repo": {"full_name": target.FORK}},
    }


def junit(*, totals="tests='3' errors='1' failures='1' skipped='1'", children=None):
    if children is None:
        children = ["<testcase name='a'><failure/></testcase>", "<testcase name='b'><error/></testcase>", "<testcase name='c'><skipped/></testcase>"]
    return f"<testsuites><testsuite {totals}>{''.join(children)}</testsuite></testsuites>"


class TargetTests(unittest.TestCase):
    def test_main_equal(self):
        def fetch(path):
            return {"commit": {"sha": S1}}
        x = target.resolve("main", "", "", fetch)
        self.assertEqual(x["sha"], S1)
        self.assertIsNone(x["number"])

    def test_main_divergent_fails(self):
        def fetch(path):
            return {"commit": {"sha": S1 if path.startswith(target.FORK) else S2}}
        with self.assertRaisesRegex(target.TargetError, "differ"):
            target.resolve("main", "", "", fetch)

    def test_pr_exact_head(self):
        x = target.resolve("pull_request", "25", S1, lambda path: fake_pr())
        self.assertEqual(x["number"], 25)
        self.assertEqual(x["sha"], S1)
        self.assertEqual(x["base_sha"], S2)

    def test_head_changed_fails(self):
        with self.assertRaisesRegex(target.TargetError, "differs"):
            target.resolve("pull_request", "25", S2, lambda path: fake_pr())

    def test_pr_draft_fails(self):
        with self.assertRaisesRegex(target.TargetError, "non-draft"):
            target.resolve("pull_request", "25", "", lambda path: fake_pr(draft=True))

    def test_pr_closed_fails(self):
        with self.assertRaisesRegex(target.TargetError, "open"):
            target.resolve("pull_request", "25", "", lambda path: fake_pr(state="closed"))

    def test_wrong_head_repository_fails(self):
        with self.assertRaisesRegex(target.TargetError, "fork"):
            target.resolve("pull_request", "25", "", lambda path: fake_pr(head_repo="other/fork"))

    def test_refuse_malformed_input(self):
        for pr in ("0", "-1", "25/../26", "abc", "1234567", "25;exit 1"):
            with self.subTest(pr=pr), self.assertRaises(target.TargetError):
                target.resolve("pull_request", pr, "", lambda path: fake_pr())
        with self.assertRaises(target.TargetError):
            target.resolve("pull_request", "25", "deadbeef", lambda path: fake_pr())

    def test_api_host_and_path_guard(self):
        with self.assertRaises(target.TargetError):
            target.github_get("../user", opener=lambda x, timeout: None)


class EvidenceTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.path = Path(self.temp.name) / "input.xml"

    def write(self, xml):
        self.path.write_text(xml, encoding="utf-8")
        return self.path

    def test_counted_mixed(self):
        counts, cases = evidence.collect_junit(self.write(junit()))
        self.assertEqual(counts, {"passed": 0, "failed": 1, "errors": 1, "skipped": 1})
        self.assertEqual([x["id"] for x in cases], ["case-000001", "case-000002", "case-000003"])
        self.assertNotIn("name", str(cases))

    def test_success(self):
        xml = junit(totals="tests='2' errors='0' failures='0' skipped='0'", children=["<testcase name='secret name 1'/>", "<testcase name='secret name 2'/>"])
        counts, cases = evidence.collect_junit(self.write(xml))
        self.assertEqual(counts["passed"], 2)
        self.assertNotIn("secret name", str(cases))

    def test_subtest_mismatch(self):
        xml = junit(totals="tests='3' errors='0' failures='0' skipped='0'", children=["<testcase name='one'/>"])
        with self.assertRaisesRegex(evidence.CollectionError, "declared=3 serialized=1 delta=2"):
            evidence.collect_junit(self.write(xml))

    def test_incorrect_failure_count(self):
        xml = junit(totals="tests='1' errors='0' failures='1' skipped='0'", children=["<testcase name='one'/>"])
        with self.assertRaisesRegex(evidence.CollectionError, "FAILURES_CASE_MISMATCH"):
            evidence.collect_junit(self.write(xml))

    def test_conflicting_case_results(self):
        xml = junit(totals="tests='1' errors='0' failures='1' skipped='0'", children=["<testcase><failure/><skipped/></testcase>"])
        with self.assertRaisesRegex(evidence.CollectionError, "CONFLICTING"):
            evidence.collect_junit(self.write(xml))

    def test_malformed(self):
        with self.assertRaisesRegex(evidence.CollectionError, "MALFORMED"):
            evidence.collect_junit(self.write("<testsuites><testsuite>"))

    def test_missing(self):
        with self.assertRaisesRegex(evidence.CollectionError, "MISSING"):
            evidence.collect_junit(self.path)

    def test_zero_tests(self):
        xml = junit(totals="tests='0' errors='0' failures='0' skipped='0'", children=[])
        with self.assertRaisesRegex(evidence.CollectionError, "NO_TESTS"):
            evidence.collect_junit(self.write(xml))

    def test_checksum_mutation(self):
        self.write("abc")
        first = evidence.digest(self.path)
        self.write("abc123")
        self.assertNotEqual(first, evidence.digest(self.path))

    def test_actual_pytest_success(self):
        source = Path(self.temp.name) / "positive"
        source.mkdir()
        (source / "test_example.py").write_text("def test_pass():\n    assert 1 == 1\n", encoding="utf-8")
        code, timed_out, seconds, raw_log, junit_path = evidence.launch_pytest(source, source, ["test_example.py"])
        counts, anonymous = evidence.collect_junit(junit_path)
        self.assertEqual((code, timed_out, counts["passed"], len(anonymous)), (0, False, 1, 1))
        self.assertIsNotNone(evidence.digest(raw_log))

    def test_actual_pytest_failure(self):
        source = Path(self.temp.name) / "negative"
        source.mkdir()
        (source / "test_example.py").write_text("def test_fail():\n    assert 1 == 2\n", encoding="utf-8")
        code, timed_out, seconds, raw_log, junit_path = evidence.launch_pytest(source, source, ["test_example.py"])
        counts, anonymous = evidence.collect_junit(junit_path)
        self.assertEqual((code, timed_out, counts["failed"]), (1, False, 1))

    def test_actual_pytest_timeout(self):
        source = Path(self.temp.name) / "timed_out"
        source.mkdir()
        (source / "test_example.py").write_text("import time\ndef test_slow():\n    time.sleep(10)\n", encoding="utf-8")
        with patch.object(evidence, "MAX_SECONDS", 1), patch.object(evidence, "HEARTBEAT", 0.25):
            code, timed_out, seconds, raw_log, junit_path = evidence.launch_pytest(source, source, ["test_example.py"])
        self.assertTrue(timed_out)
        self.assertNotEqual(code, 0)
        self.assertLess(seconds, 5)


class GateTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.parent = Path(self.temp.name)
        self.private = self.parent / "romarr-ci-private"
        self.public = self.parent / "romarr-ci-public"
        self.private.mkdir()
        self.public.mkdir()
        self.patches = patch.dict(os.environ, {"RUNNER_TEMP": str(self.parent), "ARTIFACT_STATUS": "success"}, clear=False)
        self.patches.start()
        self.addCleanup(self.patches.stop)
        self.target = {"mode": "pull_request", "repository": target.FORK, "number": 25,
                       "pr_url": f"https://github.com/{target.FORK}/pull/25", "base_ref": "main",
                       "head_ref": "feature", "base_sha": S2, "sha": S1}
        target.atomic_json(self.private / "target.json", self.target)
        self.summary = {"test_status": "PASS", "pytest_exit_code": 0,
                        "environment_status": "PASS", "collection_status": "PASS",
                        "counts": {"passed": 1, "failed": 0, "errors": 0, "skipped": 0},
                        "tested_sha": S1, "scope": "full", "pr_url": self.target["pr_url"], "first_error": None}
        self.cases = {"schema": evidence.CASE_SCHEMA, "tested_sha": S1,
                      "counts": self.summary["counts"], "cases": [{"id": "case-000001", "outcome": "passed"}]}
        target.atomic_json(self.public / "summary.json", self.summary)
        target.atomic_json(self.public / "testcases.json", self.cases)
        target.atomic_json(self.public / "postcheck.json", {"status": "UNCHANGED", "details": []})
        evidence.report_and_manifest()

    def test_green_with_valid_evidence(self):
        evidence.final_gate()

    def test_pytest_failure_never_green(self):
        summary = {**self.summary, "test_status": "FAIL", "pytest_exit_code": 1}
        target.atomic_json(self.public / "summary.json", summary)
        evidence.report_and_manifest()
        with self.assertRaises(SystemExit) as raised:
            evidence.final_gate()
        self.assertEqual(raised.exception.code, 1)

    def test_collection_failure_never_green(self):
        summary = {**self.summary, "collection_status": "FAILED"}
        target.atomic_json(self.public / "summary.json", summary)
        evidence.report_and_manifest()
        with self.assertRaises(SystemExit) as raised:
            evidence.final_gate()
        self.assertEqual(raised.exception.code, 1)

    def test_stale_head_never_green(self):
        target.atomic_json(self.public / "postcheck.json", {"status": "STALE_OR_UNVERIFIED", "details": ["head moved"]})
        evidence.report_and_manifest()
        with self.assertRaises(SystemExit) as raised:
            evidence.final_gate()
        self.assertEqual(raised.exception.code, 1)

    def test_manipulated_case_counts_block(self):
        cases = {**self.cases, "cases": [{"id": "case-000001", "outcome": "failed"}]}
        target.atomic_json(self.public / "testcases.json", cases)
        evidence.report_and_manifest()
        with self.assertRaises(SystemExit) as raised:
            evidence.final_gate()
        self.assertEqual(raised.exception.code, 2)

    def test_manipulated_manifest_block(self):
        (self.public / "HANDOFF.md").write_text("tampered", encoding="utf-8")
        with self.assertRaises(SystemExit) as raised:
            evidence.final_gate()
        self.assertEqual(raised.exception.code, 2)

    def test_artifact_upload_failure_never_green(self):
        with patch.dict(os.environ, {"ARTIFACT_STATUS": "failure"}):
            with self.assertRaises(SystemExit) as raised:
                evidence.final_gate()
            self.assertEqual(raised.exception.code, 1)


if __name__ == "__main__":
    unittest.main()
