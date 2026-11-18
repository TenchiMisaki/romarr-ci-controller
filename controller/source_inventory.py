"""Private source inventory comparison for trusted, independently supplied inputs."""
from dataclasses import dataclass

from platform_receipts import ExpectedPlatform


@dataclass(frozen=True)
class ObservedInventory:
    """Private case outcomes from an independent execution observer."""

    receipt: ExpectedPlatform
    cases: tuple[tuple[str, str], ...]


def inventory_verifier(load_expected, load_observed):
    """Adapt independent inventory and provenance providers to the receipt collector.

    The caller supplies trusted providers. This comparison does not authenticate
    their origin. All case identities stay within the private verifier.
    """
    def verify(receipt, counts):
        if type(receipt) is not ExpectedPlatform or receipt.scope != 'source-full':
            return False
        expected = load_expected(receipt.source_repo, receipt.source_sha, receipt.base_sha,
                                 receipt.platform)
        observed = load_observed(receipt)
        if (type(expected) is not tuple or not 1 <= len(expected) <= 10000
                or any(type(case) is not str or not case for case in expected)
                or len(set(expected)) != len(expected)
                or type(observed) is not ObservedInventory or observed.receipt != receipt
                or type(observed.cases) is not tuple or len(observed.cases) != len(expected)):
            return False

        remaining = set(expected)
        for row in observed.cases:
            if type(row) is not tuple or len(row) != 2:
                return False
            case, outcome = row
            if type(case) is not str or case not in remaining or outcome != 'passed':
                return False
            remaining.remove(case)
        return counts == dict(passed=len(expected), failed=0, errors=0, skipped=0)

    return verify
