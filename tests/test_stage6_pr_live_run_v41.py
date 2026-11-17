"""Negative and positive invariants for manual in-progress advisory verification."""
import copy
import pytest
from stage6_pr_identity_v32 import IdentityRejected
from stage6_pr_live_run_v41 import verify_advisory_run

SHA='a'*40
PATH='.github/workflows/stage6-pr-manual-candidate.yml'
RUN={'repository':{'full_name':'TenchiMisaki/romarr-ci-controller'},
     'id':123, 'run_attempt':1, 'head_sha':SHA, 'path':PATH,
     'event':'workflow_dispatch', 'status':'in_progress','conclusion':None}

def check(x):
    return verify_advisory_run(x,controller_sha=SHA,run_id=123,
                               attempt=1,workflow_path=PATH)

def test_active_verifier_is_advisory_only():
    z=check(copy.deepcopy(RUN))
    assert z.state=='ACTIVE_VERIFIER_NOT_TEST_ACCEPTED'
    assert (z.test_accepted,z.publication_authorized,z.unattended_dispatch_enabled)==(False,False,False)

def test_completed_success_is_still_advisory_only():
    x=dict(RUN,status='completed',conclusion='success')
    z=check(x)
    assert z.state=='COMPLETED_RUN_ADVISORY_ONLY' and not z.test_accepted

@pytest.mark.parametrize('status,conclusion',[
    ('queued',None),('waiting',None),('in_progress','success'),
    ('in_progress','failure'),('completed',None),('completed','failure'),
    ('completed','cancelled'),('completed','skipped'),('unknown',None)])
def test_other_states_rejected(status,conclusion):
    with pytest.raises(IdentityRejected): check(dict(RUN,status=status,conclusion=conclusion))

@pytest.mark.parametrize('key,value',[
    ('id',124),('run_attempt',2),('head_sha','b'*40),
    ('path','.github/workflows/other.yml'),('event','schedule'),
    ('repository',{'full_name':'other/repo'})])
def test_active_run_mismatched_identity_rejected(key,value):
    with pytest.raises(IdentityRejected): check(dict(RUN,**{key:value}))

def test_does_not_mutate_input():
    x=copy.deepcopy(RUN)
    check(x)
    assert x==RUN

def test_invalid_shape_rejected():
    with pytest.raises(IdentityRejected): check(None)
