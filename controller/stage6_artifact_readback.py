"""Offline, read-only GitHub Actions artifact metadata + advisory ZIP integrity gate.

This verifies only *an externally supplied artifact and public metadata*. It does
not fetch, download, authenticate source pytest, upload, accept or publish results.
Callers must separately enforce credential-free, vetted HTTPS artifact downloads.
"""
from __future__ import annotations

from dataclasses import dataclass
import hashlib
import re
from typing import Any

import stage6_hosted_advisory_bundle as bundle
import stage6_hosted_provenance as provenance

_ARTIFACT_NAME = 'stage6-advisory-provenance-v1'
_SHA = re.compile(r'[0-9a-f]{64}\Z')


@dataclass(frozen=True)
class Readback:
    state: str
    reason: str = ''
    sha256: str = ''
    test_accepted: bool = False
    publication_authorized: bool = False
    unattended_dispatch_enabled: bool = False


def verify_downloaded_advisory(metadata: object, downloaded: object,
                               expected: provenance.Expectation,
                               verified_job_ids: tuple[int, int],
                               independent_digest: str, *,
                               expected_artifact_id: int) -> Readback:
    """Fail closed on exact identity, length, digest, and canonical private ZIP.

    ``expected_artifact_id`` MUST be recorded independently from the artifact
    metadata being verified; simply accepting any positive ID permits substitution.
    ``independent_digest`` MUST be from a trusted expectation, not the ZIP or
    metadata supplied by the same untrusted source. A matching ZIP still does
    not authenticate pytest or source provenance.
    """
    try:
        if not isinstance(metadata, dict) or type(downloaded) is not bytes:
            return Readback('BLOCKED', 'ARTIFACT_INPUT_INVALID')
        if (type(expected_artifact_id) is not int or expected_artifact_id <= 0):
            return Readback('BLOCKED', 'EXPECTED_ARTIFACT_ID_INVALID')
        if (not isinstance(independent_digest, str)
                or not _SHA.fullmatch(independent_digest)):
            return Readback('BLOCKED', 'INDEPENDENT_DIGEST_MISSING')
        if (set(metadata) != {'id', 'name', 'size_in_bytes', 'expired',
                              'workflow_run', 'digest', 'state'}
                or type(metadata['id']) is not int
                or metadata['id'] != expected_artifact_id
                or metadata['name'] != _ARTIFACT_NAME
                or type(metadata['size_in_bytes']) is not int
                or metadata['size_in_bytes'] != len(downloaded)
                or metadata['size_in_bytes'] > 8192
                or metadata['expired'] is not False
                or metadata['state'] != 'completed'
                or type(metadata['workflow_run']) is not dict
                or set(metadata['workflow_run']) != {'id', 'head_sha'}
                or metadata['workflow_run']['id'] != expected.run_id
                or metadata['workflow_run']['head_sha'] != expected.controller_sha):
            return Readback('BLOCKED', 'ARTIFACT_METADATA_MISMATCH')
        actual = hashlib.sha256(downloaded).hexdigest()
        if (metadata['digest'] != 'sha256:' + actual
                or actual != independent_digest):
            return Readback('BLOCKED', 'ARTIFACT_DIGEST_MISMATCH')
        if not bundle.verify_sealed(downloaded, expected, verified_job_ids):
            return Readback('BLOCKED', 'ADVISORY_ARCHIVE_MISMATCH')
        return Readback('ADVISORY_ARTIFACT_READBACK_VERIFIED', sha256=actual)
    except (KeyError, ValueError, TypeError, AttributeError):
        return Readback('BLOCKED', 'ARTIFACT_METADATA_INVALID')
