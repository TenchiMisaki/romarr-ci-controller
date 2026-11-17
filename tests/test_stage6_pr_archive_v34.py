"""Synthetic archives only; no GitHub API calls or source execution."""
import copy
import hashlib
import io
import json
import stat
import zipfile
import pytest
from stage6_pr_identity_v32 import IdentityRejected
from stage6_pr_archive_v34 import verify_advisory_bytes, SCHEMA
H, B = 'a'*40, 'b'*40
RUN = 123

def canonical(x):
    return (json.dumps(x, sort_keys=True, separators=(',', ':'), allow_nan=False)+'\n').encode('ascii')

def build(mod=None, *, extra=None, compression=zipfile.ZIP_DEFLATED, comment=b'', prefix=b''):
    record={'schema':SCHEMA,'run_id':RUN,'head_sha':H,'base_sha':B,'passing_cases':70,'pytest_exit':0,'test_accepted':False,'publication_authorized':False,'unattended_dispatch_enabled':False}
    if mod: mod(record)
    advisory=canonical(record)
    manifest=canonical({'schema':SCHEMA,'files':{'advisory.json':{'sha256':hashlib.sha256(advisory).hexdigest(),'bytes':len(advisory)}}})
    with io.BytesIO() as buf:
        with zipfile.ZipFile(buf,'w',compression=compression) as z:
            z.writestr('advisory.json',advisory)
            z.writestr('manifest.json',manifest)
            if extra: z.writestr(extra,b'unexpected')
            z.comment=comment
        return prefix+buf.getvalue()

def verify(raw, **kwargs):
    return verify_advisory_bytes(raw,expected_archive_sha256=kwargs.get('digest',hashlib.sha256(raw).hexdigest()),expected_run_id=kwargs.get('run_id',RUN),expected_head_sha=kwargs.get('head',H),expected_base_sha=kwargs.get('base',B))

def test_positive_advisory_never_trusted():
    result=verify(build())
    assert result.state=='ADVISORY_BYTES_VERIFIED_NOT_ACCEPTED'
    assert result.passing_cases==70
    assert (result.test_accepted,result.publication_authorized,result.unattended_dispatch_enabled)==(False,False,False)

@pytest.mark.parametrize('change', ['head','base','run','exit','cases_zero','cases_boolean','approve','publish','unattended','unexpected_key'])
def test_reject_record_changes(change):
    def edit(d):
        if change=='head': d['head_sha']='f'*40
        elif change=='base': d['base_sha']='f'*40
        elif change=='run': d['run_id']+=1
        elif change=='exit': d['pytest_exit']=1
        elif change=='cases_zero': d['passing_cases']=0
        elif change=='cases_boolean': d['passing_cases']=True
        elif change=='approve': d['test_accepted']=True
        elif change=='publish': d['publication_authorized']=True
        elif change=='unattended': d['unattended_dispatch_enabled']=True
        else: d['extra']='x'
    with pytest.raises(IdentityRejected):verify(build(edit))

@pytest.mark.parametrize('extra', ['trace.log','../private','advisory.json','/tmp/file','manifest.json','private.xml'])
def test_reject_extra_and_duplicate_members(extra):
    with pytest.raises(IdentityRejected):verify(build(extra=extra))

@pytest.mark.parametrize('which', ['digest','run_id','head','base','trailing','bad_bytes'])
def test_reject_identity_and_bytes(which):
    raw=build()
    if which=='digest': kw={'digest':'f'*64}
    elif which=='run_id': kw={'run_id':124}
    elif which=='head': kw={'head':'f'*40}
    elif which=='base': kw={'base':'f'*40}
    elif which=='trailing': raw+=b'JUNK';kw={}
    else:raw=raw[:-12];kw={}
    with pytest.raises(IdentityRejected):verify(raw,**kw)

def test_stored_zip_accepted(): assert verify(build(compression=zipfile.ZIP_STORED)).passing_cases==70

def test_nonempty_zip_comment_accepted(): assert verify(build(comment=b'owned archive comment')).passing_cases==70

def test_prefix_zip_rejected():
    # ZIP files with prepended bytes are valid to zipfile but disallowed by this
    # candidate's strict ZIP central-directory / early-signature policy.
    with pytest.raises(IdentityRejected):verify(build(prefix=b'junk'))
