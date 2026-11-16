# ROMarr CI Controller — Fully Automated Project 2

**Working backlog — November 15, 2026 evidence baseline.** This is the implementation and acceptance plan for [draft PR #23](https://github.com/TenchiMisaki/romarr-ci-controller/pull/23), not an instruction to deploy ROMarr or automatically approve privileged work. Recheck live repository refs, runs and reviews before acting: dated results below do not prove a later run occurred.

## Goal and boundaries

I want to replace routine manual Windows/SSH ROMarr source-test coordination with a GitHub-hosted controller that can follow a change from discovery through testing, review and permitted follow-up. It should do that against an **exact source revision**, produce evidence that can be independently checked, and retain a separate, owner-controlled manual test fallback until the hosted replacement is independently accepted.

The intended loop is:

1. Discover eligible ROMarr fork PRs and changed **head or base** revisions on roughly a five-minute cadence, without assuming GitHub cron runs exactly on time.
2. Confirm the repository, PR number, full head/base SHAs, controller revision, dependencies, eligible workflow and immutable claim identity.
3. Deduplicate revisions and, **only after owner-controlled enablement**, dispatch at most one bounded, exact-source pytest run for an eligible change; record the actual run ID.
4. Independently reconcile the test process and exit, anonymized JUnit case accounting, source freshness, job steps, artifact digest, ZIP/manifest, and test-skip policy.
5. Follow CodeRabbit's real review and unresolved threads, together with other relevant CI; review completion alone does not mean no findings.
6. Investigate real defects, make only authorized personal-fork corrections, then retest and request review again on the changed SHA.
7. Publish sanitized actionable status, continue when safe, alert on real failures or missed work and recover from interruptions without quietly authorizing an upstream PR, merge, release or deployment.

This follows four broad phases: **A** discovery and architecture; **B** unattended exact-source pytest; **C** CodeRabbit investigation and authorized correction; and **D** decisions, alerts and recovery. Phase A has substantial accepted pieces. B–D are still incomplete.

## What has been built and verified

### Stage 1 — Manual source-pinned pytest and sanitized receipts

The manual `.github/workflows/romarr-pytest.yml` pins the source head/base and uses the required Python, Node and archive dependencies. Test, evidence collection, source identity and environment outcomes are classified separately; a failed collector is not automatically a ROMarr code failure. Public evidence uses anonymous per-case outcomes, a summary, postcheck, manifest and hash/ZIP integrity information. Private raw JUnit and logs do not belong in public artifacts.

**Accepted scope:** manual hosted tests and receipt generation on the tested revisions, not autonomous scheduling or deployment. See [VALIDATION.md](https://github.com/TenchiMisaki/romarr-ci-controller/blob/main/VALIDATION.md) for the detailed run records. Do not rerun immutable accepted source simply to generate another copy of the same results.

### Stage 2A/B/C — PR watcher, revision claims and manual one-target dispatch

Controller PRs #1–#6 established eligibility filtering, exact head/base identity, legacy/v2 claim handling, a one-target manual dispatch path and a run-ID ledger. Draft, backlog and review PRs are excluded from ordinary eligible candidates.

[ROMarr fork PR #28](https://github.com/TenchiMisaki/romarr/pull/28) has a v2 claim and run-ID record associated with [pytest run #43676714571](https://github.com/TenchiMisaki/romarr-ci-controller/actions/runs/43676714571). Its verified receipt reported **4,029 passed, four skipped, zero failed or errored**. The four skips still require an explicit policy decision. This acceptance does **not** enable unattended dispatch, justify a duplicate run or silently clear a partial claim.

### Stage 3 — Scheduled read-only PR and CodeRabbit monitor

Controller PRs #7–#11 added PR/CodeRabbit metadata, a seven-day sanitized summary, an advisory next-untested candidate, and the UTC schedule `2-59/5 * * * *`. An earlier [native schedule run #43689231985](https://github.com/TenchiMisaki/romarr-ci-controller/actions/runs/43689231985) succeeded. The independent external read-only fallback also produced a successful [dispatch run #43690137352](https://github.com/TenchiMisaki/romarr-ci-controller/actions/runs/43690137352) after its JSON-response truncation issue was corrected.

**Boundary:** these results predate the later merged Stage 5 revision. This monitor is read-only; it is not a pytest runner, a receipt accepter or an auto-fix system. Reboot persistence, missed-run alerts, source/fallback collision handling and credential renewal remain separate checks.

### Stage 4 and 4A — Trusted receipt collection and hosted manual verification

[Controller PR #19](https://github.com/TenchiMisaki/romarr-ci-controller/pull/19) implemented immutable receipt acceptance. [PR #20](https://github.com/TenchiMisaki/romarr-ci-controller/pull/20) added bounded GET-only collection with approved HTTPS redirect hosts, no forwarding of storage tokens, a **16 MiB artifact limit**, ZIP digest/member/case checks and final live PR/run/tag freshness validation.

[PR #21](https://github.com/TenchiMisaki/romarr-ci-controller/pull/21) merged the manual read-only receipt workflow with `contents: read` and `actions: read`, plus negative permission/trigger tests. Its accepted source-head CI passed **251 unit tests** and the completed CodeRabbit review had no remaining actionable threads. Stage **4A was subsequently exercised**, not merely merged: [hosted run #43724559960](https://github.com/TenchiMisaki/romarr-ci-controller/actions/runs/43724559960) verified the existing PR #28 claim, run and artifact and returned `RECEIPT_VERIFIED_SKIPS_REQUIRE_POLICY`. It did not trigger pytest again.

### Stage 5 — Read-only receipt integration into monitoring

[Controller PR #24](https://github.com/TenchiMisaki/romarr-ci-controller/pull/24) merged the receipt inspector into the read-only monitor. The exact reviewed head passed [Ubuntu CI #43732634653](https://github.com/TenchiMisaki/romarr-ci-controller/actions/runs/43732634653) with **300 tests passed and no skips/errors/failures**, plus compilation, artifact and live metadata smoke. CodeRabbit completed with no actionable findings or unresolved review threads.

The [feature-branch monitor run #43733394087](https://github.com/TenchiMisaki/romarr-ci-controller/actions/runs/43733394087) and three subsequent post-merge `workflow_dispatch` runs ([08:14](https://github.com/TenchiMisaki/romarr-ci-controller/actions/runs/43734324585), [08:24](https://github.com/TenchiMisaki/romarr-ci-controller/actions/runs/43735269131) and [08:34](https://github.com/TenchiMisaki/romarr-ci-controller/actions/runs/43736203053), Pacific time on November 15) produced verified sanitized receipt summaries. PR #28 remained `RECEIPT_VERIFIED_SKIPS_REQUIRE_POLICY`; PR #29 was `NOT_DISPATCHED`.

**Still missing:** a genuine native GitHub `schedule` event on the merged Stage 5 controller `main` revision `300a40331db03811b3e9994bd4392d030b22740e`. The three observed `workflow_dispatch` events do not prove native scheduled delivery or identify the particular actor that initiated them. Alert delivery, fallback collisions, reboot persistence and token recovery remain unaccepted. Stage 5 must not dispatch pytest.

### Stage 6 milestone — first real ROMarr source test on GitHub-hosted runners (November 15, 2026)

[Controller PR #26](https://github.com/TenchiMisaki/romarr-ci-controller/pull/26) was merged after the updated exact-head CodeRabbit review completed without new actionable findings. The earlier review finding involving JUnit XML child-element truthiness was corrected, tested with negative fixtures, and marked resolved/outdated. The manual workflow pins the Python Docker base image by digest and does not change the read-only Stage 5 monitor.

[Hosted manual source-pilot run #43775641984](https://github.com/TenchiMisaki/romarr-ci-controller/actions/runs/43775641984) completed **successfully** on controller `main` commit `dc2d263491b19f5963337ef62f098f84558fbf91` (`workflow_dispatch`, attempt 1). The source-test job fetched pinned ROMarr fork commit `3c9896d2406d331c4f25c8a9f661c711ffe51745` and ran `tests/test_wired.py` in the restricted, network-disabled Docker test container. Its log reported **70 anonymous passing test cases**. The separate validation job also completed successfully and confirmed the bounded 70-case handoff and expected source revision. Job-by-job logs, rather than only the workflow status, were checked.

**Accepted milestone:** a real, pinned ROMarr test file successfully ran in the hosted source job, and a separate hosted job checked its advisory, anonymous output. This follows the successful synthetic two-job success/failure canary in [PR #25](https://github.com/TenchiMisaki/romarr-ci-controller/pull/25).

**Not accepted or enabled:** this fixed-revision manual pilot does not test a changing PR head/base or provide a trusted PR receipt. It explicitly prints `TEST_ACCEPTED: false`, `PUBLICATION_AUTHORIZED: false`, and `PR_SOURCE_TESTED: false`. Comprehensive source-test coverage, independent provenance and trusted allowlisted artifact publication, negative/race/recovery tests, Stage 5 native schedule acceptance, skipped-test policy, deduplication, alerting, owner-controlled unattended dispatch/disarm, and replacement of the manual fallback remain open. Do not enable unattended pytest or retire the fallback based on this milestone.

**Next engineering step:** implement the trusted publisher/allowlisted receipt boundary, prove full source/run/commit integrity and negative cases on hosted runners, then separately review and authorize one tightly scoped unattended trial.

## The next engineering work and acceptance gates

### Stage 5 — Finish operational scheduling acceptance

Observe a real native scheduled run on the applicable merged `main` revision and inspect its actual event, SHA, run attempt, jobs, steps, sanitized output and artifact integrity. Compare this with independent fallback behavior rather than treating any `workflow_dispatch` as a schedule event. Check collision/duplicate avoidance over multiple intervals. Record a missing run as **NOT OBSERVED**, not automatically a failed workflow.

The four PR #28 pytest skips also need a specific policy determination; they must not be silently counted as clean tests.

### Stage 6 — Governed unattended pytest (Phase B): BLOCKED

**Security design gap discovered on the inspected Stage 5 controller source:** the manual `.github/workflows/romarr-pytest.yml` installs dependencies and runs tests controlled by the selected ROMarr source in a runner later used by the token-bearing `controller/target.py postcheck`. The public evidence directory exists before untrusted execution, and the later upload may include members beyond the receipt files that `controller/evidence.py` actually validates. This is a **potential tampering and unintended-publication path**. No exploit or leaked credential was verified.

Before enabling any unattended runner, isolate untrusted dependency installation and pytest from fresh, minimally privileged trusted verification and artifact publication. The trusted side must verify immutable source/run provenance and accept **only strictly allowlisted files**. Keep the Stage 5 monitor GET-only; do **not** grant it write/dispatch permissions.

The separate dispatch controller needs an explicit **disabled-by-default owner enable/disarm**, one exact eligible PR/head/base per cycle, independently revalidated identity, immutable claim-before-dispatch, a unique run-ID ledger, bounded concurrency/rate and safe handling of stale or duplicate work. Do not blindly retry uncertain API POSTs. If a claim is created but dispatch or run-ID tagging fails, keep it in an explicit reconciliation state: a later worker must not silently retry, delete the claim or trigger another test. Retain the existing manual one-target path for recovery.

**Required negative and recovery cases:** new PR; changed head or base; unchanged no-op; draft/backlog/review exclusion; concurrent workers; interrupted run; partial claim/tag failure; stale source; corrupted/extra evidence member; tampered test or trusted script; expired/oversized artifact; bad redirect or credentials; missing GitHub jobs; transient GET failure; uncertain POST; and permission/authentication errors. Failed identity, integrity or authorization checks stop dependent operations rather than silently changing targets.

**Acceptance:** exact-source Linux tests, completed exact-head CodeRabbit review and findings assessment, required public-content/security scan, successful negative/race/partial-write tests, one separately owner-authorized live unattended trial, independent receipt reconciliation, observed no-duplicate behavior and a working disarm path. Until then **Stage 6 is NOT ENABLED / NOT ACCEPTED**.

### Stage 7 — CodeRabbit follow-up and permitted fork-only repair (Phase C)

Build stateful monitoring of the actual CodeRabbit check, reviewed SHA, complete review summary, inline comments, unresolved/outdated threads and quality checks. Green execution status alone is not zero defects. Handle review queues and rate limits with finite polling and attempt budgets.

For a material finding, trace real code and callers; distinguish confirmed source defects from review mistakes, platform/test-environment problems and evidence-collection failures. Under existing fork-only authority, make the smallest change in an isolated branch, run the affected and broader tests justified by the risk, and request review on the final SHA. Preserve the tested source identity and do not automatically promote an upstream-connected branch.

**Not authorized by this stage:** new official upstream PRs/comments, upstream-connected branch promotion, automatic merge, deployment or protected documentation publication. Those remain independent owner gates.

### Stage 8 — Decision engine, alerts and recovery (Phase D)

Keep a durable record for each immutable revision: TEST, COLLECTION, ENVIRONMENT, SOURCE, REVIEW, skip policy, other CI, claims, actual workflow/run IDs and the next permitted action. Distinguish **PASS, FAIL, SKIPPED, BLOCKED, NOT TESTED, COLLECTION FAILED, STALE** and pending review instead of flattening everything into green/red.

Continue from verified states—new revision, pending run, completed receipt, failed test, real review finding, corrected head or rate limit—without repeating work or acting on stale data. Test missed-run and failed-job alerts, actual notification delivery, native/fallback collision avoidance, restart persistence, credential expiry/renewal, interrupted claims, API failures, disarm/rollback and artifact retention. A configured timer, successful dispatch or one happy-path receipt is not full operational acceptance.

Keep an existing, independently operated test/recovery path available as a **manual fallback** until the hosted workflow is accepted as primary. Retire only genuinely redundant manual work after separate owner approval and proof.

## Related coverage and supporting evidence

The controller handles source-level CI and review evidence. Docker image/platform builds, browser/mobile tests, native Windows executable packaging, live UI/API behavior, official upstream contributions, release and production deployment each require independent validation and authorization. A passing controller receipt does not prove any of those areas.

**Stage 5 Windows validation context:** The offline Windows runs surfaced an OS-restricted real-symlink test, missing Bash in existing Linux-oriented tests and Unix process-group timeout incompatibilities. The 300-test Windows suite completed with **10 errors and one skip**, so it was **not** a Windows PASS. The accepted 300-test Linux CI result above was a separate run on the reviewed Stage 5 head; it does not retroactively clear the earlier Windows errors. Individual filenames, exception traces, launcher repair and hashes are in the original Git commits and test records, not duplicated as an incident log here.

**Security/publication:** Earlier owner-run Gitleaks 8.30.1 directory and Git-history checks passed for the exact seven-file Stage 5 candidate and a separately published companion append. A later companion amendment was published with an **owner-authorized scanner exception**, manual privacy review and limited secret-pattern checks; the maintained scanner and newly reachable history were **NOT VERIFIED** for that amendment. Do not generalize any prior scan to new source or weaken the standing prepublication gate.

**Separate fork-main sync observation:** At the November 15 check, ROMarr fork `main` was reportedly two commits behind official upstream after [ROMarr PR #192](https://github.com/BlizzHacker/romarr/pull/192), with a potential ancestry-safe fast-forward. No sync was performed in that work session because the required scan/history gate was unavailable. Recheck the live refs and gate before any future action; do not treat an eligible fast-forward as completed or refresh unrelated branches.

**Documentation follow-up:** The controller `README.md` and `VALIDATION.md` status introductions and a monitor workflow header were noted as referring to older Stage 3/Stage 5-candidate status. Those are documentation discrepancies, not demonstrated controller failures; amend under the normal publication checks without changing cron as a cosmetic fix.

## Resume work safely

Before continuing, review this backlog, [controller README](https://github.com/TenchiMisaki/romarr-ci-controller/blob/main/README.md), [VALIDATION.md](https://github.com/TenchiMisaki/romarr-ci-controller/blob/main/VALIDATION.md), applicable repository `AGENTS.md`, and current source, GitHub Actions jobs and CodeRabbit reviews. Reconcile the controller's current `main` revision, relevant fork branches, target PR head/base SHAs and claim/run identities. Previous green tests belong to their exact revisions, not a later moving head.

**Start with the unfinished native Stage 5 schedule acceptance and Stage 6 isolation/design**, without repeating accepted source tests or silently enabling more privileged automation. Stop only at the real security, owner-controlled GitHub, upstream or production boundaries.
