# ROMarr CI Controller — Fully Automated Project 2

## Current Stage 6 continuation — November 16, 2026 (Pacific)

This section supersedes the older open-review and pending-canary status below;
the dated earlier checkpoints remain preserved.

- **MERGED:** Controller PR #30 merged into `main` at
  `4e474dc54a133a490e75540fe021f1275f376245`. The merge tree is
  `06a57925415a7191dd9ab40286b31476b2a85a44`.
- **HOSTED MANUAL CANARY PASS:** [Run #44026734606](https://github.com/TenchiMisaki/romarr-ci-controller/actions/runs/44026734606)
  completed successfully on that merge, event `workflow_dispatch`, attempt 1.
  Independent API reads and job logs confirmed the isolated source step,
  allowlisted advisory upload and separate provenance-verifier step all passed.
  Source PR #31 used head `ea3d78139f7c10931101142cae5b1fc78ad00635`
  and base `0e48c8855fbba318103f1b9986275eb2bb614580`.
  The verifier reported `ADVISORY_COLLECTED_NOT_TEST_ACCEPTED` and
  `TEST_ACCEPTED: false`. The earlier failed canary is superseded by this success.
- **REUSED:** The recorded 310 unittest / 296 Stage 6 pytest final CI evidence,
  exact implementation-tree/history Gitleaks 8.30.1 evidence and completed
  CodeRabbit findings assessment remain valid for their recorded implementation.
  No source-test rerun was needed to reconcile this status.
- **BOUNDARY:** The workflow remains manual/advisory-only. Trusted complete test
  receipts, unattended pytest, automatic remediation, deployment and fallback
  retirement are not enabled or accepted.

### Remaining coverage and implementation order

| Area | Existing evidence | Remaining acceptance |
| --- | --- | --- |
| Exact source and base freshness | Existing v32/v35/v36 positive and rejection tests; successful manual canary | Source movement at the future actual dispatch boundary and complete receipt correlation |
| Advisory bytes and transport | Existing archive/member/digest, redirect, job/step and source sanitizer regressions | Governed complete receipt acceptance, expired artifact and live transient failure recovery |
| Concurrency and duplicate claims | Existing manual claim mechanisms are separate from advisory execution | Durable cross-run claims, one global outstanding dispatch, changed revision and duplicate policy |
| Disarm and restart | No accepted unattended adapter | Owner-only policy, policy generation, restart persistence, in-flight boundary |
| Partial write / uncertain POST | No accepted live automatic recovery | Persist uncertainty before POST, unique run-ID reconciliation, no blind retry or claim deletion |
| Operations | Successful read-only monitor runs are dated observations | Native/fallback collision, sustained cadence, real alert delivery, credential renewal and recovery |

**Next isolated change:** develop an offline, disabled-by-default local claim
ledger prototype and targeted negative/race/restart tests. It must have no network
adapter, credentials, workflow integration, automatic reset or receipt acceptance.
A local SQLite race test is not distributed-scheduler acceptance. New source
publication still needs final-tree/history scans, exact-head CI and CodeRabbit.

**Recovery design:** preserve ambiguous claims and evidence; do not retry uncertain
dispatch writes or erase a reservation to make a worker proceed. A later adapter
needs independently authenticated run/source correlation, explicit reconciliation,
bounded rate/concurrency and tested storage/credential recovery. Disarm prevents
future attempts but cannot undo an already-issued request. Keep the manual fallback
until separate operational acceptance.

## Historical Stage 6 review — November 16, 2026 (Pacific)

The corrected manual exact-PR advisory implementation is published in [review PR #30](https://github.com/TenchiMisaki/romarr-ci-controller/pull/30), final implementation head `b874db533bc0bc76f6c33b6aec57f52d6d627572`: two isolated review commits above `8500d14500663050db43b22d93c4cb53c491c498`. The final diff contains 26 files (25 additions and one modified controller CI workflow). This section supersedes older pending-publication and v31-next-step wording below; dated earlier evidence remains preserved.

- **Publication integrity:** All 26 final public file blob hashes matched the scanned outgoing payload. The final hosted CI merge tree `06a57925415a7191dd9ab40286b31476b2a85a44` exactly matched the scanned implementation tree. The new review branch is isolated; `main` and this backlog branch retain their separate roles.
- **Prepublication security:** Gitleaks 8.30.1 passed the corrected payload directory, complete final tree, and exact server-created outgoing commit range with zero findings. A separate synthetic positive control produced the expected detection. The existing 23-file privacy/provenance review was reused after hash reconciliation; the two CI coverage files received current review. No private reports or raw source-test logs were published.
- **Hosted regression CI:** [Run #44022580952](https://github.com/TenchiMisaki/romarr-ci-controller/actions/runs/44022580952), associated with this PR head, completed successfully on the PR merge ref `9547dfe4f120fdfc124e5b306b5a06eee8699740`. Logs recorded **308 unittest cases passed** and **294 Stage 6 pytest cases passed**, with zero test failures or skips. Two expected warnings came from duplicate-member ZIP rejection fixtures. Compilation, the public README artifact smoke, and live read-only monitor checks also passed. The earlier 294-test offline evidence was reused during preparation rather than rerun to produce another candidate.
- **CodeRabbit follow-up:** The initial 25-file exact-head review identified one valid missing transitive import in the source job's sparse checkout. Commit `b874db533bc0bc76f6c33b6aec57f52d6d627572` adds `controller/stage6_pr_identity_v32.py` to that checkout and adds `tests/test_stage6_pr_sparse_checkout.py`. Its positive regression runs the real sanitizer using only the declared files and produces an advisory; its negative regression omits the identity module and reproduces the original import failure. Both passed locally. The finding was replied to and resolved after hosted regression acceptance. The incremental CodeRabbit check completed successfully on `b874db533bc0bc76f6c33b6aec57f52d6d627572`; the updated review summary reported no new actionable comments, and all inline review threads were resolved. The initial full review and the final incremental review are distinct evidence scopes.
- **Final hosted CI:** [Run #44023862157](https://github.com/TenchiMisaki/romarr-ci-controller/actions/runs/44023862157), head `b874db533bc0bc76f6c33b6aec57f52d6d627572`, completed successfully on merge ref `da6c80563a285808fe296148252bc790d4d68310`. Logs recorded **310 unittest cases passed** and **296 Stage 6 pytest cases passed**, with zero failures/skips and the same two intentional duplicate-ZIP fixture warnings. Compilation, public README artifact smoke and live read-only monitor checks passed. Gitleaks 8.30.1 also passed the revised complete tree and exact two-commit outgoing history with zero findings. These controller tests do not establish a successful hosted run of the new manual exact-PR workflow.
- **Implementation map:** `.github/workflows/stage6-pr-manual-candidate.yml` contains the manual-only source/verifier jobs. `controller/stage6_pr_source_v42.py` handles isolated source-result sanitization; the identity, receipt, archive, branch, final-gate, collector, transport, entrypoint, discovery and live-run modules provide bounded independent verification. The paired `tests/test_stage6_pr_*.py` files exercise offline success and rejection paths. Controller PR CI now runs both unittest discovery and the Stage 6 pytest selection, with `PYTHONPATH=controller`, and includes the new workflow in its path filter.

**Next:** The PR #30 code-review cycle and hosted controller regressions are complete at the recorded head. Preserve that revision and prepare the separately controlled manual exact-PR hosted acceptance. The new manual exact-PR workflow has **not** been exercised as a hosted source run. A controlled manual canary, live PR/run/artifact provenance, negative/race/failure/recovery paths, scheduling/dispatch acceptance and owner acceptance remain distinct gates. Workflow availability on the default branch is not permission to merge this PR. Preserve the established manual fallback.

**Not enabled or accepted:** unattended pytest, automatic remediation, trusted changing-PR receipt acceptance, merging, deployment, and replacement of the established test method. The existing read-only monitor remains separate.

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

**Later native-schedule observation (November 15):** [run #43776973721](https://github.com/TenchiMisaki/romarr-ci-controller/actions/runs/43776973721) was a genuine `schedule` event, completed successfully on later merged controller `main` `dc2d263491b19f5963337ef62f098f84558fbf91` (attempt 1). This closes the narrow *not yet observed* evidence gap at that later revision; it does **not** retroactively establish a schedule event on the older `300a4033` head or sustained cadence. Subsequent successful `workflow_dispatch` events are independent fallback/external runs, not native-schedule proof. Native/fallback collision prevention, alert delivery, restart persistence and token recovery remain unaccepted. Stage 5 must not dispatch pytest.

### Stage 6 milestone — first real ROMarr source test on GitHub-hosted runners (November 15, 2026)

[Controller PR #26](https://github.com/TenchiMisaki/romarr-ci-controller/pull/26) was merged after the updated exact-head CodeRabbit review completed without new actionable findings. The earlier review finding involving JUnit XML child-element truthiness was corrected, tested with negative fixtures, and marked resolved/outdated. The manual workflow pins the Python Docker base image by digest and does not change the read-only Stage 5 monitor.

[Hosted manual source-pilot run #43775641984](https://github.com/TenchiMisaki/romarr-ci-controller/actions/runs/43775641984) completed **successfully** on controller `main` commit `dc2d263491b19f5963337ef62f098f84558fbf91` (`workflow_dispatch`, attempt 1). The source-test job fetched pinned ROMarr fork commit `3c9896d2406d331c4f25c8a9f661c711ffe51745` and ran `tests/test_wired.py` in the restricted, network-disabled Docker test container. Its log reported **70 anonymous passing test cases**. The separate validation job also completed successfully and confirmed the bounded 70-case handoff and expected source revision. Job-by-job logs, rather than only the workflow status, were checked.

**Accepted milestone:** a real, pinned ROMarr test file successfully ran in the hosted source job, and a separate hosted job checked its advisory, anonymous output. This follows the successful synthetic two-job success/failure canary in [PR #25](https://github.com/TenchiMisaki/romarr-ci-controller/pull/25).

**Not accepted or enabled:** this fixed-revision manual pilot does not test a changing PR head/base or provide a trusted PR receipt. It explicitly prints `TEST_ACCEPTED: false`, `PUBLICATION_AUTHORIZED: false`, and `PR_SOURCE_TESTED: false`. Comprehensive source-test coverage, independent provenance and trusted allowlisted artifact publication, negative/race/recovery tests, Stage 5 native schedule acceptance, skipped-test policy, deduplication, alerting, owner-controlled unattended dispatch/disarm, and replacement of the manual fallback remain open. Do not enable unattended pytest or retire the fallback based on this milestone.

**Next engineering step:** the isolated trusted-verifier/readback **candidate is now staged and reviewed in PR #27** (details below); prove its hosted exact-head behavior, approved redirect/readback, source/run/commit integrity and negative cases before separately considering a tightly scoped owner-authorized unattended trial.

### Stage 6 v31 milestone — isolated advisory artifact-readback review completed (November 15, 2026)

[Controller review PR #27](https://github.com/TenchiMisaki/romarr-ci-controller/pull/27) was published as an **open, non-draft, unmerged** eight-file isolated change, `review/stage6-v31-manual-artifact-readback` at head `73905a4fb490ab39ebf32eb3eb3ae48bfb6a2a55` against controller `main` `dc2d263491b19f5963337ef62f098f84558fbf91`. The approved v31 payload was checked against its complete eight-file manifest and historical Gitleaks 8.30.1/actionlint 1.7.12 scan evidence before publication; the resulting GitHub diff has **eight additions-only files** (1,307 added lines, zero deletions), and the public branch/file blobs were independently read back. The eight files add manual, advisory-only source isolation, readback and verifier components; this is a reviewed candidate, **not installed/merged runtime**.

[Controller unit-test run #43795143683](https://github.com/TenchiMisaki/romarr-ci-controller/actions/runs/43795143683) completed **successfully on PR #27's exact head** (the existing controller test workflow, compiler and read-only smoke steps). These existing tests do **not** demonstrate that the new Stage 6 modules and hosted artifact readback executed successfully. The **exact-head CodeRabbit check completed successfully** on November 15 at approximately 7:05 p.m. Pacific; its final PR summary reported **no actionable comments**, and no unresolved inline review threads were found. CodeRabbit's check success and the substantive zero-actionable review are separate observations.

**Stage 6 acceptance remains BLOCKED / NOT ENABLED:** the new `workflow_dispatch` workflow was added only on the review branch, so it has **not** been dispatched or exercised as a hosted v31 canary. The trusted GitHub run/job and source provenance, vetted storage redirect, outer artifact digest, strict member allowlist, negative/race/failure paths, and independently accepted advisory readback still require a hosted end-to-end exercise. No PR-head source-test receipt, autonomous scheduler/dispatch, remediation, merge or deployment is authorized by this milestone. Retain the owner-controlled manual fallback.

**Operational monitoring note:** the separate hourly read-only outage watch was reconfigured to use supported repository-level run collection, distinguish `COLLECTION FAILED` from actual monitor failure, and distinguish native `schedule` from external `workflow_dispatch` events. Its saved enabled configuration was verified; the revised watch's next execution/recovery behavior was **not yet observed** at this milestone. A previous inconclusive report was a **collection failure**, not confirmed evidence of an underlying workflow outage.

**Next:** preserve PR #27 at the reviewed head; plan a separately controlled hosted manual v31 exercise only when the workflow is available on the default branch and the redirect/credential/public-artifact gates are independently satisfied. Separately complete Stage 5 sustained native/fallback scheduling and alert/recovery acceptance. Do not merge PR #27 or enable unattended pytest as an implicit consequence of a green review.
## The next engineering work and acceptance gates

### Stage 5 — Finish operational scheduling acceptance

A genuine successful native `schedule` event was observed on later controller `main` in run #43776973721. Next verify sustained native cadence, actual monitor artifacts and job/step outputs across subsequent scheduled events, separate them from external `workflow_dispatch` fallback, and prove collision/duplicate avoidance and alert/recovery behavior. A missing event is **NOT OBSERVED** until sufficient evidence exists; it is not automatically a failed workflow.

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

**Resume from the Current Stage 6 review section above: PR #30 exact-head review and then separately controlled manual exact-PR hosted acceptance.** Do not repeat accepted source tests, confuse read-only workflow successes with hosted source acceptance, merge the review PR, or silently enable privileged automation. Stop only at the real security, owner-controlled GitHub, upstream or production boundaries.
