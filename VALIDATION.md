# Validation receipt — controller v01

**Result: PREPARED / OFFLINE TESTS PASS / LIVE GITHUB ACTIONS NOT TESTED.**

## Source-derived design checks

- Matched the official ROMarr fork's existing `.github/workflows/docker.yml` **pytest test job only**: Python 3.13, public `rom-hub` commit `02e9a1dbc7ebca5191b4a977233a4d6d0466ed4b`, and Archive.org test fixture `v0.4.1` resolved by GitHub to full commit `3b49c1c67ccedfc5f072c19e3dd4990fec0b0d5f`.
- Added Node.js 24 because ROMarr UI tests may explicitly skip Node-dependent regressions when the executable is absent.
- Preserved existing offline marker behavior from `pytest.ini`. The source checkout is pinned to a full Git commit; source head and base are rechecked after testing.
- No Docker build/publish, upstream comments, main-branch mutation, production/preview action, external scheduler, billable AI access, or infrastructure secrets.
- GitHub Actions are identified by verified GitHub commit IDs for `actions/checkout@v5`, `actions/setup-python@v6`, `actions/setup-node@v6`, and `actions/upload-artifact@v4`.

## Checks actually executed during package preparation

- Python 3.13.5 `compileall` **PASS** for the controller and tests.
- Python `unittest` **28 PASS / 0 FAIL**, including exact SHA/draft/base identity gates, malformed inputs, synthetic JUnit tally/subtest mismatch, manifest tampering, stale PR, collection failure, artifact failure, real pytest PASS/FAIL, and controlled pytest timeout.
- Additional live **local** pytest 9.0.2 JUnit fixture with one pass and one expected skip: raw process exit 0, exact individual JUnit counts reconstructed **PASS**. It is a collector proof, not a ROMarr full-suite test.
- YAML parsed using PyYAML 6.0.3; confirmed one `workflow_dispatch` trigger, no schedule/push/PR triggers, `ubuntu-24.04`, read-only `contents` permission and six full-SHA action references. Static workflow inspection **PASS**.

## Not performed

- GitHub-native `actionlint` execution **NOT TESTED** (not installed in the package preparation environment).
- GitHub-hosted workflow execution, Python package installation against ROMarr's actual dependency tree, PR #25/#21 full pytest, Node-dependent ROMarr regression execution and external source checkout **NOT TESTED**.
- Scheduled detection, CodeRabbit monitor, persistent deduplication and automated code correction **NOT INSTALLED**.
- An artifact upload to the actual GitHub controller and GitHub run/readback are **NOT TESTED**.

## Scope and recovery

These are reproducible **offline code and parser** results, not proof of a live CI PASS. First publish the controller to its separate repository and run the manual `main` baseline; inspect the actual Actions job, artifact members, SHA attribution, case counts, and unexpected skips before testing any PR head or enabling scheduling. If a failure occurs, preserve the run evidence and original source; do not modify the ROMarr fork or private synchronization automation to compensate.
