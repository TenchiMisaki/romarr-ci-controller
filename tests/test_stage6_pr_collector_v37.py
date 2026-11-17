"""Synthetic ordered transport tests. These are NOT live GitHub acceptance."""
import copy
import pytest
from stage6_pr_collector_v37 import collect_ordered
from test_stage6_pr_final_gate_v36 import fixture


def harness(mutate=None, fail_index=None):
    d = fixture()
    e = d['evidence'].expected
    pr = f'https://api.github.com/repos/TenchiMisaki/romarr/pulls/{e.pr.pr_number}'
    branch = 'https://api.github.com/repos/TenchiMisaki/romarr/branches/main'
    run = f'https://api.github.com/repos/TenchiMisaki/romarr-ci-controller/actions/runs/{e.run_id}'
    jobs = run + '/jobs?per_page=100'
    artifact = f'https://api.github.com/repos/TenchiMisaki/romarr-ci-controller/actions/artifacts/{e.artifact_id}'
    archive = artifact + '/zip'
    ordered = [(pr, d['pr_before']), (branch, d['branch_before']),
               (run, d['run']), (jobs, d['jobs']), (artifact, d['artifact']),
               (pr, d['pr_after']), (branch, d['branch_after']),
               (archive, d['raw_zip']), (pr, d['pr_final']), (branch, d['branch_final'])]
    calls = []
    def get_json(url):
        index = len(calls)
        calls.append(('json', url))
        assert ordered[index][0] == url
        if index == fail_index:
            raise TimeoutError('synthetic token=TEST-DO-NOT-LEAK')
        val = copy.deepcopy(ordered[index][1])
        if mutate:
            val = mutate(index, val)
        return val
    def get_bytes(url, limit, digest):
        index = len(calls)
        calls.append(('bytes', url))
        assert index == 7 and url == archive
        assert limit == e.max_archive_bytes and digest == e.artifact_sha256
        if index == fail_index:
            raise OSError('synthetic token=TEST-DO-NOT-LEAK')
        val = ordered[index][1]
        return mutate(index, val) if mutate else val
    return d['evidence'],get_json,get_bytes,calls,ordered


def test_ordered_positive_returns_advisory_only():
    e,g,b,calls,ordered = harness()
    result = collect_ordered(evidence=e,get_json=g,get_artifact_bytes=b)
    assert result.state == 'ADVISORY_COLLECTED_NOT_TEST_ACCEPTED'
    assert not result.test_accepted and not result.publication_authorized
    assert not result.unattended_dispatch_enabled
    assert [u for _,u in calls] == [u for u,_ in ordered]
    assert [x for x,_ in calls] == ['json']*7+['bytes']+['json']*2


@pytest.mark.parametrize('index', list(range(10)))
def test_collection_failure_at_every_step_fails_closed(index):
    e,g,b,calls,_ = harness(fail_index=index)
    outcome = collect_ordered(evidence=e,get_json=g,get_artifact_bytes=b)
    assert outcome.state == 'BLOCKED'
    assert 'TEST-DO-NOT-LEAK' not in outcome.reason
    assert not outcome.test_accepted
    assert len(calls) == index+1


@pytest.mark.parametrize('index,change', [
    (0,'head'),(5,'head'),(8,'head'),(1,'base'),(6,'base'),(9,'base'),
    (3,'job'),(4,'digest'),(7,'bytes'),(2,'run'),(8,'missing')])
def test_drift_and_tamper_block(index,change):
    def modify(i, val):
        if i != index:return val
        if change=='head': val['head']['sha']='f'*40
        elif change=='base': val['commit']['sha']='f'*40
        elif change=='job': val['jobs'][0]['conclusion']='failure'
        elif change=='digest': val['digest']='sha256:'+'f'*64
        elif change=='bytes': val=val[:-1]
        elif change=='run': val['conclusion']='failure'
        elif change=='missing':val=None
        return val
    e,g,b,_,_=harness(mutate=modify)
    assert collect_ordered(evidence=e,get_json=g,get_artifact_bytes=b).state=='BLOCKED'


def test_invalid_collector_callbacks_rejected():
    e,g,b,_,_=harness()
    assert collect_ordered(evidence=e,get_json=None,get_artifact_bytes=b).state=='BLOCKED'
    assert collect_ordered(evidence=e,get_json=g,get_artifact_bytes=None).state=='BLOCKED'
    assert collect_ordered(evidence={},get_json=g,get_artifact_bytes=b).state=='BLOCKED'


def test_callback_internal_error_does_not_leak_details():
    e,g,b,_,_=harness()
    def broken(url):raise RuntimeError('Authorization: Bearer FAKE_TEST_SECRET')
    result=collect_ordered(evidence=e,get_json=broken,get_artifact_bytes=b)
    assert result.state=='BLOCKED'
    assert 'FAKE_TEST_SECRET' not in result.reason
