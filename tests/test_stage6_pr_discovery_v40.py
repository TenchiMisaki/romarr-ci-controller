"""Offline-only strict run-scoped artifact selection and integration tests."""
import copy
import pytest
from stage6_pr_discovery_v40 import (DiscoveryTransport, listing_url,
    run_discovered_manual, select_artifact)
from stage6_pr_identity_v32 import IdentityRejected
from stage6_pr_entrypoint_v39 import ARTIFACT_NAME
from test_stage6_pr_entrypoint_v39 import env, SHA

ID=5678
RUN=1234
DIGEST='d'*64
BASE=f'https://api.github.com/repos/TenchiMisaki/romarr-ci-controller/actions/artifacts/{ID}'

def artifact():
    return {'id':ID,'name':ARTIFACT_NAME,'expired':False,'digest':'sha256:'+DIGEST,
            'size_in_bytes':350,'url':BASE,'archive_download_url':BASE+'/zip',
            'workflow_run':{'id':RUN,'head_sha':SHA,'head_branch':'main'}}

def listing(): return {'total_count':1,'artifacts':[artifact()]}

def test_exact_run_scoped_url():
    assert listing_url(RUN)=='https://api.github.com/repos/TenchiMisaki/romarr-ci-controller/actions/runs/1234/artifacts?per_page=100&page=1'

@pytest.mark.parametrize('n',[False,0,-1,10**19,1.2,'1234'])
def test_invalid_run_id(n):
    with pytest.raises(IdentityRejected): listing_url(n)

def test_valid_complete_listing():
    assert select_artifact(listing(),run_id=RUN,attempt=1,controller_sha=SHA)==(ID,DIGEST)

@pytest.mark.parametrize('mutate',[
    lambda x:x.update(total_count=2),
    lambda x:x['artifacts'].append(copy.deepcopy(x['artifacts'][0])),
    lambda x:x['artifacts'][0].update(expired=True),
    lambda x:x['artifacts'][0].update(digest='sha256:bad'),
    lambda x:x['artifacts'][0].update(size_in_bytes=0),
    lambda x:x['artifacts'][0].update(size_in_bytes=65537),
    lambda x:x['artifacts'][0].update(url='https://example.com/'),
    lambda x:x['artifacts'][0].update(archive_download_url='https://example.com/'),
    lambda x:x['artifacts'][0]['workflow_run'].update(id=5000),
    lambda x:x['artifacts'][0]['workflow_run'].update(head_sha='b'*40),
    lambda x:x['artifacts'][0]['workflow_run'].update(head_branch='other'),
    lambda x:x['artifacts'][0].update(name='wrong'),
    lambda x:x['artifacts'][0].update(id=0),
])
def test_invalid_listing_is_blocked(mutate):
    x=listing();mutate(x)
    with pytest.raises(IdentityRejected):select_artifact(x,run_id=RUN,attempt=1,controller_sha=SHA)

@pytest.mark.parametrize('listing_data',[{},None,{'total_count':0,'artifacts':[]},
    {'total_count':101,'artifacts':[artifact()]*101},{'total_count':True,'artifacts':[artifact()]}])
def test_incomplete_listing_rejected(listing_data):
    with pytest.raises(IdentityRejected):select_artifact(listing_data,run_id=RUN,attempt=1,controller_sha=SHA)

def test_retry_attempt_is_fail_closed():
    with pytest.raises(IdentityRejected,match='RUN_ATTEMPT_UNSUPPORTED'):
        select_artifact(listing(),run_id=RUN,attempt=2,controller_sha=SHA)

@pytest.mark.parametrize('field',["EXPECTED_ARTIFACT_ID","EXPECTED_ARTIFACT_SHA256"])
def test_pre_supplied_producer_claim_is_refused(field):
    d=env();d.pop('EXPECTED_ARTIFACT_ID');d.pop('EXPECTED_ARTIFACT_SHA256');d[field]='false-producer-claim'
    assert run_discovered_manual(d,transport_factory=lambda _: (_ for _ in ()).throw(AssertionError('network touched'))).state=='BLOCKED'


def test_bad_workflow_identity_blocks_before_api():
    d=env();d.pop('EXPECTED_ARTIFACT_ID');d.pop('EXPECTED_ARTIFACT_SHA256');d['GITHUB_REF']='refs/heads/other'
    calls=[]
    def factory(token): calls.append(token);return None
    assert run_discovered_manual(d,transport_factory=factory).state=='BLOCKED'
    assert calls==[]


def test_transport_listing_never_calls_ambient_url(monkeypatch):
    import stage6_pr_discovery_v40 as m
    calls=[]
    def fake_get(opener,url,token,**kw):
        calls.append((url,token,kw));return b'{"artifacts":[],"total_count":0}'
    monkeypatch.setattr(m,'_get',fake_get)
    t=DiscoveryTransport('fixture-token',opener=object())
    assert t.list_run_artifacts(1234)=={'artifacts':[],'total_count':0}
    assert calls[0][0]==listing_url(1234)
    assert calls[0][1]=='fixture-token'
    assert calls[0][2]['expected_status']==200


def test_discovery_then_v39_collection_succeeds_with_synthetic_full_harness():
    from test_stage6_pr_collector_v37 import harness
    from stage6_pr_entrypoint_v39 import SOURCE_JOB,SOURCE_STEP,WORKFLOW
    evidence,_,_,_,ordered=harness()
    exp=evidence.expected
    e=env()
    e.update({'GITHUB_SHA':exp.controller_sha,'EXPECTED_CONTROLLER_SHA':exp.controller_sha,
              'GITHUB_RUN_ID':str(exp.run_id),'EXPECTED_RUN_ID':str(exp.run_id),
              'GITHUB_RUN_ATTEMPT':str(exp.run_attempt),'EXPECTED_RUN_ATTEMPT':str(exp.run_attempt),
              'EXPECTED_PR_NUMBER':str(exp.pr.pr_number),
              'EXPECTED_PR_HEAD_SHA':exp.pr.head_sha,
              'EXPECTED_PR_BASE_SHA':exp.pr.base_sha})
    e.pop('EXPECTED_ARTIFACT_ID');e.pop('EXPECTED_ARTIFACT_SHA256')
    responses=copy.deepcopy(ordered)
    responses[2][1]['path']=WORKFLOW
    responses[3][1]['jobs'][0]['name']=SOURCE_JOB
    responses[3][1]['jobs'][0]['steps'][0]['name']=SOURCE_STEP
    a=copy.deepcopy(responses[4][1]);a['name']=ARTIFACT_NAME
    class FakeTransport:
        def __init__(self,token):
            assert token=='test-fixture-token'
            self.position=0
        def list_run_artifacts(self,run_id):
            assert run_id==exp.run_id
            return {'total_count':1,'artifacts':[copy.deepcopy(a)]}
        def get_json(self,url):
            pos=self.position;self.position+=1
            assert pos!=7 and responses[pos][0]==url
            return copy.deepcopy(responses[pos][1])
        def get_artifact_bytes(self,url,max_bytes,digest):
            pos=self.position;self.position+=1
            assert pos==7 and responses[pos][0]==url and digest==exp.artifact_sha256
            return responses[pos][1]
    # The harness source artifact name must be changed on the individual metadata fetch.
    responses[4][1]['name']=ARTIFACT_NAME
    result=run_discovered_manual(e,transport_factory=FakeTransport)
    assert result.state=='ADVISORY_COLLECTED_NOT_TEST_ACCEPTED'
    assert result.artifact_id==exp.artifact_id
    assert result.artifact_sha256==exp.artifact_sha256
    assert result.test_accepted is False
    assert result.publication_authorized is False
    assert result.unattended_dispatch_enabled is False


def test_discovery_ambiguous_no_followup_reads():
    data=env();data.pop('EXPECTED_ARTIFACT_ID');data.pop('EXPECTED_ARTIFACT_SHA256')
    class Fake:
        def __init__(self,token):pass
        def list_run_artifacts(self,run_id):return {'total_count':2,'artifacts':[artifact(),artifact()]}
        def get_json(self,url):raise AssertionError('should not call')
    result=run_discovered_manual(data,transport_factory=Fake)
    assert result.state=='BLOCKED'
    assert result.artifact_id==0
