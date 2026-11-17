# ROMarr CI Controller — Fully Automated Project 2

## Separate fork-sync security investigation — November 17, 2026 (Pacific)

This is a related security-evidence checkpoint only; it does not change the
Stage 6–8 or CP acceptance criteria, implementation branches, or operational state.

The failed source scan was reproduced on an independently reconstructed exact
Git tree using official-checksum-verified Gitleaks 8.30.1. The third finding is
`generic-api-key` at `tests/soundtracks_support.py:18`, public blob
`be5413a930121e137664633f64ddcbf482deccf9`, introduced by official
[upstream commit 4ca16cd0](https://github.com/BlizzHacker/romarr/commit/4ca16cd0810b56699d6808f2b67909213fd76710).
The source is a loopback-only fake RomM authentication fixture used by redaction
tests; no genuine credential exposure was identified in the focused trace.
No matched values or raw scanner output are published.

All 70 newly reachable historical blobs produced their exact required scanner
canary; only the same fixture was additional. Filename-sensitive traversal found
zero eligible aliases/findings. A private, unmerged dormant exact-fixture
proposal passed 22 focused local regressions and 293 hosted Linux controller
tests. It has no workflow wiring; the active gate still rejects three findings.
Full source/platform acceptance remains blocked, and prior successful artifacts
remain preserved. CodeRabbit review is pending at this checkpoint.

**Continuation:** complete exact-head review and separately approve the exact
public-fixture exception before any separately reviewed tree/history wiring.
Do not enable unattended testing, alter Project 2 work, merge, deploy, or
interpret this diagnostic milestone as publication authorization.

## Current integrated development — November 17, 2026 (Pacific)

This section supersedes older current-state introductions and next-step wording;
all dated milestones and the complete CP-01–CP-10 requirements below are retained.
The scope expansion at commit `712c5734d20651a813e9e7954d8777c66cc7e4d7` was
independently read before this update. The original Stage 6–8 operational handoff
is unchanged and remains NOT ACCEPTED / NOT ENABLED.

### Original Stage 6–8 implementation

[PR #32](https://github.com/TenchiMisaki/romarr-ci-controller/pull/32), branch
`review/stage6-hosted-claims`, is **MERGED** into main at
`f078b2dfbcd1f69f09ffa9a58cb171b86fdd99bc`; reviewed head
`7b73d5a4b2c3c6a020a408f80b12031cc9c585ed`. The merge tree
`0ee699ff3918c983ed746509233d2483967dded0` exactly matches the scanned,
reviewed and final CI-tested tree. This is COMPLETE for the dormant code increment;
original Stage 6–8 hosted operational acceptance remains IN PROGRESS / NOT ACCEPTED.

- Stage 6: dormant Git-backed cross-run state, sole-parent non-force updates with
  independent readback, authenticated owner-control adapter/default-disabled
  acceptance contract, exact source/legacy-claim gates, durable uncertainty before
  POST, direct run ID and source/nonce-bound run correlation. No state branch,
  immutable revision tag, credential service or unattended caller is provisioned.
- Stage 7: existing exact-head CodeRabbit parser integrated with persistent bounded
  refresh, source rechecks and separate findings/thread states. No automatic code
  remediation or upstream action.
- Stage 8: persistent tick deduplication, integrated cycle, failed/pending/advisory
  states, atomic failure-alert intent, bounded confirmed-nondelivery retry and
  preserved uncertain delivery. Real notification delivery is NOT TESTED.
- Local focused regressions: **64 PASS**, plus compilation/whitespace checks.
  The race negative control reproduced two winners with identical commit IDs,
  while the corrected unique-attempt commits permit exactly one winner.
- [Initial CI #44033617080](https://github.com/TenchiMisaki/romarr-ci-controller/actions/runs/44033617080):
  **367 unittest / 296 Stage 6 pytest PASS** at `ebcc30d5`.
- [Corrected-head CI #44035731802](https://github.com/TenchiMisaki/romarr-ci-controller/actions/runs/44035731802):
  **372 unittest / 296 Stage 6 pytest PASS**, compilation, public-artifact smoke and
  live read-only monitor checks passed. The two warnings are the pre-existing
  deliberate duplicate-ZIP fixtures.
- [Initial CodeRabbit review](https://github.com/TenchiMisaki/romarr-ci-controller/pull/32#pullrequestreview-5934245311)
  found three valid issues: review refresh missing from the cycle, terminal-run
  alert intent/retry loss, and identical same-second state commits permitting
  duplicate dispatch fences. All three have scoped corrections and regressions at
  `6a4fc5b7`. A further valid stale-review starvation finding was corrected at
  `7b73d5a4` with two additional regressions; invalid collection remains blocked.
  [Final CI #44037114684](https://github.com/TenchiMisaki/romarr-ci-controller/actions/runs/44037114684)
  passed **374 unittest / 296 Stage 6 pytest**, compilation and read-only smoke checks.
  [Final CodeRabbit assessment](https://github.com/TenchiMisaki/romarr-ci-controller/pull/32#issuecomment-6940919987)
  covers exact head `7b73d5a4`, with no new actionable findings and all four
  review threads resolved before merge.
- Gitleaks 8.30.1: initial/corrected complete trees and exact outgoing server
  histories passed with zero findings. Scanner binary/accepted positive control
  reused after identity verification. Corrected server tree
  `32e2bd09881d0b378a90c6519d088c93be3fd9a2` matched scanned bytes.

Detailed design/recovery:
[controller cycle acceptance plan](https://github.com/TenchiMisaki/romarr-ci-controller/blob/review/stage6-hosted-claims/docs/proposals/controller-cycle-acceptance.md).
These are implementation and controller-test results, not live hosted durable
storage, dispatch/recovery, owner-control, complete receipt or scheduler acceptance.

### Cross-platform increment

[PR #33](https://github.com/TenchiMisaki/romarr-ci-controller/pull/33), branch
`review/cross-platform-advisory`, is OPEN / UNMERGED at
`58e30591114d89bfdef79aa0ce02ecfe5d15f8bc` after the five original review findings
were corrected. The original six-file increment was based on `3f4ee847`; the
correction adds a seventh file for independent Windows Job Object ownership.
The new CI merge parents independently bind main `f078b2df` and head `58e30591`;
combined-source hosted verification and final review remain separate gates.

| Requirements | Implemented advisory scope | Acceptance still open |
| --- | --- | --- |
| CP-01, CP-09 | Prepared digest-pinned Docker health/dependency/permission probe; standard/browser profiles; isolated execution/owned cleanup | Real image runs, negative/recovery behavior, complete runtime/plugin/architecture policy |
| CP-02, CP-06 | Prepared Windows Python 3.11/3.13 source/toolchain checks and focused suite/JUnit adapter | Actual ROMarr runs on both minors, loopback/authentication/persistence, dependencies |
| CP-03 | File/OCI subject digest and pinned GitHub CLI signed-attestation adapter with exact source/signer constraints | Live valid/invalid attestations and package-to-contained-EXE provenance; labels are insufficient |
| CP-04, CP-08 | Strict typed three-file receipts, authenticated run/job/step/artifact contract, count/skip/privacy/ZIP guards | Ordered live producer/verifier integration and per-platform upload acceptance |
| CP-05 | Actual prepared EXE digest/launch/proof adapter | Real EXE execution and independent provenance/timeout cleanup acceptance |
| CP-07, CP-10 | Same-revision versioned required/optional readiness and separate failure dimensions | Accepted live evidence/policy; missing platforms remain NOT TESTED; no release authority |

**Original local CP contracts: 26 PASS** at `6b0ccb25`; corrected candidate:
**36 PASS** on Windows/Python 3.15.2, compilation/whitespace PASS. New GitHub Actions
matrix tests controller contracts only on Linux 3.13 and Windows 3.11/3.13; it is
not ROMarr platform acceptance. [Platform matrix #44036374376](https://github.com/TenchiMisaki/romarr-ci-controller/actions/runs/44036374376)
and [controller CI #44036374198](https://github.com/TenchiMisaki/romarr-ci-controller/actions/runs/44036374198)
completed successfully at `6b0ccb25`.
[CodeRabbit's initial review](https://github.com/TenchiMisaki/romarr-ci-controller/pull/33#pullrequestreview-5934423535)
found five valid issues: hidden local ZIP-header metadata, collection failure
upgraded to PASS, output bounds applied after process exit, skipped Windows tests
reported PASS, and descendant cleanup after successful EXE launcher exit. All five
have candidate corrections and regressions in `58e30591`; threads remain open
pending revised-head verification.

The corrected implementation accounts for local/central archive layout, preserves
collection failure, emits SKIPPED receipts, drains both streams live with bounded
retention and terminates owned process trees. The independent Windows adapter
creates the process suspended, assigns a kill-on-close Job Object before resuming,
and verifies cleanup after launcher exit or timeout. Local tests execute safe
Python fixture trees, output floods, timeout and assignment-denial cases. Initial
local failures (missing import, incomplete JUnit fixture and termination-observation
race) were corrected before publication; neither these tests nor the hosted contract
matrix establish ROMarr runtime acceptance.

Revised-head [controller CI #44107365945](https://github.com/TenchiMisaki/romarr-ci-controller/actions/runs/44107365945)
and [platform matrix #44107366168](https://github.com/TenchiMisaki/romarr-ci-controller/actions/runs/44107366168)
completed successfully on merge `82b12f848ef3a7f1f4f28c913911485b3c1e4bff`, tree
`b023a9631e8c7a890308f400f89fb0e630e36cc4`, with independently verified parents
`f078b2df` and `58e30591`. Controller CI ran **410 unittest cases: 407 passed,
3 Windows-only cases skipped on Linux**, plus **296 Stage 6 pytest PASS** and two
existing deliberate duplicate-ZIP warnings. Windows Python 3.11 and 3.13 each ran
**36 PASS / zero skips**; Linux ran **33 PASS / 3 Windows-only skips**. Compilation,
public-artifact and live read-only smoke checks passed. These skips are the explicit
OS gates for native Job Object tests, exercised on both Windows minors, not ROMarr
source-suite skip acceptance. Exact-head CodeRabbit remains IN PROGRESS. Do not
merge until the revised-head review and unresolved-thread gates pass.
Gitleaks 8.30.1 final-tree/outgoing-history/exact-server-history scans passed with
zero findings. Server tree `55a54d4c78123a7d913886bd3e16afd33064f105` matched the
scanned payload. Privacy/provenance review completed; no substantial maintainer
source copied. Official CI/runtime interfaces were read for interoperability at
`BlizzHacker/romarr@3d2bc6cc2ede0cd555e49e44b3fc84bf7e9f2f1a`.

Per-capability design/limits:
[cross-platform advisory acceptance](https://github.com/TenchiMisaki/romarr-ci-controller/blob/review/cross-platform-advisory/docs/proposals/cross-platform-advisory.md).
Correction publication: Gitleaks 8.30.1 complete tree, outgoing history and exact
server-created history passed with zero findings; server tree
`d2fd4a3def92addc2c0d99b3c41a5e6bba64ab15` matches scanned bytes. Independent
privacy/provenance review completed. No substantial third-party source was copied.

No release builds/publishing, new credentials, source/platform scheduler,
automatic remediation, production changes or fallback retirement were introduced.

### Remaining operational gates and execution limits

- Complete independent source/test/JUnit/skip/job/artifact receipt acceptance;
  the preserved 70-case manual workflow remains advisory.
- Actual durable hosted state races, nonce-correlated dispatch and uncertain-write
  recovery, owner-only arm/disarm entrypoint/acceptance record, immutable-ref and
  storage protections, credential expiry/renewal and recovery.
- Sustained native/fallback cadence/collision behavior, missed/failed-run alerts,
  real provider delivery/receipt reconciliation, interruption/retention recovery.
- Separately owner-authorized bounded unattended trial and primary-method handoff;
  preserve the independent manual fallback until separate retirement approval.
- Live platform probes require a supported disposable executor and prepared
  immutable artifacts. The current local environment has no Docker and only
  Python 3.15; direct GitHub transport fails DNS. Connected GitHub reads/writes
  remain usable for reviewed publication and hosted controller tests. No live
  Docker, ROMarr Windows 3.11/3.13, EXE or signed-network-attestation acceptance
  is inferred from offline fixtures.
- Next: complete exact-head reviews and legitimate corrections, reconcile hosted
  matrix results, merge only after applicable gates, then risk-appropriate combined
  source validation. Continue independent development without enabling operation.

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

### Completed focused ledger increment

[Controller PR #31](https://github.com/TenchiMisaki/romarr-ci-controller/pull/31)
merged at `3f4ee847585a5252b34cb26ddddb62cdd8929ec7`. The merged tree
`f83e550593f977826cae687cb0e743b2c779031d` independently matched the
scanned implementation tree and hosted CI merge tree.

- New offline tests: **13/13 PASS** on Windows/Python 3.15.2.
  Initial test-only Windows cleanup errors were corrected by explicitly closing
  assertion connections; no safety check was relaxed.
- [Linux CI #44028502729](https://github.com/TenchiMisaki/romarr-ci-controller/actions/runs/44028502729):
  **323 unittest cases PASS**, including the 13 new ledger tests; **296 existing
  Stage 6 pytest cases PASS**, zero failures/skips, plus compilation, artifact
  smoke and live read-only monitor checks. Two expected warnings came from the
  deliberate duplicate-ZIP rejection fixtures.
- [Completed CodeRabbit assessment](https://github.com/TenchiMisaki/romarr-ci-controller/pull/31#issuecomment-6940214429):
  exact source/covered head `6a81ab54ffdaca3a2e8a2029fd556c412f20262f`,
  no actionable comments, no inline comments and no unresolved review threads.
  The bot published its assessment in the PR conversation; no separate submitted
  review node was present. Its successful execution and substantive assessment
  were independently checked.
- Gitleaks **8.30.1**: final tree, proposed outgoing history and exact
  server-created outgoing commit history all passed with zero findings.
  Scanner binary matched the previously verified digest; accepted positive-control
  evidence was reused. All three public file blobs matched the scanned source.
- Source and workflow isolation: no network adapter, credentials, workflow edits,
  automatic retry/reset, receipt acceptance or source execution was introduced.
  The prototype is not imported by any workflow.

The implementation adds `controller/stage6_dispatch_ledger.py`,
`tests/test_stage6_dispatch_ledger.py` and
[the scoped design and acceptance limits](https://github.com/TenchiMisaki/romarr-ci-controller/blob/main/docs/proposals/stage6-dispatch-ledger-design.md).
Its real eight-worker SQLite race verifies one local reservation; interruption
tests preserve uncertainty across restart; generation checks block old tickets
after disarm/rearm. This is **OFFLINE PROTOTYPE VERIFIED**, not installed hosted
claim storage, authenticated owner control, run-bound recovery or unattended
testing acceptance.

### Next implementation boundary

Use the existing controller-owned immutable claim/run mechanisms as a design
input for a separately reviewed hosted durable backend; do not treat a runner-local
SQLite file as cross-run storage. Preserve legacy/v2 claims and accepted receipts.
Before connecting a dispatcher, implement and test unique run-ID correlation,
independent authenticated source/run observations, bounded reconciliation of
uncertain writes, storage/credential recovery and real failure alerts. Do not
silently add a claim reset, retry, schedule, privileged monitor permission or test
receipt acceptance.

A separately accepted live unattended trial, operational handoff and fallback
retirement remain owner-controlled. None is requested or enabled merely by this
prototype merge. The existing manual source-test fallback is preserved.

### Remaining coverage and implementation order

| Area | Existing evidence | Remaining acceptance |
| --- | --- | --- |
| Exact source and base freshness | Existing v32/v35/v36 positive and rejection tests; successful manual canary | Source movement at the future actual dispatch boundary and complete receipt correlation |
| Advisory bytes and transport | Existing archive/member/digest, redirect, job/step and source sanitizer regressions | Governed complete receipt acceptance, expired artifact and live transient failure recovery |
| Concurrency and duplicate claims | Existing manual claim mechanisms are separate from advisory execution | Durable cross-run claims, one global outstanding dispatch, changed revision and duplicate policy |
| Disarm and restart | No accepted unattended adapter | Owner-only policy, policy generation, restart persistence, in-flight boundary |
| Partial write / uncertain POST | No accepted live automatic recovery | Persist uncertainty before POST, unique run-ID reconciliation, no blind retry or claim deletion |
| Operations | Successful read-only monitor runs are dated observations | Native/fallback collision, sustained cadence, real alert delivery, credential renewal and recovery |

**Local ledger increment completed:** the offline prototype and targeted negative/race/restart tests are merged as recorded above. Distributed-scheduler, run-bound reconciliation and live recovery acceptance remain open; the prototype does not provide them.

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

## Continuity, progress and recovery contract

This draft backlog #23 remains the authoritative Project 2 roadmap, progress index
and acceptance tracker; this existing companion is its complete engineering and
recovery handoff. Do not create another backlog, tracking repository or checkpoint
system. Keep this summary readable for humans and agents, link evidence and retain
historical milestones, failures, decisions, requirements and recovery boundaries.

At every new or resumed session, read current applicable owner guidance, this PR
and complete companion, applicable repository instructions and live branches,
commits, PRs, Actions, artifacts and CodeRabbit findings. Reconcile published state,
identify milestones absent from the backlog and resume the last independently
verified point. GitHub establishes actual published state; backlog requirements
and acceptance records establish intended behavior. An open PR may contain complete
work; a merge does not establish operational acceptance; previous tests apply only
to equivalent source/dependencies/environment/scope; a green workflow proves only
its actual checks; a backlog update does not prove code publication; unpublished
local changes are not recoverable merely because a conversation mentions them.

Update this existing handoff and the concise PR synopsis alongside significant
verified milestones, merged PRs, acceptance outcomes, major changes or new blockers.
Record exact refs/runs, actual tests/scans/review, current work, unresolved tasks,
dependencies, next action and recovery limits. COMPLETE means implemented and
verified for the stated acceptance scope; IN PROGRESS means development or checks
remain; BLOCKED names an actual dependency/authorization; NOT TESTED means validation
was not performed; NOT ACCEPTED means required operational acceptance is missing.
Do not postpone recoverable progress until a final response.

After interruption, independently inspect GitHub before retrying any uncertain
mutation, dispatch or PR creation. Record uncertainty and unsuccessful checks; never
blindly retry non-idempotent work, create duplicates or overwrite newer edits. If a
usage limit or interruption becomes apparent, publish verified progress while the
required gates and execution remain available. This is a recovery strategy, not a
guarantee of a final write or response at exhaustion.

Continue independent authorized development, testing, review and backlog work
without routine approval pauses or repeated audits. A blocked operation blocks only
dependent work. Preserve exact-source, privacy/secret scans, CodeRabbit, protected
originals and recovery; no unattended tests, credential-bearing deployment,
production changes, upstream merge, automatic remediation or manual-fallback
retirement without separate required authorization and operational acceptance.

Routine authored progress omits repetitive execution-target headings; targeting,
preflight, identity, permissions, source/destination, security and recovery checks
remain enforced. Manual commands still identify an unambiguous target and shell.
Interface-generated indicators are outside this presentation preference.

These continuity requirements are owner-authorized. Their permanent private
owner-guidance publication remains BLOCKED pending original-byte preservation,
current-destination drift checks and independent readback. Repository records do not
update ChatGPT Project Instructions; any required manual synchronization is PENDING.
The shell execution blocker is cleared in the current session; direct Git transport
still fails DNS. Do not infer unavailable toolchains or live platform acceptance.

## Resume work safely

Before continuing, review this backlog, [controller README](https://github.com/TenchiMisaki/romarr-ci-controller/blob/main/README.md), [VALIDATION.md](https://github.com/TenchiMisaki/romarr-ci-controller/blob/main/VALIDATION.md), applicable repository `AGENTS.md`, and current source, GitHub Actions jobs and CodeRabbit reviews. Reconcile the controller's current `main` revision, relevant fork branches, target PR head/base SHAs and claim/run identities. Previous green tests belong to their exact revisions, not a later moving head.

**Resume from the Current integrated development section above: PR #32 is merged; finish PR #33 revised-head combined-source CI/review, then independently gated hosted and platform acceptance.** Do not repeat accepted source tests, confuse read-only workflow successes with hosted source acceptance, merge the review PR, or silently enable privileged automation. Stop only at the real security, owner-controlled GitHub, upstream or production boundaries.

## Approved scope expansion — cross-platform evidence verification (November 16, 2026)

**Owner request:** Include the following ten capabilities in the scope of Fully Automated Project 2 **now**. They are an authorized engineering backlog and acceptance-design expansion, not evidence that the capabilities are built, tested, activated, or accepted. Preserve all existing Stage 1–8 requirements, milestones and acceptance gates. Continue current Stage 6–8 critical-path implementation without interrupting Work, invalidating completed evidence, or changing the definition of the existing hosted automation acceptance. Implement these as separately reviewed, bounded increments as dependencies allow; no requirement to run all platforms for every source change.

### Cross-platform workstream requirements (CP-01–CP-10)

| ID | Priority | Capability and minimum acceptance direction |
| --- | --- | --- |
| CP-01 | 1 | **Docker image runtime smoke:** Isolated candidate-image startup; bounded readiness/health checks, dependencies, runtime permissions and independently verified build identity. Include browser-enabled image variant when supported. Distinguish image build, startup, health and test failures. |
| CP-02 | 2 | **Windows compatibility matrix:** Windows Python 3.11 and 3.13 supported application tests, including loopback/authentication/persistence paths where applicable; retain per-version outcomes and exact inputs. |
| CP-03 | 3 | **Packaged build provenance:** Independently correlate running Docker image/native executable repository, full source commit, build type, workflow, immutable artifact/digest and actual execution; reject missing, foreign, stale and contradictory identities. |
| CP-04 | 4 | **Multi-platform receipts:** Versioned, explicitly typed source/Docker/Windows/native-executable/future Android receipt schemas, each bound to immutable source and controller revisions, workflow/run/attempt/job and test scope. Platform acceptance must remain independent; missing results are NOT TESTED/NOT CONFIGURED, never PASS. |
| CP-05 | 5 | **Real Windows executable smoke:** Launch the actual candidate executable in a properly isolated Windows environment and verify startup, expected behavior and build provenance; do not mistake packaging success for runtime acceptance. |
| CP-06 | 6 | **Platform toolchain preflights:** Verify actual available interpreters, archive tools, containers, dependencies, permissions and versions per suite; fail closed on unsupported or missing prerequisites instead of reporting an application test failure. |
| CP-07 | 7 | **Release-readiness aggregation:** Summarize independently verified source, image, Windows, executable and optional mobile results for one exact revision, without inferring release approval or automatically publishing/merging. Required/optional platforms and skip policy are explicit and versioned. |
| CP-08 | 8 | **Artifact allowlist parity:** Strict schema/file allowlists, bounded size and content verification, deterministic manifests/digests and negative secret/privacy-leakage tests for each applicable workflow; no raw logs/secrets or overly permissive fallbacks. |
| CP-09 | 9 | **Runtime dependency validation:** Confirm required archive executables, plugins, imports and permissions within tested images/binaries; distinguish missing environment dependencies from application behavior defects. |
| CP-10 | 10 | **Cross-platform failure classification:** Record build, environment/preflight, startup, assertion/test, evidence-collection, provenance, freshness, skipped, incomplete and unsupported states separately, with actionable but sanitized diagnostics. |

### Development order and integration boundaries

1. **Preserve Stage 6 critical path**: durable hosted claims, authenticated owner arm/disarm, unique run identity, uncertain-dispatch recovery and the existing manual/advisory-only boundary. Do not introduce unattended execution, new GitHub permissions, automatic retries or claim deletion through this scope update.
2. **Begin CP design and isolated advisory increments** alongside safe work when dependencies and review capacity permit: prioritize CP-01 + CP-03 Docker/provenance, CP-02 Windows, and CP-04 independent receipts, then CP-05–CP-10. Reuse established source identity, JUnit, manifest, sanitizer, artifact transport, run/job/step and CodeRabbit evidence mechanisms; avoid duplicating maintainer CI.
3. **Keep maintainer build ownership**: ROMarr's own workflows build/publish release images, Windows installers and future mobile artifacts. Controller may trigger only separately accepted test workflows and independently verify their outputs; it must not take ownership of release publishing or modify upstream CI by implication.
4. **Stage 7–8 integration**: Add advisory-only cross-platform status, alert/risk classification and release-readiness reporting after evidence integrity gates. The new platform checks must not silently become prerequisites for the *existing* Stage 6–8 operational handoff or retroactively invalidate completed acceptance.
5. **Separate activation/acceptance**: Each new workflow needs exact-source provenance, isolated runner/permissions, privacy and secrets pre-publication review, negative tests, exact-head CI and CodeRabbit where required, recovery and owner acceptance before unattended use. No automatic remediation, upstream PR creation/merge, production deployment or manual-fallback retirement.

### Initial interoperability and acceptance baseline

The controller's `controller/public_evidence.py` already recognizes official ROMarr's three-member `summary.json`, `cases.json`, `manifest.json` evidence ZIP schema. This is **artifact self-consistency validation only**; source freshness, run identity, workflow/job outcomes, acceptance of platform-specific claims and operational reliability remain separate gates. Extend schemas conservatively and version them rather than interpreting existing source-only artifacts as Docker/Windows/native-executable acceptance.

**Status on scope entry:** CP-01–CP-10 = APPROVED FOR PLANNING / NOT IMPLEMENTED OR ACCEPTED BY THIS BACKLOG UPDATE. Stage 6–8 implementation and operational acceptance remain in progress. This section records owner-requested scope, not a test or publication claim.

