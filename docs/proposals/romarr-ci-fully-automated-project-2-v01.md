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

### Stage 6 real Git integration — COMPLETE (local integration increment)

[PR #34](https://github.com/TenchiMisaki/romarr-ci-controller/pull/34), branch
`review/stage6-git-state-integration`, is **MERGED** into main at
`fdb013cdb1314725eecfb6bf271a9b593be12208`; reviewed head
`78c7d55581f895731a1ce5c6f286fb17f3f7e4a8`, based on main `485bb794`.
Seven new integration tests use disposable bare repositories, real object IDs,
sole-parent commits, ancestry, expected-old ref transactions and strict Git fsck.
Eight same-parent/same-second writers have exactly one successful distinct fence;
a controlled nonce collision reproduces eight idempotent successes. A lost fence
response persists the uncertain claim into a separate Python process and never
dispatches; rejected fences preserve reservations, stale leases create no extra
objects/writes, and Git-valid noncanonical state is rejected.

Local Linux/Python 3.12.14: **58 focused controller/integration tests PASS**,
including all seven new tests; compilation/whitespace checks PASS. The new
[hosted CI #44124206164](https://github.com/TenchiMisaki/romarr-ci-controller/actions/runs/44124206164)
passed **414 unittest cases / 3 Windows-only skips**, **296 Stage 6 pytest cases**,
compilation, public-artifact and live read-only smoke checks. Gitleaks 8.30.1
complete-tree, outgoing-history and exact-server-history scans passed with zero
findings; the official scanner release archive digest and positive control passed.
Initial server tree `11fe1c70cca1ed91c062de4c92f47ec27c8a4fe9` matched scanned bytes.
[Initial CodeRabbit review](https://github.com/TenchiMisaki/romarr-ci-controller/pull/34#pullrequestreview-5942291879)
found one valid test gap: a read-only restart adapter could mask a regressed fence.
Correction `78c7d555` uses a fresh writable adapter and requires exact
`DISPATCH_FENCE_REJECTED`, unchanged persisted head/state, zero created commits,
zero PATCH attempts and no dispatch. All 58 focused tests passed again. Corrected
server tree `9522e1a2d74fc9987c9f21e63949431189bf496e` matches the zero-finding
complete-tree/outgoing/exact-server-history scans.
[Corrected-head CI #44125967968](https://github.com/TenchiMisaki/romarr-ci-controller/actions/runs/44125967968)
passed **414 unittest cases / 3 Windows-only skips** and **296 pytest cases**,
compilation, public-artifact and live read-only checks. Its merge tree is exactly
`9522e1a2d74fc9987c9f21e63949431189bf496e`, with parents main `485bb794` and
reviewed head `78c7d555`.
[Final CodeRabbit assessment](https://github.com/TenchiMisaki/romarr-ci-controller/pull/34#issuecomment-6953852456)
covers exact head `78c7d555`, reports no new actionable findings and confirms the
original concern addressed; its thread is resolved. Independent main/commit
readback verifies merge `fdb013cd` has the same tested/scanned tree and exact
parents `485bb794` / `78c7d555`. This completes the isolated local Git integration
increment; hosted operational acceptance remains IN PROGRESS / NOT ACCEPTED.

The REST boundary is modeled; real Git object/ref behavior is exercised. These
tests do not establish authenticated GitHub mutations, distributed scheduling,
credential transport or operational acceptance. Production code, workflows,
credentials, state branches, tags and source execution remain unchanged.

### Deployment prerequisite collector — COMPLETE (read-only increment)

[PR #35](https://github.com/TenchiMisaki/romarr-ci-controller/pull/35) is **MERGED**
into main at `7a90efff5ac384a2e2319bc727137a2a2df24c1c`; reviewed head
`d8a54b7c9e2322cf78ccdc0a3942e2a586c727f0`, based on merged `fdb013cd`. The dormant read-only collector reuses canonical Git state validation
and exact revision-tag verification, adds fixed numeric repository/owner gates,
allows only required GET paths, rechecks identity and cannot authorize activation
or dispatch. GET 404 is classified **NOT FOUND OR NOT VISIBLE**, distinct from
invalid data and collection failure, rather than claiming proven resource absence.

Local Linux/Python 3.12.14: **68 focused tests PASS**, including 13 new cases with
real disposable Git state; compilation/whitespace PASS. Gitleaks 8.30.1 final-tree,
outgoing-history and exact-server-history scans passed with zero findings and a
verified scanner/positive control. Tree `f5594b08b85b6119e3c2fa9d339f9f0805517f27`
matches the scanned bytes.
[Hosted CI #44129151304](https://github.com/TenchiMisaki/romarr-ci-controller/actions/runs/44129151304)
passed **427 unittest cases / 3 Windows-only skips** and **296 pytest cases**,
compilation, public-artifact and live read-only smoke checks. CI merge
`3a55820c571e36a8946cb22eff3c21f94ce14655` has the exact scanned tree and parents
`fdb013cd` / `d8a54b7c`; its complete tree/history security scans also passed.
[Final CodeRabbit assessment](https://github.com/TenchiMisaki/romarr-ci-controller/pull/35#issuecomment-6954550022)
covers exact head `d8a54b7c`, with no actionable findings and no review threads.
Independent main/commit readback verifies merge `7a90efff` has the exact tested
and scanned tree, with parents `fdb013cd` / `d8a54b7c`. This completes the dormant
read-only collector increment; it does not establish deployment acceptance.

A live read-only run of the actual collector through an authenticated connector
bridge verified repository identity and independent readback at controller
`fdb013cd`; state and exact revision-tag reads returned 404, correctly reported as
NOT FOUND OR NOT VISIBLE. This supersedes the earlier definitive absence wording
for current prerequisite reporting. No state/tag creation, owner arming, source
dispatch, credential deployment or protection change occurred. Live operational
acceptance remains NOT TESTED / NOT ACCEPTED; the manual fallback is preserved.

### Owner-bound advisory trial — COMPLETE (dormant library increment)

[PR #36](https://github.com/TenchiMisaki/romarr-ci-controller/pull/36) is **MERGED**
at `f2842962cf406affc7944bbc2b9e85e9050179a2`; corrected reviewed head
`7405e4cadcf809adc725f86369e760dccc6c27da`, based on `7a90efff`.
It binds one advisory trial to canonical approval bytes with an independently
configured SHA-256 pin, exact owner/repositories/workflow/controller/PR/head/base,
and issued/expiry times. Approval is immutable and rechecked before arm,
reservation, durable fence and POST. Expiry preserves unknown claims; authenticated
disarm and known-run reconciliation remain available. It neither installs an
owner entrypoint nor creates actual acceptance evidence or a live approval.

Local Linux/Python 3.12.14: **84 focused tests PASS**, including 16 new cases and
real Git expiry/restart/disarm; compilation/whitespace PASS. Final-tree, outgoing
and exact-server-history Gitleaks 8.30.1 scans passed with zero findings, verified
scanner identity and positive control. Tree `84a4ead24ca6ef285f3d6c48497a04cd4bbb9ea0`
matches the scanned bytes.
[CI #44133893688](https://github.com/TenchiMisaki/romarr-ci-controller/actions/runs/44133893688)
passed **443 unittest cases / 3 Windows-only skips** and **296 pytest cases**,
compilation/public-artifact/read-only smoke checks on initial head `42419f23`.
[Initial CodeRabbit architecture assessment](https://github.com/TenchiMisaki/romarr-ci-controller/pull/36#issuecomment-6955214803)
identified a valid expiry gap during the adapter's last pre-POST tag GET. Corrected
head `7405e4ca` carries a `pre_post` predicate through the real adapter and checks
it after that lookup, directly before the mutating request. Two additional
regressions cover delayed lookup expiry and real GET/guard/POST ordering; **86
focused tests PASS**. Corrected tree `ead56a466f09a3cc0f5c0e4596e13eb20e4c5b1d`
and exact outgoing/server/CI-merge histories passed zero-finding security scans.
[Corrected CI #44135723376](https://github.com/TenchiMisaki/romarr-ci-controller/actions/runs/44135723376)
passed **445 unittest cases / 3 Windows-only skips** and **296 pytest cases**,
compilation/public-artifact/read-only checks. Its merge tree and both parents were
independently verified.
[Final CodeRabbit assessment](https://github.com/TenchiMisaki/romarr-ci-controller/pull/36#issuecomment-6955214803)
covers corrected head `7405e4ca`, with no actionable findings, no unresolved
threads and no retained architecture concern. Independent main/commit readback
verified merge `f2842962` has the exact tested/scanned tree and parents
`7a90efff` / `7405e4ca`. This completes the dormant owner-trial library, not an
installed owner entrypoint or accepted runtime.

The expected approval digest, controller, clock, credentials and source isolation
must come from an independently accepted trusted deployment. Hashing arbitrary
PR/caller JSON cannot authenticate approval. Existing coordinator default-disabled
behavior and low-level trusted-host capability are preserved; only the new
subclass adds this trial binding. No real owner approval, state/tag, credentials,
workflow caller, source execution or unattended activation was provisioned.

### Ordered full-source receipt collection — COMPLETE (dormant library increment)

[PR #37](https://github.com/TenchiMisaki/romarr-ci-controller/pull/37) is **MERGED**
at `8a98172685accf23e2a0e51d72bbc954237dc95a`; corrected reviewed head
`8fca04b4a0ecbc47bf381f5101cd9c3f112f9e60`, based on `f2842962`.
The dormant collector enforces exact eligible PR/current-base, complete metadata,
source recheck, bounded artifact download, envelope validation, independent
execution provenance and final metadata/source read order. It accepts only
source-full Linux or Windows 3.11/3.13 contract scope; focused/package/foreign
scope is rejected before reads. Missing proof remains ADVISORY_BLOCKED and every
test-acceptance/publication/unattended authority flag remains false.

The existing HTTP transport's 64 KiB default is preserved; full-source collection
uses an explicit per-instance limit up to 4 MiB, with unchanged fixed targets,
TLS/redirect policy, token-free storage, bounds and digest checks. **119 combined
focused tests PASS**, including 16 new cases, both Windows receipt identities,
real canonical envelopes, a larger-than-64-KiB bundle through concrete transport
with modeled HTTP, expiry/source changes and safe failures. Compilation and
whitespace PASS. Final-tree/outgoing/exact-server-history Gitleaks 8.30.1 scans
passed with zero findings, verified scanner and positive control. Tree
`44d72071a638517a211711156608ab39ba5ad981` matches scanned bytes.
[CI #44137393619](https://github.com/TenchiMisaki/romarr-ci-controller/actions/runs/44137393619)
passed **461 unittest cases / 3 Windows-only skips** and **296 pytest cases**,
compilation/public-artifact/read-only smoke checks. Its merge tree and parents
`f2842962` / `912644fc` were independently verified.
[Initial CodeRabbit finding](https://github.com/TenchiMisaki/romarr-ci-controller/pull/37#discussion_r4603397444)
identified uncaught ordinary callback exceptions. Corrected head `8fca04b4`
returns only a fixed sanitized BLOCKED result for ordinary exceptions, preserving
KeyboardInterrupt/SystemExit. **121 combined focused tests PASS**, including
new generic metadata/download/provenance errors and process-control propagation.
Corrected tree `8be1e4b20be427d9792e2078c65fa8678321c5c7` and exact outgoing/server
histories passed zero-finding scans.
[Corrected CI #44139201775](https://github.com/TenchiMisaki/romarr-ci-controller/actions/runs/44139201775)
passed **463 unittest cases / 3 Windows-only skips** and **296 pytest cases**,
compilation/public-artifact/read-only checks. Its exact merge tree/parents and
complete tree/history security scans passed.
[Final CodeRabbit assessment](https://github.com/TenchiMisaki/romarr-ci-controller/pull/37#issuecomment-6955705908)
covers exact corrected head `8fca04b4`, with no actionable findings, no retained
architecture concerns and the original thread resolved. Independent main/commit
readback verifies merge `8a981726` has the exact tested/scanned tree and parents
`f2842962` / `8fca04b4`. This completes dormant ordered collection, not accepted
live full-source producer/execution evidence.

The caller must independently approve the full-suite producer/workflow/job/steps
and execution provenance. The existing focused advisory producer does not emit
this contract and is not relabeled as full-suite evidence. No producer job,
credentials, live receipt, source run or unattended caller was provisioned.

### Cross-platform increment

[PR #33](https://github.com/TenchiMisaki/romarr-ci-controller/pull/33), branch
`review/cross-platform-advisory`, is **MERGED** at
`485bb794d08fbded30ca80f5c735d3e3d9bcf2b7`, final reviewed head
`58e30591114d89bfdef79aa0ce02ecfe5d15f8bc`. The five original findings were
corrected. The merge tree exactly matches the CI/scanned combined tree
`b023a9631e8c7a890308f400f89fb0e630e36cc4`; parents are `f078b2df` and `58e30591`.
This completes the reviewed advisory increment, not CP runtime acceptance. The original six-file increment was based on `3f4ee847`; the
correction adds a seventh file for independent Windows Job Object ownership.
The new CI merge parents independently bind main `f078b2df` and head `58e30591`;
combined-source hosted verification and final review passed before merge.

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
have verified corrections and regressions in `58e30591`; all five threads are
resolved. [Final assessment](https://github.com/TenchiMisaki/romarr-ci-controller/pull/33#issuecomment-6941311587)
independently covers exact head `58e30591` and reports no new actionable findings.

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
source-suite skip acceptance. Exact-head CodeRabbit completed successfully;
all five threads are resolved. The actual combined merge tree was independently
reconstructed and passed Gitleaks with zero findings.
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

### Stage 5 schedule observations — PARTIAL EVIDENCE

A November 17 authenticated API read found nine native `schedule` monitor runs,
all successful. Observed creation gaps range from **206 to 579 minutes**, so this
does not establish the configured five-minute native cadence. The latest native
[run #44084226387](https://github.com/TenchiMisaki/romarr-ci-controller/actions/runs/44084226387)
used controller `3f4ee847`; its read-only audit, receipt inspection, summary and
artifact steps passed. This is observed execution, not proof of each expected
trigger or the reason for unobserved events.

The latest 20 `workflow_dispatch` monitor runs, from November 17 13:34–16:44 UTC,
all succeeded at roughly ten-minute intervals. The latest
[run #44129126445](https://github.com/TenchiMisaki/romarr-ci-controller/actions/runs/44129126445)
used `fdb013cd`, with all read-only job steps passed. API metadata identifies one
unexpired, run-bound sanitized-summary artifact for each latest native/manual
sample, with a digest and seven-day expiry. Artifact ZIP bytes were NOT downloaded
or independently validated in this observation; summary content, complete source
receipts, caller identity, native/fallback collisions, alert delivery and recovery
remain separate acceptance gates. No schedule, fallback, permissions or source
execution was changed. Stage 5 operational acceptance remains IN PROGRESS.

### Retained native/manual monitor artifacts — verified November 17

This closes the earlier sampled artifact-byte inspection gap only; it does not
supersede the partial scheduling or operational-acceptance limits above.
Independent connector download of the retained summary from native schedule
[run #44084226387](https://github.com/TenchiMisaki/romarr-ci-controller/actions/runs/44084226387)
(artifact `14328945959`, controller `3f4ee847`) and external workflow-dispatch
[run #44154567953](https://github.com/TenchiMisaki/romarr-ci-controller/actions/runs/44154567953)
(artifact `14359254374`, controller `8a981726`, attempt 1) produced the exact
819-byte ZIPs matching their independently collected SHA-256 metadata:

| Run | Archive SHA-256 |
| --- | --- |
| `44084226387` | `fd2f15cbc04e972db1ad35ad9ca11acfc4a5dc10519f8bd9dc475f7b5d734b77` |
| `44154567953` | `6df06dd5d7a7e5fef7b651e2dbec6170bff6c938494ee7c09603ddeff33d2400` |

Both contain only the regular `romarr-monitor-summary.md`, with valid CRC, UTF-8,
no archive/member comments or central extra fields. The 1,065-byte Markdown is
byte-identical across both, SHA-256
`ba1c0c79cdc82473f5020ac680c0bf804e6434194ad40cd277aed0aa8de95de9`.
Its inspected content explicitly distinguishes historical receipt metadata and
review readiness from passing tests, reports no eligible new unclaimed revision,
and states that no completed claimed receipt was eligible for inspection. It
contains no raw source-test logs or private paths. This is point-in-time retained
monitor evidence, not complete source receipt validation, public-history security
certification, a current PR-status guarantee or actual scheduler acceptance.
The external run's collection/finalization/publication/upload steps all passed;
artifact metadata binds the run/controller and seven-day retention. No new run,
source dispatch, schedule, caller credential or production mutation was requested.
The latest native scheduled run is still the recorded 12:33 UTC sample; the
native cadence gap therefore remains unresolved. Actual external-caller identity,
collision/duplicate behavior, alert delivery and recovery remain NOT TESTED.

### Anonymous source receipt serialization — PR #38 MERGED

[PR #38](https://github.com/TenchiMisaki/romarr-ci-controller/pull/38) adds the
missing dormant full-source envelope serializer at reviewed candidate
`a17a5b20cbb93500df541c4241b4495f51c4e1eb`, tree
`916ad23562bb935eff08805f42ee19c28a37d571`, based on main `8a981726`.
It converts bounded private UTF-8 pytest JUnit into anonymous ordinal/outcome
records and deterministic receipt/cases/manifest ZIP bytes, checked by the
existing independent parser. Explicit suite/root counters, actual outcomes,
exit codes, independently pinned expected counts and size bounds must agree.
Unsafe XML, hidden nested outcomes, ambiguous structures and inconsistent exits
are rejected; failures/errors and skips remain non-PASS. No private test names,
paths, logs, messages or properties enter the public envelope.

Local serializer/collector regressions: **29 PASS**, including 11 new serializer
tests, real serializer/consumer round trips, independent-proof blocking, XML,
privacy, counts/exits and 10,000-case bounds. Compilation/whitespace passed.
[Hosted CI #44153979497](https://github.com/TenchiMisaki/romarr-ci-controller/actions/runs/44153979497)
passed **474 unittest cases / 3 Windows-only skips** and **296 pytest cases**,
compilation, public artifact smoke and live read-only monitor checks.
The CI merge `44d86fe1803c034d9969a7cdc6a4b8d8ab9b3aa6` has the exact scanned
candidate tree and parents main `8a981726` / head `a17a5b20`.
Complete candidate/server/CI-merge trees and outgoing histories passed Gitleaks
8.30.1 checksum and positive-control checks with zero findings.
[Final CodeRabbit assessment](https://github.com/TenchiMisaki/romarr-ci-controller/pull/38#issuecomment-6957910108)
independently covers exact head `a17a5b20`, with no actionable findings or retained
architecture concerns and no review threads. Review was observed in progress from
19:01 UTC and complete by 19:08 UTC; no extra review request was posted.
PR #38 is MERGED at `cd320e3fe6d0abf37164de08c471d9d096d9f0e9`.
Independent Git commit readback confirms the exact tested/scanned tree and parents
`8a981726` / `a17a5b20`; this is the current verified main after PR #38.
The previously approved bootstrap tag remains pinned to `8a981726`; this dormant
increment does not silently retarget that authorization.

The full-suite selection, absence of deselection, toolchain identity and completed
isolated execution must be proven independently by a trusted host. Count matching
is not execution provenance. Producer provenance stays BLOCKED and freshness
NOT_TESTED; independent consumer proof remains mandatory. No runner, workflow,
uploader, credential loader or unattended source test is installed. The existing
focused advisory producer is unchanged. Original Stage 6–8 acceptance is unchanged.

### Isolated manual hosted-state canary — PR #39 MERGED

[PR #39](https://github.com/TenchiMisaki/romarr-ci-controller/pull/39) prepares
head `60e31687b3bfc122ec738bf6a978d442b6c6a9b5`, tree
`e40d19d56b96ce0ba8c7a733181e52e6c425045b`, based on main `cd320e3f`.
The workflow is an INERT proposal under `docs/proposals`, not installed Actions
configuration. No live canary, ephemeral writer, source job or dispatch ran.

The candidate routes the reviewed GitHubState backend to one new retained
`controller-canary-<run_id>-<attempt>` ref only. It keeps canonical initial disabled
state, verifies the owner/manual/main/hosted-Linux/exact-SHA context, rejects an
existing canary, force/deletion/operational-state/source-dispatch targets, and
never retries writes or deletes retained history. Eight distinct same-parent
writers must have exactly one winner; only explicit HTTP 422 non-fast-forward
rejection counts as an expected losing request. Auth, transport, rate-limit and
other validation failures block instead. A successful subsequent write has its
response deliberately dropped, then a fresh adapter verifies the sole-parent
successor and disabled bytes. This is simulated response-loss/fresh-client
coverage, not a naturally observed network failure or separate-process restart.

Eight focused local tests PASS using actual disposable Git objects, including
the duplicate-commit negative control. Compilation/whitespace PASS.
[CI #44164373921](https://github.com/TenchiMisaki/romarr-ci-controller/actions/runs/44164373921)
passed **482 unittest cases / 3 Windows-only skips / 296 pytest cases**,
compilation, public artifact and read-only monitor smoke checks. CI merge
`4dc85b712dc579075a618eaf2601bb51eaf7167b` has the exact candidate tree and
parents `cd320e3f` / `60e31687`. Candidate/server/CI-merge tree and outgoing-history
Gitleaks 8.30.1 checks passed with the official digest and positive control.
[CodeRabbit review](https://github.com/TenchiMisaki/romarr-ci-controller/pull/39#pullrequestreview-5945698434)
identified two valid failure-handling defects: a real TimeoutError could be
misclassified as injected response loss, and a failed final operational GET
could retain a passing report. Correction head
`01a1541d59392719dfca5654be0cf048cd4f5fb5`, tree
`a3910e2f408ef694cffbd78e72618222c8fefefc`, adds a dedicated injection
exception, clears PASS before final readback and on failure, and adds both
regressions. All ten focused local tests, compilation, whitespace and corrected
candidate/server tree/history Gitleaks checks PASS.
[Corrected-head CI #44165879502](https://github.com/TenchiMisaki/romarr-ci-controller/actions/runs/44165879502)
passed **484 unittest cases / 3 Windows-only skips / 296 pytest cases** and all
compilation/artifact/read-only monitor steps. Actual CI checkout
`85d39234f649977caf895b5646acf9c30583bf35` has exact tree `a3910e2f` and
parents `cd320e3f` / `01a1541d`; its tree/history scans PASS.
[Incremental CodeRabbit review](https://github.com/TenchiMisaki/romarr-ci-controller/pull/39#issuecomment-6959545166)
completed on exact head `01a1541d`, with no new actionable comments, no
outstanding merge-blocking risk and no retained architecture concerns.
[Final assessment](https://github.com/TenchiMisaki/romarr-ci-controller/pull/39#issuecomment-6959325650)
covers that exact SHA. Both original review threads are resolved; the second was
closed with the correction/test evidence after final review completion.
PR #39 merged at `68969a12e6968b58cb38e9490becda2bf359a16e`; independent
Git and REST readback verifies exact tested/scanned tree `a3910e2f` and parents
`cd320e3f` / `01a1541d`. At this PR #39 milestone the workflow was INERT
under `docs/proposals`; the later approved PR #40 installation is recorded below.

The owner explicitly APPROVED installation and one manual run of the reviewed
canary on November 17, 2026 (Pacific). Approval covers its ephemeral job token
with repository contents-write permission, broader than a provider-side per-ref
grant; the application allowlist is not a provider permission boundary. It
permits one new retained run-owned canary branch and append-only disabled-state
commits, not operational-state/tag/protection changes, source execution,
unattended policy, fallback retirement or repeat mutating attempts.

### Manual canary installation — PR #40 MERGED / RUN PENDING

[PR #40](https://github.com/TenchiMisaki/romarr-ci-controller/pull/40) prepares
head `574585475d9d5178f98b9b6af81f0a8ac514d2f8`, tree
`98c63fff9428353e80e97dd99697fa49f2263f91`, on base `68969a12`.
It moves the exact executor workflow proposal to
`.github/workflows/controller-state-canary.yml` (only its status comment changes),
adds that workflow path to the controller CI trigger, and updates the proposal's
approval/install status. The Python executor is unchanged. Thirteen focused
local tests PASS: ten reviewed executor cases plus three workflow contract cases
with negative controls for automatic events, source input, expanded permissions,
persisted credentials, command/artifact drift and owner gates. Compilation,
whitespace and exact candidate/server Gitleaks tree/history checks PASS.
[CI #44168577515](https://github.com/TenchiMisaki/romarr-ci-controller/actions/runs/44168577515)
passed **487 unittest cases / 3 Windows-only skips / 296 pytest cases**, compilation,
public-artifact and read-only monitor steps. Actual CI checkout
`effd6ba75d8536d8af367b0aa79edd4b8e99622d` has exact tree `98c63fff` and parents
`68969a12` / `57458547`; tree/history security scans PASS.
[Automatic CodeRabbit review](https://github.com/TenchiMisaki/romarr-ci-controller/pull/40#issuecomment-6959915173)
found one valid test-guard gap: custom shell templates at step, job-default or
workflow-default scope could bypass the approved run command without failing the
validator. Correction head `bf089435dcc83d79a9b2a0733d04b1f7fd143987`, tree
`3a025d500274a3c14228c36dd10d11ee064b92f9`, rejects shell keys and workflow/job
defaults and adds all three negative controls. All 13 focused local tests,
compilation, whitespace and exact candidate/server tree/history Gitleaks checks
PASS. [Corrected CI #44169577023](https://github.com/TenchiMisaki/romarr-ci-controller/actions/runs/44169577023)
passed **487 unittest cases / 3 Windows-only skips / 296 pytest cases** and all
compilation/artifact/read-only monitor steps. CI merge `50d2c2ab` has exact tree
`3a025d50` and parents `68969a12` / `bf089435`; its tree/history scans PASS.
[Incremental review request](https://github.com/TenchiMisaki/romarr-ci-controller/pull/40#issuecomment-6960062561)
completed on exact head `bf089435` with no new actionable comments or retained
architecture concerns. The original thread is resolved and marked addressed.
[Final assessment](https://github.com/TenchiMisaki/romarr-ci-controller/pull/40#issuecomment-6959915173)
retains the explicit broader repository token scope and interruption limits.
PR #40 merged at `f09e7cf6b1f27ee10de7cc2dc120f1b2bd8638d2`.
Independent REST merge readback confirms exact tested/scanned tree `3a025d50`
and parents `68969a12` / `bf089435`. Installed workflow bytes match the reviewed
candidate. The official public Actions API reports workflow ID `421843249`,
name `Manual controller state canary`, expected path and state `active`.
No executor/workflow behavior changed in the correction; no live canary has run.

Pre-run independent reads reconfirm operational state ref `d2930189`, revision
tag `8a981726`, and unchanged Active state/revision rulesets with exact targets,
required restrictions and no bypass actors. These are configuration/ref checks,
not actual refused-update/deletion behavior. The official repository rule-suite
history endpoint was also checked read-only; it returns integration HTTP 403,
so historical refusal evidence cannot be verified through this connection.
Do not infer absent or ineffective protections from that collection limit.

The connector has no workflow-dispatch capability and local GitHub CLI is not
authenticated. The owner must initiate the one approved run from the official
[workflow page](https://github.com/TenchiMisaki/romarr-ci-controller/actions/workflows/controller-state-canary.yml):
Run workflow, branch `main`, controller SHA
`f09e7cf6b1f27ee10de7cc2dc120f1b2bd8638d2`, approval
`CREATE_RETAINED_CANARY_ONLY`, then Run workflow once. If main moves, do not
substitute an unreviewed SHA; the executor fails closed for a changed run SHA.
After the owner runs it, inspect exact run/actor/head/jobs/logs/artifact,
retained canary state/ancestry and unchanged operational ref/tag/protections.
No repeat mutating run is implied by this handoff. Do not request or
handle credentials in chat. At the installation handoff no live canary had run; hosted observations,
operational acceptance and actual real-ref protection refusals remain NOT TESTED.

### First installed canary attempt — HOST GATE BLOCKED / NO MUTATIONS

[Run #44172592345](https://github.com/TenchiMisaki/romarr-ci-controller/actions/runs/44172592345),
attempt 1, was an owner-triggered workflow_dispatch on main at installed SHA
`f09e7cf6b1f27ee10de7cc2dc120f1b2bd8638d2`, actor and triggering actor
TenchiMisaki / 71314201. The canary step failed at HOST_GATE before the
credential-bearing API path or any mutation. Logs show EXPECTED_CONTROLLER_SHA
received `f09e7cf6b1f27ee10de7` and CANARY_APPROVAL received
`cc2dc120f1b2bd8638d2`: the intended SHA was split across the two inputs.
This is an input rejection, not evidence of a repository permission failure or
storage/concurrency defect. The runtime gate was not weakened or bypassed.

The summary upload succeeded. Artifact `14367434051`, name
`controller-state-canary-44172592345-1`, is bound to the exact run/head/repository.
Independent download verified 274 bytes, SHA-256
`2fadea9e8147944d398d113fa53c10a963fea76626406a5221ad51662a431142`,
single `controller-canary-summary.json`, ZIP CRC and exact parsed result:
BLOCKED_OR_UNCERTAIN / HOST_GATE / operational_acceptance NOT TESTED.
Read-only post-run checks found the expected canary ref absent (404), operational
state still `d2930189`, revision tag still `8a981726`, and main still `f09e7cf6`.
No retained canary history was created and no source dispatch occurred.

Next owner action: start a NEW Run workflow invocation (not Re-run jobs with the
same rejected inputs), branch main, full controller SHA
`f09e7cf6b1f27ee10de7cc2dc120f1b2bd8638d2`, approval
`CREATE_RETAINED_CANARY_ONLY`. The existing scope approval persists for one
actual bounded canary exercise; this blocked pre-mutation invocation does not
justify changing permissions or repeat mutating attempts. Hosted storage race,
simulated response loss, operational acceptance and real-ref refusal behavior
remain NOT TESTED. Preserve this failed run and its summary as negative evidence.

### Approved disabled storage/revision bootstrap — STATE CREATED / ENFORCEMENT PENDING

The owner explicitly approved the exact disabled bootstrap and additive
protection scope on November 17, 2026. This approval persists; no repeat routine
approval is needed. The scope is **APPROVED / PARTIALLY CONFIGURED**. Provisioning and actual
enforcement acceptance remain incomplete. Existing protections
must be preserved; any additional security-sensitive scope requires separate approval. The current
connection exposes repository reads and ordinary Git/PR writes, but no ruleset
write capability; that is a tool boundary, not evidence that protection was set.
A November 17 read verified existing ruleset `27344007` is active and covers only
the default branch, with deletion/non-fast-forward restrictions and no bypass.
Applicable classic protections and branch-rule enumeration remain NOT VERIFIED.

| Proposed target | Exact proposed preparation | Acceptance/recovery boundary |
| --- | --- | --- |
| `refs/heads/controller-state-v1` | Create only if absent, with a sole canonical `state.json`: schema 1, policy disabled/generation 0, empty claims/alerts and null last tick | Never replace an existing ref or reset history; preserve exact initial commit/tree/blob and independent readback |
| State protection | New active branch ruleset matching only `refs/heads/controller-state-v1`; deletion and non-fast-forward restrictions, no bypass actors | Existing default-branch ruleset remains separate; prove actual applicability and rejection behavior before operational acceptance |
| `refs/tags/controller-revision-8a98172685accf23e2a0e51d72bbc954237dc95a` | New lightweight tag pointing directly at the exact reviewed controller commit, only if absent | Reject an existing/moved/mismatched tag; identity alone is not immutability |
| Revision protection | New active tag ruleset matching only `refs/tags/controller-revision-*`; block updates/deletions, no bypass actors | Independently read back actual settings and refusal behavior; future exceptional recovery remains a separate owner-controlled change |

Approval covers only the listed disabled bootstrap and additive protections.
The owner manually created revision-tag ruleset `27484547` and state-branch
ruleset `27485340`. Independent REST readback confirms both Active, exact
`refs/tags/controller-revision-*` and `refs/heads/controller-state-v1` targets,
respectively update/deletion and deletion/non-fast-forward restrictions, empty
bypass lists and `current_user_can_bypass=never`. Existing main ruleset `27344007`
is unchanged. Repository numeric identity and owner were reverified; the owner
permission lookup returned `admin`. Classic protection collection returned 403
`Resource not accessible by integration`; applicable-branch-rule enumeration was
rejected by the connector allowlist. A subsequent credential-free read through the
official public REST endpoint returned both deletion and non-fast-forward rules
from ruleset `27485340` as applicable to `controller-state-v1`. This closes the
applicability collection gap; actual rejected-write behavior remains NOT TESTED.
Classic protection access remains a collection limit, not evidence of absence.

Matching-ref collection returned an empty list before creation. The approved
state branch was created once at `d2930189ec0aa9c59b1a2fdf108fe75892f9ad03`,
with sole parent reviewed controller `8a98172685accf23e2a0e51d72bbc954237dc95a`.
Independent readback confirmed sole-member tree
`023ee9a1690d81c8a9344839c125c721e62d9702`, blob
`36bf4390dd0ccb6d6cb82e279dd613440b454013`, 96 canonical bytes, SHA-256
`4b7cf0033429ef787b37bb343498d4c163d761c1311ef510b759cfb36bd50983`.
Policy remains disabled/generation 0, claims and alerts empty, last tick null.
The production encoder/validator checked the initial state locally. Complete
candidate/server trees and outgoing histories passed checksum-verified Gitleaks
8.30.1 with the accepted positive control. No existing ref was replaced.

The owner subsequently approved the website-only prerelease route with no
attached assets or activation. Supporting branch
`checkpoint/controller-revision-8a981726` was created and independently verified
at the approved commit. The initial owner-published release used a historical
claim tag; after the website correction, live release `449111426` is published
as a prerelease, with zero attached assets, exact tag
`controller-revision-8a98172685accf23e2a0e51d72bbc954237dc95a` and target
`checkpoint/controller-revision-8a981726`. Independent exact-ref readback confirms
it is a lightweight tag pointing directly at
`8a98172685accf23e2a0e51d72bbc954237dc95a`. Revision ruleset `27484547` remains
Active with update/deletion restrictions and no bypass actors. The historical
claim tag still points to `79966309584ede300f3449e6fcccc8dfb2027c4e` and was not
moved by this work. The state branch remains at `d2930189`.

The production read-only deployment preflight was then executed against the
public GitHub REST API with normal TLS verification and redirects rejected.
The reviewed preflight/backend/API/coordinator files were byte-equivalent to
approved controller `8a981726`. Nine sequential, credential-free GETs completed
November 17, 11:43:07–11:43:45 PST (38.66 seconds): repository, exact lightweight
revision, canonical sole-member state, disabled policy/generation 0 with zero
claims/alerts, final tag readback and final repository identity all PASS.
`prerequisites=PASS`, `operational_acceptance=NOT TESTED`,
`activation_allowed=false`, `dispatch_allowed=false`. This is a point-in-time
public-read observation, not authenticated owner-entrypoint, credential-role,
protection refusal, hosted mutation/concurrency, source/provenance or recovery
acceptance. No credentials were loaded and no mutating method was used.

The missing-tag provisioning blocker is now resolved. Configured protections and
exact tag identity still do not establish actual rejected-write behavior. No
force/delete probes, arming, credential deployment or source dispatch occurred.
Configuration
readback alone is not enforcement acceptance. No credential deployment, actual
trial approval record, source dispatch, scheduled caller, unattended activation
or fallback retirement is bundled into this approval. After supported provisioning and readback,
run the read-only prerequisite collector, then separately complete hosted mutation,
owner-control, full-source producer/provenance/skip and failure/recovery acceptance.
A valid initial state or protection write is not a completed operational handoff.

### Remaining operational gates and execution limits

**Earlier post-PR #33 preflight — historical November 17 checkpoint:** the
examined main was `485bb794d08fbded30ca80f5c735d3e3d9bcf2b7`; then-current verified
main was `8a98172685accf23e2a0e51d72bbc954237dc95a` after PR #37; PR #38 above
records the newer verified main. Independent authenticated GitHub
reads returned 404 for the dedicated `controller-state-v1` branch and the exact
`controller-revision-485bb794d08fbded30ca80f5c735d3e3d9bcf2b7` tag. The existing
manual exact-PR advisory workflow is present at this revision. Real durable-backend
race/restart/dispatch acceptance is therefore **BLOCKED: storage and immutable
revision prerequisites were not independently established**. The newer collector
above correctly preserves 404 absence/visibility ambiguity. No canary, state/tag creation,
security-setting change or source dispatch was performed by this preflight.

The implementation still has no installed authenticated owner entrypoint bound to
an accepted deployment/authorization record, notification provider or complete
trusted full-suite source receipt. These remain independent development and
operational gates. Provisioning must preserve role isolation, immutable-ref and
state protections, prepublication scanning and recoverable originals; it must not
be bundled with unattended enablement or credential-service deployment.

The previous session's private owner-guidance original-byte transfer failed at
service discovery with DNS before download/replacement. The resumed session has
the complete supplied 19-file project snapshot and direct Git transport. An
owner-requested continuity/recovery amendment package is now **PREPARED / VERIFIED**
with three amended references, all 19 exact protected originals, semantic
cross-reference positive/negative checks, strict ZIP inventory and CRC validation.
It was saved and made available privately. Actual protected-destination publication,
OneDrive synchronization and Project Instructions remain **NOT VERIFIED / PENDING**;
package availability is not active publication. Existing public continuity rules
remain preserved here; no private content or package is copied into this repository.

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
  immutable artifacts. The prior workstation had no Docker and only Python 3.15,
  with failed direct Git DNS. The resumed controller-only Linux workspace has
  Python 3.12.14 and working Git transport; Docker is unavailable. ROMarr Windows
  3.11/3.13, packaged EXE, live images and signed-attestation acceptance still need
  their prepared artifacts and supported isolated executors. No platform acceptance
  is inferred from controller integration or contract tests.
- Next: continue the existing hosted owner-control, complete-receipt,
  state/dispatch/recovery acceptance path from merged `8a981726`. Local Git,
  read-only preflight, owner-trial binding and ordered full-source collection
  libraries are complete. The approved bootstrap/protection scope above
  remains ENFORCEMENT / HOSTED ACCEPTANCE PENDING; do not repeat accepted tests or create another
  tracker. Preserve live acceptance gates and disabled unattended operation.

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

**Resume from the Current integrated development section above: PR #32 and PR #33 are merged; continue independently gated hosted state/dispatch/recovery and platform acceptance.** Do not repeat accepted source tests, confuse read-only workflow successes with hosted source acceptance, merge the review PR, or silently enable privileged automation. Stop only at the real security, owner-controlled GitHub, upstream or production boundaries.

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

