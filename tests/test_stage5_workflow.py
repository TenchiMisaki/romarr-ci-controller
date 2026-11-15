"""Offline static safety checks for candidate monitor workflow (not hosted)."""
from pathlib import Path
import unittest

import yaml

ROOT = Path(__file__).resolve().parents[1]
PATH = ROOT / ".github" / "workflows" / "romarr-pr-monitor.yml"


class WorkflowSafety(unittest.TestCase):
    def setUp(self):
        self.source = PATH.read_text(encoding="utf-8")
        self.document = yaml.load(self.source, Loader=yaml.BaseLoader)

    def test_readonly_trigger_only(self):
        self.assertEqual(set(self.document["on"]), {"schedule", "workflow_dispatch"})
        self.assertEqual(self.document["on"]["schedule"], [{"cron": "2-59/5 * * * *"}])

    def test_action_permission_is_read_only_and_scoped(self):
        expected = {"contents": "read", "actions": "read"}
        self.assertEqual(self.document["permissions"], expected)
        self.assertEqual(self.document["jobs"]["inspect"]["permissions"], expected)
        self.assertNotIn("write", str(self.document["permissions"]))

    def test_unchanged_external_fallback_identity(self):
        self.assertEqual(self.document["concurrency"]["group"], "romarr-pr-monitor-readonly")
        self.assertEqual(self.document["concurrency"]["cancel-in-progress"], "false")
        self.assertEqual(self.document["jobs"]["inspect"]["timeout-minutes"], "10")

    def test_single_receipt_audit_before_render(self):
        steps = self.document["jobs"]["inspect"]["steps"]
        commands = [(i, x.get("run", "")) for i, x in enumerate(steps) if "run" in x]
        audits = [(i, c) for i, c in commands if "scheduled_receipt.py audit" in c]
        finalizers = [(i, c) for i, c in commands if "scheduled_receipt.py finalize" in c]
        self.assertEqual(len(audits), 1)
        self.assertEqual(len(finalizers), 1)
        self.assertLess(next(i for i, c in commands if "status.py audit" in c), audits[0][0])
        self.assertLess(audits[0][0], finalizers[0][0])
        self.assertEqual(steps[finalizers[0][0]]["if"], "${{ !cancelled() }}")
        self.assertEqual(steps[audits[0][0]]["env"], {"GH_TOKEN": "${{ github.token }}"})

    def test_no_privileged_commands_or_source_tests(self):
        commands = "\n".join(x.get("run", "") for x in self.document["jobs"]["inspect"]["steps"])
        for prohibited in ("pytest ", "dispatch_one", "claim_exists(", "git push", "git reset", "curl -X POST", "curl -X PATCH"):
            self.assertNotIn(prohibited, commands)

    def test_only_pinned_allowlisted_actions(self):
        steps = self.document["jobs"]["inspect"]["steps"]
        uses = [s["uses"] for s in steps if "uses" in s]
        self.assertEqual(uses, [
            "actions/checkout@fbc6f3992d24b796d5a048ff273f7fcc4a7b6c09",
            "actions/setup-python@ece7cb06caefa5fff74198d8649806c4678c61a1",
            "actions/upload-artifact@b7c566a772e6b6bfb58ed0dc250532a479d7789f",
        ])
        self.assertEqual(steps[0]["with"]["persist-credentials"], "false")

    def test_finalize_publish_and_upload_even_after_prior_failure(self):
        steps = self.document["jobs"]["inspect"]["steps"]
        finalize_idx = next(i for i, step in enumerate(steps)
                            if "scheduled_receipt.py finalize" in step.get("run", ""))
        for step in steps[finalize_idx:]:
            self.assertEqual(step.get("if"), "${{ !cancelled() }}")

    def test_only_sanitized_summary_public_artifact(self):
        upload = self.document["jobs"]["inspect"]["steps"][-1]
        self.assertEqual(upload["with"]["retention-days"], "7")
        self.assertEqual(upload["with"]["path"], "${{ runner.temp }}/romarr-monitor-summary.md")
        self.assertNotIn("romarr-status.json", upload["with"]["path"])
        self.assertNotIn("romarr-receipt.json", upload["with"]["path"])

    def test_static_yaml_parses_as_expected(self):
        self.assertEqual(self.document["jobs"]["inspect"]["runs-on"], "ubuntu-24.04")
        self.assertEqual(self.document["name"], "ROMarr PR and CodeRabbit read-only monitor")


if __name__ == "__main__":
    unittest.main()
