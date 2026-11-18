"""Exercise the private inventory check at the collector boundary."""
from dataclasses import replace
import unittest

from source_inventory import ObservedInventory, inventory_verifier
import test_source_receipt_collector as collector_fixtures


class SourceInventoryTests(unittest.TestCase):
    def collect(self, extra_cases):
        fixture = collector_fixtures.SourceCollectorTests()
        fixture.setUp()
        count = fixture.fixture.receipt['counts']['passed'] + extra_cases
        names = tuple(f'fixture-case-{index}' for index in range(count))
        rows = tuple((name, 'passed') for name in names)
        verifier = inventory_verifier(lambda *_: names,
            lambda receipt: ObservedInventory(receipt, rows))
        return fixture.collect(verify_inventory=verifier), fixture.calls

    def test_matching_private_and_anonymous_totals_remain_advisory(self):
        result, calls = self.collect(0)
        self.assertEqual(result.state, 'ADVISORY_VERIFIED')
        self.assertTrue(any(kind == 'PROOF' for kind, _ in calls))

    def test_mismatched_private_and_anonymous_totals_stop_before_proof(self):
        result, calls = self.collect(1)
        self.assertEqual(result.state, 'BLOCKED')
        self.assertEqual(result.reason, 'SOURCE_INVENTORY_MISMATCH')
        self.assertFalse(any(kind == 'PROOF' for kind, _ in calls))

    def test_incorrect_private_evidence_is_rejected_before_proof(self):
        for fault in ('run', 'digest', 'outcome', 'substitution'):
            with self.subTest(fault=fault):
                fixture = collector_fixtures.SourceCollectorTests()
                fixture.setUp()
                receipt = fixture.expected
                count = fixture.fixture.receipt['counts']['passed']
                names = tuple(f'fixture-case-{index}' for index in range(count))
                rows = tuple((name, 'passed') for name in names)
                if fault == 'run':
                    receipt = replace(receipt, run_id=receipt.run_id + 1)
                elif fault == 'digest':
                    receipt = replace(receipt, artifact_sha256='0' * 64)
                elif fault == 'outcome':
                    rows = ((names[0], 'skipped'),) + rows[1:]
                else:
                    rows = (('unexpected-case', 'passed'),) + rows[1:]

                observed = ObservedInventory(receipt, rows)
                verifier = inventory_verifier(lambda *_: names, lambda _: observed)
                result = fixture.collect(verify_inventory=verifier)
                self.assertEqual(result.reason, 'SOURCE_INVENTORY_MISMATCH')
                self.assertFalse(any(kind == 'PROOF' for kind, _ in fixture.calls))

    def test_provider_failures_are_sanitized(self):
        def unavailable(*args):
            raise OSError('private fixture detail')

        for load_expected, load_observed in (
            (unavailable, lambda _: None),
            (lambda *_: ('fixture-case',), unavailable),
        ):
            with self.subTest(provider=load_expected):
                fixture = collector_fixtures.SourceCollectorTests()
                fixture.setUp()
                result = fixture.collect(verify_inventory=inventory_verifier(
                    load_expected, load_observed))
                self.assertEqual(result.state, 'BLOCKED')
                self.assertEqual(result.reason, 'SOURCE_COLLECTION_OR_VALIDATION_FAILED')
                self.assertNotIn('private fixture detail', repr(result))
                self.assertFalse(any(kind == 'PROOF' for kind, _ in fixture.calls))

    def test_truthy_non_boolean_verdict_is_rejected(self):
        fixture = collector_fixtures.SourceCollectorTests()
        fixture.setUp()
        result = fixture.collect(verify_inventory=lambda *_: 1)
        self.assertEqual(result.reason, 'SOURCE_INVENTORY_MISMATCH')
        self.assertFalse(any(kind == 'PROOF' for kind, _ in fixture.calls))
