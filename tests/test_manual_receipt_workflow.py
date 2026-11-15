"""Prevent manual receipt verification from gaining test/dispatch/write authority.

These narrow source checks supplement, not replace, GitHub-hosted runtime proof.
"""
from pathlib import Path
import re
import unittest

WORKFLOW = (Path(__file__).resolve().parents[1] / ".github" / "workflows"
            / "romarr-receipt-manual.yml")

CHECKOUT = "fbc6f3992d24b796d5a048ff273f7fcc4a7b6c09"
SETUP_PYTHON = "ece7cb06caefa5fff74198d8649806c4678c61a1"


def validate(text):
    """Check literal security-critical workflow structure without executing YAML."""
    def require(condition, label):
        if not condition:
            raise ValueError(label)

    require(text.count("\non:\n") == 1, "one explicit event map")
    require(re.search(r"(?m)^  workflow_dispatch:\s*$", text) is not None,
            "manual trigger")
    for forbidden_event in ("schedule", "push", "pull_request", "workflow_call", "repository_dispatch"):
        require(re.search(rf"(?m)^  {forbidden_event}:\s*$", text) is None,
                "unexpected trigger")
    require(text.count("permissions:\n  contents: read\n  actions: read") == 1,
            "global least-privilege permission")
    require(text.count("    permissions:\n      contents: read\n      actions: read") == 1,
            "job least-privilege permission")
    require(not re.search(r"(?m)^\s+(?:actions|contents|checks|deployments|issues|pull-requests): write\s*$", text),
            "write permission")
    require("runs-on: ubuntu-24.04" in text and "timeout-minutes: 10" in text,
            "bounded expected runner")
    require(text.count("      - name: Checkout controller sources") == 1,
            "one checkout step")
    jobs = text.split("\njobs:\n", 1)
    require(len(jobs) == 2, "one jobs block")
    headers = re.findall(r"(?m)^  ([a-z][a-z0-9_-]*):\s*$", jobs[1])
    require(headers == ["verify"], "exactly one read-only job")
    uses = re.findall(r"(?m)^\s+uses: ([^\n]+)$", text)
    require(uses == [f"actions/checkout@{CHECKOUT} # v5",
                     f"actions/setup-python@{SETUP_PYTHON} # v6"],
            "only reviewed pinned actions")
    runs = re.findall(r"(?m)^\s+run: ([^\n]+)$", text)
    require(runs == ["python controller/receipt_collector.py"],
            "only reviewed existing read-only collector command")
    require(f"uses: actions/checkout@{CHECKOUT}" in text,
            "pinned checkout")
    require(f"uses: actions/setup-python@{SETUP_PYTHON}" in text,
            "pinned Python setup")
    require("persist-credentials: false" in text,
            "non-persisted checkout auth")
    require("GIT_CONFIG_COUNT: '1'" in text and
            "GIT_CONFIG_KEY_0: init.defaultBranch" in text and
            "GIT_CONFIG_VALUE_0: main" in text,
            "clean git initialization")
    require(text.count("run: python controller/receipt_collector.py") == 1,
            "run reviewed GET-only collector exactly once")
    require("GH_TOKEN: \${{ github.token }}" in text,
            "job-scoped token")
    for input_name, env_name in (("pr_number", "PR"), ("head_sha", "HEAD_SHA"),
                                 ("base_sha", "BASE_SHA")):
        require(f"ROMARR_SELECTED_{env_name}: \${{{{ inputs.{input_name} }}}}" in text,
                "pinned selection via environment")
        require(re.search(rf"(?m)^      {input_name}:\s*$", text) is not None,
                "required workflow input")
    require(text.count("required: true") == 3,
            "all three selection inputs required")
    require("python-version: '3.13'" in text, "known Python major/minor")
    for unsafe in ("watch.py dispatch", "ROMARR_WATCH_DISPATCH", "contents: write",
                   "actions: write", "continue-on-error", "upload-artifact@",
                   "gh api", "gh workflow run", "git push", "workflow_dispatch:" + "\n  schedule"):
        require(unsafe not in text, "unaccepted operation or success masking")
    require(not re.search(r"(?m)^\s+run:.*\$\{\{", text),
            "untrusted expressions must never be placed in shell code")
    return True


class ManualReceiptWorkflow(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.source = WORKFLOW.read_text(encoding="utf-8")

    def test_manual_read_only_pilot(self):
        self.assertTrue(validate(self.source))

    def test_reject_schedule_trigger(self):
        with self.assertRaisesRegex(ValueError, "unexpected trigger"):
            validate(self.source.replace("  workflow_dispatch:",
                                         "  schedule:\n    - cron: '* * * * *'\n  workflow_dispatch:"))

    def test_reject_write_scope(self):
        with self.assertRaisesRegex(ValueError, "least-privilege"):
            validate(self.source.replace("  actions: read", "  actions: write", 1))

    def test_reject_removed_artifact_permission(self):
        with self.assertRaisesRegex(ValueError, "least-privilege"):
            validate(self.source.replace("  actions: read\n", "", 1))

    def test_reject_automatic_dispatch(self):
        with self.assertRaisesRegex(ValueError, "unaccepted operation"):
            validate(self.source + "\n# forbidden: python controller/watch.py dispatch\n")

    def test_reject_shell_input_interpolation(self):
        with self.assertRaisesRegex(ValueError, "only reviewed existing|untrusted expressions"):
            validate(self.source.replace("run: python controller/receipt_collector.py",
                                         "run: python controller/receipt_collector.py \${{ inputs.pr_number }}"))

    def test_reject_extra_action(self):
        with self.assertRaisesRegex(ValueError, "only reviewed pinned actions"):
            validate(self.source + "\n      - name: Added unreviewed action\n        uses: user/action@main\n")

    def test_reject_extra_run(self):
        with self.assertRaisesRegex(ValueError, "only reviewed existing"):
            validate(self.source + "\n      - name: Added command\n        run: echo unexpected\n")

    def test_reject_unpinned_checkout(self):
        with self.assertRaisesRegex(ValueError, "only reviewed pinned actions|pinned checkout"):
            validate(self.source.replace(CHECKOUT, "main"))

    def test_reject_credential_persistence(self):
        with self.assertRaisesRegex(ValueError, "non-persisted checkout"):
            validate(self.source.replace("persist-credentials: false",
                                         "persist-credentials: true"))


if __name__ == "__main__":
    unittest.main()
