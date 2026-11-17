"""Installed manual workflow privilege/trigger boundary; never executes it."""
import copy
from pathlib import Path
import unittest

import yaml

ROOT = Path(__file__).resolve().parents[1]
PATH = ROOT / '.github/workflows/controller-state-canary.yml'


def validate(document):
    """Reject automatic/source-bearing entrypoints and unreviewed commands."""
    def require(condition):
        if not condition:
            raise ValueError('CANARY_WORKFLOW_BOUNDARY_CHANGED')
    require(set(document['on']) == {'workflow_dispatch'})
    inputs = document['on']['workflow_dispatch']['inputs']
    require(set(inputs) == {'controller_sha', 'approval'})
    require(all(x['required'] == 'true' and x['type'] == 'string' for x in inputs.values()))
    require(document['permissions'] == {'contents': 'read'})
    require(document['concurrency'] == dict(group='controller-manual-state-canary', **{'cancel-in-progress':'false'}))
    require(set(document['jobs']) == {'canary'})
    job = document['jobs']['canary']
    require(job['if'] == "github.repository_id == '1458032121' && github.actor_id == '71314201' && github.ref == 'refs/heads/main'")
    require(job['runs-on'] == 'ubuntu-24.04' and job['timeout-minutes'] == '10')
    require(job['permissions'] == {'contents':'write'})
    steps = job['steps']
    require(len(steps) == 4)
    require(steps[0]['uses'] == 'actions/checkout@fbc6f3992d24b796d5a048ff273f7fcc4a7b6c09')
    require(steps[0]['with'] == {'ref':'${{ github.sha }}','persist-credentials':'false'})
    require(steps[1]['uses'] == 'actions/setup-python@ece7cb06caefa5fff74198d8649806c4678c61a1')
    require(steps[1]['with'] == {'python-version':'3.13'})
    require(steps[2]['run'] == 'python -u controller/hosted_state_canary.py')
    require(steps[2]['env'] == dict(GH_TOKEN='${{ github.token }}',
        CANARY_APPROVAL='${{ inputs.approval }}',EXPECTED_CONTROLLER_SHA='${{ inputs.controller_sha }}'))
    require(steps[3]['uses'] == 'actions/upload-artifact@b7c566a772e6b6bfb58ed0dc250532a479d7789f')
    require(steps[3]['if'] == '${{ !cancelled() }}')
    require(steps[3]['with'] == {'name':'controller-state-canary-${{ github.run_id }}-${{ github.run_attempt }}',
        'path':'${{ runner.temp }}/controller-canary-summary.json','if-no-files-found':'error','retention-days':'7'})
    require(all('run' not in x for i,x in enumerate(steps) if i != 2))
    require(all('env' not in x for i,x in enumerate(steps) if i != 2))
    require(all('shell' not in step for step in steps))
    require('defaults' not in document and 'defaults' not in job)


class StateCanaryWorkflowTests(unittest.TestCase):
    def setUp(self):
        self.document = yaml.load(PATH.read_text(), Loader=yaml.BaseLoader)

    def test_installed_manual_privilege_boundary(self):
        validate(self.document)
        self.assertFalse((ROOT/'docs/proposals/hosted-state-canary.workflow.yml').exists())
        ci = yaml.load((ROOT/'.github/workflows/controller-unit-tests.yml').read_text(), Loader=yaml.BaseLoader)
        self.assertIn('.github/workflows/controller-state-canary.yml', ci['on']['pull_request']['paths'])

    def test_automatic_triggers_and_source_inputs_rejected(self):
        for event in ('schedule','push','pull_request','workflow_run'):
            changed=copy.deepcopy(self.document); changed['on'][event]={}
            with self.subTest(event=event), self.assertRaises(ValueError):validate(changed)
        changed=copy.deepcopy(self.document)
        changed['on']['workflow_dispatch']['inputs']['source_ref']={'required':'true','type':'string'}
        with self.assertRaises(ValueError):validate(changed)

    def test_privilege_command_and_artifact_drift_rejected(self):
        for mutation in ('permission','credentials','command','artifact','gate','step_shell','job_shell','workflow_shell'):
            changed=copy.deepcopy(self.document); job=changed['jobs']['canary']
            if mutation=='permission':job['permissions']['actions']='write'
            if mutation=='credentials':job['steps'][0]['with']['persist-credentials']='true'
            if mutation=='command':job['steps'][2]['run']='python controller/watch.py dispatch'
            if mutation=='artifact':job['steps'][3]['with']['path']='.'
            if mutation=='gate':job['if']='true'
            if mutation=='step_shell':job['steps'][2]['shell']='python {0}'
            if mutation=='job_shell':job['defaults']={'run':{'shell':'python {0}'}}
            if mutation=='workflow_shell':changed['defaults']={'run':{'shell':'python {0}'}}
            with self.subTest(mutation=mutation),self.assertRaises(ValueError):validate(changed)


if __name__ == '__main__':unittest.main()
