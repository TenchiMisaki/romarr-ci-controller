"""Offline protection observations never stand in for refused-write evidence."""
import copy
import json
import unittest

from controller_api import ReadNotFound
from durable_state import PREFIX, StateBlocked
from protection_preflight import (BASE, BRANCHES, EXPECTED, ProtectionReader,
                                 configuration, inspect_protections)
from stage6_pr_identity_v32 import CONTROLLER_REPO


class Reader:
    def __init__(self):
        self.calls = []
        self.rows = {BASE: dict(id=1458032121, full_name=CONTROLLER_REPO, private=False,
            archived=False, disabled=False, default_branch='main', owner=dict(id=71314201))}
        for n, (target, selector, rules) in EXPECTED.items():
            self.rows[PREFIX+'rulesets/'+str(n)] = dict(id=n, target=target,
                source=CONTROLLER_REPO, source_type='Repository', enforcement='active',
                bypass_actors=[], conditions=dict(ref_name=dict(include=[selector], exclude=[])),
                rules=[dict(type=rule) for rule in sorted(rules)])
        for branch, n in BRANCHES.items():
            self.rows[PREFIX+'rules/branches/'+branch] = [dict(type=rule, ruleset_id=n,
                ruleset_source=CONTROLLER_REPO, ruleset_source_type='Repository')
                for rule in sorted(EXPECTED[n][2])]

    def request(self, method, path):
        self.calls.append((method, path))
        row = self.rows[path]
        if isinstance(row, Exception):
            raise row
        return copy.deepcopy(row)


class ProtectionTests(unittest.TestCase):
    def test_double_read_pass_never_accepts_enforcement_or_activation(self):
        reader = Reader()
        report = inspect_protections(reader)
        self.assertEqual(report['configuration_observations'], 'PASS')
        self.assertEqual(len(reader.calls), 12)
        self.assertTrue(all(method == 'GET' for method, _ in reader.calls))
        for key in ('refused_write_enforcement', 'tag_applicability', 'operational_acceptance'):
            self.assertEqual(report[key], 'NOT TESTED')
        self.assertFalse(report['activation_allowed'])
        self.assertFalse(report['dispatch_allowed'])

    def test_mutations_and_foreign_paths_refused_before_reader(self):
        reader = Reader()
        api = ProtectionReader(reader)
        for method, path, body in [('PATCH', BASE, None), ('DELETE', BASE, None),
                ('GET', BASE, {}), ('GET', BASE+'?x=1', None), ('GET', 'user', None),
                ('GET', PREFIX+'rulesets/1', None), ('GET', ['bad'], None)]:
            with self.subTest(method=method, path=path), self.assertRaises(StateBlocked):
                api.request(method, path, body)
        self.assertEqual(reader.calls, [])

    def test_repository_mismatch_stops_all_other_reads(self):
        for key, bad in [('id', True), ('default_branch', 'other'), ('private', True),
                         ('owner', dict(id=1)), ('full_name', 'foreign/repo')]:
            reader = Reader()
            reader.rows[BASE][key] = bad
            self.assertEqual(inspect_protections(reader)['configuration_observations'], 'BLOCKED')
            self.assertEqual(len(reader.calls), 1)

    def test_wrong_ruleset_scope_bypass_and_missing_restrictions_fail(self):
        for key, bad in [('id', True), ('target', 'tag'), ('enforcement', 'evaluate'),
                ('bypass_actors', [dict(actor_id=1)]), ('source', 'foreign/repo'),
                ('source_type', 'Organization'), ('conditions', {}), ('rules', []),
                ('rules', [dict(type=[])]), ('rules', None)]:
            with self.subTest(key=key, bad=bad):
                reader = Reader()
                reader.rows[PREFIX+'rulesets/27485340'][key] = bad
                report = inspect_protections(reader)
                self.assertEqual(report['configuration_observations'], 'BLOCKED')
                self.assertEqual(report['checks']['initial_ruleset_27485340']['status'], 'FAIL')

    def test_omitted_bypass_field_is_unverified_not_assumed_empty(self):
        reader = Reader()
        del reader.rows[PREFIX+'rulesets/27485340']['bypass_actors']
        report = inspect_protections(reader)
        self.assertEqual(report['configuration_observations'], 'BLOCKED')
        self.assertEqual(report['checks']['initial_ruleset_27485340']['code'], 'PROTECTION_UNVERIFIED')
        self.assertEqual(report['refused_write_enforcement'], 'NOT TESTED')

    def test_required_rules_with_unknown_parameters_or_duplicates_are_invalid(self):
        for duplicate in (False, True):
            reader = Reader()
            row = reader.rows[PREFIX+'rulesets/27485340']
            if duplicate:
                row['rules'].append(copy.deepcopy(row['rules'][0]))
            else:
                row['rules'][0]['parameters'] = dict(unexpected=True)
            self.assertEqual(inspect_protections(reader)['configuration_observations'], 'BLOCKED')

    def test_final_repository_identity_change_cannot_pass(self):
        reader = Reader()
        original = reader.request
        count = 0
        def changed(method, path):
            nonlocal count
            row = original(method, path)
            if path == BASE:
                count += 1
                if count == 2: row['owner']['id'] = 1
            return row
        reader.request = changed
        report = inspect_protections(reader)
        self.assertEqual(report['configuration_observations'], 'BLOCKED')
        self.assertEqual(report['checks']['repository_readback']['status'], 'FAIL')

    def test_more_restrictive_rules_preserved_and_private_parameters_not_exported(self):
        reader = Reader()
        row = reader.rows[PREFIX+'rulesets/27485340']
        row['rules'].append(dict(type='pull_request', parameters=dict(private_fixture='not-public')))
        before = copy.deepcopy(reader.rows)
        report = inspect_protections(reader)
        self.assertEqual(report['configuration_observations'], 'PASS')
        self.assertEqual(reader.rows, before)
        self.assertNotIn('not-public', json.dumps(report))

    def test_branch_rule_source_and_coverage_must_match(self):
        path = PREFIX+'rules/branches/controller-state-v1'
        for key, bad in [('ruleset_id', 1), ('ruleset_source', 'foreign/repo'),
                         ('ruleset_source_type', 'Organization'), ('type', 'update')]:
            reader = Reader()
            reader.rows[path][0][key] = bad
            report = inspect_protections(reader)
            self.assertEqual(report['checks']['initial_branch_controller-state-v1']['status'], 'FAIL')
            self.assertEqual(report['configuration_observations'], 'BLOCKED')

    def test_denied_missing_and_transport_reads_do_not_imply_protections_absent(self):
        for error, expected in [(ReadNotFound('private fixture'), 'BLOCKED'),
                (StateBlocked('API_HTTP_403'), 'COLLECTION FAILED'),
                (TimeoutError('private fixture'), 'COLLECTION FAILED')]:
            reader = Reader()
            reader.rows[PREFIX+'rulesets/27485340'] = error
            report = inspect_protections(reader)
            self.assertEqual(report['checks']['initial_ruleset_27485340']['status'], expected)
            self.assertEqual(report['configuration_observations'], 'BLOCKED')
            self.assertNotIn('private fixture', json.dumps(report))

    def test_change_between_valid_configuration_reads_is_blocked(self):
        reader = Reader()
        original = reader.request
        count = 0
        def changed(method, path):
            nonlocal count
            row = original(method, path)
            if path == PREFIX+'rulesets/27485340':
                count += 1
                if count == 2: row['rules'].append(dict(type='pull_request'))
            return row
        reader.request = changed
        report = inspect_protections(reader)
        self.assertEqual(report['configuration_observations'], 'BLOCKED')
        self.assertEqual(report['checks']['stable_ruleset_27485340']['code'], 'PROTECTION_CHANGED_DURING_READ')

    def test_later_success_cannot_erase_first_failed_observation(self):
        reader = Reader()
        original = reader.request
        count = 0
        def recovered(method, path):
            nonlocal count
            if path == PREFIX+'rulesets/27485340':
                count += 1
                if count == 1: raise StateBlocked('API_HTTP_403')
            return original(method, path)
        reader.request = recovered
        self.assertEqual(inspect_protections(reader)['configuration_observations'], 'BLOCKED')
