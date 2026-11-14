"""Stage 2 discovery, identity, collision, dispatch, and failure-path tests."""
import importlib.util
from pathlib import Path
import unittest
from unittest.mock import patch
from urllib.error import HTTPError, URLError

MODULE = Path(__file__).resolve().parents[1] / "controller" / "watch.py"
spec = importlib.util.spec_from_file_location("romarr_watch", MODULE)
w = importlib.util.module_from_spec(spec)
spec.loader.exec_module(w)
H = "a" * 40
B = "b" * 40
C = "c" * 40


def pr(number=25, head=H, base=B, title="feat: add feature", ref="feature/update", draft=False):
    return {"number": number, "state": "open", "draft": draft, "title": title,
            "head": {"sha": head, "ref": ref, "repo": {"full_name": w.SOURCE}},
            "base": {"sha": base, "ref": "main", "repo": {"full_name": w.SOURCE}}}


class Stub:
    def __init__(self, p=None, prior=False, dispatch=None, fail=None):
        self.p = p or pr()
        self.prior = prior
        self.dispatch = dispatch or {"workflow_run_id": 123,
                                     "html_url": "https://github.com/TenchiMisaki/romarr-ci-controller/actions/runs/123"}
        self.fail = fail
        self.calls = []

    def request(self, method, path, body=None, allow_missing=False):
        self.calls.append((method, path, body))
        if self.fail and (method, path.split("?")[0]) == self.fail:
            raise w.WatchError("synthetic failure")
        if path.endswith("/pulls?state=open&per_page=100&page=1"):
            return [self.p]
        if path.endswith("/pulls?state=open&per_page=100&page=2"):
            return []
        if path == f"repos/{w.SOURCE}/pulls/{self.p['number']}":
            return self.p
        if path == f"repos/{w.CONTROLLER}/git/ref/heads/main":
            return {"ref": "refs/heads/main", "object": {"sha": C}}
        if "/git/ref/tags/" in path:
            if not self.prior:
                return None
            return {"ref": "refs/tags/" + path.split("/tags/")[1],
                    "object": {"type": "commit", "sha": C}}
        if path.endswith("/git/refs"):
            return {"ref": body["ref"]}
        if path.endswith("/dispatches"):
            return self.dispatch
        raise AssertionError(f"Unexpected API call: {method} {path}")


class Discovery(unittest.TestCase):
    def test_eligible(self):
        result, reason = w.classify(pr())
        self.assertEqual((result["number"], result["sha"], reason), (25, H, "eligible"))

    def test_skip_draft_and_backlog_and_review(self):
        for p in (pr(draft=True), pr(title="Backlog: roadmap"),
                  pr(ref="review/patch"), pr(ref="notes/roadmap"), pr(title="Review: patch")):
            with self.subTest(title=p["title"], ref=p["head"]["ref"]):
                self.assertIsNone(w.classify(p)[0])

    def test_skip_other_repo(self):
        p = pr()
        p["head"]["repo"]["full_name"] = "other/repo"
        self.assertEqual(w.classify(p)[1], "unapproved_repository")

    def test_bad_head_sha_blocks(self):
        with self.assertRaises(w.WatchError):
            w.classify(pr(head="deadbeef"))

    def test_bool_pr_number_blocks(self):
        with self.assertRaises(w.WatchError):
            w.classify(pr(number=True))

    def test_wrong_repo_type_is_skipped(self):
        p = pr()
        p["head"]["repo"] = "untrusted"
        self.assertEqual(w.classify(p)[1], "unapproved_repository")

    def test_live_pr_shape_classification(self):
        # The PR numbers and statuses were independently observed November 14.
        records = [pr(number=21, title="feat(ui): polish update page layout and build information"),
                   pr(number=25, title="feat(update): check for newer Nightly builds and make Git updates safer (Part 5A)"),
                   pr(number=26, ref="review/pr188-ssh-remote-aliases-20261114"),
                   pr(number=6, title="Backlog: ROMarr System Update", draft=True)]
        states = [(p["number"], w.classify(p)[1]) for p in records]
        self.assertEqual(states, [(21, "eligible"), (25, "eligible"),
                                  (26, "backlog_or_review"), (6, "draft_or_unknown")])

    def test_missing_base_blocks(self):
        p = pr()
        p["base"] = None
        with self.assertRaises(w.WatchError):
            w.classify(p)

    def test_pagination_and_sorted(self):
        s = Stub()
        eligible, other = w.discover(s)
        self.assertEqual(len(eligible), 1)
        self.assertEqual(other, [])

    def test_claim_dedup_key(self):
        self.assertEqual(w.claim_name(w.classify(pr())[0]), "romarr-ci-v1/pr-25-" + H)

    def test_changed_head_fails_freshness(self):
        s = Stub(p=pr(head=B))
        with self.assertRaisesRegex(w.WatchError, "changed"):
            w.verify_fresh(s, w.classify(pr())[0])

    def test_changed_base_fails_freshness(self):
        s = Stub(p=pr(base=C))
        with self.assertRaisesRegex(w.WatchError, "changed"):
            w.verify_fresh(s, w.classify(pr())[0])


class Dispatch(unittest.TestCase):
    def setUp(self):
        self.c = w.classify(pr())[0]
        self.env = {"GITHUB_REPOSITORY": w.CONTROLLER, "GITHUB_ACTIONS": "true",
                    "RUNNER_OS": "Linux", "ROMARR_WATCH_DISPATCH": "YES", "GITHUB_SHA": C}

    def test_wrong_target_blocks(self):
        env = dict(self.env, GITHUB_REPOSITORY="BlizzHacker/romarr")
        with self.assertRaises(w.WatchError):
            w.verify_controller(Stub(), env)

    def test_missing_explicit_flag_blocks(self):
        env = {k: v for k, v in self.env.items() if k != "ROMARR_WATCH_DISPATCH"}
        with self.assertRaises(w.WatchError):
            w.verify_controller(Stub(), env)

    def test_main_moved_blocks(self):
        env = dict(self.env, GITHUB_SHA=H)
        with self.assertRaises(w.WatchError):
            w.verify_controller(Stub(), env)

    def test_success(self):
        s = Stub()
        o = w.dispatch_one(s, self.c, C)
        self.assertEqual((o["status"], o["run_url"].split("/")[-1]), ("DISPATCHED", "123"))
        self.assertEqual([x[0] for x in s.calls].count("POST"), 3)  # tag, dispatch, run tag
        posts = [x for x in s.calls if x[0] == "POST"]
        self.assertEqual(posts[1][2]["inputs"]["expected_sha"], H)
        self.assertTrue(posts[1][2]["return_run_details"])

    def test_prior_claim_skips(self):
        s = Stub(prior=True)
        result = w.dispatch_one(s, self.c, C)
        self.assertEqual(result["status"], "ALREADY_CLAIMED")
        self.assertFalse(any(x[0] == "POST" for x in s.calls))

    def test_claim_write_error_does_not_dispatch(self):
        s = Stub(fail=("POST", f"repos/{w.CONTROLLER}/git/refs"))
        with self.assertRaises(w.WatchError):
            w.dispatch_one(s, self.c, C)
        self.assertFalse(any(x[1].endswith("/dispatches") for x in s.calls))

    def test_dispatch_write_error_never_retries(self):
        s = Stub(fail=("POST", f"repos/{w.CONTROLLER}/actions/workflows/{w.WORKFLOW}/dispatches"))
        with self.assertRaises(w.WatchError):
            w.dispatch_one(s, self.c, C)
        self.assertEqual(sum(x[1].endswith("/dispatches") for x in s.calls), 1)

    def test_missing_run_id_blocks(self):
        s = Stub(dispatch={"status": 204})
        with self.assertRaisesRegex(w.WatchError, "run ID"):
            w.dispatch_one(s, self.c, C)

    def test_mismatch_run_url_blocks(self):
        s = Stub(dispatch={"workflow_run_id": 123, "html_url": "https://other.example/123"})
        with self.assertRaisesRegex(w.WatchError, "mismatch"):
            w.dispatch_one(s, self.c, C)

    def test_read_only_audit_has_no_mutations(self):
        s = Stub()
        result = w.run("audit", s, {})
        self.assertEqual(result["results"][0]["status"], "UNCLAIMED")
        self.assertFalse(any(x[0] == "POST" for x in s.calls))

    def test_wrong_command_fails(self):
        with self.assertRaises(w.WatchError):
            w.run("delete", Stub(), {})


class Transport(unittest.TestCase):
    def test_api_disallows_other_repo(self):
        with self.assertRaises(w.WatchError):
            w.API().request("GET", "repos/other/target/pulls")

    def test_api_requires_token_for_write(self):
        with self.assertRaises(w.WatchError):
            w.API().request("POST", f"repos/{w.CONTROLLER}/git/refs", {})

    def test_no_retry_for_post(self):
        def fail(req, timeout):
            raise URLError("synthetic")
        with self.assertRaisesRegex(w.WatchError, "transport"):
            w.API("dummy-token", opener=fail).request("POST", f"repos/{w.CONTROLLER}/git/refs", {})


if __name__ == "__main__":
    unittest.main()
