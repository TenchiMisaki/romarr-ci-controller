# ROMarr GitHub pytest controller — manual pilot v01

**Status: PREPARED / NOT INSTALLED / NO GITHUB-HOSTED TEST EXECUTED.**

This is a separate **public** GitHub repository to host ROMarr test orchestration. It does **not** modify `TenchiMisaki/romarr`, `BlizzHacker/romarr`, any separate fork-sync automation, any private infrastructure, or production Docker services. No workflow schedules, deployments, image publication, or PR-writing permissions are included in v01.

## Why a separate repo

The personal ROMarr fork's `main` is maintained by a guarded **fast-forward-only** sync with upstream. Adding controller-only commits to fork `main` could create divergence and break that process. This standalone controller tests immutable public fork commits without committing anything to ROMarr.

## Prerequisites and source of truth

- Create **public** GitHub repository `TenchiMisaki/romarr-ci-controller`, initialize it with a README to establish its `main` branch, and do not add Actions secrets or additional workflows. The verified package README will replace that initial placeholder during publication. Once the repository exists and the GitHub connection has access, the staged files can be published and read back.
- GitHub Actions must be enabled. Stage 1 has **only** `workflow_dispatch`; it does not auto-run on pushes or a timer.
- Official ROMarr `main` `AGENTS.md`, `pytest.ini`, `.github/workflows/docker.yml`, and `.coderabbit.yaml` remain the authoritative external project conventions. The controller doesn't change those files.
- Proven external CI dependencies: `rom-hub` Git commit `02e9a1dbc7ebca5191b4a977233a4d6d0466ed4b` and Archive.org fixture repo tag `v0.4.1`, resolved to `3b49c1c67ccedfc5f072c19e3dd4990fec0b0d5f`. GitHub action dependencies are pinned by complete reviewed tag SHAs.

## First execution, only after publishing to its own `main`

Open the controller repository → **Actions** → **ROMarr pytest - Manual CI pilot** → **Run workflow**. For the **first** baseline check, select `target=main`, `scope=full`, leave `expected_sha` blank (the runner pins the identical upstream/fork `main` commit during preflight). `pr_number` is ignored for main.

Once that run actually passes and its evidence integrity is checked, select `target=pull_request`, `pr_number=25`, `scope=full`, and leave `expected_sha` blank or supply the **currently verified** complete 40-hex head. Repeat separately for PR #21 as appropriate. Each run fetches exact metadata, checks out the immutable SHA, runs pytest, and independently rechecks live heads and source status. A changed head/base results in `STALE_OR_UNVERIFIED`, not a false current-head PASS.

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

Ask: "Continue ROMarr PR #25. Read its latest GitHub pytest controller run, `HANDOFF.md`, sanitized evidence and current CodeRabbit findings; evaluate any failures and correct valid issues under our fork-first procedures."

The ordinary ChatGPT session remains user-initiated. The controller cannot automatically summon ChatGPT or create source changes. This is **the baseline manual-dispatch pytest milestone**, before a separate authenticated scheduler/review monitor is installed and accepted.

## Recovery and modification boundaries

Remove or disable the workflow **only in the standalone controller repo** to stop runs. Never change existing sync mechanisms, the ROMarr fork's protected `main`, private Git tokens, upstream branches or production to troubleshoot a controller failure. Keep the original candidate package and its verification receipts. If an Actions run fails, retrieve the sanitized artifact/run steps first; distinguish environment/collector/actual test failures and retain prior successful evidence. Stage 2 polling will require a separate design and acceptance review.

## Validation status

The packaged scripts are verified only to the extent documented with the delivery receipt. Live GitHub runner execution, upstream dependency installation, exact PR tests, full CI acceptance, scheduling, CodeRabbit monitoring and ChatGPT handoff retrieval remain **NOT TESTED** until demonstrated from an actual published controller run.
