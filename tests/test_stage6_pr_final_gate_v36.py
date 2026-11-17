"""Offline final-gate tamper tests; no transport, GitHub write or real PR receipt."""
import copy
import hashlib
import pytest
from stage6_pr_identity_v32 import IdentityRejected
from stage6_pr_final_gate_v36 import FinalEvidence, verify_final_candidate
from test_stage6_pr_receipt_v33 import sample
from test_stage6_pr_archive_v34 import build

B = 'b' * 40

def fixture():
    d = sample()
    raw = build()
    d['expected'] = copy.copy(d['expected'])
    # Metadata digest must be bound to exactly the supplied raw bytes.
    from dataclasses import replace
    digest = hashlib.sha256(raw).hexdigest()
    expected = replace(d['expected'], artifact_sha256=digest)
    d['artifact']['digest'] = 'sha256:' + digest
    d['artifact']['size_in_bytes'] = len(raw)
    return dict(
        evidence=FinalEvidence(expected, expected.pr.head_sha),
        pr_before=d['before'], pr_after=d['after'], pr_final=copy.deepcopy(d['after']),
        branch_before={'name':'main','commit':{'sha':B}},
        branch_after={'name':'main','commit':{'sha':B}},
        branch_final={'name':'main','commit':{'sha':B}},
        run=d['run'], jobs=d['jobs'], artifact=d['artifact'], raw_zip=raw)


def test_positive_is_explicitly_not_accepted():
    assert verify_final_candidate(**fixture()) == 'FINAL_PR_ADVISORY_IDENTITIES_AND_BYTES_VERIFIED_NOT_TEST_ACCEPTED'

@pytest.mark.parametrize('changed', ['final_head','final_base','final_closed','final_draft','final_branch',
                                     'before_branch','after_branch','raw_zip','outer_digest','job_failure',
                                     'artifact_expired','pr_after_changed','missing_final','missing_branch','missing_raw'])
def test_reject_final_drift_tampering_and_incomplete_collection(changed):
    d = fixture()
    if changed == 'final_head':d['pr_final']['head']['sha'] = 'c'*40
    elif changed == 'final_base':d['pr_final']['base']['sha'] = 'c'*40
    elif changed == 'final_closed':d['pr_final']['state'] = 'closed'
    elif changed == 'final_draft':d['pr_final']['draft'] = True
    elif changed == 'final_branch':d['branch_final']['commit']['sha'] = 'c'*40
    elif changed == 'before_branch':d['branch_before']['commit']['sha'] = 'c'*40
    elif changed == 'after_branch':d['branch_after']['commit']['sha'] = 'c'*40
    elif changed == 'raw_zip':d['raw_zip'] = d['raw_zip'][:-5]
    elif changed == 'outer_digest':d['artifact']['digest'] = 'sha256:'+'f'*64
    elif changed == 'job_failure':d['jobs']['jobs'][0]['conclusion'] = 'failure'
    elif changed == 'artifact_expired':d['artifact']['expired'] = True
    elif changed == 'pr_after_changed':d['pr_after']['head']['sha'] = 'c'*40
    elif changed == 'missing_final':d['pr_final'] = None
    elif changed == 'missing_branch':d['branch_final'] = None
    elif changed == 'missing_raw':d['raw_zip'] = None
    with pytest.raises(IdentityRejected):verify_final_candidate(**d)


def test_wrong_source_sha_rejected():
    d=fixture()
    with pytest.raises(IdentityRejected): FinalEvidence(d['evidence'].expected, 'f'*40)


def test_wrong_final_evidence_type_rejected():
    d=fixture();d['evidence']={}
    with pytest.raises(IdentityRejected):verify_final_candidate(**d)
