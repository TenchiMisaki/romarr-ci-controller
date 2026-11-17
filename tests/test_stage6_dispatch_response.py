import unittest

from stage6_dispatch_response import dispatch_run_id, verify_dispatch_observation
from stage6_pr_identity_v32 import CONTROLLER_REPO, IdentityRejected


class DispatchResponseTests(unittest.TestCase):
    def setUp(self):
        path = f"{CONTROLLER_REPO}/actions/runs/123"
        self.body = dict(workflow_run_id=123, run_url=f"https://api.github.com/repos/{path}",
                         html_url=f"https://github.com/{path}")
        self.run = dict(id=123, run_attempt=1, repository=dict(full_name=CONTROLLER_REPO),
                        head_sha="a" * 40, event="workflow_dispatch", status="in_progress",
                        conclusion=None, path=".github/workflows/stage6-pr-manual-candidate.yml")

    def test_active_observation_is_advisory(self):
        result = verify_dispatch_observation(200, self.body, self.run, controller_sha="a" * 40)
        self.assertFalse(result.test_accepted)

    def test_missing_ambiguous_and_foreign_responses(self):
        for status, body in [(204, None), (502, self.body), (200, {}),
                             (200, dict(self.body, workflow_run_id=True)),
                             (200, dict(self.body, run_url=self.body["html_url"])),
                             (200, dict(self.body, html_url=self.body["html_url"] + "4"))]:
            with self.subTest(status=status, body=body), self.assertRaises(IdentityRejected):
                dispatch_run_id(status, body)

    def test_different_run_attempt_workflow_or_revision_blocks(self):
        for change in [dict(id=124), dict(run_attempt=2), dict(path="other.yml"),
                       dict(head_sha="b" * 40), dict(event="push")]:
            with self.subTest(change=change), self.assertRaises(IdentityRejected):
                verify_dispatch_observation(200, self.body, dict(self.run, **change),
                                            controller_sha="a" * 40)
