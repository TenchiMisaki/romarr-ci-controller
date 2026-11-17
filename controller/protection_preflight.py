"""Read-only configured/applicable protection observations, never enforcement proof.

No transport, credentials, workflow or administrative write is installed here.
An independently trusted caller supplies a reader. All observations are dated
snapshots; prohibited-write behavior and operational acceptance remain untested.
"""
from __future__ import annotations

import hashlib
import datetime
import json

from controller_api import ReadNotFound
from durable_state import PREFIX, StateBlocked
from stage6_pr_identity_v32 import CONTROLLER_REPO

BASE = PREFIX.rstrip('/')
EXPECTED = {
    27344007: ('branch', '~DEFAULT_BRANCH', frozenset({'deletion', 'non_fast_forward'})),
    27485340: ('branch', 'refs/heads/controller-state-v1', frozenset({'deletion', 'non_fast_forward'})),
    27484547: ('tag', 'refs/tags/controller-revision-*', frozenset({'deletion', 'update'})),
}
BRANCHES = {'main': 27344007, 'controller-state-v1': 27485340}
PATHS = frozenset({BASE} | {PREFIX+'rulesets/'+str(n) for n in EXPECTED}
                  | {PREFIX+'rules/branches/'+name for name in BRANCHES})


class ProtectionReader:
    """Allow only six fixed GET targets; reject writes before the reader sees them."""
    def __init__(self, reader):
        self.reader = reader

    def request(self, method, path, body=None):
        """No arbitrary URL, ref, ruleset, query, credentials or mutation input."""
        if method != 'GET' or type(path) is not str or path not in PATHS or body is not None:
            raise StateBlocked('PROTECTION_READ_ONLY_TARGET_REQUIRED')
        return self.reader.request('GET', path)


def repository(row):
    """Bind observations to the fixed public owner/repository and default branch."""
    if (type(row) is not dict or type(row.get('id')) is not int or row['id'] != 1458032121
            or row.get('full_name') != CONTROLLER_REPO or row.get('private') is not False
            or row.get('archived') is not False or row.get('disabled') is not False
            or row.get('default_branch') != 'main' or type(row.get('owner')) is not dict
            or type(row['owner'].get('id')) is not int or row['owner']['id'] != 71314201):
        raise StateBlocked('PROTECTION_REPOSITORY_INVALID')
    return 'FIXED_PUBLIC_REPOSITORY'


def required_rule(rule):
    """Allow only parameterless restrictions or the equivalent strict update form."""
    if rule == dict(type=rule['type']):
        return True
    parameters = rule.get('parameters')
    return (rule['type'] == 'update' and set(rule) == {'type', 'parameters'}
            and type(parameters) is dict and set(parameters) == {'update_allows_fetch_and_merge'}
            and type(parameters['update_allows_fetch_and_merge']) is bool
            and parameters['update_allows_fetch_and_merge'] is False)


def configuration(row, identifier):
    """Require approved selectors/restrictions/no bypass; retain stronger rules."""
    target, selector, required = EXPECTED[identifier]
    if (type(row) is not dict or type(row.get('id')) is not int or row['id'] != identifier
            or row.get('source') != CONTROLLER_REPO or row.get('source_type') != 'Repository'
            or row.get('target') != target or row.get('enforcement') != 'active'
            or row.get('bypass_actors') != []
            or row.get('conditions') != dict(ref_name=dict(include=[selector], exclude=[]))
            or type(row.get('rules')) is not list or len(row['rules']) > 100
            or any(type(rule) is not dict or type(rule.get('type')) is not str for rule in row['rules'])
            or not required.issubset({rule['type'] for rule in row['rules']})
            or any(rule['type'] in required and not required_rule(rule) for rule in row['rules'])
            or any(sum(rule['type'] == kind for rule in row['rules']) != 1 for kind in required)):
        raise StateBlocked('PROTECTION_CONFIGURATION_INVALID')
    # Never export arbitrary rule parameters, names, actor metadata or URLs.
    fields = {key: row[key] for key in ('id', 'source', 'source_type', 'target',
              'enforcement', 'bypass_actors', 'conditions', 'rules')}
    return hashlib.sha256(json.dumps(fields, sort_keys=True, separators=(',', ':'),
                                    allow_nan=False).encode()).hexdigest()


def applicability(rows, identifier):
    """Require each approved branch restriction from its exact ruleset source."""
    required = EXPECTED[identifier][2]
    if type(rows) is not list or len(rows) > 1000 or any(type(row) is not dict for row in rows):
        raise StateBlocked('PROTECTION_APPLICABILITY_INVALID')
    observed = {row.get('type') for row in rows
                if type(row.get('ruleset_id')) is int and row['ruleset_id'] == identifier
                and row.get('ruleset_source_type') == 'Repository'
                and row.get('ruleset_source') == CONTROLLER_REPO and type(row.get('type')) is str}
    if not required.issubset(observed):
        raise StateBlocked('PROTECTION_APPLICABILITY_INVALID')
    return 'APPROVED_BRANCH_RULES_OBSERVED'


def observe(operation):
    """Sanitize collector failures without disguising permission/visibility gaps."""
    try:
        return dict(status='PASS', value=operation())
    except ReadNotFound:
        return dict(status='BLOCKED', code='NOT_FOUND_OR_NOT_VISIBLE')
    except StateBlocked as error:
        return dict(status='COLLECTION FAILED' if str(error).startswith('API_') else 'FAIL',
                    code='PROTECTION_UNVERIFIED')
    except (OSError, TimeoutError):
        return dict(status='COLLECTION FAILED', code='PROTECTION_READ_FAILED')
    except (ValueError, TypeError, KeyError, AttributeError, RecursionError):
        return dict(status='FAIL', code='PROTECTION_INVALID_RESPONSE')


def inspect_protections(reader):
    """Double-read fixed settings and branch applicability; never certify refusal.

    No tag-applicability REST endpoint is assumed. Missing or denied reads block
    only their observations; they never imply missing protections. No settings,
    ref writes, destructive probes or administration permissions are requested.
    """
    api = ProtectionReader(reader)
    report = dict(schema=1, repository=CONTROLLER_REPO,
        observed_at=datetime.datetime.now(datetime.timezone.utc).isoformat(),
        configuration_observations='BLOCKED',
        refused_write_enforcement='NOT TESTED', tag_applicability='NOT TESTED',
        operational_acceptance='NOT TESTED', activation_allowed=False, dispatch_allowed=False,
        checks={})
    checks = report['checks']
    checks['repository'] = observe(lambda: repository(api.request('GET', BASE)))
    if checks['repository']['status'] != 'PASS':
        return report
    for pass_name in ('initial', 'readback'):
        for identifier in EXPECTED:
            checks[pass_name+'_ruleset_'+str(identifier)] = observe(lambda n=identifier:
                configuration(api.request('GET', PREFIX+'rulesets/'+str(n)), n))
        for branch, identifier in BRANCHES.items():
            checks[pass_name+'_branch_'+branch] = observe(lambda b=branch, n=identifier:
                applicability(api.request('GET', PREFIX+'rules/branches/'+b), n))
    checks['repository_readback'] = observe(lambda: repository(api.request('GET', BASE)))
    for identifier in EXPECTED:
        first, last = (checks[name+'_ruleset_'+str(identifier)] for name in ('initial', 'readback'))
        if first['status'] == last['status'] == 'PASS' and first['value'] != last['value']:
            checks['stable_ruleset_'+str(identifier)] = dict(status='FAIL', code='PROTECTION_CHANGED_DURING_READ')
    if all(check['status'] == 'PASS' for check in checks.values()):
        report['configuration_observations'] = 'PASS'
    return report
