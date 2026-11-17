"""Read-only observations of dormant deployment prerequisites, never acceptance.

The caller supplies an authenticated reader from an independently trusted host.
No credentials, source jobs, workflow, state branch or revision tag are created.
Even complete observations cannot authorize arming, dispatch or a deployment.
"""
from __future__ import annotations

import re

from controller_api import ReadNotFound, verify_controller_revision
from controller_cycle import OWNER_ID, validate
from durable_state import GitHubState, PREFIX, STATE_REF, StateBlocked
from stage6_pr_identity_v32 import CONTROLLER_REPO, SHA

REPOSITORY_ID = 1458032121


class ReadOnlyProbe:
    """Refuse mutations before calling even an accidentally privileged adapter."""

    def __init__(self, reader):
        self.reader = reader

    def request(self, method, path, body=None):
        """Forward only the metadata, state-object and exact revision read paths."""
        if (method != 'GET' or body is not None or type(path) is not str
                or not (path in {PREFIX.rstrip('/'), PREFIX + 'git/ref/' + STATE_REF}
                    or re.fullmatch(re.escape(PREFIX)
                        + r'git/(?:commits|trees|blobs)/[0-9a-f]{40}', path)
                    or re.fullmatch(re.escape(PREFIX)
                        + r'git/ref/tags/controller-revision-[0-9a-f]{40}', path))):
            raise StateBlocked('PREFLIGHT_READ_ONLY_TARGET_REQUIRED')
        return self.reader.request(method, path)


def _repository(reader):
    """Require fixed numeric repository/owner identities and public visibility."""
    row = reader.request('GET', PREFIX.rstrip('/'))
    if (type(row) is not dict or type(row.get('id')) is not int
            or row['id'] != REPOSITORY_ID or row.get('full_name') != CONTROLLER_REPO
            or row.get('private') is not False or row.get('archived') is not False
            or row.get('disabled') is not False or type(row.get('owner')) is not dict
            or type(row['owner'].get('id')) is not int or row['owner']['id'] != OWNER_ID):
        raise StateBlocked('PREFLIGHT_REPOSITORY_IDENTITY_INVALID')


def _observe(operation, component):
    """Classify observation failures with fixed codes, never raw server content."""
    try:
        value = operation()
        return dict(status='PASS', code=component + '_OBSERVED'), value
    except ReadNotFound:
        return dict(status='BLOCKED', code=component + '_NOT_FOUND_OR_NOT_VISIBLE'), None
    except StateBlocked as exc:
        # Existing adapters expose fixed codes. Do not echo arbitrary exceptions
        # from injected transports, state payloads or tests into public reports.
        status = 'COLLECTION FAILED' if str(exc).startswith('API_') else 'FAIL'
        return dict(status=status, code=component + '_UNVERIFIED'), None
    except (AttributeError, KeyError, TypeError, ValueError):
        return dict(status='FAIL', code=component + '_INVALID_RESPONSE'), None
    except (OSError, TimeoutError):
        return dict(status='COLLECTION FAILED', code=component + '_READ_FAILED'), None


def inspect_deployment(reader, *, controller_sha):
    """Inspect identity, exact revision tag and canonical disabled state.

    PASS is limited to these point-in-time observations. No permissions,
    immutable-ref protection, owner acceptance, live race, source receipt or
    recovery behavior is certified. A 404 can hide inaccessible resources.
    Unknown claims are counted but never reset, deleted, retried or disclosed.
    """
    if type(controller_sha) is not str or not SHA.fullmatch(controller_sha):
        raise StateBlocked('CONTROLLER_SHA_INVALID')
    api = ReadOnlyProbe(reader)
    report = dict(schema=1, repository=CONTROLLER_REPO, controller=controller_sha,
                  prerequisites='BLOCKED', operational_acceptance='NOT TESTED',
                  activation_allowed=False, dispatch_allowed=False, checks={})
    checks = report['checks']
    checks['repository'], _ = _observe(lambda: _repository(api), 'REPOSITORY')
    if checks['repository']['status'] != 'PASS':
        return report
    checks['revision'], _ = _observe(
        lambda: verify_controller_revision(api, controller_sha), 'REVISION')

    def state_snapshot():
        head, state = GitHubState(api).load()
        validate(state)
        return head, state

    checks['state'], observed = _observe(state_snapshot, 'STATE')
    if observed is not None:
        head, state = observed
        checks['state']['head'] = head
        checks['policy'] = dict(status='PASS' if not state['policy']['enabled'] else 'BLOCKED',
            code='POLICY_DISABLED' if not state['policy']['enabled'] else 'POLICY_ALREADY_ENABLED',
            generation=state['policy']['generation'], retained_claims=len(state['claims']),
            retained_alerts=len(state['alerts']))
    # Independent final reads detect changes during collection, not future
    # immutability. Never reclassify a failed first observation as a later PASS.
    if checks['revision']['status'] == 'PASS':
        checks['revision_readback'], _ = _observe(
            lambda: verify_controller_revision(api, controller_sha), 'REVISION_READBACK')
    checks['repository_readback'], _ = _observe(lambda: _repository(api), 'REPOSITORY_READBACK')
    if all(check['status'] == 'PASS' for check in checks.values()):
        report['prerequisites'] = 'PASS'
    return report
