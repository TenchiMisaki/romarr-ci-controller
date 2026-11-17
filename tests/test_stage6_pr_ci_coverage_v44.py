"""Regression guard: host CI must execute both unittest and Stage 6 pytest suites.

The GitHub Actions runner executes on a PR merge ref. This static test cannot
replace a real hosted check or assert that source-level ROMarr tests ran.
"""
from pathlib import Path

import yaml

WORKFLOW = (Path(__file__).resolve().parents[1] / '.github' / 'workflows'
            / 'controller-unit-tests.yml')


def _workflow():
    result = yaml.safe_load(WORKFLOW.read_text(encoding='utf-8'))
    assert type(result) is dict
    return result


def _steps():
    workflow = _workflow()
    return workflow['jobs']['unit']['steps']


def _only(step_name):
    results = [x for x in _steps() if x.get('name') == step_name]
    assert len(results) == 1
    return results[0]


def test_existing_unit_suite_preserved():
    unit = _only('Run offline controller regression suite')
    assert unit['run'] == "python -m unittest discover -s tests -p 'test_*.py' -v"


def test_import_path_for_unittest_pytest_modules():
    assert _only('Run offline controller regression suite')['env'] == {'PYTHONPATH': 'controller'}
    assert _only('Run isolated Stage 6 pytest regression suite')['env'] == {'PYTHONPATH': 'controller'}


def test_pytest_suite_exact_target():
    assert _only('Run isolated Stage 6 pytest regression suite')['run'] == (
        'python -m pytest -q tests/test_stage6_pr_*.py'
    )


def test_offline_tests_run_before_monitor_smokes():
    names = [x['name'] for x in _steps()]
    assert names.index('Run offline controller regression suite') < names.index(
        'Run isolated Stage 6 pytest regression suite') < names.index(
        'Smoke-test Node.js 24 artifact action with public README only')
    assert names.index('Run isolated Stage 6 pytest regression suite') < names.index(
        'Audit live ROMarr PRs (read-only; no dispatch)')


def test_pinned_test_dependencies_and_python_unchanged():
    assert _only('Install pinned pytest and PyYAML for regression checks')['run'] == (
        "python -m pip install 'pytest==9.2.0' 'PyYAML==6.0.3'"
    )
    assert _only('Set up Python 3.13')['with']['python-version'] == '3.13'


def test_pr_trigger_and_no_automatic_testing_dispatch():
    workflow = _workflow()
    event = workflow.get('on', workflow.get(True))  # PyYAML reads YAML 1.1 'on' as bool
    assert type(event) is dict
    assert set(event) == {'pull_request'}
    assert set(event['pull_request']['types']) == {'opened', 'reopened', 'synchronize'}
    assert set(event['pull_request']['paths']) >= {'controller/**', 'tests/**'}
    assert set(workflow['jobs']) == {'unit'}


def test_stage6_manual_workflow_change_triggers_controller_ci():
    workflow = _workflow()
    event = workflow.get('on', workflow.get(True))
    assert '.github/workflows/stage6-pr-manual-candidate.yml' in event['pull_request']['paths']


def test_read_only_permissions_and_no_checkout_token_persistence():
    workflow = _workflow()
    assert workflow['permissions'] == {'contents': 'read'}
    assert _only('Checkout controller PR merge result')['with']['persist-credentials'] is False
    assert not any(x.get('permissions') for x in workflow['jobs'].values())


def test_existing_monitor_commands_preserved():
    assert _only('Audit live ROMarr PRs (read-only; no dispatch)')['run'] == (
        'python controller/watch.py audit')
    assert _only('Collect live PR pytest and CodeRabbit state (read-only)')['run'] == (
        'python controller/status.py audit > "$RUNNER_TEMP/romarr-live-status.json"')


def test_unittest_pytest_job_change_is_scoped():
    workflow = _workflow()
    assert workflow['jobs']['unit']['runs-on'] == 'ubuntu-24.04'
    assert workflow['jobs']['unit']['timeout-minutes'] == 10
    assert len(_steps()) == 10
