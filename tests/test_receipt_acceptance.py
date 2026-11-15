"""Offline contract tests for read-only Stage 3 receipt metadata verifier."""
import copy
import hashlib
import json
from pathlib import Path
import sys
import tempfile
import unittest
from zipfile import ZipFile

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "controller"))
from receipt_acceptance import ReceiptError, verify_receipt
from public_evidence import inspect

HEAD = "07e97f4a86b806a63c549f36e169ac21595e9626"
BASE = "29f52812ff53b58c2f21e910ba267a87acb922a3"
CONTROLLER_SHA = "79966309584ede300f3449e6fcccc8dfb2027c4e"
RUN_ID = 43676714571
ARTIFACT_ID = 14146484206
CLAIM = f"romarr-ci-v2/pr-28-h-{HEAD}-b-{BASE}"

STEPS = (
    "Resolve and pin source on GitHub",
    "Checkout pinned public ROMarr source (read-only)",
    "Run exact-source pytest and collect anonymous case outcomes",
    "Independently recheck the live source head and local checkout",
    "Finalize sanitized evidence and checksum manifest",
    "Upload sanitized evidence (never raw JUnit or test logs)",
    "Final evidence acceptance gate",
)


def stub_inspector(path, *, repository, head, base, scope):
    """Contract fixture; integration with real inspector is separately gated."""
    with ZipFile(path) as z:
        counts = json.loads(z.read("summary.json"))["counts"]
    return {"artifact_integrity": "PASS", "case_reconciliation": "PASS",
            "repository": repository, "head": head, "base": base,
            "scope": scope, "counts": counts,
            "skips_require_review": counts["skipped"] > 0}


class TestReceiptAcceptance(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.path = Path(self.temp.name) / "receipt.zip"
        self.meta = {
            "pr": {"number": 28, "state": "open", "draft": False,
                   "head": {"sha": HEAD, "repo": {"full_name": "TenchiMisaki/romarr"}},
                   "base": {"sha": BASE, "repo": {"full_name": "TenchiMisaki/romarr"}}},
            "run": {"id": RUN_ID, "run_attempt": 1, "repository": {"full_name": "TenchiMisaki/romarr-ci-controller"},
                    "head_repository": {"full_name": "TenchiMisaki/romarr-ci-controller"},
                    "head_branch": "main", "head_sha": CONTROLLER_SHA,
                    "event": "workflow_dispatch", "path": ".github/workflows/romarr-pytest.yml",
                    "status": "completed", "conclusion": "success",
                    "html_url": f"https://github.com/TenchiMisaki/romarr-ci-controller/actions/runs/{RUN_ID}"},
            "jobs": {"total_count": 1, "jobs": [{"name": "Exact-commit native ROMarr pytest", "run_id": RUN_ID,
                     "run_attempt": 1, "head_sha": CONTROLLER_SHA, "status": "completed", "conclusion": "success",
                     "steps": [{"name": n, "status": "completed", "conclusion": "success"} for n in STEPS]}]},
            "artifact_listing": {"total_count": 1, "artifacts": [{
                "id": ARTIFACT_ID, "name": f"romarr-pytest-handoff-{RUN_ID}-1", "expired": False,
                "size_in_bytes": 0, "digest": "", "workflow_run": {"id": RUN_ID,
                  "head_sha": CONTROLLER_SHA, "head_branch": "main"},
                "archive_download_url": f"https://api.github.com/repos/TenchiMisaki/romarr-ci-controller/actions/artifacts/{ARTIFACT_ID}/zip"}]},
            "claim_ref": {"ref": "refs/tags/" + CLAIM, "object": {"type": "commit", "sha": CONTROLLER_SHA}},
            "run_ref": {"ref": f"refs/tags/{CLAIM}-run-{RUN_ID}", "object": {"type": "commit", "sha": CONTROLLER_SHA}},
            "expected_pr": 28, "expected_head": HEAD, "expected_base": BASE,
            "controller_sha": CONTROLLER_SHA,
            "archive_path": str(self.path), "inspect_artifact": stub_inspector,
        }
        self.write_archive()

    def write_archive(self, *, skipped=4):
        payload = {"pr_number": 28, "pr_url": "https://github.com/TenchiMisaki/romarr/pull/28",
                   "run_id": str(RUN_ID), "run_attempt": "1", "tested_sha": HEAD, "base_sha": BASE,
                   "counts": {"passed": 2, "skipped": skipped, "failed": 0, "errors": 0}}
        cases = {"pr_number": 28, "run_id": str(RUN_ID), "run_attempt": "1"}
        with ZipFile(self.path, "w") as z:
            z.writestr("summary.json", json.dumps(payload))
            z.writestr("testcases.json", json.dumps(cases))
        a = self.meta["artifact_listing"]["artifacts"][0]
        a["size_in_bytes"] = self.path.stat().st_size
        a["digest"] = "sha256:" + hashlib.sha256(self.path.read_bytes()).hexdigest()

    def accept(self, data=None):
        return verify_receipt(**(data or self.meta))

    def reject(self, mutate, text):
        data = copy.deepcopy(self.meta)
        mutate(data)
        with self.assertRaisesRegex(ReceiptError, text):
            self.accept(data)

    def test_positive_with_skips_remains_non_authorizing(self):
        r = self.accept()
        self.assertEqual(r["status"], "RECEIPT_VERIFIED_SKIPS_REQUIRE_POLICY")
        self.assertEqual(r["skip_policy"], "UNVERIFIED")
        self.assertFalse(r["unattended_actions_authorized"])

    def test_positive_zero_skips_not_automatic_merge(self):
        self.write_archive(skipped=0)
        r = self.accept()
        self.assertEqual(r["status"], "RECEIPT_VERIFIED_NO_SKIPS")
        self.assertFalse(r["unattended_actions_authorized"])

    def test_controller_sha_drift(self):
        self.reject(lambda d: d["run"].update(head_sha=HEAD), "workflow-run")

    def test_wrong_source_head(self):
        self.reject(lambda d: d["pr"]["head"].update(sha=BASE), "head/base")

    def test_wrong_source_repository(self):
        self.reject(lambda d: d["pr"]["head"]["repo"].update(full_name="BlizzHacker/romarr"), "head/base")

    def test_wrong_workflow(self):
        self.reject(lambda d: d["run"].update(path=".github/workflows/romarr-pr-monitor.yml"), "workflow-run")

    def test_bad_conclusion(self):
        self.reject(lambda d: d["run"].update(conclusion="failure"), "workflow-run")

    def test_wrong_run_tag(self):
        self.reject(lambda d: d["run_ref"].update(ref="refs/tags/another"), "run-ID tag")

    def test_missing_required_step(self):
        self.reject(lambda d: d["jobs"]["jobs"][0]["steps"].pop(), "required job step")

    def test_skipped_required_step(self):
        self.reject(lambda d: d["jobs"]["jobs"][0]["steps"][2].update(conclusion="skipped"), "required job step")

    def test_artifact_digest_mismatch(self):
        self.reject(lambda d: d["artifact_listing"]["artifacts"][0].update(digest="sha256:"+"0"*64), "digest mismatch")

    def test_wrong_run_id_in_artifact(self):
        self.reject(lambda d: d["artifact_listing"]["artifacts"][0]["workflow_run"].update(id=9876), "Artifact metadata")

    def test_expired_artifact(self):
        self.reject(lambda d: d["artifact_listing"]["artifacts"][0].update(expired=True), "Artifact metadata")

    def test_missing_artifact_collection(self):
        self.reject(lambda d: d["artifact_listing"].update(total_count=2), "Incomplete or ambiguous")

    def test_duplicate_job_collection(self):
        self.reject(lambda d: d["jobs"].update(total_count=2), "Incomplete or unexpected")

    def test_untrusted_inspector(self):
        self.reject(lambda d: d.update(inspect_artifact=lambda *a, **k: {"artifact_integrity": "FAIL"}), "Detailed artifact")

    def test_wrong_run_id_in_summary(self):
        with ZipFile(self.path, "w") as z:
            z.writestr("summary.json", json.dumps({"run_id": "1", "counts": {"passed":2,"skipped":4,"failed":0,"errors":0}}))
            z.writestr("testcases.json", json.dumps({"run_id": "1"}))
        art = self.meta["artifact_listing"]["artifacts"][0]
        art["size_in_bytes"] = self.path.stat().st_size
        art["digest"] = "sha256:" + hashlib.sha256(self.path.read_bytes()).hexdigest()
        with self.assertRaisesRegex(ReceiptError, "Artifact summary"):
            self.accept()

    def test_changed_attempt(self):
        self.reject(lambda d: d["run"].update(run_attempt=2), "Job identity")

    def test_bad_source_postcheck_result(self):
        self.reject(lambda d: d.update(inspect_artifact=lambda *a, **k:
                          {**stub_inspector(*a, **k), "artifact_integrity": "FAIL"}), "Detailed artifact")

    def test_duplicate_run_step(self):
        self.reject(lambda d: d["jobs"]["jobs"][0]["steps"].append(
            {"name": STEPS[0], "status": "completed", "conclusion": "success"}), "required job step")


class TestRealInspectorIntegration(unittest.TestCase):
    def setUp(self):
        self.fixture = TestReceiptAcceptance(methodName="test_positive_with_skips_remains_non_authorizing")
        self.fixture.setUp()
        self.addCleanup(self.fixture.doCleanups)
        self.write_real_zip()

    def write_real_zip(self, *, tamper=None, skipped=1):
        ctx = self.fixture.meta
        head = ctx["expected_head"]
        base = ctx["expected_base"]
        run = ctx["run"]["id"]
        cases = [{"id": "case-000001", "outcome": "passed"},
                 {"id": "case-000002", "outcome": "skipped" if skipped else "passed"}]
        counts = {"passed": 1 if skipped else 2, "skipped": skipped, "failed": 0, "errors": 0}
        summary = {"schema": "romarr-ci-result-v1", "repository": "TenchiMisaki/romarr",
                   "scope": "full", "tested_sha": head, "base_sha": base,
                   "run_id": str(run), "run_attempt": "1", "pr_number": 28,
                   "pr_url": "https://github.com/TenchiMisaki/romarr/pull/28",
                   "pytest_exit_code": 0, "test_status": "PASS", "environment_status": "PASS",
                   "collection_status": "PASS", "counts": counts}
        case_doc = {"schema": "pr-pytest-cases-v1", "repository": "TenchiMisaki/romarr",
                    "tested_sha": head, "scope": "full", "run_id": str(run),
                    "run_attempt": "1", "pr_number": 28, "counts": counts, "cases": cases}
        post = {"status": "UNCHANGED", "tested_sha": head}
        files = {"HANDOFF.md": b"Sanitized offline fixture.\n",
                 "summary.json": json.dumps(summary, sort_keys=True).encode(),
                 "postcheck.json": json.dumps(post, sort_keys=True).encode(),
                 "testcases.json": json.dumps(case_doc, sort_keys=True).encode()}
        manifest = {"schema": "romarr-ci-manifest-v1",
                    "files": {k: hashlib.sha256(v).hexdigest() for k, v in files.items()}}
        files["manifest.json"] = json.dumps(manifest, sort_keys=True).encode()
        if tamper:
            files[tamper] = b"corrupted evidence"
        with ZipFile(self.fixture.path, "w") as z:
            for name, blob in files.items():
                z.writestr(name, blob)
        meta = ctx["artifact_listing"]["artifacts"][0]
        meta["size_in_bytes"] = self.fixture.path.stat().st_size
        meta["digest"] = "sha256:" + hashlib.sha256(self.fixture.path.read_bytes()).hexdigest()

    def test_real_inspector_accepts_skips_but_not_unattended_authorization(self):
        result = verify_receipt(**{**self.fixture.meta, "inspect_artifact": inspect})
        self.assertEqual(result["status"], "RECEIPT_VERIFIED_SKIPS_REQUIRE_POLICY")
        self.assertEqual(result["counts"], {"passed": 1, "skipped": 1, "failed": 0, "errors": 0})
        self.assertFalse(result["unattended_actions_authorized"])

    def test_real_inspector_accepts_no_skips_without_approving_actions(self):
        self.write_real_zip(skipped=0)
        result = verify_receipt(**{**self.fixture.meta, "inspect_artifact": inspect})
        self.assertEqual(result["status"], "RECEIPT_VERIFIED_NO_SKIPS")
        self.assertFalse(result["unattended_actions_authorized"])

    def test_real_inspector_rejects_tampered_manifest_member_even_with_matching_zip_digest(self):
        self.write_real_zip(tamper="summary.json")
        with self.assertRaisesRegex(ReceiptError, "Detailed public-artifact inspection failed"):
            verify_receipt(**{**self.fixture.meta, "inspect_artifact": inspect})

    def test_real_inspector_rejects_missing_expected_member_even_with_matching_zip_digest(self):
        self.write_real_zip(tamper="postcheck.json")
        with self.assertRaisesRegex(ReceiptError, "Detailed public-artifact inspection failed"):
            verify_receipt(**{**self.fixture.meta, "inspect_artifact": inspect})


if __name__ == "__main__":
    unittest.main()
