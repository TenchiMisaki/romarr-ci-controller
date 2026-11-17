"""Real local Git objects/refs; synthetic API semantics, never hosted acceptance."""
import base64
from concurrent.futures import ThreadPoolExecutor
import copy
import json
import os
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile
import threading
import unittest
from unittest.mock import patch

from controller_cycle import Controller, initial_state
from durable_state import GitHubState, PREFIX, STATE_REF, StateBlocked, encode
from stage6_pr_identity_v32 import ExactPR
from test_controller_cycle import Ports


class LocalGitAPI:
    """Disposable real Git storage behind a narrowly modeled REST boundary.

    This fixture is not an authenticated GitHub server. The modeled non-force
    endpoint checks ancestry and then uses Git's expected-old-object transaction.
    An idempotent update to the existing target succeeds, as required to expose
    duplicate fences when two callers produce identical commit objects.
    """

    def __init__(self, root, *, initialize=True):
        self.root = Path(root)
        self.git = shutil.which('git')
        if self.git is None:
            raise RuntimeError('Git is a required integration-test prerequisite')
        self.env = dict(PATH=os.environ.get('PATH', ''), HOME=str(self.root),
            GIT_CONFIG_NOSYSTEM='1', GIT_CONFIG_GLOBAL=os.devnull,
            GIT_TERMINAL_PROMPT='0', GIT_AUTHOR_NAME='Fixture',
            GIT_AUTHOR_EMAIL='fixture@example.invalid', GIT_COMMITTER_NAME='Fixture',
            GIT_COMMITTER_EMAIL='fixture@example.invalid',
            GIT_AUTHOR_DATE='2000-01-01T00:00:00+00:00',
            GIT_COMMITTER_DATE='2000-01-01T00:00:00+00:00')
        if 'SystemRoot' in os.environ:
            self.env['SystemRoot'] = os.environ['SystemRoot']
        if initialize:
            self.run('init', '--bare', '--initial-branch=state')
        elif self.oid('rev-parse', '--is-bare-repository') != 'true':
            raise RuntimeError('Expected existing bare fixture repository')
        self.lock = threading.Lock()
        self.local = threading.local()
        self.barrier = None
        self.patches = 0
        self.created = []
        self.before_patch = self.after_patch = False
        if initialize:
            self.publish(encode(initial_state()))

    def run(self, *args, raw=None, check=True):
        """Use only this fixture repository; no shell, remote, hooks or tokens."""
        return subprocess.run([self.git, '-C', str(self.root), *args], input=raw,
            env=self.env, stdout=subprocess.PIPE, stderr=subprocess.PIPE,
            check=check, timeout=15)

    def oid(self, *args, raw=None):
        """Return a Git-produced immutable object ID, not a synthetic digest."""
        return self.run(*args, raw=raw).stdout.decode().strip()

    def publish(self, raw):
        """Provision synthetic seed bytes in the disposable fixture only."""
        blob = self.oid('hash-object', '-w', '--stdin', raw=raw)
        tree = self.oid('mktree', raw=f'100644 blob {blob}\tstate.json\n'.encode())
        head = self.oid('commit-tree', tree, raw=b'synthetic seed\n')
        self.run('update-ref', 'refs/'+STATE_REF, head)
        return head

    def head(self):
        """Read a real ref; do not fabricate missing storage."""
        result = self.run('rev-parse', '--verify', 'refs/'+STATE_REF, check=False)
        if result.returncode:
            raise StateBlocked('FIXTURE_STATE_MISSING')
        return result.stdout.decode().strip()

    def request(self, method, path, body=None):
        """Translate the backend's fixed object requests to actual Git plumbing."""
        if not path.startswith(PREFIX):
            raise AssertionError('Foreign repository')
        suffix = path[len(PREFIX):]
        if method == 'GET' and suffix == 'git/ref/'+STATE_REF:
            observed = self.head()
            reads = getattr(self.local, 'reads', 0)+1
            self.local.reads = reads
            # Every writer captures both pre-PATCH observations before any
            # writer can update the branch. Later readbacks remain independent.
            if self.barrier is not None and reads <= 2:
                self.barrier.wait(timeout=15)
            return dict(ref='refs/'+STATE_REF, object=dict(type='commit', sha=observed))
        if method == 'GET' and suffix.startswith('git/commits/'):
            sha = suffix.rsplit('/', 1)[1]
            headers = self.run('cat-file', 'commit', sha).stdout.split(b'\n\n', 1)[0].decode().splitlines()
            return dict(sha=sha, tree=dict(sha=headers[0].split()[1]),
                parents=[dict(sha=line.split()[1]) for line in headers if line.startswith('parent ')])
        if method == 'GET' and suffix.startswith('git/trees/'):
            sha = suffix.rsplit('/', 1)[1]
            rows = []
            for line in self.run('ls-tree', '-z', sha).stdout.split(b'\0'):
                if line:
                    metadata, name = line.decode().split('\t', 1)
                    mode, kind, blob = metadata.split()
                    rows.append(dict(path=name, mode=mode, type=kind, sha=blob))
            return dict(sha=sha, truncated=False, tree=rows)
        if method == 'GET' and suffix.startswith('git/blobs/'):
            sha = suffix.rsplit('/', 1)[1]
            raw = self.run('cat-file', 'blob', sha).stdout
            return dict(sha=sha, encoding='base64', size=len(raw), content=base64.b64encode(raw).decode())
        if method == 'POST' and suffix == 'git/blobs':
            return dict(sha=self.oid('hash-object', '-w', '--stdin', raw=base64.b64decode(body['content'], validate=True)))
        if method == 'POST' and suffix == 'git/trees':
            lines = [f"{r['mode']} {r['type']} {r['sha']}\t{r['path']}\n" for r in body['tree']]
            return dict(sha=self.oid('mktree', raw=''.join(lines).encode()))
        if method == 'POST' and suffix == 'git/commits':
            if len(body['parents']) != 1:
                raise AssertionError('Only one parent is allowed')
            sha = self.oid('commit-tree', body['tree'], '-p', body['parents'][0], raw=(body['message']+'\n').encode())
            with self.lock:
                self.created.append(sha)
            return dict(sha=sha, tree=dict(sha=body['tree']), parents=[dict(sha=p) for p in body['parents']])
        if method == 'PATCH' and suffix == 'git/refs/'+STATE_REF:
            if body.get('force') is not False:
                raise AssertionError('Force update forbidden')
            with self.lock:
                self.patches += 1
                if self.before_patch:
                    raise StateBlocked('FIXTURE_WRITE_NOT_SENT')
                old, target = self.head(), body['sha']
                if self.run('merge-base', '--is-ancestor', old, target, check=False).returncode:
                    raise StateBlocked('FIXTURE_NON_FAST_FORWARD')
                self.run('update-ref', 'refs/'+STATE_REF, target, old)
                if self.after_patch:
                    self.after_patch = False
                    raise TimeoutError('synthetic lost mutation response')
            return dict()
        raise AssertionError((method, suffix))


class GitStateIntegrationTests(unittest.TestCase):
    """Exercise the published backend with persistent real object/ref semantics."""

    def setUp(self):
        """Allocate only a new run-owned temporary bare repository."""
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.api = LocalGitAPI(self.temp.name)
        self.store = GitHubState(self.api)

    def test_real_objects_sole_parent_and_fresh_client_readback(self):
        head, state = self.store.load()
        state['last_tick'] = 100
        saved = self.store.save(head, state)
        self.assertEqual(GitHubState(LocalGitReader(self.api)).load(), (saved, state))
        self.assertEqual(self.api.oid('rev-parse', saved+'^'), head)
        self.assertEqual(self.api.run('cat-file', 'blob', saved+':state.json').stdout, encode(state))
        self.api.run('fsck', '--strict', '--no-reflogs')

    def race(self):
        """Hold all eight workers at the same parent and fixed Git timestamp."""
        parent = self.api.head()
        self.api.barrier = threading.Barrier(8)
        def worker(_):
            """Return success only after the backend's independent readback."""
            try:
                GitHubState(self.api).save(parent, initial_state())
                return True
            except StateBlocked:
                return False
        with ThreadPoolExecutor(max_workers=8) as pool:
            results = list(pool.map(worker, range(8)))
        self.api.barrier = None
        return results

    def test_eight_identical_same_second_writers_have_one_winner(self):
        self.assertEqual(sum(self.race()), 1)
        self.assertEqual(len(set(self.api.created)), 8)
        self.assertEqual(self.api.patches, 8)
        self.api.run('fsck', '--strict', '--no-reflogs')

    def test_negative_control_identical_commit_ids_admit_eight_successes(self):
        # Deliberately reproduce the retired fence defect, only in this fixture.
        with patch('durable_state.uuid.uuid4') as nonce:
            nonce.return_value.hex = '0'*32
            self.assertEqual(sum(self.race()), 8)
        self.assertEqual(len(set(self.api.created)), 1)

    def prepare_dispatch(self):
        """Use existing source/owner fixtures; no real dispatch authority."""
        ports = Ports()
        controller = Controller(self.store, ports, controller_sha='c'*40, operational_acceptance=True)
        controller.policy(True)
        key, nonce = controller.reserve(ExactPR(42, 'a'*40, 'b'*40), 100)
        return ports, controller, key, nonce

    def test_lost_fence_response_survives_restart_without_dispatch(self):
        ports, controller, key, nonce = self.prepare_dispatch()
        self.api.after_patch = True
        with self.assertRaises(TimeoutError):
            controller.dispatch(key, nonce)
        self.assertEqual(ports.posts, 0)
        self.assertEqual(self.store.load()[1]['claims'][key]['state'], 'DISPATCH_UNCERTAIN')
        # A separate Python process receives only the repository path and the
        # test module paths, with no inherited credentials or in-memory state.
        root = Path(__file__).resolve().parents[1]
        env = dict(self.api.env, PYTHONPATH=os.pathsep.join((str(root/'controller'), str(root/'tests'))))
        program = ('import json,sys; from test_git_state_integration import LocalGitAPI; '
            'from durable_state import GitHubState; '
            'print(json.dumps(GitHubState(LocalGitAPI(sys.argv[1],initialize=False)).load()))')
        observed = subprocess.run([sys.executable, '-c', program, str(self.api.root)],
            env=env, stdout=subprocess.PIPE, stderr=subprocess.PIPE, check=True, timeout=15)
        self.assertEqual(json.loads(observed.stdout), list(self.store.load()))
        restarted = Controller(GitHubState(LocalGitReader(self.api)), ports,
            controller_sha='c'*40, operational_acceptance=True)
        with self.assertRaises(StateBlocked):
            restarted.dispatch(key, nonce)
        self.assertEqual(ports.posts, 0)

    def test_rejected_fence_preserves_reservation_and_never_dispatches(self):
        ports, controller, key, nonce = self.prepare_dispatch()
        parent, before = self.store.load()
        self.api.before_patch = True
        with self.assertRaises(StateBlocked):
            controller.dispatch(key, nonce)
        self.assertEqual(self.store.load(), (parent, before))
        self.assertEqual(before['claims'][key]['state'], 'RESERVED')
        self.assertEqual(ports.posts, 0)

    def test_stale_lease_does_not_create_or_retry_objects(self):
        head, state = self.store.load()
        self.store.save(head, dict(state, last_tick=100))
        created, patches = len(self.api.created), self.api.patches
        with self.assertRaises(StateBlocked):
            self.store.save(head, dict(state, last_tick=200))
        self.assertEqual((len(self.api.created), self.api.patches), (created, patches))

    def test_valid_git_objects_with_noncanonical_json_are_rejected(self):
        self.api.publish(b'{ "schema":1 }\n')
        self.api.run('fsck', '--strict', '--no-reflogs')
        with self.assertRaisesRegex(StateBlocked, 'STATE_BYTES_INVALID'):
            self.store.load()


class LocalGitReader:
    """A fresh adapter boundary sharing only persistent Git storage."""

    def __init__(self, backend):
        self.backend = backend

    def request(self, method, path, body=None):
        """Restart observations must never repair storage by writing."""
        if method != 'GET':
            raise StateBlocked('READ_ONLY_RESTART_OBSERVATION')
        return copy.deepcopy(self.backend.request(method, path, body))


if __name__ == '__main__':
    unittest.main()
