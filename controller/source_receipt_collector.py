"""Ordered read-only source-full platform receipt collection; no installed job.

The caller supplies independently authenticated, fixed-target metadata/download
and provenance adapters. Callback injection is not proof of authentication,
TLS, redirect isolation, source execution or a trusted deployment by itself.
"""
from __future__ import annotations

from dataclasses import dataclass

from platform_receipts import (ExpectedPlatform, MAX_ZIP, PlatformRejected,
    PlatformResult, github_metadata, verify_platform)
from stage6_dispatch_ledger import _source
from stage6_pr_identity_v32 import CONTROLLER_REPO, ExactPR, IdentityRejected, SOURCE_REPO

API = 'https://api.github.com/repos/'
SOURCE_PLATFORMS = {'source-linux', 'windows-py311', 'windows-py313'}


@dataclass(frozen=True)
class SourceCollection:
    """Fixed collection status; verified receipts remain advisory-only."""
    state: str
    reason: str = ''
    receipt: PlatformResult | None = None
    required_scope: str = 'source-full'
    test_accepted: bool = False
    publication_authorized: bool = False
    unattended_enabled: bool = False


def collect_source_receipt(*, expected, source, get_json, get_artifact_bytes,
                           verify_execution=None):
    """Bind a full-source envelope to ordered independent live observations.

    The trusted host must approve expected workflow/job/step/source scope before
    construction. Download uses a fixed artifact-ID URL, 4 MiB limit and expected
    digest; its adapter must isolate storage requests from API credentials.
    Execution provenance is checked once after archive validation, then fresh
    run/jobs/artifact and final PR/base reads gate the returned advisory result.
    Missing proof remains blocked. There are no retries, writes or source jobs.
    """
    if (type(expected) is not ExpectedPlatform or type(source) is not ExactPR
            or not callable(get_json) or not callable(get_artifact_bytes)
            or verify_execution is not None and not callable(verify_execution)):
        return SourceCollection('BLOCKED', 'SOURCE_COLLECTOR_INPUT_INVALID')
    e = expected
    if (e.platform not in SOURCE_PLATFORMS or e.scope != 'source-full'
            or e.source_repo != SOURCE_REPO or e.producer_repo != CONTROLLER_REPO
            or e.producer_sha != e.controller_sha or e.subject_sha256 is not None
            or (e.source_sha, e.base_sha) != (source.head_sha, source.base_sha)):
        return SourceCollection('BLOCKED', 'SOURCE_COLLECTOR_SCOPE_INVALID')
    pr_url = API + SOURCE_REPO + f'/pulls/{source.pr_number}'
    branch_url = API + SOURCE_REPO + '/branches/main'
    run_url = API + CONTROLLER_REPO + f'/actions/runs/{e.run_id}'
    jobs_url = run_url + '/jobs?per_page=100'
    artifact_url = API + CONTROLLER_REPO + f'/actions/artifacts/{e.artifact_id}'
    identity = dict(repo=e.source_repo, head=e.source_sha, base=e.base_sha)

    def source_read():
        """Require a fresh eligible exact PR and independently fetched base tip."""
        _source(get_json(pr_url), get_json(branch_url), source)

    def metadata_read():
        """Require complete run/job/step/artifact identity before using bytes."""
        run, jobs, artifact = get_json(run_url), get_json(jobs_url), get_json(artifact_url)
        github_metadata(e, run=run, jobs=jobs, artifact=artifact)
        return run, jobs, artifact

    try:
        source_read()
        run, jobs, artifact = metadata_read()
        source_read()
        raw = get_artifact_bytes(artifact_url + '/zip', MAX_ZIP, e.artifact_sha256)
        if type(raw) is not bytes or len(raw) != artifact['size_in_bytes']:
            raise PlatformRejected('SOURCE_ARTIFACT_BYTE_COUNT_MISMATCH')
        # Validate the entire envelope, anonymous cases, counts and full scope
        # before invoking a separately privileged provenance verifier.
        verify_platform(e, raw=raw, run=run, jobs=jobs, artifact=artifact,
                        source_before=identity, source_after=identity)
        proof = None if verify_execution is None else verify_execution(e)
        # Reject expiry or metadata/source changes during download/provenance.
        run, jobs, artifact = metadata_read()
        if len(raw) != artifact['size_in_bytes']:
            raise PlatformRejected('SOURCE_ARTIFACT_BYTE_COUNT_MISMATCH')
        source_read()
        result = verify_platform(e, raw=raw, run=run, jobs=jobs, artifact=artifact,
            source_before=identity, source_after=identity,
            verify_subject=None if verify_execution is None else lambda _: proof)
        return SourceCollection(result.state, receipt=result)
    except (IdentityRejected, PlatformRejected, ValueError, TypeError, KeyError,
            AttributeError, OSError, RuntimeError, TimeoutError):
        # Never expose callback errors, signed URLs, raw source or artifact data.
        return SourceCollection('BLOCKED', 'SOURCE_COLLECTION_OR_VALIDATION_FAILED')
