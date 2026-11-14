"""Offline Stage 2B status tests: no network and no source writes."""
import io
import json
import unittest
from unittest.mock import Mock
from controller import status as s


H = "a" * 40
B = "b" * 40
C = "c" * 40
P = {"number": 21, "sha": H, "base_sha": B,
     "base_ref": "feature/base", "head_ref": "feature/ui"}
COVERED = ('<!-- final_review_risk_coverage:{"sourceCommitId":"' + H +
           '","coveredCommitId":"' + H + '","kind":"reviewed"} -->')


class ReadAPI:
    def __init__(self, *, claimed=False, legacy=False, ledger=None, run=None,
                 checks=None, comments=None, artifacts=None):
        self.claimed = claimed
        self.legacy = legacy
        self.ledger = ledger if ledger is not None else []
        self.run = run or {}
        self.checks = checks if checks is not None else []
        self.comments = comments if comments is not None else []
        self.artifacts = artifacts if artifacts is not None else []
        self.calls = []

    def request(self, method, path, body=None, allow_missing=False):
        self.calls.append((method, path))
        if method != "GET":
            raise AssertionError("status unexpectedly attempted mutation")
        if "/git/ref/tags/romarr-ci-v2/" in path:
            return ({"ref": "refs/tags/" + path.split("/tags/")[1],
                     "object": {"sha": C, "type": "commit"}} if self.claimed else None)
        if "/git/ref/tags/romarr-ci-v1/" in path:
            return ({"ref": "refs/tags/" + path.split("/tags/")[1],
                     "object": {"sha": C, "type": "commit"}} if self.legacy else None)
        if "/git/matching-refs/tags/" in path:
            return self.ledger
        if "/actions/runs/" in path and path.endswith("/artifacts"):
            return {"artifacts": self.artifacts}
        if "/actions/runs/" in path:
            return self.run
        if "/check-runs?" in path:
            return {"total_count": len(self.checks), "check_runs": self.checks}
        if "/comments?" in path:
            return self.comments
        if "/pulls/21" in path:
            return {"number": 21, "state": "open", "draft": False,
                    "title": "feat: UI",
                    "head": {"sha": H, "ref": "feature/ui", "repo": {"full_name": s.watch.SOURCE}},
                    "base": {"sha": B, "ref": "feature/base", "repo": {"full_name": s.watch.SOURCE}}}
        raise AssertionError("Unknown API route: " + path)


def check(head=H, status="completed", conclusion="success"):
    return {"name": "CodeRabbit", "head_sha": head, "status": status,
            "conclusion": conclusion, "app": {"slug": "coderabbitai"}}


def comment(body=COVERED + "\nNo actionable comments were generated in the recent review."):
    return {"user": {"login": "coderabbitai[bot]"},
            "updated_at": "2026-11-14T22:00:00Z", "body": body}


def threads(unresolved=0):
    return lambda n, sha: {"state": "VERIFIED", "unresolved": unresolved,
                           "total": unresolved}


class Pagination(unittest.TestCase):
    def test_wrapped_checks(self):
        api = ReadAPI(checks=[check()])
        rows = s.pages(api, f"commits/{H}/check-runs")
        self.assertEqual(rows[0]["name"], "CodeRabbit")
        self.assertEqual(len(api.calls), 1)

    def test_bare_comments(self):
        self.assertEqual(s.pages(ReadAPI(comments=[comment()]), "issues/21/comments")[0]["body"], comment()["body"])

    def test_bad_collection_fails_closed(self):
        with self.assertRaises(s.watch.WatchError):
            s.pages(Mock(request=lambda *args: {"unexpected": []}), "issues/21/comments")


class Review(unittest.TestCase):
    def test_review_ready_requires_all_three_checks(self):
        r = s.review_status(ReadAPI(checks=[check()], comments=[comment()]),
                            P, thread_reader=threads())
        self.assertEqual(r["status"], "REVIEW_READY")
        self.assertEqual(r["new_findings"], "NO_NEW_ACTIONABLE")
        self.assertEqual(r["unresolved_threads"], 0)

    def test_green_check_only_is_not_clean(self):
        r = s.review_status(ReadAPI(checks=[check()]), P, thread_reader=threads())
        self.assertEqual(r["status"], "REVIEW_NOT_VERIFIED")
        self.assertEqual(r["coverage"], "NOT_VERIFIED")

    def test_old_commit_review_is_not_current(self):
        body = COVERED.replace(H, C) + "\nNo actionable comments were generated in the recent review."
        r = s.review_status(ReadAPI(checks=[check()], comments=[comment(body)]),
                            P, thread_reader=threads())
        self.assertEqual(r["coverage"], "STALE_OR_INCOMPLETE")
        self.assertNotEqual(r["status"], "REVIEW_READY")

    def test_unresolved_threads_block(self):
        r = s.review_status(ReadAPI(checks=[check()], comments=[comment()]),
                            P, thread_reader=threads(1))
        self.assertEqual(r["status"], "UNRESOLVED_THREADS")

    def test_actionable_new_review_not_clean(self):
        r = s.review_status(ReadAPI(checks=[check()],
                         comments=[comment(COVERED + "\nActionable comments posted: 1")]),
                         P, thread_reader=threads())
        self.assertEqual(r["new_findings"], "UNKNOWN_OR_ACTIONABLE")
        self.assertNotEqual(r["status"], "REVIEW_READY")

    def test_unavailable_thread_collector_not_clean(self):
        def failed(n, sha):
            raise s.watch.WatchError("GraphQL forbidden")
        r = s.review_status(ReadAPI(checks=[check()], comments=[comment()]),
                            P, thread_reader=failed)
        self.assertEqual(r["threads"], "COLLECTION_FAILED")
        self.assertEqual(r["status"], "REVIEW_NOT_VERIFIED")

    def test_incomplete_check_is_not_clean(self):
        r = s.review_status(ReadAPI(checks=[check(status="in_progress", conclusion=None)],
                                     comments=[comment()]), P, thread_reader=threads())
        self.assertNotEqual(r["status"], "REVIEW_READY")


class Receipts(unittest.TestCase):
    def test_no_claim(self):
        self.assertEqual(s.pytest_status(ReadAPI(), P)["status"], "NOT_DISPATCHED")

    def test_legacy_needs_reconciliation(self):
        a = ReadAPI(legacy=True)
        self.assertEqual(s.pytest_status(a, P)["status"], "LEGACY_CLAIM_RECONCILE")
        self.assertTrue(all(m == "GET" for m, _ in a.calls))

    def test_claim_without_run_never_passes(self):
        self.assertEqual(s.pytest_status(ReadAPI(claimed=True), P)["status"],
                         "CLAIM_WITHOUT_UNIQUE_RUN")

    def test_exact_run_success_is_metadata_only(self):
        run_id = 123
        tag = "refs/tags/" + s.watch.claim_name(P) + "-run-" + str(run_id)
        api = ReadAPI(claimed=True, ledger=[{"ref": tag, "object": {"type": "commit", "sha": C}}],
                      run={"id": run_id, "event": "workflow_dispatch", "head_sha": C,
                           "path": ".github/workflows/romarr-pytest.yml",
                           "html_url": "https://github.com/" + s.watch.CONTROLLER + "/actions/runs/123",
                           "status": "completed", "conclusion": "success"},
                      artifacts=[{"name": "romarr-pytest-handoff-123-1",
                                  "expired": False, "size_in_bytes": 12049}])
        self.assertEqual(s.pytest_status(api, P)["status"],
                         "WORKFLOW_SUCCESS_ARTIFACT_PRESENT_CONTENTS_UNVERIFIED")


    def test_run_ledger_with_untrusted_controller_sha_blocks(self):
        run_id = 123
        tag = "refs/tags/" + s.watch.claim_name(P) + "-run-" + str(run_id)
        api = ReadAPI(claimed=True, ledger=[{"ref": tag, "object": {"type": "commit", "sha": C}}],
                      run={"id": run_id, "event": "workflow_dispatch", "head_sha": H,
                           "path": ".github/workflows/romarr-pytest.yml",
                           "html_url": "https://github.com/" + s.watch.CONTROLLER + "/actions/runs/123",
                           "status": "completed", "conclusion": "success"})
        with self.assertRaisesRegex(s.watch.WatchError, "identity/workflow/controller SHA"):
            s.pytest_status(api, P)

    def test_run_ledger_missing_commit_metadata_blocks(self):
        api = ReadAPI(claimed=True, ledger=[{"ref": "refs/tags/" + s.watch.claim_name(P) + "-run-123"}])
        with self.assertRaisesRegex(s.watch.WatchError, "valid controller commit"):
            s.pytest_status(api, P)

    def test_success_without_artifact_is_not_verified(self):
        api = ReadAPI(claimed=True,
                      ledger=[{"ref": "refs/tags/" + s.watch.claim_name(P) + "-run-123",
                               "object": {"type": "commit", "sha": C}}],
                      run={"id": 123, "event": "workflow_dispatch", "head_sha": C,
                           "path": ".github/workflows/romarr-pytest.yml",
                           "html_url": "https://github.com/" + s.watch.CONTROLLER + "/actions/runs/123",
                           "status": "completed", "conclusion": "success"})
        self.assertEqual(s.pytest_status(api, P)["status"], "WORKFLOW_SUCCESS_ARTIFACT_UNVERIFIED")

    def test_duplicate_run_tags_fail_closed(self):
        prefix = "refs/tags/" + s.watch.claim_name(P) + "-run-"
        x = ReadAPI(claimed=True, ledger=[{"ref": prefix + "123"},
                                          {"ref": prefix + "124"}])
        self.assertEqual(s.pytest_status(x, P)["status"], "CLAIM_WITHOUT_UNIQUE_RUN")

    def test_running_job_not_pass(self):
        api = ReadAPI(claimed=True,
                      ledger=[{"ref": "refs/tags/" + s.watch.claim_name(P) + "-run-123",
                               "object": {"type": "commit", "sha": C}}],
                      run={"id": 123, "event": "workflow_dispatch", "head_sha": C,
                           "path": ".github/workflows/romarr-pytest.yml",
                           "html_url": "https://github.com/" + s.watch.CONTROLLER + "/actions/runs/123",
                           "status": "in_progress"})
        self.assertEqual(s.pytest_status(api, P)["status"], "IN_PROGRESS")


class GraphQL(unittest.TestCase):
    def test_auth_required(self):
        with self.assertRaisesRegex(s.watch.WatchError, "authentication"):
            s.graphql_threads(21, H, "")

    def test_read_only_query_resolved(self):
        def opener(request, timeout):
            self.assertEqual(request.get_method(), "POST")
            self.assertEqual(request.full_url, "https://api.github.com/graphql")
            body = json.loads(request.data.decode())
            self.assertTrue(body["query"].lstrip().startswith("query("))
            self.assertNotIn("mutation", body["query"])
            self.assertEqual(body["variables"]["number"], 21)
            response = {"data": {"repository": {"pullRequest": {
                "headRefOid": H, "reviewThreads": {
                    "pageInfo": {"hasNextPage": False, "endCursor": None},
                    "nodes": [{"isResolved": True, "isOutdated": False, "path": "romarr/ui.py"}]
                }}}}}
            return Mock(status=200, __enter__=lambda x: x, __exit__=lambda *args: None,
                        read=lambda: json.dumps(response).encode())
        result = s.graphql_threads(21, H, "dummy", opener=opener)
        self.assertEqual(result, {"state": "VERIFIED", "total": 1, "unresolved": 0})

    def test_graphql_errors_fail_closed(self):
        response = {"errors": [{"message": "not authorized"}]}
        def opener(request, timeout):
            class Fake:
                status = 200
                def __enter__(self):
                    return self
                def __exit__(self, *args):
                    return None
                def read(self):
                    return json.dumps(response).encode()
            return Fake()
        with self.assertRaises(s.watch.WatchError):
            s.graphql_threads(21, H, "dummy", opener=opener)


if __name__ == "__main__":
    unittest.main()
