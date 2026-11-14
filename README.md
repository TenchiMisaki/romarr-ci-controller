# ROMarr GitHub pytest controller — manual pilot v01

**Status: GITHUB-HOSTED FULL PYTEST BASELINE ACCEPTED WITH ARCHIVE-TOOL PREREQUISITES VERIFIED.**

This is a separate **public** GitHub repository to host ROMarr test orchestration. It does **not** modify `TenchiMisaki/romarr`, `BlizzHacker/romarr`, any separate fork-sync automation, any private infrastructure, or production Docker services. No workflow schedules, deployments, image publication, or PR-writing permissions are included in v01.

## Why a separate repo

The personal ROMarr fork's `main` is maintained by a guarded **fast-forward-only** sync with upstream. Adding controller-only commits to fork `main` could create divergence and break that process. This standalone controller tests immutable public fork commits without committing anything to ROMarr.

## Prerequisites and source of truth

- The **public** `TenchiMisaki/romarr-ci-controller` repository is initialized and its six v01 source files were published to `main` at commit `a1134a2bd29e2163eae52929d6f1c4459982db28` (November 14, 2026). Their Git blob hashes were independently read back and matched the original v01 ZIP. Do not add Actions secrets or additional workflows without a separate review.
- GitHub Actions must be enabled. Stage 1 has **only** `workflow_dispatch`; it does not auto-run on pushes or a timer.
- Official ROMarr `main` `AGENTS.md`, `pytest.ini`, `.github/workflows/docker.yml`, and `.coderabbit.yaml` remain the authoritative external project conventions. The controller doesn't change those files.
- Proven external CI dependencies: `rom-hub` Git commit `02e9a1dbc7ebca5191b4a977233a4d6d0466ed4b` and Archive.org fixture repo tag `v0.4.1`, resolved to `3b49c1c67ccedfc5f072c19e3dd4990fec0b0d5f`. GitHub action dependencies are pinned by complete reviewed tag SHAs.

## Manual execution

Open the controller repository → **Actions** → **ROMarr pytest - Manual CI pilot** → **Run workflow**. To retest the baseline, select `target=main`, `scope=full`, leave `expected_sha` blank (the runner pins identical upstream/fork `main` during preflight); `pr_number` is ignored for main. The initial baseline was accepted on November 14, 2026, before archive prerequisites were added.

The archive-tool baseline was accepted in [run #43629839935](https://github.com/TenchiMisaki/romarr-ci-controller/actions/runs/43629839935). To test a ROMarr PR head, select `target=pull_request`, `pr_number=25`, `scope=full`, and leave `expected_sha` blank or supply the **currently verified** complete 40-hex head. Repeat separately for PR #21 as appropriate. Each run fetches exact metadata, checks out the immutable SHA, runs pytest, and independently rechecks live heads and source status. A changed head/base results in `STALE_OR_UNVERIFIED`, not a false current-head PASS.

## Evidence and safety

The runner captures private raw pytest output/JUnit XML only in the GitHub-hosted job's temporary storage. **Do not upload these raw files into a public repository.** Public artifacts contain `summary.json`, `postcheck.json`, `HANDOFF.md`, `manifest.json`, and `testcases.json` only when JUnit accounting actually succeeds. The case file contains anonymous ordinal IDs and pass/fail/error/skip states, without test names, input parameters, absolute paths, tracebacks, or credentials. Hashes of temporary private XML/logs are evidence *identifiers*, not a claim those ephemeral originals are durably retained or independently retrievable later.

- `TEST`, `COLLECTION`, `ENVIRONMENT` and `SOURCE` are separate status gates.
- A pytest zero exit is **not** an overall PASS if JUnit totals disagree with serialized cases (`unittest.subTest()` mismatch), if a required regression is skipped because Node is absent, if evidence is invalid, or if PR/base/source moved.
- Node.js 24 is deliberately installed. If a particular first-party regression still skips for an unexpected dependency, inspect that skip and do **not** claim complete required coverage from pytest exit zero alone. The first pilot reports actual skip counts; subsequent acceptance must review any unexpected skips.
- The `structural` scope runs ROMarr's documented invariant tests; `full` runs the default offline suite using `pytest.ini` (`not network`). Neither runs network-marked tests, production Docker, a browser, or private homelab APIs.
- For all executable jobs the target is **GitHub Actions / `ubuntu-24.04` runner / `TenchiMisaki/romarr-ci-controller` job**, not private systems. The scripts verify controller identity before invoking test code.
- The controller's `GITHUB_TOKEN` is used only in read-only GitHub metadata steps. Checkout credentials are not persisted; no user-generated token, homelab secret, GitHub App installation change, or CodeRabbit Autofix is needed.
- GitHub Actions build logs and artifacts in a public repository are visible to others; never feed private test fixtures, credentials, ROM files, private paths, or raw infrastructure logs into this system.

## Handoff to ChatGPT

For **controller development**, ask: "Continue Stage 2 in [controller PR #1](https://github.com/TenchiMisaki/romarr-ci-controller/pull/1). Read the latest controller source, unit-test workflow, README and VALIDATION; use the accepted Stage 1 pytest controller without rebuilding it. Finish eligible-PR discovery, deduplicated dispatch and CodeRabbit monitoring under the separate approval gates. Keep ROMarr feature PRs, including upstream #188, out of the controller implementation scope."

The ordinary ChatGPT session remains user-initiated. The controller cannot automatically summon ChatGPT or create source changes. This is **the baseline manual-dispatch pytest milestone**, before a separate authenticated scheduler/review monitor is installed and accepted.

## Recovery and modification boundaries

Remove or disable the workflow **only in the standalone controller repo** to stop runs. Never change existing sync mechanisms, the ROMarr fork's protected `main`, private Git tokens, upstream branches or production to troubleshoot a controller failure. Keep the original candidate package and its verification receipts. If an Actions run fails, retrieve the sanitized artifact/run steps first; distinguish environment/collector/actual test failures and retain prior successful evidence. Stage 2 polling will require a separate design and acceptance review.

## Validation status

The initial manual full baseline [run #43628828155](https://github.com/TenchiMisaki/romarr-ci-controller/actions/runs/43628828155) is **PASS** at ROMarr source `3aeede0ff0e3b9ad0b305d6e4baaaa1252bb0176`: 3,814 passed, 19 skipped, 0 failed/errors; test/collection/source verification passed. The **archive-tool-enabled** full baseline [run #43629839935](https://github.com/TenchiMisaki/romarr-ci-controller/actions/runs/43629839935), controller revision `0bfc16d3294ca73570c407fc69c73c5743fc8a67`, is **PASS** on the same ROMarr source: **3,831 passed / 2 skipped / 0 failures/errors**, pytest exit 0, collection PASS, source UNCHANGED, final GitHub job SUCCESS. Runner installation of missing `libarchive-tools` and `unar` completed, `bsdtar`, `7z`, `unar`, and `lsar` were found, and ROMarr detected a split-RAR reader (`7z`). The downloaded five-member artifact `romarr-pytest-handoff-43629839935-1` passed ZIP CRC, manifest SHA-256 and individual case-count reconciliation (**3,833 cases**). The 17 fewer skipped cases are observed but cannot be attributed to specific tests from the anonymous public report alone. Both are **source tests only**, not Docker, browser or production acceptance. The subsequent manual controller [PR #25 test #43630641521](https://github.com/TenchiMisaki/romarr-ci-controller/actions/runs/43630641521) passed at ROMarr source `1e5796032968f574b41772e1674d1d7a8d64d16c`: **3,864 passed, 2 skipped**, zero failures/errors, with source postcheck UNCHANGED, sanitized evidence and final gate PASS. Its 3,866 anonymous cases and artifact hashes were independently checked. **That is historical source evidence:** PR #25 later advanced to `0a54b3f`, so the controller has not yet validated its current head. PR #21's current head also remains unverified by this controller. Unattended scheduling and CodeRabbit monitoring remain **NOT INSTALLED**.

## Stage 2 development — separate controller PR #1 (November 14, 2026)

[Controller PR #1](https://github.com/TenchiMisaki/romarr-ci-controller/pull/1) is the existing, **open, unmerged** Stage 2 review branch `feature/stage2-pr-watch`. It was not overwritten by ROMarr's upstream PR #188. It adds a **manual-only** candidate watcher for the personal fork's open, non-draft code PRs; `review/` staging branches and `notes/` backlog branches are excluded. Legitimate stacked feature PRs remain eligible. Candidate dispatch includes full-head SHA identity, source freshness verification, controller-owned immutable claim tags, and bounded duplicate/parallel dispatch protection. Ambiguous writes retain their claims for investigation rather than retrying automatically. This design still has a documented limitation: the claim key uses PR + head SHA, not base SHA.

The new [read-only PR unit-test workflow](https://github.com/TenchiMisaki/romarr-ci-controller/actions/workflows/controller-unit-tests.yml) uses Python 3.13 and pinned pytest 9.2.0 for controller subprocess tests. [Run #43640462488](https://github.com/TenchiMisaki/romarr-ci-controller/actions/runs/43640462488) passed **57 controller tests** on the code revision that includes the narrowed API write allowlist and stacked-feature eligibility. The earlier unit workflow failure was caused by missing pytest in that temporary CI job, not a ROMarr source-test regression; the job setup was corrected. Further documentation commits require their own final-head readback.

**Not accepted or enabled:** the Stage 2 `romarr-pr-watch.yml` workflow is still on a feature branch, has no schedule, and cannot be manually dispatched from the GitHub Actions UI until a separately approved version exists on default `main`. Live claim-tag creation, auto-dispatch/run-ID correlation, persistent scheduler, CodeRabbit monitoring, failure recovery, and end-to-end Stage 2 acceptance remain **NOT TESTED / NOT INSTALLED**. The accepted `romarr-pytest.yml` Stage 1 manual workflow and `main` have not been changed by this PR. Do not merge or enable write/scheduled dispatch without separate approval.
