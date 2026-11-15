"""Offline negative/positive contracts for the exact-target read-only collector."""
from __future__ import annotations

from copy import deepcopy
from io import BytesIO
import json
import hashlib
from pathlib import Path
import shutil
import sys
import tempfile
import unittest
from urllib.error import HTTPError, URLError
from zipfile import ZipFile

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "controller"))
from receipt_collector import (CollectionError, GitHubReadClient, _host_is_artifact_storage,
                               collect_once, MAX_ARCHIVE)
from public_evidence import inspect

HEAD = "07e97f4a86b806a63c549f36e169ac21595e9626"
BASE = "29f52812ff53b58c2f21e910ba267a87acb922a3"
CONTROLLER_SHA = "79966309584ede300f3449e6fcccc8dfb2027c4e"
RUN_ID = 43676714571
ARTIFACT_ID = 14146484206
CLAIM = f"romarr-ci-v2/pr-28-h-{HEAD}-b-{BASE}"
SOURCE = "TenchiMisaki/romarr"
CONTROLLER = "TenchiMisaki/romarr-ci-controller"
STEPS = (
    "Resolve and pin source on GitHub",
    "Checkout pinned public ROMarr source (read-only)",
    "Run exact-source pytest and collect anonymous case outcomes",
    "Independently recheck the live source head and local checkout",
    "Finalize sanitized evidence and checksum manifest",
    "Upload sanitized evidence (never raw JUnit or test logs)",
    "Final evidence acceptance gate",
)


def metadata():
    """Synthetic metadata modeled on public run #43676714571 (no live API)."""
    tag = {"ref": "refs/tags/" + CLAIM, "object": {"type": "commit", "sha": CONTROLLER_SHA}}
    run_tag = {"ref": "refs/tags/" + CLAIM + "-run-" + str(RUN_ID),
               "object": {"type": "commit", "sha": CONTROLLER_SHA}}
    pr = {"number": 28, "state": "open", "draft": False,
          "head": {"sha": HEAD, "repo": {"full_name": SOURCE}},
          "base": {"sha": BASE, "repo": {"full_name": SOURCE}}}
    run = {"id": RUN_ID, "run_attempt": 1,
           "repository": {"full_name": CONTROLLER}, "head_repository": {"full_name": CONTROLLER},
           "head_branch": "main", "head_sha": CONTROLLER_SHA, "event": "workflow_dispatch",
           "path": ".github/workflows/romarr-pytest.yml",
           "status": "completed", "conclusion": "success",
           "html_url": f"https://github.com/{CONTROLLER}/actions/runs/{RUN_ID}"}
    jobs = {"total_count": 1, "jobs": [{"name": "Exact-commit native ROMarr pytest",
             "run_id": RUN_ID, "run_attempt": 1, "head_sha": CONTROLLER_SHA,
             "status": "completed", "conclusion": "success",
             "steps": [{"name": n, "status": "completed", "conclusion": "success"} for n in STEPS]}]}
    art = {"total_count": 1, "artifacts": [{"id": ARTIFACT_ID,
           "name": f"romarr-pytest-handoff-{RUN_ID}-1", "size_in_bytes": 0,
           "digest": "",
           "expired": False, "workflow_run": {"id": RUN_ID, "head_sha": CONTROLLER_SHA, "head_branch": "main"},
           "archive_download_url": f"https://api.github.com/repos/{CONTROLLER}/actions/artifacts/{ARTIFACT_ID}/zip"}]}
    paths = {
        f"repos/{SOURCE}/pulls/28": pr,
        f"repos/{CONTROLLER}/git/ref/tags/{CLAIM}": tag,
        f"repos/{CONTROLLER}/git/matching-refs/tags/{CLAIM}-run-": [run_tag],
        f"repos/{CONTROLLER}/git/ref/tags/{CLAIM}-run-{RUN_ID}": run_tag,
        f"repos/{CONTROLLER}/actions/runs/{RUN_ID}": run,
        f"repos/{CONTROLLER}/actions/runs/{RUN_ID}/jobs?filter=latest&per_page=100&page=1": jobs,
        f"repos/{CONTROLLER}/actions/runs/{RUN_ID}/artifacts?per_page=100&page=1": art,
    }
    return paths


def make_zip(path):
    """Create a synthetic, valid five-member controller ZIP; no private data."""
    counts = {"passed": 1, "skipped": 1, "failed": 0, "errors": 0}
    case_doc = {"schema": "pr-pytest-cases-v1", "repository": SOURCE,
                "tested_sha": HEAD, "scope": "full", "run_id": str(RUN_ID),
                "run_attempt": "1", "pr_number": 28, "counts": counts,
                "cases": [{"id": "case-000001", "outcome": "passed"},
                          {"id": "case-000002", "outcome": "skipped"}]}
    summary = {"schema": "romarr-ci-result-v1", "repository": SOURCE,
               "scope": "full", "tested_sha": HEAD, "base_sha": BASE,
               "run_id": str(RUN_ID), "run_attempt": "1", "pr_number": 28,
               "pr_url": f"https://github.com/{SOURCE}/pull/28", "pytest_exit_code": 0,
               "test_status": "PASS", "environment_status": "PASS",
               "collection_status": "PASS", "counts": counts}
    files = {"HANDOFF.md": b"Anonymous, synthetic receipt test fixture.\n",
             "summary.json": json.dumps(summary).encode(),
             "postcheck.json": json.dumps({"status": "UNCHANGED", "tested_sha": HEAD}).encode(),
             "testcases.json": json.dumps(case_doc).encode()}
    manifest = {"schema": "romarr-ci-manifest-v1",
                "files": {k: hashlib.sha256(v).hexdigest() for k, v in files.items()}}
    files["manifest.json"] = json.dumps(manifest).encode()
    with ZipFile(path, "w") as z:
        for name, payload in files.items():
            z.writestr(name, payload)
    return {"size_in_bytes": path.stat().st_size,
            "digest": "sha256:" + hashlib.sha256(path.read_bytes()).hexdigest()}


class FakeClient:
    def __init__(self, fixture, archive):
        self.fixture = fixture
        self.archive = archive
        self.calls = []
        self.artifact_calls = []
        self.after_pr = None
        self.after_run = None

    def get(self, path):
        self.calls.append(path)
        if self.after_pr is not None and len(self.calls) > 7 and path.endswith("/pulls/28"):
            return deepcopy(self.after_pr)
        if self.after_run is not None and len(self.calls) > 7 and path.endswith(f"/actions/runs/{RUN_ID}"):
            return deepcopy(self.after_run)
        if path not in self.fixture:
            raise CollectionError("Unknown fake GET path")
        return deepcopy(self.fixture[path])

    def artifact(self, artifact_id, destination):
        self.artifact_calls.append(artifact_id)
        shutil.copyfile(self.archive, destination)


class ReceiptCollector(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.archive = Path(self.temp.name) / "source.zip"
        info = make_zip(self.archive)
        self.fixture = metadata()
        self.fixture[f"repos/{CONTROLLER}/actions/runs/{RUN_ID}/artifacts?per_page=100&page=1"]["artifacts"][0].update(info)
        self.client = FakeClient(self.fixture, self.archive)

    def run_receipt(self, client=None):
        return collect_once(pr_number=28, expected_head=HEAD,
                            expected_base=BASE, client=client or self.client,
                            inspect_artifact=inspect)

    def test_positive_synthetic_artifact_and_digest(self):
        got = self.run_receipt()
        self.assertEqual(got["counts"], {"passed": 1, "skipped": 1, "failed": 0, "errors": 0})
        self.assertEqual(got["status"], "RECEIPT_VERIFIED_SKIPS_REQUIRE_POLICY")
        self.assertFalse(got["unattended_actions_authorized"])
        self.assertEqual(self.client.artifact_calls, [ARTIFACT_ID])
        self.assertEqual(len(self.client.calls), 11)

    def test_wrong_expected_head_fails_before_reads(self):
        with self.assertRaisesRegex(CollectionError, "PR/head/base"):
            collect_once(pr_number=28, expected_head="x", expected_base=BASE, client=self.client)
        self.assertEqual(self.client.calls, [])

    def test_pr_head_drift_blocks_before_download(self):
        self.fixture[f"repos/{SOURCE}/pulls/28"]["head"]["sha"] = BASE
        with self.assertRaisesRegex(CollectionError, "PR moved"):
            self.run_receipt()
        self.assertEqual(self.client.artifact_calls, [])

    def test_pr_drift_during_download_blocks_current_result(self):
        pr = deepcopy(self.fixture[f"repos/{SOURCE}/pulls/28"])
        pr["head"]["sha"] = BASE
        self.client.after_pr = pr
        with self.assertRaisesRegex(CollectionError, "changed during collection"):
            self.run_receipt()
        self.assertEqual(self.client.artifact_calls, [ARTIFACT_ID])

    def test_harmless_review_timestamp_change_does_not_stale_evidence(self):
        pr = deepcopy(self.fixture[f"repos/{SOURCE}/pulls/28"])
        pr["updated_at"] = "2026-11-15T05:01:00Z"
        run = deepcopy(self.fixture[f"repos/{CONTROLLER}/actions/runs/{RUN_ID}"])
        run["updated_at"] = "2026-11-15T05:01:00Z"
        self.client.after_pr = pr
        self.client.after_run = run
        self.assertEqual(self.run_receipt()["public_evidence"], "PASS")

    def test_run_attempt_change_blocks_current_result(self):
        run = deepcopy(self.fixture[f"repos/{CONTROLLER}/actions/runs/{RUN_ID}"])
        run["run_attempt"] = 2
        self.client.after_run = run
        with self.assertRaisesRegex(CollectionError, "changed during collection"):
            self.run_receipt()

    def test_missing_claim_fails_closed(self):
        del self.fixture[f"repos/{CONTROLLER}/git/ref/tags/{CLAIM}"]
        with self.assertRaisesRegex(CollectionError, "Unknown fake GET path"):
            self.run_receipt()

    def test_duplicate_ledger_blocks(self):
        k = f"repos/{CONTROLLER}/git/matching-refs/tags/{CLAIM}-run-"
        self.fixture[k].append(deepcopy(self.fixture[k][0]))
        with self.assertRaisesRegex(CollectionError, "ambiguous"):
            self.run_receipt()

    def test_missing_ledger_blocks(self):
        k = f"repos/{CONTROLLER}/git/matching-refs/tags/{CLAIM}-run-"
        self.fixture[k] = []
        with self.assertRaisesRegex(CollectionError, "ambiguous"):
            self.run_receipt()

    def test_running_not_accepted(self):
        self.fixture[f"repos/{CONTROLLER}/actions/runs/{RUN_ID}"]["status"] = "in_progress"
        with self.assertRaisesRegex(CollectionError, "not complete"):
            self.run_receipt()

    def test_wrong_job_head_rejected(self):
        self.fixture[f"repos/{CONTROLLER}/actions/runs/{RUN_ID}/jobs?filter=latest&per_page=100&page=1"]["jobs"][0]["head_sha"] = BASE
        with self.assertRaisesRegex(CollectionError, "Receipt validation blocked"):
            self.run_receipt()

    def test_artifact_metadata_incomplete_blocks(self):
        self.fixture[f"repos/{CONTROLLER}/actions/runs/{RUN_ID}/artifacts?per_page=100&page=1"]["total_count"] = 2
        with self.assertRaisesRegex(CollectionError, "ambiguous"):
            self.run_receipt()

    def test_artifact_digest_tampering_rejected(self):
        self.fixture[f"repos/{CONTROLLER}/actions/runs/{RUN_ID}/artifacts?per_page=100&page=1"]["artifacts"][0]["digest"] = "sha256:" + "0" * 64
        with self.assertRaisesRegex(CollectionError, "Receipt validation blocked"):
            self.run_receipt()

    def test_source_pr_cannot_be_bypassed(self):
        self.fixture[f"repos/{SOURCE}/pulls/28"]["head"]["repo"]["full_name"] = "BlizzHacker/romarr"
        with self.assertRaisesRegex(CollectionError, "PR moved"):
            self.run_receipt()

    def test_untrusted_run_ref_mismatch(self):
        self.fixture[f"repos/{CONTROLLER}/git/ref/tags/{CLAIM}-run-{RUN_ID}"]["object"]["sha"] = BASE
        with self.assertRaisesRegex(CollectionError, "run-ID tag mismatch"):
            self.run_receipt()


class FakeResponse:
    def __init__(self, data=b"{}", status=200, headers=None):
        self.data = BytesIO(data)
        self.status = status
        self.headers = headers or {}
    def read(self, size=-1): return self.data.read(size)
    def __enter__(self): return self
    def __exit__(self, *args): self.data.close()


class FakeOpener:
    def __init__(self, redirect=None, metadata=b"{}", artifact_bytes=None):
        self.redirect = redirect
        self.metadata = metadata
        self.artifact_bytes = artifact_bytes if artifact_bytes is not None else b"abc"
        self.requests = []
    def open(self, request, timeout=15):
        self.requests.append(request)
        if request.full_url.endswith("/zip"):
            raise HTTPError(request.full_url, 302, "Found", {"Location": self.redirect}, None)
        if request.full_url.startswith("https://api.github.com/"):
            return FakeResponse(self.metadata)
        return FakeResponse(self.artifact_bytes, headers={"Content-Length": str(len(self.artifact_bytes))})


class TransportSecurity(unittest.TestCase):
    def test_storage_domains_allowlist(self):
        for url in ("https://results-receiver.actions.githubusercontent.com/a",
                    "https://abc.blob.core.windows.net/container/blob?sig=test",
                    "https://pipelines.actions.githubusercontent.com/file"):
            self.assertTrue(_host_is_artifact_storage(url), url)
        for url in ("http://abc.blob.core.windows.net/x", "https://evil.example/x",
                    "https://a.blob.core.windows.net.evil.example/x",
                    "https://user:pass@a.blob.core.windows.net/x",
                    "https://127.0.0.1/x", "file:///etc/passwd", "https://a.blob.core.windows.net:8443/x",
                    "https://a.blob.core.windows.net/x#fragment"):
            self.assertFalse(_host_is_artifact_storage(url), url)

    def test_redirect_disallows_token_to_storage(self):
        mock = FakeOpener(redirect="https://sample.blob.core.windows.net/artifact/blob?sig=secret")
        with tempfile.TemporaryDirectory() as root:
            client = GitHubReadClient(token="private-test-token", opener=mock)
            size = client.artifact(1, Path(root) / "file.zip")
            self.assertEqual(size, 3)
        self.assertEqual(len(mock.requests), 2)
        self.assertIn("Authorization", mock.requests[0].headers)
        self.assertNotIn("Authorization", mock.requests[1].headers)
        self.assertNotIn("private-test-token", str(mock.requests[1].headers))

    def test_redirect_host_rejected_before_second_request(self):
        mock = FakeOpener(redirect="https://private.example.test/leak?token=a")
        with tempfile.TemporaryDirectory() as root:
            with self.assertRaisesRegex(CollectionError, "Unapproved artifact redirect host"):
                GitHubReadClient(token="secret", opener=mock).artifact(1, Path(root) / "file.zip")
        self.assertEqual(len(mock.requests), 1)

    def test_download_oversize_blocks(self):
        mock = FakeOpener(redirect="https://a.blob.core.windows.net/x", artifact_bytes=b"x" * (MAX_ARCHIVE + 1))
        with tempfile.TemporaryDirectory() as root:
            with self.assertRaisesRegex(CollectionError, "size exceeds"):
                GitHubReadClient(opener=mock).artifact(1, Path(root) / "file.zip")

    def test_metadata_duplicate_keys_rejected(self):
        mock = FakeOpener(metadata=b'{"id":1,"id":2}')
        with self.assertRaisesRegex(CollectionError, "Duplicate GitHub metadata"):
            GitHubReadClient(opener=mock).get(f"repos/{SOURCE}/pulls/28")

    def test_api_path_excludes_other_repositories(self):
        mock = FakeOpener()
        with self.assertRaisesRegex(CollectionError, "Unapproved GitHub"):
            GitHubReadClient(opener=mock).get("repos/SomeOtherUser/private-repo/issues/1")
        self.assertEqual(mock.requests, [])

    def test_transient_http_reads_retry_bounded_with_visible_interval(self):
        calls, intervals = [], []
        class TransientOpener:
            def open(self, req, timeout):
                calls.append(req.full_url)
                if len(calls) < 3:
                    raise HTTPError(req.full_url, 503, "Unavailable", {}, None)
                return FakeResponse(b'{"ok":true}')
        client = GitHubReadClient(opener=TransientOpener(), sleep=intervals.append)
        self.assertEqual(client.get(f"repos/{SOURCE}/pulls/28"), {"ok": True})
        self.assertEqual(len(calls), 3)
        self.assertEqual(intervals, [2, 4])

    def test_auth_and_rate_limit_not_retried(self):
        for code in (401, 403, 404, 429):
            calls, intervals = [], []
            class DeniedOpener:
                def open(self, req, timeout):
                    calls.append(req)
                    raise HTTPError(req.full_url, code, "denied", {}, None)
            with self.assertRaisesRegex(CollectionError, f"HTTP {code}"):
                GitHubReadClient(opener=DeniedOpener(), sleep=intervals.append).get(
                    f"repos/{SOURCE}/pulls/28")
            self.assertEqual(len(calls), 1)
            self.assertEqual(intervals, [])

    def test_transport_reads_retry_bounded(self):
        calls, intervals = [], []
        class FailingOpener:
            def open(self, req, timeout):
                calls.append(req)
                raise URLError("synthetic offline failure")
        with self.assertRaisesRegex(CollectionError, "transport failed"):
            GitHubReadClient(opener=FailingOpener(), sleep=intervals.append).get(
                f"repos/{SOURCE}/pulls/28")
        self.assertEqual(len(calls), 3)
        self.assertEqual(intervals, [2, 4])

    def test_no_untrusted_api_redirect(self):
        class RedirectOpener:
            def open(self, req, timeout):
                raise HTTPError(req.full_url, 302, "Found", {"Location": "https://example.test/?token=secret"}, None)
        with self.assertRaisesRegex(CollectionError, "HTTP 302"):
            GitHubReadClient(token="secret", opener=RedirectOpener()).get(f"repos/{SOURCE}/pulls/28")

    def test_missing_archive_refuses_overwrite(self):
        mock = FakeOpener(redirect="https://a.blob.core.windows.net/x")
        with tempfile.TemporaryDirectory() as root:
            p = Path(root) / "file.zip"
            p.write_bytes(b"valuable prior contents")
            with self.assertRaisesRegex(CollectionError, "Unsafe artifact destination"):
                GitHubReadClient(opener=mock).artifact(1, p)
            self.assertEqual(p.read_bytes(), b"valuable prior contents")

    def test_no_non_get_implementation(self):
        self.assertFalse(hasattr(GitHubReadClient, "post"))
        self.assertFalse(hasattr(GitHubReadClient, "delete"))
        self.assertFalse(hasattr(GitHubReadClient, "put"))


if __name__ == "__main__":
    unittest.main()
