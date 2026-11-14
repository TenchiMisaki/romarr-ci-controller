"""Keep GitHub Actions logs unambiguous while retaining all real safety gates."""
from pathlib import Path
from tempfile import TemporaryDirectory
import os
import shutil
import subprocess
import unittest

ROOT = Path(__file__).resolve().parents[1]
WORKFLOW = ROOT / ".github" / "workflows" / "romarr-pytest.yml"
PREPARE = ROOT / "controller" / "scripts" / "prepare_archive_tools.sh"
VERIFY = ROOT / "controller" / "scripts" / "verify_archive_tools.sh"

class ArchiveLogClarity(unittest.TestCase):
    def test_workflow_runs_files_without_echoing_guards(self):
        content = WORKFLOW.read_text(encoding="utf-8")
        self.assertIn("run: bash controller/controller/scripts/prepare_archive_tools.sh", content)
        self.assertIn("working-directory: romarr\n        run: bash ../controller/controller/scripts/verify_archive_tools.sh", content)
        self.assertNotIn("FAIL:", content)
        self.assertIn("run: python controller/controller/evidence.py gate", content)

    def test_workflow_checkout_layout_is_explicit(self):
        content = WORKFLOW.read_text(encoding="utf-8")
        self.assertEqual(content.count("path: controller"), 1)
        self.assertIn("working-directory: romarr", content)
        self.assertIn("run: bash controller/controller/scripts/prepare_archive_tools.sh", content)
        self.assertIn("run: bash ../controller/controller/scripts/verify_archive_tools.sh", content)

    def test_prepare_script_resolves_from_real_actions_workspace(self):
        # A real checkout with path: controller installs repository files inside
        # <workspace>/controller, so source-relative scripts add another controller/.
        with TemporaryDirectory() as temp:
            workspace = Path(temp)
            destination = workspace / "controller" / "controller" / "scripts"
            destination.mkdir(parents=True)
            shutil.copy2(PREPARE, destination / PREPARE.name)
            env = dict(os.environ, GITHUB_REPOSITORY="wrong/unapproved",
                       GITHUB_ACTIONS="true", RUNNER_OS="Linux")
            p = subprocess.run(
                ["bash", "controller/controller/scripts/prepare_archive_tools.sh"],
                cwd=workspace, env=env, capture_output=True, text=True)
            self.assertNotEqual(p.returncode, 0)
            self.assertIn("FAIL: unexpected runner identity", p.stderr)
            self.assertNotIn("No such file or directory", p.stderr)
            self.assertIn("================ DIAGNOSTIC FINISH ================", p.stdout)

    def test_verify_script_resolves_from_real_actions_workspace(self):
        with TemporaryDirectory() as temp:
            workspace = Path(temp)
            destination = workspace / "controller" / "controller" / "scripts"
            destination.mkdir(parents=True)
            shutil.copy2(VERIFY, destination / VERIFY.name)
            pkg = workspace / "romarr" / "romarr"
            pkg.mkdir(parents=True)
            (pkg / "__init__.py").write_text("", encoding="utf-8")
            (pkg / "library.py").write_text(
                "from types import SimpleNamespace\n"
                "def bsdtar_path(): return 'found'\n"
                "def rar_tool(): return SimpleNamespace(kind='7z')\n",
                encoding="utf-8")
            p = subprocess.run(
                ["bash", "../controller/controller/scripts/verify_archive_tools.sh"],
                cwd=workspace / "romarr", capture_output=True, text=True)
            self.assertEqual(p.returncode, 0, p.stderr)
            self.assertIn("ROMarr archive tool detection PASS", p.stdout)
            self.assertNotIn("FAIL:", p.stdout + p.stderr)

    def test_all_six_rejection_messages_still_exist(self):
        first = PREPARE.read_text(encoding="utf-8")
        second = VERIFY.read_text(encoding="utf-8")
        self.assertEqual(first.count("FAIL:"), 4)
        self.assertEqual(second.count("FAIL:"), 2)
        for phrase in ("unexpected runner identity", "unsupported OS", "sudo unavailable", "remains unavailable"):
            self.assertIn(phrase, first)
        for phrase in ("did not recognize libarchive bsdtar", "did not recognize a split-RAR reader"):
            self.assertIn(phrase, second)
        self.assertIn("set -euo pipefail", first)
        self.assertIn("set -euo pipefail", second)
        self.assertIn("trap finish EXIT", first)

    def test_scripts_have_valid_bash_syntax(self):
        for script in (PREPARE, VERIFY):
            with self.subTest(script=script.name):
                p = subprocess.run(["bash", "-n", str(script)], capture_output=True, text=True)
                self.assertEqual(p.returncode, 0, p.stderr)

    def test_runner_identity_gate_rejects_unapproved_target(self):
        env = dict(os.environ, GITHUB_REPOSITORY="wrong/unapproved", GITHUB_ACTIONS="true", RUNNER_OS="Linux")
        p = subprocess.run(["bash", str(PREPARE)], capture_output=True, text=True, env=env)
        self.assertNotEqual(p.returncode, 0)
        self.assertIn("FAIL: unexpected runner identity", p.stderr)
        self.assertIn("================ PREFLIGHT CHECK ================", p.stdout)
        self.assertIn("================ DIAGNOSTIC FINISH ================", p.stdout)
        self.assertNotIn("apt-get", p.stdout+p.stderr)

    def verify_with_stub(self, *, bsdtar=True, rar=True):
        with TemporaryDirectory() as temp:
            root = Path(temp)
            pkg = root / "romarr"
            pkg.mkdir()
            (pkg / "__init__.py").write_text("", encoding="utf-8")
            bsdtar_code = "'found'" if bsdtar else "None"
            rar_code = "SimpleNamespace(kind='7z')" if rar else "None"
            (pkg / "library.py").write_text(
                "from types import SimpleNamespace\n"
                "def bsdtar_path(): return " + bsdtar_code + "\n"
                "def rar_tool(): return " + rar_code + "\n", encoding="utf-8")
            return subprocess.run(["bash", str(VERIFY)], cwd=root, capture_output=True, text=True)

    def test_missing_bsdtar_still_rejects(self):
        p = self.verify_with_stub(bsdtar=False)
        self.assertNotEqual(p.returncode, 0)
        self.assertIn("FAIL: ROMarr did not recognize libarchive bsdtar", p.stderr)

    def test_missing_rar_reader_still_rejects(self):
        p = self.verify_with_stub(rar=False)
        self.assertNotEqual(p.returncode, 0)
        self.assertIn("FAIL: ROMarr did not recognize a split-RAR reader", p.stderr)

    def test_present_tools_still_pass(self):
        p = self.verify_with_stub()
        self.assertEqual(p.returncode, 0, p.stderr)
        self.assertIn("ROMarr archive tool detection PASS", p.stdout)

if __name__ == "__main__":
    unittest.main()
