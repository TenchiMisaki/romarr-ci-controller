"""Private candidate tests: host sanitizer plus workflow structural boundaries."""
import hashlib
import io
import json
from pathlib import Path
import re
import zipfile

import pytest
import yaml

from stage6_pr_source_v42 import SourceBlocked, sanitize_junit
from stage6_pr_archive_v34 import verify_advisory_bytes

H = 'a'*40
B = 'b'*40
RUN = 44


def xml(cases=2, **changes):
    attrs = {'tests': str(cases), 'failures': '0', 'errors': '0', 'skipped': '0'}
    attrs.update({k: str(v) for k,v in changes.items()})
    a = ' '.join(f'{k}="{v}"' for k,v in attrs.items())
    return (f'<testsuites><testsuite {a}>'+('<testcase name="p"/>'*cases)+'</testsuite></testsuites>').encode()


def create_archive(advisory, manifest):
    f=io.BytesIO()
    with zipfile.ZipFile(f,'w',compression=zipfile.ZIP_STORED) as z:
        z.writestr('advisory.json',advisory)
        z.writestr('manifest.json',manifest)
    return f.getvalue()


def test_real_archive_verifier_compatible():
    advisory, manifest = sanitize_junit(xml(), run_id=RUN, head_sha=H, base_sha=B, pytest_exit=0)
    archive=create_archive(advisory,manifest)
    result=verify_advisory_bytes(archive,expected_archive_sha256=hashlib.sha256(archive).hexdigest(),expected_run_id=RUN,expected_head_sha=H,expected_base_sha=B)
    assert result.state=='ADVISORY_BYTES_VERIFIED_NOT_ACCEPTED'
    assert result.passing_cases==2
    assert result.test_accepted is False
    assert json.loads(advisory)['unattended_dispatch_enabled'] is False


@pytest.mark.parametrize('payload,exit_code',[
    (xml(),1),(xml(0),0),(xml(2,skipped=1),0),(xml(2,failures=1),0),
    (xml(2,errors=1),0), (b'<!DOCTYPE x [<!ENTITY y "foo">]><testsuite/>',0),
    (b'not xml',0),(xml(257),0),(b'',0),
    (b'<testsuite tests="1" failures="0" errors="0" skipped="0"><testcase><skipped/></testcase></testsuite>',0),
    (b'<testsuites><testsuite tests="1" failures="0" errors="0" skipped="0"><testcase/><testcase/></testsuite></testsuites>',0),
])
def test_invalid_junit_blocks(payload,exit_code):
    with pytest.raises(SourceBlocked):
        sanitize_junit(payload,run_id=RUN,head_sha=H,base_sha=B,pytest_exit=exit_code)


@pytest.mark.parametrize('head,base,run',[('A'*40,B,RUN),(H,'G'*40,RUN),(H,B,0),(H,B,True),(H,'',RUN)])
def test_invalid_identity_blocks(head,base,run):
    with pytest.raises(SourceBlocked):
        sanitize_junit(xml(),run_id=run,head_sha=head,base_sha=base,pytest_exit=0)


def workflow():
    # Worktree layout matches the proposed repo-relative installation.
    root=Path(__file__).resolve().parents[1]
    return yaml.safe_load((root/'.github/workflows/stage6-pr-manual-candidate.yml').read_text())


def test_manual_only_and_two_jobs():
    w=workflow()
    triggers=w.get('on',w.get(True)) # PyYAML YAML 1.1 compatibility
    assert set(triggers)=={'workflow_dispatch'}
    assert set(w['jobs'])=={'isolated_source','isolated_reviewer'}
    assert w['permissions']=={}
    assert w['concurrency']['cancel-in-progress'] is False
    assert w['jobs']['isolated_source']['permissions']=={}
    assert w['jobs']['isolated_reviewer']['needs']==['isolated_source']
    assert w['jobs']['isolated_reviewer']['permissions']=={'actions':'read','contents':'read'}


def test_no_token_in_source_steps():
    src=workflow()['jobs']['isolated_source']
    text=str(src)
    assert 'github.token' not in text.lower()
    assert 'secrets.' not in text.lower()
    assert '--network none' in text
    assert '--read-only' in text
    assert 'persist-credentials' in text
    assert '--cap-drop ALL' in text
    assert 'stage6_pr_source_v42.py' in text
    assert 'EXPECTED_PR_HEAD_SHA' in text


def test_verifier_separate_token_and_no_source_outputs():
    w=workflow()
    source=str(w['jobs']['isolated_source'])
    reviewer=str(w['jobs']['isolated_reviewer'])
    assert 'github.token' in reviewer.lower()
    assert 'github.token' not in source.lower()
    assert 'needs.isolated_source.outputs' not in reviewer
    assert 'stage6_pr_discovery_v40.py' in reviewer
    assert 'inputs.pr_number' in reviewer


def test_upload_member_allowlist_and_retention():
    steps=workflow()['jobs']['isolated_source']['steps']
    up=[s for s in steps if s.get('name','').startswith('Upload only')]
    assert len(up)==1
    u=up[0]['with']
    assert u['name']=='romarr-stage6-pr-advisory'
    assert u['retention-days']==1
    assert u['if-no-files-found']=='error'
    assert set(x.strip().rsplit('/',1)[-1] for x in u['path'].splitlines())=={'advisory.json','manifest.json'}


def test_exact_step_name_contract():
    from stage6_pr_entrypoint_v39 import SOURCE_JOB,SOURCE_STEP,WORKFLOW,ARTIFACT_NAME
    w=workflow()
    assert w['jobs']['isolated_source']['name']==SOURCE_JOB
    assert sum(s.get('name')==SOURCE_STEP for s in w['jobs']['isolated_source']['steps'])==1
    assert WORKFLOW=='.github/workflows/stage6-pr-manual-candidate.yml'
    assert any(s.get('with',{}).get('name')==ARTIFACT_NAME for s in w['jobs']['isolated_source']['steps'])


def test_all_trusted_files_are_sparsely_checked_out():
    from pathlib import Path
    root=Path(__file__).resolve().parents[1]
    w=workflow()
    for job in w['jobs'].values():
        s=job['steps'][0]['with']['sparse-checkout']
        for line in s.splitlines():
            f=line.strip()
            assert f.startswith('controller/')
            assert ((root / f) if (root / 'controller').is_dir() else (root / f.split('/', 1)[1])).is_file(), f
