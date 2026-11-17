"""Manual-only Stage 6 v39 trusted-verifier entrypoint CANDIDATE.

No authorization to dispatch, schedule, publish, or accept tests. All expectations
are supplied by a separately trusted workflow configuration/owner input; source
job outputs cannot establish those expectations. This module cannot distinguish
untrusted workflow environment substitutions and is not hosted-accepted.
"""
from __future__ import annotations

from dataclasses import dataclass
import os
import re

from stage6_pr_identity_v32 import ExactPR, IdentityRejected
from stage6_pr_receipt_v33 import ExpectedArtifact
from stage6_pr_final_gate_v36 import FinalEvidence
from stage6_pr_collector_v37 import collect_ordered
from stage6_pr_transport_v38 import ReadOnlyGitHubTransport

CONTROLLER = 'TenchiMisaki/romarr-ci-controller'
SHA40 = re.compile(r'[0-9a-f]{40}\Z')
SHA64 = re.compile(r'[0-9a-f]{64}\Z')
DECIMAL = re.compile(r'[1-9][0-9]{0,18}\Z')
WORKFLOW = '.github/workflows/stage6-pr-manual-candidate.yml'
SOURCE_JOB = 'Isolated exact-PR ROMarr source tests'
SOURCE_STEP = 'Run pinned source in offline container'
ARTIFACT_NAME = 'romarr-stage6-pr-advisory'

@dataclass(frozen=True)
class EntryResult:
    state: str
    reason: str = ''
    test_accepted: bool = False
    publication_authorized: bool = False
    unattended_dispatch_enabled: bool = False


def _required(data: dict, key: str) -> str:
    value = data.get(key)
    if type(value) is not str or not value or value != value.strip():
        raise IdentityRejected('MISSING_EXPECTATION')
    return value


def _int(data: dict, key: str) -> int:
    value = _required(data, key)
    if not DECIMAL.fullmatch(value):
        raise IdentityRejected('INVALID_INTEGER')
    return int(value)


def prepare_manual_evidence(data: dict) -> FinalEvidence:
    """Preflight GitHub runner identity and independently configured expectations.

    This is intentionally *not* a discovery mechanism. A trusted owner/workflow
    must bind each expectation without consuming arbitrary test-job output.
    """
    if type(data) is not dict:
        raise IdentityRejected('INVALID_ENV')
    if (data.get('GITHUB_ACTIONS') != 'true'
            or data.get('GITHUB_REPOSITORY') != CONTROLLER
            or data.get('GITHUB_EVENT_NAME') != 'workflow_dispatch'
            or data.get('GITHUB_REF') != 'refs/heads/main'
            or data.get('GITHUB_WORKFLOW_REF') is None):
        raise IdentityRejected('RUNNER_IDENTITY_INVALID')
    sha = _required(data, 'GITHUB_SHA')
    if not SHA40.fullmatch(sha) or sha != _required(data, 'EXPECTED_CONTROLLER_SHA'):
        raise IdentityRejected('CONTROLLER_SHA_MISMATCH')
    # Bound to one exact manual workflow path/ref; never infer an arbitrary path.
    if _required(data, 'GITHUB_WORKFLOW_REF') != (
            CONTROLLER + '/' + WORKFLOW + '@refs/heads/main'):
        raise IdentityRejected('WORKFLOW_REF_INVALID')
    run_id = _int(data, 'GITHUB_RUN_ID')
    attempt = _int(data, 'GITHUB_RUN_ATTEMPT')
    if run_id != _int(data, 'EXPECTED_RUN_ID') or attempt != _int(data, 'EXPECTED_RUN_ATTEMPT'):
        raise IdentityRejected('RUN_IDENTITY_MISMATCH')
    pr_number = _int(data, 'EXPECTED_PR_NUMBER')
    head = _required(data, 'EXPECTED_PR_HEAD_SHA')
    base = _required(data, 'EXPECTED_PR_BASE_SHA')
    digest = _required(data, 'EXPECTED_ARTIFACT_SHA256')
    if not SHA40.fullmatch(head) or not SHA40.fullmatch(base) or not SHA64.fullmatch(digest):
        raise IdentityRejected('SHA_INVALID')
    # No source-job accepted/published flags may influence these constants.
    e = ExpectedArtifact(
        pr=ExactPR(pr_number=pr_number, head_sha=head, base_sha=base),
        controller_sha=sha, workflow_path=WORKFLOW, run_id=run_id,
        run_attempt=attempt, source_job_name=SOURCE_JOB,
        required_source_steps=(SOURCE_STEP,),
        artifact_id=_int(data, 'EXPECTED_ARTIFACT_ID'),
        artifact_name=ARTIFACT_NAME, artifact_sha256=digest,
    )
    return FinalEvidence(expected=e, source_sha=head)


def run_manual(data: dict, *, transport_factory=ReadOnlyGitHubTransport) -> EntryResult:
    """Run read-only ordered collection, never emit trusted test acceptance.

    Network transport is injected exclusively to permit offline tests. Real
    execution requires a separately reviewed GitHub workflow with no token in
    the source job and a trusted verifier running on a different runner.
    """
    try:
        evidence = prepare_manual_evidence(data)
        token = _required(data, 'GITHUB_TOKEN')
        transport = transport_factory(token)
        result = collect_ordered(evidence=evidence,
                                 get_json=transport.get_json,
                                 get_artifact_bytes=transport.get_artifact_bytes)
        if result.state != 'ADVISORY_COLLECTED_NOT_TEST_ACCEPTED':
            return EntryResult('BLOCKED', 'COLLECTION_NOT_VERIFIED')
        return EntryResult('ADVISORY_COLLECTED_NOT_TEST_ACCEPTED')
    except (IdentityRejected, ValueError, KeyError, TypeError, RuntimeError, OSError):
        return EntryResult('BLOCKED', 'ENTRYPOINT_VALIDATION_FAILED')


def main():
    result = run_manual(dict(os.environ))
    if result.state != 'ADVISORY_COLLECTED_NOT_TEST_ACCEPTED':
        print('BLOCKED: manual evidence validation incomplete')
        raise SystemExit(1)
    print('ADVISORY_COLLECTED_NOT_TEST_ACCEPTED')
    print('TEST_ACCEPTED: false')
    print('PUBLICATION_AUTHORIZED: false')
    print('UNATTENDED_DISPATCH_ENABLED: false')
    print('PR_SOURCE_TESTED: not independently accepted')


if __name__ == '__main__':
    main()
