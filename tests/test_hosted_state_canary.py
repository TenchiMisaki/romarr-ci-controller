"""Manual candidate with real disposable Git; no credentials/network or live refs."""
import copy
import io
import json
import os
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch
from urllib.error import HTTPError

from controller_cycle import initial_state
from durable_state import PREFIX, STATE_REF, StateBlocked, encode
from hosted_state_canary import (APPROVAL, CanaryAPI, CanaryConflict, Wire, context, exercise, main)
from test_git_state_integration import LocalGitAPI

REF='heads/controller-canary-123-1'


class FixtureWire:
    """Real bare-Git objects behind an explicit modeled GitHub canary boundary."""
    def __init__(self,root):
        self.git=LocalGitAPI(root)
        self.exists=False
        self.calls=[]
        self.denied=False
    def __call__(self,method,path,body=None):
        self.calls.append((method,path,copy.deepcopy(body)))
        if method=='GET' and path==PREFIX+'git/matching-refs/'+REF:
            return [dict(ref='refs/'+REF)] if self.exists else []
        if method=='POST' and path==PREFIX+'git/refs':
            if self.exists:raise StateBlocked('EXISTING_REF')
            if body['ref']!='refs/'+REF:raise AssertionError('Foreign ref')
            self.git.run('update-ref','refs/'+STATE_REF,body['sha'])
            self.exists=True
            return dict(ref='refs/'+REF,object=dict(type='commit',sha=body['sha']))
        if path in {PREFIX+'git/ref/'+REF,PREFIX+'git/refs/'+REF}:
            if method=='PATCH' and self.denied:raise StateBlocked('AUTH_OR_OTHER_FAILURE')
            old=path
            path=path.replace(REF,STATE_REF)
            try: row=self.git.request(method,path,body)
            except StateBlocked as error:
                if str(error)=='FIXTURE_NON_FAST_FORWARD':raise CanaryConflict('CONFLICT') from None
                raise
            if old.endswith('/'+REF) and method=='GET':row['ref']='refs/'+REF
            return row
        return self.git.request(method,path,body)


class CanaryTests(unittest.TestCase):
    """Meaningful exclusivity, uncertainty and target-refusal checks."""
    def setUp(self):
        self.temp=tempfile.TemporaryDirectory();self.addCleanup(self.temp.cleanup)
        self.wire=FixtureWire(self.temp.name)
        self.api=CanaryAPI(self.wire,REF)
        self.controller=self.wire.git.head()

    def test_seed_race_and_fresh_client_lost_response_observation(self):
        seed=self.api.seed(self.controller)
        result=exercise(self.api)
        self.assertEqual(result['seed'],seed)
        self.assertEqual(result['successes'],1)
        self.assertEqual(result['state'],'CANARY_OBSERVATIONS_PASS')
        self.assertTrue(result['simulated_lost_response'])
        self.assertFalse(result['policy_enabled'])
        self.assertFalse(result['source_dispatch_allowed'])
        self.assertEqual(self.wire.git.oid('rev-parse',result['final']+'^'),result['winner'])
        self.assertEqual(self.wire.git.oid('rev-parse',result['winner']+'^'),seed)
        self.wire.git.run('fsck','--strict','--no-reflogs')
        self.assertEqual(self.wire.git.run('cat-file','blob',result['final']+':state.json').stdout,encode(initial_state()))
        for method,path,body in self.wire.calls:
            if method=='PATCH':
                self.assertEqual(path,PREFIX+'git/refs/'+REF)
                self.assertIs(body['force'],False)
            self.assertNotIn('/actions/',path)

    def test_real_timeout_after_successful_patch_is_not_simulated_loss(self):
        self.api.seed(self.controller)
        original=self.wire
        def timeout_after_success(method,path,body=None):
            row=original(method,path,body)
            if method=='PATCH' and self.api.drop_response:
                raise TimeoutError('private transport failure')
            return row
        self.api.wire=timeout_after_success
        with self.assertRaises(TimeoutError):exercise(self.api)
        self.assertTrue(self.api.drop_response)

    def test_final_operational_read_failure_cannot_report_pass(self):
        class API:
            def __init__(self,*args):self.reads=0
            def _call(self,method,path):
                if not path:return dict(id=1458032121,owner=dict(id=71314201),
                    private=False,archived=False,disabled=False)
                self.reads+=1
                if self.reads==2:raise TimeoutError('private transport failure')
                return dict(ref='refs/'+STATE_REF)
            def seed(self,sha):pass
        with patch.dict(os.environ,dict(RUNNER_TEMP=self.temp.name,GITHUB_SHA='a'*40)), \
                patch('hosted_state_canary.context',return_value=REF), \
                patch('hosted_state_canary.Wire'), \
                patch('hosted_state_canary.CanaryAPI',API), \
                patch('hosted_state_canary.exercise',return_value=dict(
                    schema=1,state='CANARY_OBSERVATIONS_PASS',ref=REF)), \
                patch('sys.stdout',new_callable=io.StringIO) as output:
            self.assertEqual(main(),1)
        report=json.loads((Path(self.temp.name)/'controller-canary-summary.json').read_text())
        self.assertEqual(report['state'],'BLOCKED_OR_UNCERTAIN')
        self.assertEqual(report['phase'],'OPERATIONAL_READBACK')
        self.assertNotIn('private transport failure',output.getvalue())

    def test_existing_canary_is_never_reinitialized(self):
        self.api.seed(self.controller);before=len(self.wire.calls)
        head=self.wire.git.head()
        with self.assertRaisesRegex(StateBlocked,'EXISTING_REF_PRESERVED'):
            self.api.seed(self.controller)
        self.assertEqual(self.wire.git.head(),head)
        self.assertEqual([m for m,_,_ in self.wire.calls[before:]],['GET'])

    def test_non_conflict_failures_cannot_count_as_expected_race_losers(self):
        self.api.seed(self.controller);self.wire.denied=True
        with self.assertRaises(StateBlocked):exercise(self.api)

    def test_duplicate_commit_negative_control_is_not_an_exclusive_race(self):
        self.api.seed(self.controller)
        with patch('durable_state.uuid.uuid4') as nonce:
            nonce.return_value.hex='0'*32
            with self.assertRaisesRegex(StateBlocked,'CANARY_RACE_NOT_EXCLUSIVE'):
                exercise(self.api)

    def test_force_delete_foreign_operational_and_dispatch_targets_rejected(self):
        for method,path,body in [('DELETE',PREFIX+'git/refs/'+STATE_REF,None),
                ('POST',PREFIX+'actions/workflows/source.yml/dispatches',{}),
                ('PATCH',PREFIX+'git/refs/'+REF,{'sha':'a'*40,'force':False}),
                ('PATCH',PREFIX+'git/refs/'+STATE_REF,{'sha':'a'*40,'force':True}),
                ('GET','repos/foreign/repo/git/ref/'+STATE_REF,None)]:
            with self.subTest(method=method,path=path),self.assertRaises(StateBlocked):
                self.api.request(method,path,body)
        self.assertEqual(self.wire.calls,[])
        for ref in ('heads/controller-state-v1','tags/controller-revision-'+'a'*40,REF+'\n'):
            with self.assertRaises(StateBlocked):CanaryAPI(self.wire,ref)

    def test_only_canonical_disabled_bytes_and_sole_state_tree_allowed(self):
        import base64
        state=initial_state();state['policy']['enabled']=True
        for body in ({'encoding':'base64','content':base64.b64encode(encode(state)).decode()},
                     {'encoding':'base64','content':base64.b64encode(b'private').decode()}):
            with self.assertRaises(StateBlocked):self.api.request('POST',PREFIX+'git/blobs',body)
        with self.assertRaises(StateBlocked):self.api.request('POST',PREFIX+'git/trees',{'tree':[]})
        self.assertEqual(self.wire.calls,[])

    def test_manual_host_exact_pin_owner_and_approval_gates(self):
        env=dict(GITHUB_REPOSITORY='TenchiMisaki/romarr-ci-controller',GITHUB_REPOSITORY_ID='1458032121',
            GITHUB_ACTOR_ID='71314201',GITHUB_TRIGGERING_ACTOR='TenchiMisaki',GITHUB_EVENT_NAME='workflow_dispatch',
            GITHUB_REF='refs/heads/main',RUNNER_ENVIRONMENT='github-hosted',RUNNER_OS='Linux',
            CANARY_APPROVAL=APPROVAL,GITHUB_SHA='a'*40,EXPECTED_CONTROLLER_SHA='a'*40,
            GITHUB_RUN_ID='123',GITHUB_RUN_ATTEMPT='1')
        self.assertEqual(context(env),REF)
        for key in env:
            changed=dict(env);changed[key]='wrong'
            with self.subTest(key=key),self.assertRaises(StateBlocked):context(changed)

    def test_http_only_exact_non_fast_forward_422_is_a_conflict(self):
        for status,message,kind in [(422,'Update is not a fast forward',CanaryConflict),
                (403,'private',StateBlocked),(422,'Validation Failed',StateBlocked),
                (500,'private',StateBlocked)]:
            for method in ('PATCH','POST'):
                calls=[]
                class Opener:
                    def open(self,req,timeout):
                        calls.append(req)
                        raise HTTPError(req.full_url,status,'private',{},io.BytesIO(json.dumps(dict(message=message)).encode()))
                with patch('hosted_state_canary.build_opener',return_value=Opener()):
                    with self.assertRaises(StateBlocked) as caught:
                        Wire('synthetic-fixture')(method,PREFIX+'git/refs/'+REF,dict(sha='a'*40,force=False))
                    self.assertEqual(isinstance(caught.exception,CanaryConflict),kind is CanaryConflict and method=='PATCH')
                    self.assertNotIn('private',str(caught.exception))
                self.assertEqual(len(calls),1)


if __name__=='__main__':unittest.main()
