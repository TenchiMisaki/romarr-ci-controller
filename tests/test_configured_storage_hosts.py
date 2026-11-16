"""Exact host allowlist regression tests for the manual advisory verifier.

Uses unittest, matching the controller's GitHub unit workflow discovery. Tests
operate entirely offline and do not handle credentials or dispatch workflows.
"""
from pathlib import Path
import sys
import unittest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'controller'))
import stage6_manual_readback_v28 as m  # noqa: E402
import stage6_artifact_http as transport  # noqa: E402

A = 'productionresultssa32.blob.core.windows.net'
B = 'productionresultssa31.blob.core.windows.net'


class ConfiguredStorageHostsTests(unittest.TestCase):
    def invalid(self, primary, secondary=''):
        with self.assertRaisesRegex(ValueError, 'STORAGE_HOST_CONFIGURATION_INVALID'):
            m.configured_storage_hosts(primary, secondary)

    def test_legacy_primary_unchanged(self):
        self.assertEqual(m.configured_storage_hosts(A), frozenset({A}))

    def test_secondary_exact_set(self):
        self.assertEqual(m.configured_storage_hosts(A, B), frozenset({A, B}))

    def test_order_does_not_matter(self):
        self.assertEqual(m.configured_storage_hosts(B, A), frozenset({A, B}))

    def test_approved_only_and_no_wildcard(self):
        hosts = m.configured_storage_hosts(A, B)
        for host in (A, B):
            self.assertTrue(transport._host_allowed('https://' + host + '/download?sig=synthetic', hosts))
        self.assertFalse(transport._host_allowed('https://productionresultssa30.blob.core.windows.net/download', hosts))
        self.assertFalse(transport._host_allowed('https://attacker.invalid/download', hosts))
        self.assertFalse(transport._host_allowed('http://' + B + '/download', hosts))
        self.assertFalse(transport._host_allowed('https://user@' + B + '/download', hosts))

    def test_missing_both(self):
        self.invalid('')

    def test_duplicate(self):
        self.invalid(A, A)

    def test_secondary_space(self):
        self.invalid(A, ' ')

    def test_primary_leading_space(self):
        self.invalid(' ' + A)

    def test_primary_newline(self):
        self.invalid(A + '\n')

    def test_uppercase(self):
        self.invalid(A.upper())

    def test_wildcard(self):
        self.invalid('*.blob.core.windows.net')

    def test_url_prefix(self):
        self.invalid('https://' + A)

    def test_api_github(self):
        self.invalid('api.github.com')

    def test_other_domain(self):
        self.invalid(A, 'other.example')

    def test_port(self):
        self.invalid(A, B + ':443')

    def test_hostname_suffix(self):
        self.invalid(A + '.evil.invalid')

    def test_primary_none(self):
        self.invalid(None)

    def test_secondary_none(self):
        self.invalid(A, None)

    def test_primary_int(self):
        self.invalid(17)

    def test_secondary_int(self):
        self.invalid(A, 17)


if __name__ == '__main__':
    unittest.main()
