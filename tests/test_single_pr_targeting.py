"""Stage 2C: fail-closed exact single-PR selection and unrelated-PR isolation."""
import unittest

from test_watch import Stub, pr, H, B, C, w


def selected(pr_record=None):
    """Build an exact selector for one synthetic eligible fork PR."""
    record = pr_record or pr()
    return {
        "GITHUB_REPOSITORY": w.CONTROLLER,
        "GITHUB_ACTIONS": "true",
        "RUNNER_OS": "Linux",
        "ROMARR_WATCH_DISPATCH": "YES",
        "GITHUB_SHA": C,
        "ROMARR_SELECTED_PR": str(record["number"]),
        "ROMARR_SELECTED_HEAD_SHA": record["head"]["sha"],
        "ROMARR_SELECTED_BASE_SHA": record["base"]["sha"],
    }


class IsolatedApi(Stub):
    """Reject broad discovery or unrelated-PR lookups in mutating mode."""

    def request(self, method, path, body=None, allow_missing=False):
        if "/pulls?state=" in path:
            raise AssertionError("Dispatch attempted broad PR discovery")
        if path.startswith(f"repos/{w.SOURCE}/pulls/") and path != f"repos/{w.SOURCE}/pulls/{self.p['number']}":
            raise AssertionError("Dispatch inspected an unrelated PR")
        return super().request(method, path, body, allow_missing)


class DriftingApi(IsolatedApi):
    """Change the chosen PR after selector verification, before the claim."""

    def __init__(self, *, drift_head=False, drift_base=False):
        super().__init__()
        self.lookups = 0
        self.drift_head = drift_head
        self.drift_base = drift_base

    def request(self, method, path, body=None, allow_missing=False):
        expected = f"repos/{w.SOURCE}/pulls/{self.p['number']}"
        if method == "GET" and path == expected:
            self.lookups += 1
            if self.lookups >= 2:
                self.calls.append((method, path, body))
                return pr(head=C if self.drift_head else H,
                          base=C if self.drift_base else B)
        return super().request(method, path, body, allow_missing)


class SinglePRTargeting(unittest.TestCase):
    """Explicit selection is mandatory before privileged claim/tag writes."""

    def test_missing_pr_number_blocks_without_claim_write(self):
        api, env = IsolatedApi(), selected()
        env.pop("ROMARR_SELECTED_PR")
        with self.assertRaisesRegex(w.WatchError, "explicit valid PR number"):
            w.run("dispatch", api, env)
        self.assertFalse(any(method == "POST" for method, _, _ in api.calls))

    def test_multiple_pr_numbers_block_before_api_calls(self):
        api, env = IsolatedApi(), selected()
        env["ROMARR_SELECTED_PR"] = "21,25"
        with self.assertRaisesRegex(w.WatchError, "explicit valid PR number"):
            w.run("dispatch", api, env)
        self.assertTrue(all(method == "GET" and path == f"repos/{w.CONTROLLER}/git/ref/heads/main"
                            for method, path, _ in api.calls))

    def test_missing_exact_head_blocks_before_api_calls(self):
        api, env = IsolatedApi(), selected()
        env["ROMARR_SELECTED_HEAD_SHA"] = ""
        with self.assertRaisesRegex(w.WatchError, "Selected PR head SHA"):
            w.run("dispatch", api, env)
        self.assertFalse(any("git/ref/tags" in path for _, path, _ in api.calls))

    def test_invalid_exact_base_blocks_before_api_calls(self):
        api, env = IsolatedApi(), selected()
        env["ROMARR_SELECTED_BASE_SHA"] = "abc"
        with self.assertRaisesRegex(w.WatchError, "Selected PR base SHA"):
            w.run("dispatch", api, env)
        self.assertFalse(any("git/ref/tags" in path for _, path, _ in api.calls))

    def test_head_mismatch_fails_closed(self):
        api, env = IsolatedApi(), selected()
        env["ROMARR_SELECTED_HEAD_SHA"] = C
        with self.assertRaisesRegex(w.WatchError, "does not match"):
            w.run("dispatch", api, env)
        self.assertFalse(any(method == "POST" for method, _, _ in api.calls))

    def test_base_mismatch_fails_closed(self):
        api, env = IsolatedApi(), selected()
        env["ROMARR_SELECTED_BASE_SHA"] = C
        with self.assertRaisesRegex(w.WatchError, "does not match"):
            w.run("dispatch", api, env)
        self.assertFalse(any(method == "POST" for method, _, _ in api.calls))

    def test_draft_is_ineligible(self):
        record = pr(draft=True)
        api = IsolatedApi(p=record)
        with self.assertRaisesRegex(w.WatchError, "not eligible"):
            w.run("dispatch", api, selected(record))
        self.assertFalse(any(method == "POST" for method, _, _ in api.calls))

    def test_review_branch_is_ineligible(self):
        record = pr(ref="review/maintainer-fix")
        api = IsolatedApi(p=record)
        with self.assertRaisesRegex(w.WatchError, "not eligible"):
            w.run("dispatch", api, selected(record))
        self.assertFalse(any(method == "POST" for method, _, _ in api.calls))

    def test_one_pr_dispatch_ignores_other_eligible_prs(self):
        # PRs #21 and #26 may coexist with #25. Dispatch must not even list
        # them, let alone claim tags or submit tests for their revisions.
        record = pr(number=25)
        api = IsolatedApi(p=record)
        result = w.run("dispatch", api, selected(record))
        self.assertEqual(len(result["eligible"]), 1)
        self.assertEqual(result["eligible"][0]["number"], 25)
        self.assertEqual(result["results"][0]["status"], "DISPATCHED")
        posts = [(path, payload) for method, path, payload in api.calls if method == "POST"]
        self.assertEqual(len(posts), 3)
        self.assertEqual(sum(path.endswith("/dispatches") for path, _ in posts), 1)
        self.assertEqual(posts[1][1]["inputs"]["pr_number"], "25")
        self.assertEqual(posts[1][1]["inputs"]["expected_sha"], H)
        self.assertEqual(posts[1][1]["inputs"]["expected_base_sha"], B)
        self.assertTrue(all("pr-21-" not in str(payload) and "pr-26-" not in str(payload)
                            for _, payload in posts))

    def test_selected_existing_v2_claim_does_not_dispatch(self):
        api = IsolatedApi(prior=True)
        result = w.run("dispatch", api, selected())
        self.assertEqual(result["results"][0]["status"], "ALREADY_CLAIMED")
        self.assertFalse(any(method == "POST" for method, _, _ in api.calls))

    def test_selected_attested_v1_claim_does_not_duplicate(self):
        record = pr(number=21, head="74196f657d0e98928d495ce54c7a8b219ff49f3a",
                    base="d0164a9e0c322cb70422dccd9a2f96a78bb41c49")
        api = IsolatedApi(p=record, legacy_only=True)
        result = w.run("dispatch", api, selected(record))
        self.assertEqual(result["results"][0]["status"], "LEGACY_BASE_ATTESTED")
        self.assertFalse(any(method == "POST" for method, _, _ in api.calls))

    def test_existing_v1_claim_changed_base_needs_new_v2_dispatch(self):
        record = pr(number=21, head="74196f657d0e98928d495ce54c7a8b219ff49f3a",
                    base="d" * 40)
        api = IsolatedApi(p=record, legacy_only=True)
        result = w.run("dispatch", api, selected(record))
        self.assertEqual(result["results"][0]["status"], "DISPATCHED")
        posts = [(path, payload) for method, path, payload in api.calls if method == "POST"]
        self.assertEqual(len(posts), 3)
        self.assertIn("-b-" + "d" * 40, posts[0][1]["ref"])
        self.assertEqual(posts[1][1]["inputs"]["expected_base_sha"], "d" * 40)

    def test_unknown_legacy_claim_never_replays(self):
        api = IsolatedApi(legacy_only=True)
        result = w.run("dispatch", api, selected())
        self.assertEqual(result["results"][0]["status"], "LEGACY_CLAIM_RECONCILE")
        self.assertFalse(any(method == "POST" for method, _, _ in api.calls))

    def test_head_changes_after_selection_no_mutation(self):
        api = DriftingApi(drift_head=True)
        with self.assertRaisesRegex(w.WatchError, "operations blocked"):
            w.run("dispatch", api, selected())
        self.assertEqual(api.lookups, 2)
        self.assertFalse(any(method == "POST" for method, _, _ in api.calls))

    def test_base_changes_after_selection_no_mutation(self):
        api = DriftingApi(drift_base=True)
        with self.assertRaisesRegex(w.WatchError, "operations blocked"):
            w.run("dispatch", api, selected())
        self.assertEqual(api.lookups, 2)
        self.assertFalse(any(method == "POST" for method, _, _ in api.calls))

    def test_claim_write_failure_does_not_dispatch_or_repeat(self):
        api = IsolatedApi(fail=("POST", f"repos/{w.CONTROLLER}/git/refs"))
        with self.assertRaisesRegex(w.WatchError, "operations blocked"):
            w.run("dispatch", api, selected())
        self.assertEqual(sum(path.endswith("/git/refs") and method == "POST"
                             for method, path, _ in api.calls), 1)
        self.assertFalse(any(path.endswith("/dispatches") for _, path, _ in api.calls))


if __name__ == "__main__":
    unittest.main()
