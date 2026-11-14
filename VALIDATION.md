# Validation receipt — controller v01

**Current status: ARCHIVE-TOOL-ENABLED FULL BASELINE PASS (November 14, 2026); exact PR workflows and scheduling not yet validated.**

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

## Not performed during original package preparation (historical)

- GitHub-native `actionlint` execution **NOT TESTED** (not installed in the package preparation environment).
- GitHub-hosted workflow execution, Python package installation against ROMarr's actual dependency tree, PR #25/#21 full pytest, Node-dependent ROMarr regression execution and external source checkout **NOT TESTED**.
- Scheduled detection, CodeRabbit monitor, persistent deduplication and automated code correction **NOT INSTALLED**.
- An artifact upload to the actual GitHub controller and GitHub run/readback are **NOT TESTED**.

## GitHub-hosted acceptance — November 14, 2026 (UTC)

- Controller revision `617e1ac98d8816432277622f252d8b072339439a`, [initial successful baseline #43628828155](https://github.com/TenchiMisaki/romarr-ci-controller/actions/runs/43628828155): ROMarr source `3aeede0ff0e3b9ad0b305d6e4baaaa1252bb0176`, 3,814 passed / 19 skipped / no failures/errors; source verification UNCHANGED; sanitized evidence and final gate PASS.
- Controller revision `0bfc16d3294ca73570c407fc69c73c5743fc8a67`, [archive-tools-enabled baseline #43629839935](https://github.com/TenchiMisaki/romarr-ci-controller/actions/runs/43629839935): **3,831 passed / 2 skipped / no failures/errors** from 3,833 cases, raw pytest exit `0`, Python 3.13.18, Node.js 24.22.2; `TEST=PASS`, `COLLECTION=PASS`, `SOURCE=UNCHANGED`, and final GitHub workflow SUCCESS.
- Runner installed missing Ubuntu `libarchive-tools` and `unar` and positively found all required executables (`bsdtar`, `7z`, `unar`, `lsar`). ROMarr's `bsdtar_path()` and `rar_tool()` checks passed, selecting `7z` as the split-RAR reader. The action does not install tools on CT107 or production.
- Downloaded public artifact `romarr-pytest-handoff-43629839935-1` (`12,396` bytes), exact ZIP SHA-256 `20d897b4380187f2c36f4dbb3a66b5e02a228dcd9b776d157572c7c0089c61bf` matched the GitHub job log. ZIP CRC, all four manifest file hashes, `summary.json`, `postcheck.json`, and **3,833 anonymous individual outcomes** independently reconciled. Raw private JUnit/log contents were intentionally not published.
- The 17-case reduction in skipped tests between baselines is **observed**, but the public anonymous evidence alone does not determine which tests changed skip status. This confirms full **offline-marked source pytest** for the pinned main revision, not network-marked, Docker/browser, deployed operation, code review, a PR head, or an unattended schedule.

## Scope and recovery

The full **main** baseline is now live-accepted for the stated source and controller revisions. Before treating any ROMarr PR as validated, run the manual PR-specific workflow on its own exact current head, examine all skips and independent artifact outcomes, and apply the separate CodeRabbit/review gates. Do not enable scheduling until independently reviewed and accepted. If a failure occurs, preserve the run evidence and original source; do not modify the ROMarr fork or private synchronization automation to compensate.
