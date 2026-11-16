"""Advisory-only GitHub run/job/artifact identity gate for a manual Stage 6 pilot.

Never imports or executes ROMarr source. No writes, dispatch, or receipt acceptance.
The job uses a read-only GitHub token provided only to the separate verifier.
"""
from __future__ import annotations

import json
import os
import re
import ssl
from urllib.error import HTTPError, URLError
from urllib.request import Request, build_opener, HTTPSHandler, HTTPRedirectHandler, ProxyHandler

REPO = 'TenchiMisaki/romarr-ci-controller'
API = f'https://api.github.com/repos/{REPO}/actions'
ARTIFACT_NAME = 'romarr-stage6-v26-advisory'
SOURCE_JOB = 'Run one real ROMarr test file in offline container'
EXPECTED_EVENT = 'workflow_dispatch'
MAX_JSON = 65_536


class _NoRedirect(HTTPRedirectHandler):
    def redirect_request(self, request, fp, code, msg, headers, newurl):
        return None


def bounded_json(response):
    """Require a bounded JSON body, not merely an HTTP success status."""
    declared = response.headers.get('Content-Length')
    if declared is not None and (not declared.isascii() or not declared.isdecimal()
                                 or int(declared) > MAX_JSON):
        raise ValueError('OVERSIZED_JSON')
    data = response.read(MAX_JSON + 1)
    if len(data) > MAX_JSON or (declared is not None and len(data) != int(declared)):
        raise ValueError('OVERSIZED_JSON')
    result = json.loads(data)
    if type(result) is not dict:
        raise ValueError('INVALID_JSON_SHAPE')
    return result


def fetch_snapshots(*, run_id: int, artifact_id: int, token: str, opener=None):
    """GET exact expected run, latest-attempt jobs, and artifact; no redirects."""
    if (type(run_id) is not int or run_id < 1 or type(artifact_id) is not int
            or artifact_id < 1 or type(token) is not str or not 1 <= len(token) <= 1024
            or any(ord(c) < 33 or ord(c) > 126 for c in token)):
        raise ValueError('INVALID_TRUSTED_INPUT')
    client = opener or build_opener(ProxyHandler({}), HTTPSHandler(
        context=ssl.create_default_context()), _NoRedirect())
    paths = (f'{API}/runs/{run_id}',
             f'{API}/runs/{run_id}/jobs?filter=latest&per_page=100',
             f'{API}/artifacts/{artifact_id}')
    results = []
    for url in paths:
        request = Request(url, headers={
            'Authorization': 'Bearer ' + token,
            'Accept': 'application/vnd.github+json',
            'X-GitHub-Api-Version': '2026-03-10',
            'User-Agent': 'romarr-stage6-v27-readonly'}, method='GET')
        try:
            with client.open(request, timeout=10) as response:
                if response.status != 200:
                    raise ValueError('HTTP_STATUS_INVALID')
                results.append(bounded_json(response))
        except (HTTPError, URLError, TimeoutError, OSError) as exc:
            raise ValueError('GITHUB_COLLECTION_FAILED') from None
    return tuple(results)


def attest(run: object, jobs: object, artifact: object, *, run_id: int,
           run_attempt: int, controller_sha: str, artifact_id: int,
           uploaded_digest: str) -> str:
    """Independently compare REST snapshots against the verifier's trusted context.

    The uploaded digest is only a consistency input; it is not independently
    established proof that downloaded bytes match metadata. Return advisory only.
    """
    if (type(run_id) is not int or run_id < 1 or type(run_attempt) is not int
            or run_attempt < 1 or type(artifact_id) is not int or artifact_id < 1
            or type(controller_sha) is not str
            or re.fullmatch('[0-9a-f]{40}', controller_sha) is None
            or type(uploaded_digest) is not str
            or re.fullmatch('[0-9a-f]{64}', uploaded_digest) is None):
        raise ValueError('INVALID_EXPECTATIONS')
    if not all(type(x) is dict for x in (run, jobs, artifact)):
        raise ValueError('INVALID_METADATA')
    if (type(run.get('id')) is not int or run['id'] != run_id
            or type(run.get('run_attempt')) is not int
            or run['run_attempt'] != run_attempt
            or run.get('head_sha') != controller_sha
            or run.get('event') != EXPECTED_EVENT
            or run.get('status') != 'in_progress'
            or run.get('conclusion') is not None
            or not isinstance(run.get('repository'), dict)
            or run['repository'].get('full_name') != REPO):
        raise ValueError('RUN_PROVENANCE_MISMATCH')
    job_list = jobs.get('jobs')
    if (type(jobs.get('total_count')) is not int
            or not isinstance(job_list, list)
            or not 1 <= len(job_list) <= 100
            or jobs['total_count'] != len(job_list)):
        raise ValueError('JOB_LIST_INCOMPLETE')
    sources = [j for j in job_list if type(j) is dict and j.get('name') == SOURCE_JOB]
    if len(sources) != 1:
        raise ValueError('SOURCE_JOB_AMBIGUOUS')
    source = sources[0]
    if (type(source.get('id')) is not int or source['id'] < 1
            or source.get('run_id') != run_id
            or source.get('run_attempt') != run_attempt
            or source.get('head_sha') != controller_sha
            or source.get('status') != 'completed'
            or source.get('conclusion') != 'success'):
        raise ValueError('SOURCE_JOB_NOT_VERIFIED')
    steps = source.get('steps')
    if (not isinstance(steps, list)
            or len(steps) < 2
            or sum(s.get('conclusion') == 'success' and
                   s.get('name') == 'Fetch immutable public ROMarr source and test without credentials'
                   for s in steps if isinstance(s, dict)) != 1
            or sum(s.get('conclusion') == 'success' and
                   s.get('name') == 'Upload only sanitized advisory and manifest'
                   for s in steps if isinstance(s, dict)) != 1):
        raise ValueError('REQUIRED_STEPS_NOT_VERIFIED')
    art_base = f'{API}/artifacts/{artifact_id}'
    linked = artifact.get('workflow_run')
    if (type(artifact.get('id')) is not int or artifact['id'] != artifact_id
            or artifact.get('name') != ARTIFACT_NAME
            or artifact.get('expired') is not False
            or type(artifact.get('size_in_bytes')) is not int
            or not 1 <= artifact['size_in_bytes'] <= 16 * 1024 * 1024
            or artifact.get('digest') != 'sha256:' + uploaded_digest
            or artifact.get('url') != art_base
            or artifact.get('archive_download_url') != art_base + '/zip'
            or type(linked) is not dict or linked.get('id') != run_id
            or linked.get('head_sha') != controller_sha):
        raise ValueError('ARTIFACT_PROVENANCE_MISMATCH')
    return 'GITHUB_API_ADVISORY_PROVENANCE_VERIFIED'


def main():
    """Run only in the authenticated, isolated verifier job."""
    try:
        run_id = int(os.environ['EXPECTED_RUN_ID'])
        attempt = int(os.environ['EXPECTED_RUN_ATTEMPT'])
        artifact_id = int(os.environ['EXPECTED_ARTIFACT_ID'])
        sha = os.environ['EXPECTED_CONTROLLER_SHA']
        digest = os.environ['UPLOADED_ARTIFACT_DIGEST']
        token = os.environ['GITHUB_TOKEN']
        run, jobs, artifact = fetch_snapshots(run_id=run_id,
                                              artifact_id=artifact_id, token=token)
        print(attest(run, jobs, artifact, run_id=run_id,
                     run_attempt=attempt, controller_sha=sha,
                     artifact_id=artifact_id, uploaded_digest=digest))
        print('DOWNLOADED_BYTES_INDEPENDENTLY_VERIFIED: false')
        print('TEST_ACCEPTED: false')
        print('PUBLICATION_AUTHORIZED: false')
        print('UNATTENDED_DISPATCH_ENABLED: false')
    except (KeyError, ValueError, TypeError, json.JSONDecodeError) as exc:
        # Never expose token, signed URL, or untrusted GitHub response.
        print('BLOCKED: authenticated GitHub artifact provenance unavailable')
        raise SystemExit(1) from None


if __name__ == '__main__':
    main()
