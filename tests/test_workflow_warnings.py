"""Guard controller workflow checkout and artifact runtime dependencies.

Static checks complement, not replace, live GitHub-hosted runner acceptance.
"""
from pathlib import Path
import re
import unittest


ROOT = Path(__file__).resolve().parents[1] / ".github" / "workflows"
WORKFLOWS = {
    "romarr-pr-watch.yml": 2,
    "romarr-pr-monitor.yml": 1,
    "controller-unit-tests.yml": 1,
    "romarr-pytest.yml": 3,
}
UPLOAD_SHA = "b7c566a772e6b6bfb58ed0dc250532a479d7789f"


class WorkflowWarnings(unittest.TestCase):
    def test_checkout_steps_pin_git_initial_branch(self):
        for name, expected in WORKFLOWS.items():
            source = (ROOT / name).read_text(encoding="utf-8")
            starts = list(re.finditer(
                r"(?m)^\s*uses: actions/checkout@[a-f0-9]{40} # v5$", source
            ))
            with self.subTest(workflow=name):
                self.assertEqual(len(starts), expected)
                for match in starts:
                    # Config must apply to the checkout action before its with: block.
                    following = source[match.end():match.end() + 190]
                    self.assertIn("env:\n", following)
                    self.assertIn("GIT_CONFIG_COUNT: '1'", following)
                    self.assertIn("GIT_CONFIG_KEY_0: init.defaultBranch", following)
                    self.assertIn("GIT_CONFIG_VALUE_0: main", following)

    def test_public_artifact_smoke_and_pytest_use_node24_action(self):
        for name in ("controller-unit-tests.yml", "romarr-pytest.yml"):
            source = (ROOT / name).read_text(encoding="utf-8")
            with self.subTest(workflow=name):
                self.assertIn("actions/upload-artifact@" + UPLOAD_SHA, source)
                self.assertNotIn("actions/upload-artifact@ea165f8d65b6e75b540449e92b4886f43607fa02", source)

    def test_existing_manual_test_and_dispatch_workflows_remain_unscheduled(self):
        for name in ("romarr-pr-watch.yml", "controller-unit-tests.yml", "romarr-pytest.yml"):
            source = (ROOT / name).read_text(encoding="utf-8")
            with self.subTest(workflow=name):
                self.assertNotRegex(source, r"(?m)^\s*schedule:\s*$")
                self.assertNotRegex(source, r"(?m)^\s*push:\s*$")


    def test_scheduled_monitor_is_read_only(self):
        source = (ROOT / "romarr-pr-monitor.yml").read_text(encoding="utf-8")
        self.assertIn("  schedule:", source)
        self.assertIn("cron: '17,47 * * * *'", source)
        self.assertIn("permissions:\\n  contents: read", source)
        self.assertIn("      contents: read", source)
        self.assertIn("python controller/watch.py audit", source)
        self.assertIn("python controller/status.py audit", source)
        self.assertIn("python controller/monitor_summary.py", source)
        self.assertNotIn("      actions: write", source)
        self.assertNotIn("      contents: write", source)
        self.assertNotIn("ROMARR_WATCH_DISPATCH", source)
        self.assertNotIn("python controller/watch.py dispatch", source)
        self.assertNotRegex(source, r"(?m)^\\s*push:\\s*$")


if __name__ == "__main__":
    unittest.main()
