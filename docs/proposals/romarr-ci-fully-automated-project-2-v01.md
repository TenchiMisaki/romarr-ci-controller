# Fully Automated Project 2 — ROMarr CI Controller

I'm building this controller to take repetitive manual work out of ROMarr development. The goal is to recognize relevant PR changes, test the exact source revision, check the results and CodeRabbit findings, and eventually handle routine follow-up without needing someone to manually drive every step.

This is the working plan for [backlog PR #23](https://github.com/TenchiMisaki/romarr-ci-controller/pull/23). It's not a request to merge code, change ROMarr's installed version, or enable privileged automation.

## What's working

The controller can run source-pinned pytest manually and generate sanitized test receipts. It also has PR eligibility checks, revision-aware claims, and a manual one-target dispatch path. A separate read-only monitor can inspect pull requests and CodeRabbit activity.

The receipt verifier can check the identity and integrity of an existing test run without rerunning the tests. [The hosted manual verification](https://github.com/TenchiMisaki/romarr-ci-controller/actions/runs/43724559960) worked against ROMarr PR #28.

**Stage 5 has been merged.** [PR #24](https://github.com/TenchiMisaki/romarr-ci-controller/pull/24) added read-only receipt verification to the monitor. Its [Linux CI run](https://github.com/TenchiMisaki/romarr-ci-controller/actions/runs/43732634653) passed 300 tests with no skips or failures, and CodeRabbit's completed review reported no actionable findings. Three subsequent `workflow_dispatch` runs on the merged version produced valid, sanitized reports.

That confirms the tested read-only path, **not** fully unattended operation. We still need to observe and verify a genuine GitHub `schedule` run on the merged Stage 5 revision. Manual or fallback dispatches aren't interchangeable with native scheduled runs.

The existing receipt for [ROMarr PR #28](https://github.com/TenchiMisaki/romarr/pull/28) reports **4,029 passed and four skipped**. Those skips still need a policy decision; they are not an unconditional pass. PR #29 was not automatically dispatched.

## What's holding up unattended testing

Stage 6 is **not enabled**. The current manual pytest workflow runs PR-controlled tests and dependencies in the same runner environment as a later authenticated postcheck. It also needs stricter handling of which evidence files can be uploaded. That creates a potential opportunity to tamper with trusted verification or public artifacts; no exploitation or secret exposure has been established.

Before we automate dispatch, we need to separate untrusted test execution from trusted verification and artifact publishing, reject unexpected evidence files, and prove that interrupted or competing runs cannot trigger duplicate tests. These protections need focused negative tests, exact-revision CI and review, and the required public-content security checks.

## Next work

1. Confirm a real native scheduled Stage 5 run and review the four existing pytest skips.
2. Fix the test-runner trust boundary and artifact allowlisting without granting write permissions to the read-only monitor.
3. Build a disabled-by-default, owner-controlled unattended dispatch path with revision checks, deduplication, rate limits, and safe recovery from partial claims.
4. Add CodeRabbit follow-up that checks actual review findings and makes only permitted fork-side corrections, followed by relevant tests and re-review.
5. Finish meaningful alerts, missed-run detection, restart and credential recovery, and independently verified fallback behavior.

## Boundaries

The controller is separate from the ROMarr application and its installation. A passing workflow doesn't authorize an upstream submission, merge, release, Docker change, or production deployment. The existing CT107 native test environment remains an on-demand fallback until the hosted approach is independently accepted.

This backlog tracks the next meaningful changes and their acceptance. Individual GitHub Actions runs, failures, patches, review comments, and earlier attempts remain available in their original GitHub records instead of being copied into a running diagnostic log here.

*Status reflects the verified November 15, 2026 work; recheck live source and workflow results before changing code or enabling automation.*
