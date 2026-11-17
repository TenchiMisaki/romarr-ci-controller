"""Synthetic positive/negative tests: no API calls, no untrusted execution."""
import copy
import pytest
from stage6_pr_identity_v32 import ExactPR, IdentityRejected
from stage6_pr_receipt_v33 import ExpectedArtifact, verify_metadata

H, B, C, D = (c * n for c, n in [('a', 40), ('b', 40), ('c', 40), ('d', 64)])
RUN, ART = 123, 456
PATH = '.github/workflows/stage6-pr-isolated-CANDIDATE.yml'
NAME = 'romarr-stage6-pr-advisory'
SOURCE = 'Untrusted source test job'
STEP = 'Run pinned ROMarr tests offline'
REPO = 'TenchiMisaki/romarr'
CONTROLLER = 'TenchiMisaki/romarr-ci-controller'


def expected():
    return ExpectedArtifact(ExactPR(29, H, B), C, PATH, RUN, 1, SOURCE, (STEP,), ART, NAME, D)


def sample():
    pr = {'number': 29, 'state': 'open', 'merged': False, 'draft': False,
          'html_url': f'https://github.com/{REPO}/pull/29',
          'head': {'repo': {'full_name': REPO}, 'sha': H},
          'base': {'repo': {'full_name': REPO}, 'sha': B}}
    run = {'id': RUN, 'run_attempt': 1, 'head_sha': C,
           'repository': {'full_name': CONTROLLER}, 'path': PATH,
           'event': 'workflow_dispatch', 'status': 'completed', 'conclusion': 'success'}
    jobs = {'total_count': 1, 'jobs': [{'id': 789, 'name': SOURCE,
            'run_id': RUN, 'run_attempt': 1, 'head_sha': C,
            'head_branch': 'main', 'run_url': f'https://api.github.com/repos/{CONTROLLER}/actions/runs/{RUN}',
            'status': 'completed', 'conclusion': 'success',
            'steps': [{'name': STEP, 'status': 'completed', 'conclusion': 'success'}]}]}
    url = f'https://api.github.com/repos/{CONTROLLER}/actions/artifacts/{ART}'
    artifact = {'id': ART, 'name': NAME, 'expired': False, 'size_in_bytes': 681,
                'digest': f'sha256:{D}', 'url': url,
                'archive_download_url': url + '/zip',
                'workflow_run': {'id': RUN, 'head_sha': C, 'head_branch': 'main'}}
    return {'before': copy.deepcopy(pr), 'after': copy.deepcopy(pr),
            'run': run, 'jobs': jobs, 'artifact': artifact, 'expected': expected()}


def reject(data):
    with pytest.raises(IdentityRejected):
        verify_metadata(**data)


def test_metadata_positive_is_not_receipt_acceptance():
    assert verify_metadata(**sample()) == 'UNTRUSTED_ARTIFACT_METADATA_IDENTIFIED'


@pytest.mark.parametrize('change', ['head', 'base', 'draft', 'closed', 'foreign_head'])
def test_changed_pr_rejected(change):
    d = sample(); p = d['after']
    if change in {'head', 'base'}: p[change]['sha'] = 'f' * 40
    elif change == 'draft': p['draft'] = True
    elif change == 'closed': p['state'] = 'closed'
    else: p['head']['repo']['full_name'] = 'BlizzHacker/romarr'
    reject(d)


@pytest.mark.parametrize('change', ['run_id', 'attempt', 'sha', 'event', 'status', 'workflow'])
def test_wrong_run_rejected(change):
    d = sample(); r = d['run']
    key, val = {'run_id': ('id', 124), 'attempt': ('run_attempt', 2),
                'sha': ('head_sha', 'f' * 40), 'event': ('event', 'push'),
                'status': ('status', 'in_progress'),
                'workflow': ('path', '.github/workflows/other.yml')}[change]
    r[key] = val
    reject(d)


@pytest.mark.parametrize('change', ['empty', 'partial', 'duplicate', 'wrong_run', 'wrong_attempt',
                                    'wrong_sha', 'wrong_run_url', 'wrong_branch', 'failed', 'missing_step', 'skipped_step', 'summary_missing_fields'])
def test_source_job_fault_rejected(change):
    d = sample(); jobs = d['jobs']; j = jobs['jobs'][0]
    if change == 'empty': jobs['jobs'] = []; jobs['total_count'] = 0
    elif change == 'partial': jobs['total_count'] = 2
    elif change == 'duplicate': jobs['jobs'].append(copy.deepcopy(j)); jobs['total_count'] = 2
    elif change == 'wrong_run': j['run_id'] = 124
    elif change == 'wrong_attempt': j['run_attempt'] = 2
    elif change == 'wrong_sha': j['head_sha'] = 'f' * 40
    elif change == 'wrong_run_url': j['run_url'] = 'https://evil.invalid/runs/123'
    elif change == 'wrong_branch': j['head_branch'] = 'feature'
    elif change == 'summary_missing_fields':
        j.pop('head_sha'); j.pop('run_attempt')
    elif change == 'failed': j['conclusion'] = 'failure'
    elif change == 'missing_step': j['steps'] = []
    elif change == 'skipped_step': j['steps'][0]['conclusion'] = 'skipped'
    reject(d)


@pytest.mark.parametrize('change', ['id', 'name', 'expired', 'digest', 'size', 'oversize',
                                    'url', 'archive_url', 'run_id', 'head_sha', 'branch'])
def test_artifact_fault_rejected(change):
    d = sample(); a = d['artifact']
    if change == 'id': a['id'] = 457
    elif change == 'name': a['name'] = 'wrong-name'
    elif change == 'expired': a['expired'] = True
    elif change == 'digest': a['digest'] = 'sha256:' + 'f' * 64
    elif change == 'size': a['size_in_bytes'] = True
    elif change == 'oversize': a['size_in_bytes'] = 65537
    elif change == 'url': a['url'] += '/evil'
    elif change == 'archive_url': a['archive_download_url'] = 'https://evil.invalid/artifact'
    elif change == 'run_id': a['workflow_run']['id'] = RUN + 1
    elif change == 'head_sha': a['workflow_run']['head_sha'] = 'f' * 40
    elif change == 'branch': a['workflow_run']['head_branch'] = 'dev'
    reject(d)


@pytest.mark.parametrize('change', ['sha', 'job_name', 'step_duplicates', 'digest', 'max_bytes',
                                    'invalid_workflow'])
def test_invalid_expectation_rejected(change):
    kw = dict(pr=ExactPR(29, H, B), controller_sha=C, workflow_path=PATH,
              run_id=RUN, run_attempt=1, source_job_name=SOURCE,
              required_source_steps=(STEP,), artifact_id=ART,
              artifact_name=NAME, artifact_sha256=D)
    if change == 'sha': kw['controller_sha'] = 'no'
    elif change == 'job_name': kw['source_job_name'] = ''
    elif change == 'step_duplicates': kw['required_source_steps'] = (STEP, STEP)
    elif change == 'digest': kw['artifact_sha256'] = 'bad'
    elif change == 'max_bytes': kw['max_archive_bytes'] = 0
    elif change == 'invalid_workflow': kw['workflow_path'] = '.github/workflows/../bad.yml'
    with pytest.raises(IdentityRejected): ExpectedArtifact(**kw)


def test_complete_rest_job_collection_may_include_separate_verifier():
    d = sample()
    d['jobs']['jobs'].append({'id': 790, 'name': 'Independent verifier',
                               'run_id': RUN, 'run_attempt': 1, 'head_sha': C,
                               'status': 'completed', 'conclusion': 'success'})
    d['jobs']['total_count'] = 2
    assert verify_metadata(**d) == 'UNTRUSTED_ARTIFACT_METADATA_IDENTIFIED'


def test_active_workflow_with_completed_source_job_is_advisory_metadata_only():
    d = sample()
    d['run']['status'] = 'in_progress'
    d['run']['conclusion'] = None
    assert verify_metadata(**d) == 'UNTRUSTED_ARTIFACT_METADATA_IDENTIFIED'


def test_active_workflow_with_failed_source_job_stays_blocked():
    d = sample()
    d['run']['status'] = 'in_progress'
    d['run']['conclusion'] = None
    d['jobs']['jobs'][0]['conclusion'] = 'failure'
    reject(d)
