"""Dormant Git-backed controller state, with fast-forward-only atomic updates.

No credentials, startup initialization, scheduler or network transport is created
here. The injected authenticated API belongs exclusively to a trusted runner.
State must be provisioned separately; missing or corrupt storage fails closed.
"""
from __future__ import annotations

import base64
import copy
import hashlib
import json

from stage6_pr_identity_v32 import CONTROLLER_REPO, SHA

STATE_REF = 'heads/controller-state-v1'
PREFIX = f'repos/{CONTROLLER_REPO}/'
MAX_BYTES = 1_000_000


class StateBlocked(RuntimeError):
    """Storage, identity or concurrency is not independently established."""


def encode(state):
    """Canonicalize bounded JSON; reject NaN and non-object state."""
    if type(state) is not dict:
        raise StateBlocked('STATE_SHAPE_INVALID')
    raw = (json.dumps(state, sort_keys=True, separators=(',', ':'),
                      allow_nan=False) + '\n').encode()
    if len(raw) > MAX_BYTES:
        raise StateBlocked('STATE_CAPACITY_REQUIRES_OWNER_ARCHIVE')
    return raw


def git_sha(kind, raw):
    """Verify Git object identity independently of API content fields."""
    return hashlib.sha1(kind.encode() + b' ' + str(len(raw)).encode() + b'\0' + raw).hexdigest()


class GitHubState:
    """One dedicated branch, one JSON blob, append-only commit ancestry.

    API.request(method, repository-relative-path, optional-json-body) must be
    authenticated, bounded, reject redirects and never retry mutations. Writes
    use a new commit whose sole parent is the observed head. Sibling updates
    cannot both fast-forward. Any lost response blocks dependent dispatch.
    """

    def __init__(self, api):
        self.api = api

    def _request(self, method, suffix, body=None):
        """Constrain this adapter to the fixed controller Git database."""
        return self.api.request(method, PREFIX + suffix, body)

    def _head(self):
        """Require exactly the dedicated branch and a commit object."""
        row = self._request('GET', 'git/ref/' + STATE_REF)
        if (type(row) is not dict or row.get('ref') != 'refs/' + STATE_REF
                or type(row.get('object')) is not dict
                or row['object'].get('type') != 'commit'
                or not SHA.fullmatch(str(row['object'].get('sha', '')))):
            raise StateBlocked('STATE_REF_INVALID')
        return row['object']['sha']

    def load(self):
        """Read a pinned tree and validate the sole bounded state blob."""
        head = self._head()
        commit = self._request('GET', 'git/commits/' + head)
        tree_sha = commit.get('tree', {}).get('sha')
        if commit.get('sha') != head or not SHA.fullmatch(str(tree_sha)):
            raise StateBlocked('STATE_COMMIT_INVALID')
        tree = self._request('GET', 'git/trees/' + tree_sha)
        rows = tree.get('tree')
        if (tree.get('sha') != tree_sha or tree.get('truncated') is not False
                or type(rows) is not list or len(rows) != 1):
            raise StateBlocked('STATE_TREE_INVALID')
        row = rows[0]
        if (row.get('path') != 'state.json' or row.get('mode') != '100644'
                or row.get('type') != 'blob' or not SHA.fullmatch(str(row.get('sha')))):
            raise StateBlocked('STATE_MEMBER_INVALID')
        blob = self._request('GET', 'git/blobs/' + row['sha'])
        if (blob.get('sha') != row['sha'] or blob.get('encoding') != 'base64'
                or type(blob.get('size')) is not int
                or not 0 < blob['size'] <= MAX_BYTES
                or type(blob.get('content')) is not str
                or len(blob['content']) > MAX_BYTES * 2):
            raise StateBlocked('STATE_BLOB_INVALID')
        try:
            raw = base64.b64decode(''.join(blob['content'].split()), validate=True)
            state = json.loads(raw)
        except (ValueError, UnicodeError) as exc:
            raise StateBlocked('STATE_DECODE_INVALID') from exc
        if len(raw) != blob['size'] or git_sha('blob', raw) != row['sha'] or encode(state) != raw:
            raise StateBlocked('STATE_BYTES_INVALID')
        # Pinning bytes is insufficient when another writer changed the branch.
        if self._head() != head:
            raise StateBlocked('STATE_CHANGED_DURING_READ')
        return head, state

    def save(self, expected, state):
        """Commit one transition; never merge, force, initialize or retry."""
        raw = encode(state)
        if not SHA.fullmatch(str(expected)) or self._head() != expected:
            raise StateBlocked('STATE_LEASE_CHANGED')
        blob = self._request('POST', 'git/blobs',
                             {'content': base64.b64encode(raw).decode(), 'encoding': 'base64'})
        digest = git_sha('blob', raw)
        if blob.get('sha') != digest:
            raise StateBlocked('STATE_WRITTEN_BLOB_MISMATCH')
        tree = self._request('POST', 'git/trees', {'tree': [
            {'path': 'state.json', 'mode': '100644', 'type': 'blob', 'sha': digest}]})
        tree_sha = tree.get('sha')
        if not SHA.fullmatch(str(tree_sha)):
            raise StateBlocked('STATE_WRITTEN_TREE_INVALID')
        commit = self._request('POST', 'git/commits', {
            'message': 'chore: record controller state transition',
            'tree': tree_sha, 'parents': [expected]})
        target = commit.get('sha')
        if (not SHA.fullmatch(str(target)) or commit.get('tree', {}).get('sha') != tree_sha
                or [p.get('sha') for p in commit.get('parents', [])] != [expected]):
            raise StateBlocked('STATE_WRITTEN_COMMIT_INVALID')
        if self._head() != expected:
            raise StateBlocked('STATE_LEASE_CHANGED')
        # A timeout is intentionally not repaired by repeating this PATCH.
        self._request('PATCH', 'git/refs/' + STATE_REF, {'sha': target, 'force': False})
        actual, observed = self.load()
        if actual != target or observed != state:
            raise StateBlocked('STATE_WRITE_READBACK_UNCERTAIN')
        return target


def transact(store, update):
    """Apply one callback to a private copy; one save, no automatic retry."""
    head, old = store.load()
    state = copy.deepcopy(old)
    result = update(state)
    store.save(head, state)
    return result
