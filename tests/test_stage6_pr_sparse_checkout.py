"""Exercise the source sanitizer with only the workflow's declared files."""
import json
from pathlib import Path, PurePosixPath
import shutil
import subprocess
import sys
import tempfile
import unittest


ROOT = Path(__file__).resolve().parents[1]
WORKFLOW = ROOT / '.github/workflows/stage6-pr-manual-candidate.yml'
PROGRAM = '''
import json
import sys
sys.path.insert(0, sys.argv[1])
from stage6_pr_source_v42 import sanitize_junit
xml = b'<testsuite tests="1" failures="0" errors="0" skipped="0"><testcase /></testsuite>'
advisory, manifest = sanitize_junit(xml, run_id=123, head_sha='a' * 40,
                                  base_sha='b' * 40, pytest_exit=0)
print(json.dumps({'advisory': json.loads(advisory), 'manifest': json.loads(manifest)}))
'''


def source_checkout_paths():
    source = WORKFLOW.read_text(encoding='utf-8').split('\n  isolated_reviewer:', 1)[0]
    lines = source.splitlines()
    start = next(i for i, line in enumerate(lines) if line.strip() == 'sparse-checkout: |')
    indent = len(lines[start]) - len(lines[start].lstrip())
    paths = []
    for line in lines[start + 1:]:
        if not line.strip():
            continue
        if len(line) - len(line.lstrip()) <= indent:
            break
        path = PurePosixPath(line.strip())
        if path.is_absolute() or '..' in path.parts or path.parts[0] != 'controller':
            raise ValueError('Unsafe sparse checkout test input')
        paths.append(path)
    return paths


def run_sparse_sanitizer(paths):
    with tempfile.TemporaryDirectory(prefix='stage6-sparse-test-') as temporary:
        root = Path(temporary)
        for path in paths:
            target = root / path
            target.parent.mkdir(parents=True, exist_ok=True)
            shutil.copyfile(ROOT / path, target)
        return subprocess.run(
            [sys.executable, '-I', '-B', '-c', PROGRAM, str(root / 'controller')],
            cwd=root, capture_output=True, text=True, timeout=15,
        )


class SourceSparseCheckout(unittest.TestCase):
    def test_workflow_file_set_can_produce_sanitized_advisory(self):
        result = run_sparse_sanitizer(source_checkout_paths())
        self.assertEqual(result.returncode, 0, result.stderr)
        output = json.loads(result.stdout)
        self.assertEqual(output['advisory']['passing_cases'], 1)
        self.assertFalse(output['advisory']['test_accepted'])
        self.assertFalse(output['advisory']['publication_authorized'])
        self.assertFalse(output['advisory']['unattended_dispatch_enabled'])
        self.assertEqual(set(output['manifest']['files']), {'advisory.json'})

    def test_previous_missing_transitive_module_is_detected(self):
        paths = [path for path in source_checkout_paths()
                 if path.name != 'stage6_pr_identity_v32.py']
        result = run_sparse_sanitizer(paths)
        self.assertNotEqual(result.returncode, 0)
        self.assertIn('ModuleNotFoundError', result.stderr)
        self.assertIn('stage6_pr_identity_v32', result.stderr)
