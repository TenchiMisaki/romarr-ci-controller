"""Offline-only tests of manual-only entrypoint and guarded expectations."""
from dataclasses import replace
import pytest

from stage6_pr_identity_v32 import IdentityRejected
from stage6_pr_entrypoint_v39 import (
    ARTIFACT_NAME, CONTROLLER, SOURCE_JOB, SOURCE_STEP, WORKFLOW,
    prepare_manual_evidence, run_manual,
)

SHA = 'a'*40
HEAD = 'b'*40
BASE = 'c'*40
DIGEST = 'd'*64

def env():
    return {
        'GITHUB_ACTIONS': 'true', 'GITHUB_REPOSITORY': CONTROLLER,
        'GITHUB_EVENT_NAME': 'workflow_dispatch', 'GITHUB_REF': 'refs/heads/main',
        'GITHUB_WORKFLOW_REF': CONTROLLER + '/' + WORKFLOW + '@refs/heads/main',
        'GITHUB_SHA': SHA, 'GITHUB_RUN_ID': '1234', 'GITHUB_RUN_ATTEMPT': '1',
        'EXPECTED_CONTROLLER_SHA': SHA, 'EXPECTED_RUN_ID': '1234',
        'EXPECTED_RUN_ATTEMPT': '1', 'EXPECTED_PR_NUMBER': '29',
        'EXPECTED_PR_HEAD_SHA': HEAD, 'EXPECTED_PR_BASE_SHA': BASE,
        'EXPECTED_ARTIFACT_ID': '5678', 'EXPECTED_ARTIFACT_SHA256': DIGEST,
        'GITHUB_TOKEN': 'test-fixture-token',
    }

def test_exact_expected_evidence_is_advisory_only():
    e = prepare_manual_evidence(env())
    assert e.source_sha == HEAD
    assert e.expected.pr.base_sha == BASE
    assert e.expected.controller_sha == SHA
    assert e.expected.workflow_path == WORKFLOW
    assert e.expected.source_job_name == SOURCE_JOB
    assert e.expected.required_source_steps == (SOURCE_STEP,)
    assert e.expected.artifact_name == ARTIFACT_NAME

@pytest.mark.parametrize(('key','bad'), [
    ('GITHUB_ACTIONS','false'), ('GITHUB_REPOSITORY','other/repo'),
    ('GITHUB_EVENT_NAME','schedule'), ('GITHUB_EVENT_NAME','pull_request'),
    ('GITHUB_REF','refs/heads/feature'),
    ('GITHUB_WORKFLOW_REF',CONTROLLER+'/'+WORKFLOW+'@refs/heads/feature'),
    ('GITHUB_WORKFLOW_REF','other/repo/'+WORKFLOW+'@refs/heads/main'),
    ('GITHUB_SHA','f'*40), ('EXPECTED_CONTROLLER_SHA','f'*40),
    ('GITHUB_RUN_ID','9999'), ('EXPECTED_RUN_ID','9999'),
    ('GITHUB_RUN_ATTEMPT','2'), ('EXPECTED_RUN_ATTEMPT','2'),
    ('EXPECTED_PR_NUMBER','0'), ('EXPECTED_PR_NUMBER','-9'),
    ('EXPECTED_PR_HEAD_SHA','bad'), ('EXPECTED_PR_BASE_SHA','wrong'),
    ('EXPECTED_ARTIFACT_ID','0'), ('EXPECTED_ARTIFACT_SHA256','x'*64),
])
def test_mismatched_or_invalid_env_is_rejected(key,bad):
    data=env();data[key]=bad
    with pytest.raises(IdentityRejected): prepare_manual_evidence(data)

def test_missing_values_fail_before_network():
    calls=[]
    def factory(token):
        calls.append(token)
        raise AssertionError('must not be called')
    for key in env():
        data=env();data.pop(key)
        if key=='GITHUB_TOKEN':
            assert run_manual(data, transport_factory=factory).state == 'BLOCKED'
        else:
            with pytest.raises(IdentityRejected): prepare_manual_evidence(data)
    assert not calls

class FakeTransport:
    def __init__(self,token):
        self.token=token
    def get_json(self,url):
        raise ValueError('synthetic test expected failure')
    def get_artifact_bytes(self,*args):
        raise AssertionError('not reachable')

def test_transport_failure_reports_only_sanitized_block():
    result=run_manual(env(),transport_factory=FakeTransport)
    assert result.state=='BLOCKED'
    assert result.reason=='COLLECTION_NOT_VERIFIED'
    assert result.test_accepted is False
    assert result.publication_authorized is False
    assert result.unattended_dispatch_enabled is False

def test_bad_token_rejected_no_exception_details():
    e=env();e['GITHUB_TOKEN']=' '
    assert run_manual(e).state=='BLOCKED'


def test_success_marker_only_when_collector_reports_advisory(monkeypatch):
    import stage6_pr_entrypoint_v39 as module
    class Result:
        state='ADVISORY_COLLECTED_NOT_TEST_ACCEPTED'
    calls=[]
    def collector(**kwargs):
        calls.append(kwargs)
        return Result()
    monkeypatch.setattr(module,'collect_ordered',collector)
    class Transport:
        def __init__(self,token):
            assert token=='test-fixture-token'
        def get_json(self,url): return {}
        def get_artifact_bytes(self,*args): return b''
    result=run_manual(env(),transport_factory=Transport)
    assert result.state=='ADVISORY_COLLECTED_NOT_TEST_ACCEPTED'
    assert not result.test_accepted
    assert len(calls)==1
    assert calls[0]['evidence'].expected.pr.head_sha==HEAD

def test_entrypoint_full_offline_collection_through_existing_v37_validator():
    """Run entrypoint -> ordered collector -> metadata/bytes/freshness end-to-end."""
    import copy
    from test_stage6_pr_collector_v37 import harness
    evidence, _, _, _, ordered = harness()
    exp = evidence.expected
    # Rebind synthetic workflow/job names to the proposed v39 contract.
    data = env()
    data.update({
        'GITHUB_SHA':exp.controller_sha,'EXPECTED_CONTROLLER_SHA':exp.controller_sha,
        'GITHUB_RUN_ID':str(exp.run_id),'EXPECTED_RUN_ID':str(exp.run_id),
        'GITHUB_RUN_ATTEMPT':str(exp.run_attempt),
        'EXPECTED_RUN_ATTEMPT':str(exp.run_attempt),
        'EXPECTED_PR_NUMBER':str(exp.pr.pr_number),
        'EXPECTED_PR_HEAD_SHA':exp.pr.head_sha,
        'EXPECTED_PR_BASE_SHA':exp.pr.base_sha,
        'EXPECTED_ARTIFACT_ID':str(exp.artifact_id),
        'EXPECTED_ARTIFACT_SHA256':exp.artifact_sha256,
    })
    responses=copy.deepcopy(ordered)
    responses[2][1]['path']=WORKFLOW
    responses[3][1]['jobs'][0]['name']=SOURCE_JOB
    responses[3][1]['jobs'][0]['steps'][0]['name']=SOURCE_STEP
    class Adapter:
        def __init__(self,token):
            assert token=='test-fixture-token'
            self.position=0
        def get_json(self,url):
            at=self.position;self.position+=1
            assert responses[at][0]==url and at != 7
            return copy.deepcopy(responses[at][1])
        def get_artifact_bytes(self,url,limit,digest):
            at=self.position;self.position+=1
            assert at==7 and responses[at][0]==url
            assert limit==exp.max_archive_bytes and digest==exp.artifact_sha256
            return responses[at][1]
    result=run_manual(data,transport_factory=Adapter)
    assert result.state=='ADVISORY_COLLECTED_NOT_TEST_ACCEPTED'
    assert not result.test_accepted
