# ROMarr CI Controller — Fully Automated Project 2

**November 15, 2026 UTC snapshot.** This is a dedicated controller roadmap and evidence index, not a completed feature or permission for further privileged operations. The controller is separate from the ROMarr fork, upstream ROMarr, the fork-sync repository and installed application. Recheck moving GitHub refs before acting.

## Original objective: the complete unattended loop

Replace routine manual Windows/SSH source-testing orchestration with a GitHub-hosted, exact-revision and evidence-driven automation controller while retaining an on-demand local fallback until accepted. The system should:
1. Detect eligible fork PRs and head/base changes on an approximately five-minute cadence, without assuming GitHub cron guarantees exact timing.
2. Pin the actual repository, PR, full head/base SHAs, controller revision, source dependencies, permitted workflow and immutable claim identity.
3. Deduplicate and, **only when separately enabled and authorized**, request a bounded exact-source pytest run for one new/changed revision; preserve known run IDs.
4. Independently reconcile pytest execution, exit, JUnit anonymous per-case accounting, source freshness, job steps, GitHub artifact digest/manifest/ZIP and skip policy.
5. Follow CodeRabbit through actual review completion, full finding content and unresolved threads, distinguish review success from no actionable findings, and monitor relevant other CI.
6. Investigate real source defects, apply only authorized fork-only fixes, retest/re-review the changed SHA, and continue through established approvals rather than stopping at every routine decision.
7. Report sanitized, durable actionable status, notify for genuine failures/missed work, recover safely from interruptions, then reduce routine owner interaction without unauthorized upstream PRs, merges or deployments.

**Original phases:** A = discovery/architecture; B = unattended exact-source pytest; C = CodeRabbit monitoring/investigation/authorized correction/retest; D = receipt-driven decision, continuation, alerts and recovery. A has substantial acceptance; B–D remain incomplete.

## Completed and independently observed

### Stage 1: Manual pinned pytest and trustworthy anonymous receipts — ACCEPTED for tested revisions
The GitHub-hosted manual workflow `.github/workflows/romarr-pytest.yml` pins source to exact head/base, uses the needed Python/Node/archive dependencies, and separates TEST, COLLECTION, SOURCE and ENVIRONMENT results. Public receipts contain anonymized ordinal/outcome cases, summary, postcheck, manifest and hash/CRC evidence; raw private JUnit/logs are not public. Historical runs are recorded in [VALIDATION.md](https://github.com/TenchiMisaki/romarr-ci-controller/blob/main/VALIDATION.md). Do not re-run accepted immutable source solely to repeat its counts.

### Stage 2A/B/C: PR watcher, base-aware immutable claim, one-target manual dispatch — CODE MERGED; LIVE V2 EXERCISED
Controller PRs #1–#6 established eligibility filters, exact SHA/base identity, legacy/v2 claim handling, one-target manual dispatch and run-ID ledger. Draft, backlog and review PRs are excluded. [ROMarr fork PR #28](https://github.com/TenchiMisaki/romarr/pull/28) has an authenticated v2 claim and run-ID tag for [run #43676714571](https://github.com/TenchiMisaki/romarr-ci-controller/actions/runs/43676714571), tested source head `07e97f4a86b806a63c549f36e169ac21595e9626`, base `29f52812ff53b58c2f21e910ba267a87acb922a3`. Evidence: **4,029 passed, 4 skipped, 0 failures, 0 errors**. Four skips remain policy-unreviewed. This does not establish unattended dispatch or approval to duplicate the run.

### Stage 3: Scheduled read-only PR/CodeRabbit monitor — OPERATIONAL WITH SCOPED ACCEPTANCE
Controller PRs #7–#11 added metadata/CodeRabbit status, sanitized seven-day summary, advisory next-untested candidate, live status-to-summary smoke and UTC cron `2-59/5 * * * *`. [Native scheduled run #43689231985](https://github.com/TenchiMisaki/romarr-ci-controller/actions/runs/43689231985) succeeded. An independently operated external read-only fallback was repaired after truncation of a GitHub runs JSON response; its successive post-repair guard/dispatch cycles passed and [fallback run #43690137352](https://github.com/TenchiMisaki/romarr-ci-controller/actions/runs/43690137352) succeeded. The monitor remains read-only and metadata-only; it does not run pytest or download/accept receipt contents. Reboot persistence, missed-run alert delivery and credential renewal are unaccepted.

### Stage 4: Read-only receipt verifier/collector and hosted manual pilot — COLLECTOR ROUTE ACCEPTED; HOSTED PILOT MERGED, NOT YET RUNTIME-ACCEPTED
Controller [PR #19](https://github.com/TenchiMisaki/romarr-ci-controller/pull/19) introduced immutable receipt acceptance; [PR #20](https://github.com/TenchiMisaki/romarr-ci-controller/pull/20) added bounded GET-only metadata and exact artifact collection, approved HTTPS redirect host, no storage-token forwarding, 16 MiB artifact bound, ZIP digest/member/case accounting and final live PR/run/tag freshness checks.
An owner-operated authenticated collector execution against the existing PR #28 receipt completed on November 14 at 22:41 PST with `RECEIPT_VERIFIED_SKIPS_REQUIRE_POLICY`, 4,029 passed / 4 skipped / 0 errors or failures, and no source retest or GitHub mutation.
Controller [PR #21](https://github.com/TenchiMisaki/romarr-ci-controller/pull/21) was **squash-merged into main** on November 15 08:41:28 UTC at `8a5338f7dccd8957dcc4bd494031da192a783f93`. Final reviewed head `cdecb0f750e8c704ac2da84f1450dfeb72c2d81e` passed [CI #43695172100](https://github.com/TenchiMisaki/romarr-ci-controller/actions/runs/43695172100): **251 unit tests**, Python compilation and live sanitized monitor smoke. CodeRabbit completed on final head; all three prior inline findings resolved/outdated, no new unresolved threads. The two merged files are the manual-only `.github/workflows/romarr-receipt-manual.yml` and its negative-permission/trigger test. Workflow grants `contents: read`/`actions: read`; it cannot dispatch pytest or write.
**Critical distinction:** the new GitHub-hosted manual *receipt workflow itself has not executed*. Merged YAML/green controller CI does not prove hosted artifact fetching works.

## Remaining roadmap — execute in order

### 4A. Live acceptance of the newly merged manual receipt workflow (next task)
- Re-read current PR #28 open/non-draft/head/base, v2 claim/run-ID ledger, existing run and artifact; do not assume historical source identity is still current.
- From controller Actions, manually launch **ROMarr receipt - manual read-only verification**, on controller `main`, with PR number `28`, head `07e97f4a86b806a63c549f36e169ac21595e9626`, base `29f52812ff53b58c2f21e910ba267a87acb922a3` **only if the live PR/ledger still match**.
- Verify event, workflow identity, commit, run attempt, all job steps, exact authenticated collector output and no other actions. Expect `RECEIPT_VERIFIED_SKIPS_REQUIRE_POLICY` for unchanged evidence. Treat anything else as a new observation requiring investigation.
- Available GitHub connector cannot directly dispatch an arbitrary manual workflow; use an authorized GitHub Actions UI/execution environment rather than pretending it ran. Keep four skips flagged.

### 5. Scheduled **read-only** full receipt integration
- On at most one already claimed exact PR revision per monitor execution, safely reuse the accepted collector; keep PR/head/base/run/job/content/digest and final freshness gates, bounded JSON/artifact sizes/timeouts and safe redirects.
- Report `NOT_DISPATCHED`, metadata-only, verified-no-skips, verified-skips-need-policy, stale, ambiguous/missing, collection failure and blocked separately.
- Preserve read-only monitor permissions, advisory next-candidate selector, seven-day sanitized output and external fallback. Negative tests cover changed PR mid-fetch, invalid tags, expired/oversized/corrupt artifacts, missing steps, HTML/redirect transport and credential scoping.
- Require exact-head CI/CodeRabbit, separately authorized merge, and a real observed scheduled run before claiming acceptance.

### 6. Governed unattended pytest (Phase B)
- Design owner-controlled enable/disarm and a separate minimally privileged dispatch context; **do not add write permission to read-only monitor**.
- One exact eligible PR/head/base per cycle; immutable claim-before-dispatch and unique run-ID ledger; concurrency/rate bounds; no blind retry after uncertain API writes or partial claims.
- Prove new PR, changed head, changed base, unchanged no-op, draft/backlog/review exclusion, two workers racing, failure between claim and ledger, stale source, incomplete source run, transient read outages and auth failures; preserve v1 claims and test receipts.
- Accept only after a real source-pinned unattended trial, independent receipt reconciliation and duplicate-prevention evidence.

### 7. CodeRabbit lifecycle, authorized repair and retest (Phase C)
- Track actual check + full review/body + inline/unresolved/outdated threads + reviewed SHA and applicable quality gates. A green CodeRabbit check is not zero findings.
- Investigate each material suggestion against source/callers; classify true defect vs false positive vs environment/collection error. Use bounded polling, rate-limit awareness and finite attempt budgets.
- Under established fork-only authority make the smallest verified correction on an isolated branch, run affected/full tests as risk warrants and request one review per changed head; preserve history, receipts and recoverability.
- No automatic upstream submission/comment, contributor-branch promotion, merge, deployment or protected documentation publication.

### 8. Durable results, decision engine, and operational recovery (Phase D)
- Per immutable revision maintain TEST / COLLECTION / ENVIRONMENT / SOURCE / REVIEW / skip policy / other CI / claim and run identity, plus next safe action. Distinguish PASS, FAILED, SKIPPED, BLOCKED, NOT TESTED, COLLECTION FAILED, STALE and pending review.
- Make actual state-based continuation possible (new revision, in-progress job, receipt verified, failed test, substantive finding, patched SHA, rate limit, no changes) rather than reporting advisory green and stopping.
- Implement and **test** missed-run and failed-job alerts, notification delivery, external/native timer collision, restart persistence, token expiry/renewal, safe disarm/rollback, transient API failures, partial claim repair and artifact retention. Observe multiple live intervals including negative/failure cases.
- Keep on-demand local test/recovery fallback until replacement is proved. After owner acceptance, retire only truly redundant manual steps, update controller usage/validation records and propose protected Homelab reference updates through separate approval/publication verification.

### 9. Independent optional coverage
Docker standard/browser images, native Windows executable/package, live application/UI/API, official upstream PRs, release and production deployment each require their own checks and approvals. A green controller status is not acceptance of those areas.

## Next-thread restart checklist
Read this issue **in full**, controller [README](https://github.com/TenchiMisaki/romarr-ci-controller/blob/main/README.md), [VALIDATION](https://github.com/TenchiMisaki/romarr-ci-controller/blob/main/VALIDATION.md), exact current controller `main`, GitHub Actions jobs/logs and CodeRabbit checks/reviews/threads. Reconcile applicable Homelab `00`, `10`, `50`, `60`, `70`, official ROMarr `AGENTS.md` when source work is in scope, and live fork PR identities. Do not redo accepted source pytest just to reproduce results. Begin with Stage **4A**, then Stage **5**; the more privileged **6–8** are design/acceptance phases, not currently enabled. Stop at actual owner-controlled write, merge, upstream or deployment gates.

**Current known controller main at backlog creation:** `8a5338f7dccd8957dcc4bd494031da192a783f93`. A future moving branch must be independently checked before execution.

---
## Backlog migration record (November 15, 2026 UTC)

This versioned Markdown file preserves the full original public [controller Issue #22](https://github.com/TenchiMisaki/romarr-ci-controller/issues/22) roadmap above, without deleting or revising that source evidence. The authoritative ongoing work record is this file on the controller's draft `Backlog:` pull request. Future material milestones should be appended here with dated GitHub evidence, not copied into the short PR description.

At migration, [controller PR #21](https://github.com/TenchiMisaki/romarr-ci-controller/pull/21) was verified squash-merged to `main` at `8a5338f7dccd8957dcc4bd494031da192a783f93`; final source-head CI passed 251 controller tests and CodeRabbit's three earlier findings were resolved. The next unfinished gate remains Stage 4A's *actual GitHub-hosted execution* of the newly merged manual receipt-verification workflow against a freshly checked immutable PR #28 target.

The draft backlog PR is **not** a merge request for executable controller changes, a new acceptance of unattended dispatch, or authority for upstream publication or production deployment.
