"""Manual-only trusted artifact discovery for the Stage 6 advisory verifier.

The authenticated run-scoped artifact listing, not untrusted source-job outputs,
provides the exact artifact ID and SHA-256. No dispatch/write/test acceptance.
No artifact is selected if the run has multiple attempts or ambiguous matches.
"""
from __future__ import annotations

from dataclasses import dataclass
import re

from stage6_pr_identity_v32 import IdentityRejected
from stage6_pr_entrypoint_v39 import (ARTIFACT_NAME, CONTROLLER,
                                        prepare_manual_evidence, run_manual)
from stage6_pr_transport_v38 import (ReadOnlyGitHubTransport, _get, _parse_json)

API = 'https://api.github.com'
HEX40 = re.compile(r'[0-9a-f]{40}\Z')
HEX64 = re.compile(r'[0-9a-f]{64}\Z')
POSITIVE = re.compile(r'[1-9][0-9]{0,18}\Z')


@dataclass(frozen=True)
class DiscoveryResult:
    state: str
    reason: str = ''
    artifact_id: int = 0
    artifact_sha256: str = ''
    test_accepted: bool = False
    publication_authorized: bool = False
    unattended_dispatch_enabled: bool = False


def listing_url(run_id: int) -> str:
    if type(run_id) is not int or run_id < 1 or run_id > 10**19 - 1:
        raise IdentityRejected('RUN_ID_INVALID')
    return f'{API}/repos/{CONTROLLER}/actions/runs/{run_id}/artifacts?per_page=100&page=1'


def select_artifact(listing: object, *, run_id: int, attempt: int,
                    controller_sha: str) -> tuple[int, str]:
    """Select exactly one unexpired current-run artifact with a complete digest.

    This requires the *complete* first-page listing. More than 100 artifacts or
    a second run attempt is intentionally unsupported until independently reviewed.
    """
    listing_url(run_id)
    if type(attempt) is not int or attempt != 1:
        raise IdentityRejected('RUN_ATTEMPT_UNSUPPORTED')
    if type(controller_sha) is not str or HEX40.fullmatch(controller_sha) is None:
        raise IdentityRejected('CONTROLLER_SHA_INVALID')
    if type(listing) is not dict or type(listing.get('total_count')) is not int:
        raise IdentityRejected('ARTIFACT_LIST_INCOMPLETE')
    items = listing.get('artifacts')
    if (type(items) is not list or not 1 <= len(items) <= 100 or
            listing['total_count'] != len(items)):
        raise IdentityRejected('ARTIFACT_LIST_INCOMPLETE')
    selected = [x for x in items if type(x) is dict and x.get('name') == ARTIFACT_NAME]
    if len(selected) != 1:
        raise IdentityRejected('ARTIFACT_AMBIGUOUS')
    x = selected[0]
    artifact_id = x.get('id')
    if type(artifact_id) is not int or artifact_id < 1:
        raise IdentityRejected('ARTIFACT_ID_INVALID')
    base = f'{API}/repos/{CONTROLLER}/actions/artifacts/{artifact_id}'
    origin = x.get('workflow_run')
    digest = x.get('digest')
    if (x.get('expired') is not False or
            type(x.get('size_in_bytes')) is not int or
            not 1 <= x['size_in_bytes'] <= 65536 or
            type(digest) is not str or not digest.startswith('sha256:') or
            HEX64.fullmatch(digest[7:]) is None or
            x.get('url') != base or x.get('archive_download_url') != base + '/zip' or
            type(origin) is not dict or origin.get('id') != run_id or
            origin.get('head_sha') != controller_sha or
            origin.get('head_branch') != 'main'):
        raise IdentityRejected('ARTIFACT_ORIGIN_UNVERIFIED')
    return artifact_id, digest[7:]


class DiscoveryTransport(ReadOnlyGitHubTransport):
    """Allow only the exact read-only run-scoped artifact-list endpoint."""

    def list_run_artifacts(self, run_id: int) -> dict:
        url = listing_url(run_id)
        raw = _get(self._opener, url, self._token, expected_status=200,
                   limit=1024 * 1024, accept='application/vnd.github+json')
        return _parse_json(raw)


def run_discovered_manual(data: dict, *, transport_factory=DiscoveryTransport):
    """Discover provenance-bound ID/digest before running v39's final collector.

    Source-job artifact ID/digest environment fields are prohibited. Expectations
    are constructed from the authenticated run-scoped listing only.
    """
    try:
        if type(data) is not dict or 'EXPECTED_ARTIFACT_ID' in data or 'EXPECTED_ARTIFACT_SHA256' in data:
            raise IdentityRejected('UNTRUSTED_ARTIFACT_INPUT')
        run_raw = data.get('GITHUB_RUN_ID')
        attempt_raw = data.get('GITHUB_RUN_ATTEMPT')
        sha = data.get('GITHUB_SHA')
        token = data.get('GITHUB_TOKEN')
        if (type(run_raw) is not str or POSITIVE.fullmatch(run_raw) is None or
                type(attempt_raw) is not str or POSITIVE.fullmatch(attempt_raw) is None or
                type(sha) is not str or HEX40.fullmatch(sha) is None or
                type(token) is not str):
            raise IdentityRejected('RUNNER_IDENTITY_INVALID')
        # Fail early on trusted workflow identity before invoking any HTTP.
        provisional = dict(data)
        provisional['EXPECTED_ARTIFACT_ID'] = '1'
        provisional['EXPECTED_ARTIFACT_SHA256'] = '0' * 64
        prepare_manual_evidence(provisional)
        transport = transport_factory(token)
        artifact_id, digest = select_artifact(transport.list_run_artifacts(int(run_raw)),
                                              run_id=int(run_raw), attempt=int(attempt_raw),
                                              controller_sha=sha)
        verified = dict(data)
        verified['EXPECTED_ARTIFACT_ID'] = str(artifact_id)
        verified['EXPECTED_ARTIFACT_SHA256'] = digest
        result = run_manual(verified, transport_factory=lambda _: transport)
        if result.state != 'ADVISORY_COLLECTED_NOT_TEST_ACCEPTED':
            return DiscoveryResult('BLOCKED', 'COLLECTION_NOT_VERIFIED')
        return DiscoveryResult('ADVISORY_COLLECTED_NOT_TEST_ACCEPTED',
                               artifact_id=artifact_id, artifact_sha256=digest)
    except (IdentityRejected, ValueError, KeyError, TypeError, RuntimeError,
            OSError, TimeoutError):
        return DiscoveryResult('BLOCKED', 'DISCOVERY_OR_VALIDATION_FAILED')


def main() -> None:
    import os
    result = run_discovered_manual(dict(os.environ))
    if result.state != 'ADVISORY_COLLECTED_NOT_TEST_ACCEPTED':
        print('BLOCKED: manual authenticated artifact discovery/verification incomplete')
        raise SystemExit(1)
    print('ADVISORY_COLLECTED_NOT_TEST_ACCEPTED')
    print('TEST_ACCEPTED: false')
    print('PUBLICATION_AUTHORIZED: false')
    print('UNATTENDED_DISPATCH_ENABLED: false')
    print('PR_SOURCE_TESTED: not independently accepted')


if __name__ == '__main__':
    main()
