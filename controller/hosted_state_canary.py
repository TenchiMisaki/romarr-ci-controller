"""Manual canary candidate; never the operational state or source dispatcher.

The inert workflow proposal must be separately accepted before use. A trusted
host supplies ephemeral credentials; no token is loaded when this is imported.
Canary refs/history are retained, never force-updated, deleted or reused.
"""
from __future__ import annotations

import base64
from concurrent.futures import ThreadPoolExecutor
import datetime
import hashlib
import json
import os
from pathlib import Path
import re
import threading
import time
from urllib.error import HTTPError
from urllib.request import Request, build_opener
import uuid

from controller_api import NoRedirect
from controller_cycle import initial_state
from durable_state import GitHubState, PREFIX, STATE_REF, StateBlocked, encode
from stage6_pr_identity_v32 import SHA

APPROVAL = 'CREATE_RETAINED_CANARY_ONLY'
MAX_RESPONSE = 2_000_000


class CanaryConflict(StateBlocked):
    """Server explicitly rejected an already-competing non-fast-forward PATCH."""


class SimulatedResponseLoss(Exception):
    """Only the deliberate post-success injection, never a transport timeout."""


def response_fingerprint(raw):
    """Bounded schema and message commitments, never raw provider error text."""
    if type(raw) is not bytes or len(raw) > MAX_RESPONSE + 1:
        raise StateBlocked('CANARY_DIAGNOSTIC_INVALID')
    def message(value):
        if type(value) is not str:
            return dict(kind='NON_STRING')
        try:
            data=value.encode('utf-8')
        except UnicodeError:
            return dict(kind='INVALID_UNICODE')
        if len(data)>4096:
            return dict(kind='OVERSIZED')
        normalized=' '.join(value.lower().replace('-', ' ').rstrip('.').split())
        known = {'update is not a fast forward':'NON_FAST_FORWARD_VARIANT',
                 'reference update failed':'REFERENCE_UPDATE_FAILED',
                 'validation failed':'VALIDATION_FAILED'}.get(normalized,'OTHER')
        return dict(kind=known,bytes=len(data),sha256=hashlib.sha256(data).hexdigest())
    result=dict(captured_bytes=len(raw),captured_sha256=hashlib.sha256(raw).hexdigest())
    if len(raw)>MAX_RESPONSE:
        return dict(result,shape='OVERSIZED_RESPONSE')
    try:
        payload=json.loads(raw)
    except (ValueError,UnicodeError):
        return dict(result,shape='MALFORMED_JSON')
    if type(payload) is not dict:
        return dict(result,shape='NON_OBJECT_JSON')
    nested=payload.get('error')
    result.update(shape='OBJECT',message=message(payload.get('message')),
                  error_message=message(nested.get('message') if type(nested) is dict else nested))
    errors=payload.get('errors')
    if type(errors) is list:
        result['errors_truncated']=len(errors)>8
        result['errors']=[message(item.get('message') if type(item) is dict else item)
                          for item in errors[:8]]
    else:
        result['errors_kind']='ABSENT_OR_NON_LIST'
    return result


class CanaryHTTPFailure(StateBlocked):
    """Bounded public HTTP metadata; never retain a response body or URL."""
    def __init__(self, status, method, reason, response_body=None,
                 body_read='SUCCESS', encoding='identity'):
        if (type(status) is not int or not 100 <= status <= 599
                or method not in {'GET', 'POST', 'PATCH'}
                or reason not in {'REFERENCE_UPDATE_FAILED', 'OTHER_RESPONSE'}
                or body_read not in {'SUCCESS','TIMEOUT','IO_ERROR'}
                or encoding not in {'identity','gzip','br','deflate','OTHER'}):
            raise StateBlocked('CANARY_DIAGNOSTIC_INVALID')
        super().__init__('CANARY_API_REQUEST_REJECTED')
        self.status, self.method, self.reason = status, method, reason
        self.response = None if response_body is None else dict(
            response_fingerprint(response_body),body_read=body_read,encoding=encoding)


SAFE_FAILURE_CODES = frozenset({
    'STATE_LEASE_CHANGED', 'STATE_CHANGED_DURING_READ',
    'STATE_WRITE_READBACK_UNCERTAIN', 'CANARY_API_REQUEST_REJECTED',
    'CANARY_RACE_NOT_EXCLUSIVE', 'CANARY_WINNER_READBACK_INVALID',
    'CANARY_RESTART_READBACK_INVALID', 'CANARY_RESPONSE_LOSS_NOT_INJECTED',
    'CANARY_RACE_WRITER_FAILED', 'CANARY_HOST_OR_AUTHORIZATION_INVALID',
    'CANARY_REPOSITORY_IDENTITY_INVALID', 'CANARY_EXISTING_REF_PRESERVED',
})


def failure_evidence(error):
    """Fixed categories/allowlisted codes only; exception text stays private."""
    if isinstance(error, CanaryHTTPFailure):
        result=dict(category='HTTP_REJECTED', status=error.status,
                    method=error.method, reason=error.reason)
        if error.response is not None:
            result['response']=error.response
        return result
    if isinstance(error, StateBlocked):
        code = str(error)
        return dict(category='STATE_BLOCKED',
                    code=code if code in SAFE_FAILURE_CODES else 'UNCLASSIFIED_STATE_BLOCK')
    if isinstance(error, TimeoutError):
        return dict(category='TRANSPORT_TIMEOUT')
    if isinstance(error, OSError):
        return dict(category='TRANSPORT_OR_IO_ERROR')
    return dict(category='UNEXPECTED_EXCEPTION')


def context(env):
    """Require owner-initiated, exact-revision GitHub-hosted manual execution."""
    if (env.get('GITHUB_REPOSITORY') != 'TenchiMisaki/romarr-ci-controller'
            or env.get('GITHUB_REPOSITORY_ID') != '1458032121'
            or env.get('GITHUB_ACTOR_ID') != '71314201'
            or env.get('GITHUB_TRIGGERING_ACTOR') != 'TenchiMisaki'
            or env.get('GITHUB_EVENT_NAME') != 'workflow_dispatch'
            or env.get('GITHUB_REF') != 'refs/heads/main'
            or env.get('RUNNER_ENVIRONMENT') != 'github-hosted'
            or env.get('RUNNER_OS') != 'Linux'
            or env.get('CANARY_APPROVAL') != APPROVAL
            or type(env.get('GITHUB_SHA')) is not str
            or not SHA.fullmatch(env['GITHUB_SHA'])
            or env.get('EXPECTED_CONTROLLER_SHA') != env['GITHUB_SHA']
            or any(not re.fullmatch(r'[1-9][0-9]{0,18}', env.get(k, ''))
                   for k in ('GITHUB_RUN_ID', 'GITHUB_RUN_ATTEMPT'))):
        raise StateBlocked('CANARY_HOST_OR_AUTHORIZATION_INVALID')
    return 'heads/controller-canary-' + env['GITHUB_RUN_ID'] + '-' + env['GITHUB_RUN_ATTEMPT']


class CanaryAPI:
    """Route the reviewed backend to one run-owned canary ref only.

    Transport credentials may have repository-wide contents permission. This
    application allowlist is not a claim of provider-side per-ref permissions.
    No Actions, settings, secrets, source or operational state writes are allowed.
    """

    def __init__(self, wire, ref):
        if not re.fullmatch(r'heads/controller-canary-[1-9][0-9]{0,18}-[1-9][0-9]{0,18}', ref):
            raise StateBlocked('CANARY_REF_INVALID')
        self.wire, self.ref = wire, ref
        self.barrier = None
        self.drop_response = False
        self.created = set()
        self.lock = threading.Lock()

    def _call(self, method, suffix, body=None):
        """Private transport boundary; do not print payloads or server errors."""
        return self.wire(method, PREFIX + suffix if suffix else PREFIX.rstrip('/'), body)

    def request(self, method, path, body=None):
        """Translate only exact backend paths and canonical disabled state writes."""
        if path == PREFIX + 'git/ref/' + STATE_REF and method == 'GET' and body is None:
            row = self._call('GET', 'git/ref/' + self.ref)
            if row.get('ref') != 'refs/' + self.ref:
                raise StateBlocked('CANARY_REF_READ_MISMATCH')
            return dict(row, ref='refs/' + STATE_REF)
        if method == 'GET' and body is None and re.fullmatch(
                re.escape(PREFIX) + r'git/(?:commits|trees|blobs)/[0-9a-f]{40}', path):
            return self.wire(method, path, None)
        if method == 'POST' and path == PREFIX + 'git/blobs':
            if (type(body) is not dict or set(body) != {'content','encoding'}
                    or body['encoding'] != 'base64'
                    or base64.b64decode(body['content'], validate=True) != encode(initial_state())):
                raise StateBlocked('CANARY_STATE_MUST_REMAIN_INITIAL_DISABLED')
            return self.wire(method, path, body)
        if method == 'POST' and path in {PREFIX+'git/trees', PREFIX+'git/commits'}:
            if path.endswith('/trees'):
                if (type(body) is not dict or set(body) != {'tree'}
                        or type(body['tree']) is not list or len(body['tree']) != 1
                        or body['tree'][0] != dict(path='state.json', mode='100644',
                            type='blob', sha='36bf4390dd0ccb6d6cb82e279dd613440b454013')):
                    raise StateBlocked('CANARY_TREE_INVALID')
            else:
                if (type(body) is not dict or set(body) != {'message','tree','parents'}
                        or body['tree'] != '023ee9a1690d81c8a9344839c125c721e62d9702'
                        or type(body['parents']) is not list or len(body['parents']) != 1
                        or not SHA.fullmatch(str(body['parents'][0]))
                        or not re.fullmatch(r'chore: record controller state transition [0-9a-f]{32}', body['message'])):
                    raise StateBlocked('CANARY_COMMIT_INVALID')
            row = self.wire(method, path, body)
            if path.endswith('/commits'):
                with self.lock:
                    self.created.add(row['sha'])
            return row
        if method == 'PATCH' and path == PREFIX + 'git/refs/' + STATE_REF:
            if (type(body) is not dict or set(body) != {'sha','force'}
                    or body['force'] is not False or body['sha'] not in self.created):
                raise StateBlocked('CANARY_PATCH_INVALID')
            if self.barrier is not None:
                self.barrier.wait(timeout=120)
            row = self._call('PATCH', 'git/refs/' + self.ref, body)
            if self.drop_response:
                self.drop_response = False
                raise SimulatedResponseLoss('CANARY_SIMULATED_LOST_RESPONSE')
            return row
        raise StateBlocked('CANARY_METHOD_OR_TARGET_REJECTED')

    def seed(self, controller_sha):
        """Create only a new run-owned ref with canonical disabled seed bytes."""
        if not SHA.fullmatch(str(controller_sha)):
            raise StateBlocked('CANARY_CONTROLLER_INVALID')
        existing = self._call('GET', 'git/matching-refs/' + self.ref)
        if existing != []:
            raise StateBlocked('CANARY_EXISTING_REF_PRESERVED')
        blob = self.request('POST', PREFIX+'git/blobs', dict(
            encoding='base64',content=base64.b64encode(encode(initial_state())).decode()))
        if blob.get('sha') != '36bf4390dd0ccb6d6cb82e279dd613440b454013':
            raise StateBlocked('CANARY_SEED_BLOB_MISMATCH')
        tree = self.request('POST', PREFIX+'git/trees', dict(tree=[dict(
            path='state.json',mode='100644',type='blob',sha=blob['sha'])]))
        row = self.request('POST', PREFIX+'git/commits', dict(tree=tree['sha'],
            parents=[controller_sha],message='chore: record controller state transition '+uuid.uuid4().hex))
        if row.get('tree',{}).get('sha') != tree['sha'] or [p.get('sha') for p in row.get('parents',[])] != [controller_sha]:
            raise StateBlocked('CANARY_SEED_COMMIT_MISMATCH')
        created = self._call('POST', 'git/refs', dict(ref='refs/'+self.ref,sha=row['sha']))
        if created.get('ref') != 'refs/'+self.ref or created.get('object',{}).get('sha') != row['sha']:
            raise StateBlocked('CANARY_SEED_REF_UNCERTAIN')
        return GitHubState(self).load()[0]


def exercise(api, progress=None):
    """Race eight identical disabled states, then simulate a lost successful PATCH.

    The loss injection occurs only after a successful real transport response;
    it is not a claim of a naturally occurring provider/network failure.
    """
    progress = {} if progress is None else progress
    progress['phase'] = 'RACE_INITIAL_READ'
    parent, state = GitHubState(api).load()
    if state != initial_state():
        raise StateBlocked('CANARY_NOT_INITIAL_DISABLED')
    api.created.clear()
    api.barrier = threading.Barrier(8)
    progress['phase'] = 'RACE_WRITERS'
    def writer(_):
        try:
            return ('winner', GitHubState(api).save(parent, initial_state()))
        except CanaryConflict:
            return ('conflict', None)
        except Exception as error:
            return ('error', failure_evidence(error))
    try:
        with ThreadPoolExecutor(max_workers=8) as pool:
            results = list(pool.map(writer, range(8)))
    finally:
        api.barrier = None
    winners = [value for kind, value in results if kind == 'winner']
    failures = [value for kind, value in results if kind == 'error']
    progress.update(phase='RACE_VALIDATE', writers=8, successes=len(winners),
                    conflicts=sum(kind == 'conflict' for kind, _ in results),
                    created_commits=len(api.created), writer_failures=failures)
    if failures:
        raise StateBlocked('CANARY_RACE_WRITER_FAILED')
    if len(winners) != 1 or len(api.created) != 8:
        raise StateBlocked('CANARY_RACE_NOT_EXCLUSIVE')
    progress['phase'] = 'WINNER_READBACK'
    winner, observed = GitHubState(api).load()
    if winner != winners[0] or observed != initial_state():
        raise StateBlocked('CANARY_WINNER_READBACK_INVALID')
    progress['phase'] = 'RESPONSE_LOSS_WRITE'
    api.drop_response = True
    try:
        GitHubState(api).save(winner, initial_state())
    except SimulatedResponseLoss:
        pass
    else:
        raise StateBlocked('CANARY_RESPONSE_LOSS_NOT_INJECTED')
    progress['phase'] = 'RESPONSE_LOSS_READBACK'
    final, observed = GitHubState(CanaryAPI(api.wire, api.ref)).load()
    commit = api.request('GET', PREFIX+'git/commits/'+final)
    if final == winner or observed != initial_state() or [p.get('sha') for p in commit['parents']] != [winner]:
        raise StateBlocked('CANARY_RESTART_READBACK_INVALID')
    return dict(schema=1, state='CANARY_OBSERVATIONS_PASS', ref=api.ref,
        seed=parent, winner=winner, final=final, writers=8, successes=1,
        simulated_lost_response=True, policy_enabled=False,
        source_dispatch_allowed=False, operational_acceptance='NOT TESTED')


class Wire:
    """Fixed GitHub API origin, TLS defaults, no redirects or write retries."""
    def __init__(self, token):
        if type(token) is not str or not token or token != token.strip():
            raise StateBlocked('CANARY_CREDENTIAL_INVALID')
        self.token = token
    def __call__(self, method, path, body=None):
        raw = None if body is None else json.dumps(body,separators=(',',':')).encode()
        req = Request('https://api.github.com/'+path,data=raw,method=method,headers={
            'Authorization':'Bearer '+self.token,'Accept':'application/vnd.github+json',
            'Content-Type':'application/json',
            'X-GitHub-Api-Version':'2026-03-10','User-Agent':'controller-manual-canary'})
        try:
            with build_opener(NoRedirect()).open(req,timeout=30) as response:
                if response.status != (201 if method=='POST' else 200):
                    raise StateBlocked('CANARY_API_STATUS_UNVERIFIED')
                data=response.read(MAX_RESPONSE+1)
                if len(data)>MAX_RESPONSE:raise StateBlocked('CANARY_API_RESPONSE_BOUND')
                return json.loads(data)
        except HTTPError as error:
            code=error.code
            body_read='SUCCESS'
            encoding=(error.headers or {}).get('Content-Encoding','identity').lower()
            if encoding not in {'identity','gzip','br','deflate'}:encoding='OTHER'
            try: raw_error=error.read(MAX_RESPONSE+1)
            except TimeoutError: raw_error=b'';body_read='TIMEOUT'
            except OSError: raw_error=b'';body_read='IO_ERROR'
            try: payload=json.loads(raw_error)
            except (ValueError, UnicodeError): payload={}
            error.close()
            if (method=='PATCH' and code==422 and type(payload) is dict
                    and payload.get('message')=='Update is not a fast forward'):
                raise CanaryConflict('CANARY_NON_FAST_FORWARD_REJECTED') from None
            reason = ('REFERENCE_UPDATE_FAILED' if type(payload) is dict
                      and payload.get('message') == 'Reference update failed' else 'OTHER_RESPONSE')
            raise CanaryHTTPFailure(code, method, reason, raw_error, body_read, encoding) from None


def main():
    """Candidate CLI; no source/operational ref or token data is printed."""
    started=time.monotonic()
    print('================ PREFLIGHT CHECK ================',flush=True)
    print('Expected: GitHub-hosted Linux / owner manual run / fixed controller repository',flush=True)
    print('Start: '+datetime.datetime.now().astimezone().isoformat(),flush=True)
    report=dict(schema=1,state='BLOCKED_OR_UNCERTAIN',phase='HOST_GATE',
                operational_acceptance='NOT TESTED')
    try:
        ref=context(os.environ)
        report.update(ref=ref,phase='REPOSITORY_GATE')
        print('Verified runtime ref: '+ref,flush=True)
        output=Path(os.environ['RUNNER_TEMP'])/'controller-canary-summary.json'
        if output.exists() or output.is_symlink():
            raise StateBlocked('CANARY_EXISTING_REPORT_PRESERVED')
        api=CanaryAPI(Wire(os.environ.get('GH_TOKEN')),ref)
        repo=api._call('GET','')
        if (repo.get('id')!=1458032121 or repo.get('owner',{}).get('id')!=71314201
                or repo.get('private') is not False or repo.get('archived') is not False
                or repo.get('disabled') is not False):
            raise StateBlocked('CANARY_REPOSITORY_IDENTITY_INVALID')
        operational=api._call('GET','git/ref/'+STATE_REF)
        report['phase']='SEED'
        print('APPLY: create retained run-owned canary only',flush=True)
        api.seed(os.environ['GITHUB_SHA'])
        report['phase']='RACE_AND_RECOVERY'
        print('VERIFY: eight-writer race and simulated lost-response readback',flush=True)
        report.update(exercise(api, report))
        report['state']='BLOCKED_OR_UNCERTAIN'
        report['phase']='OPERATIONAL_READBACK'
        if api._call('GET','git/ref/'+STATE_REF)!=operational:
            report['state']='OPERATIONAL_STATE_CHANGED_DURING_OBSERVATION'
        else:
            report['state']='CANARY_OBSERVATIONS_PASS'
    except Exception as error:
        # Preserve uncertain refs/history; never retry, repair or emit raw errors.
        report['state']='BLOCKED_OR_UNCERTAIN'
        report['failure']=failure_evidence(error)
    try:
        output=Path(os.environ['RUNNER_TEMP'])/'controller-canary-summary.json'
        with output.open('x') as stream:stream.write(json.dumps(report,sort_keys=True)+'\n')
    except (KeyError,OSError):
        report['state']='SUMMARY_COLLECTION_FAILED'
    print(json.dumps(report,sort_keys=True),flush=True)
    print('================ DIAGNOSTIC FINISH ================',flush=True)
    print(datetime.datetime.now().astimezone().isoformat()+'; elapsed seconds '+str(round(time.monotonic()-started,2)),flush=True)
    return 0 if report['state']=='CANARY_OBSERVATIONS_PASS' else 1


if __name__=='__main__':raise SystemExit(main())
