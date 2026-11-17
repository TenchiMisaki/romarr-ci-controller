# Cross-platform advisory verification: CP-01 through CP-10

This independently implemented controller increment consumes prepared artifacts;
it does not build or publish ROMarr releases. No source/platform probe is wired
to a workflow or scheduler. The new Actions matrix runs controller contract tests
only on Linux Python 3.13 and Windows Python 3.11/3.13.

The original Stage 6-8 operational handoff retains its existing definition. These
new platform capabilities have their own acceptance; they do not retroactively
invalidate prior exact-source evidence or become implicit activation conditions.

## Current implementation and limits

### Review correction verification — November 17, 2026

The five findings on the initial PR #33 head are corrected in the review candidate:
local ZIP headers and every archive byte are accounted for; failed collection is
preserved; both output streams are drained with a live 1 MiB retention limit;
Windows skips produce a valid blocked receipt; and Windows processes are created
suspended, assigned to a kill-on-close Job Object, then resumed. Cleanup terminates
and checks the job even after a successful launcher exit. Only explicitly listed
standard handles are inherited. No process-name or unrelated-PID termination is used.

Local Python 3.15.2 on Windows: **36 controller tests PASS**, including actual safe
Python process trees for launcher-exit, timeout and assignment-denial cases, live
stdout/stderr overflow and producer-to-receipt skip handling. Initial local failures
(missing import, incomplete JUnit fixture and a termination-observation race) were
corrected before publication. Hosted Linux/Windows 3.11/3.13 and exact-head review
remain separate pending gates. These fixtures do not run ROMarr, candidate images
or packaged executables and do not establish platform runtime acceptance.

The process adapter is independently implemented from documented Win32 contracts:
[job ownership](https://learn.microsoft.com/en-us/windows/win32/procthread/job-objects),
[suspended assignment](https://learn.microsoft.com/en-us/windows/win32/api/jobapi2/nf-jobapi2-assignprocesstojobobject),
and the explicit inherited-handle list. No third-party implementation was copied.

| Requirement | Advisory implementation | Remaining acceptance |
| --- | --- | --- |
| CP-01 Docker runtime | Digest-pinned prepared-image probe; local socket; no pull/build/push, host bind or published port; network none, non-root, read-only filesystem, resource limits, three consecutive health passes, identity and cleanup checks | Real standard/browser candidate runs, application assertions beyond health, negative startup/dependency/isolation/cleanup tests on disposable hosted Linux; platform/architecture policy |
| CP-02 Windows 3.11/3.13 | Clean exact-source/prepared-interpreter checks and a fixed focused file-report/path/sidecar suite; real JUnit parser reuse; separate per-version receipt identities; hosted controller-contract matrix | Actual ROMarr source runs on both versions; loopback/authentication/persistence coverage and accepted dependencies; not inferred from controller tests |
| CP-03 Build provenance | Actual file hashing or digest-pinned OCI subject; pinned GitHub CLI binary; signed SLSA verification constrained by repository, signer repository/workflow/revision and source revision | Live signed positive/negative attestations and bundle-to-contained-EXE mapping; an absent attestation blocks, even if BUILD-INFO/labels claim the expected SHA |
| CP-04 Multi-platform receipts | Versioned strict receipt/case/manifest schema; exact source/base/controller/producer/run/attempt/job/scope/artifact binding; independent authenticated metadata and provenance contracts | Accepted producer/verifier jobs and ordered live collection for each platform; other CI providers need their own authenticated adapters |
| CP-05 Windows EXE | Digest-check actual prepared EXE, launch its smoke-test interface invisibly on a disposable Windows runner, validate fixed boolean behavior proof with restricted PATH/private profile | Real package/EXE run, process-tree/timeout cleanup, UI/behavior proof and independent artifact provenance; packaging success alone is insufficient |
| CP-06 Toolchain preflight | Docker daemon OS/architecture and prepared-image identity, exact Windows interpreter minor/pytest, pinned verifier binary and clean source, private-path/runner gates | Real platform dependency/version inventories and unsupported/permission fixtures; no automatic dependency installation |
| CP-07 Release readiness | Explicit versioned required/optional platform policy; same-revision aggregation; missing platforms remain NOT TESTED; release/unattended authorization always false | Owner-accepted platform/scope/skip policy and independently authenticated live receipts; never publishes/releases/merges |
| CP-08 Allowlists/privacy | Only receipt.json, cases.json, manifest.json; bounded archive/members; canonical JSON and hashes; no extra fields, case names, raw logs, symlinks, ZIP comments/extra metadata or trailing content | Producer-side strict upload wiring and live leakage rejection for each platform; this increment uploads no candidate output |
| CP-09 Runtime dependencies | In-container archive/git/import and non-root config-write checks; browser client/unar checks; Windows dependency preflight | Real plugin/seccomp/archive-format and binary-bundled dependency/permission validation; import alone is not plugin/runtime acceptance |
| CP-10 Failure classification | Build/environment/startup/test/collection/provenance/freshness dimensions; unsupported, skipped, incomplete, blocked, stale and not-tested remain distinct | Live classification/recovery examples across supported platforms; no green result from failed/missing required evidence |

## Trust and receipt contract

The trusted verifier creates `ExpectedPlatform` from authenticated current source,
approved workflow and actual run/job/artifact observations. Candidate output never
defines its own acceptance expectations. GitHub metadata requires exact complete
job collections (bounded to 100), successful required steps and exact artifact
digest, run and producer revision. Source repo/head/base must remain unchanged on
independent reads. The collector must preserve before/download/final-read order;
passing snapshots to a pure verifier does not establish network authenticity or
ordering by itself.

### Ordered full-source collection library

`source_receipt_collector.collect_source_receipt` supplies the missing ordering
for full-source Linux or Windows 3.11/3.13 receipts in the fixed personal source
and controller repositories. It rejects focused/package scope before any read;
the trusted caller must separately approve the exact full-suite workflow, job,
required steps and producer/controller revision. No producer or execution policy
is inferred from a receipt claiming `source-full`.

The collector checks an eligible exact PR and current base, validates complete
run/job/step/artifact metadata, rechecks source, downloads only the fixed artifact
ID with a 4 MiB bound and pinned digest, and validates the complete anonymous
envelope before calling an independent execution-provenance verifier. It then
re-reads run/jobs/artifact and finally PR/base after that verifier. Expiry, stale
source, changed metadata, size/digest/count/skip/privacy failures and collection
errors block progression. Callback errors are sanitized; mutations and retries
are not implemented.

Without independent provenance, a valid bundle remains `ADVISORY_BLOCKED`.
Even verified full-source receipts remain advisory, with test acceptance,
publication and unattended flags false. Injected callbacks do not prove actual
authentication, redirect isolation or source execution. The current manual
focused advisory workflow does not produce this three-file platform contract;
it is deliberately not promoted or silently reinterpreted as full-suite evidence.
Accepted producer/verifier jobs, transport and live ordered collection remain
required. The library installs no workflow, credentials, publisher or source job.

The existing read-only HTTP adapter supports an explicit per-instance archive
limit up to 4 MiB for this contract. Its default remains 64 KiB, preserving the
current focused advisory boundary. The larger limit does not alter fixed API
targets, certificate verification, redirect allowlists, token-free storage reads,
actual byte bounds or digest checks. Tests pass a real full-size envelope through
the concrete transport with modeled HTTP; live network acceptance is separate.

### Dormant source receipt serialization

`source_receipt_producer.source_bundle` converts bounded private pytest JUnit
bytes into the same three-member platform envelope consumed by the independent
verifier. A trusted host supplies fixed source/controller/run/job identity and an
independently pinned expected case count. It accepts only the flat UTF-8 pytest
JUnit dialect, checks suite/root totals against actual case outcomes, and refuses
empty/incomplete suites, ambiguous nested outcomes, unsafe XML, unsupported exits
or exit/count disagreement. Cases contain ordinal/outcome only; names, paths,
properties, messages, output and tracebacks are never copied. Stored ZIP entries
have fixed timestamps, filenames and permissions; the real archive parser checks
the resulting bytes before they can be returned.

Failures/errors remain FAIL and skips remain SKIPPED. Provenance is BLOCKED and
freshness NOT_TESTED in producer output; the consumer still requires separately
authenticated run/job/steps, ordered fresh source reads and independent execution
proof. Matching counts cannot prove full-suite selection, absence of deselection,
toolchain identity, completed collection or safe execution. The host must establish
those facts independently before invoking this full-source serializer. The
environment/collection PASS fields are that host's assertions, not inferred facts
from XML. No runner, workflow, private-file reader, uploader or credential loader
is installed here. The existing focused advisory producer remains unchanged.
Tests exercise genuine serializer/consumer round trips with synthetic metadata,
not actual ROMarr source execution or hosted provenance acceptance.

Receipt ZIPs use schema `romarr-platform-receipt-v1`, anonymous ordinal/outcome
records and a two-file SHA-256 manifest. ZIP limit is 4 MiB; each member is at most
1 MiB, case count at most 10,000. All members and field sets are explicit. Missing
results, failed/skipped required steps, duplicate or nonordinal cases, count
mismatch, secret/path/log fields, altered digests and stale revisions reject.
No raw JUnit, process output, screenshots or build reports are uploaded here.

Producer `provenance=PASS` is never sufficient. The default independent-provenance
callback is absent, so provenance remains BLOCKED. For packages, the concrete
attestation adapter invokes a separately pinned `gh attestation verify` binary
with exact source and signer constraints; the subject is never executed in the
credential-bearing verifier. File digest and verifier bytes are checked. OCI
subjects must be digest-pinned. CLI output is bounded/private; cryptographic
verification is delegated to that explicitly trusted tool, not reimplemented.
Source-only receipts also require separately trusted source-execution provenance;
they do not inherit package attestation acceptance. No network attestation PASS
has been established by mocked contract tests.

Platform results remain advisory. Readiness aggregates one source/base/controller
identity under a versioned explicit required/optional policy. Android is reserved
as a future optional platform and is currently unsupported; no Android PASS can
be manufactured by schema reuse. Additional CI providers must implement their own
authenticated metadata adapters while reusing the bounded envelope/accounting
rules, rather than synthesizing GitHub-shaped observations.

## Probe execution and recovery

Probe entrypoints are dormant libraries, only for separately accepted disposable
runner contexts. Runner environment variables are targeting guards, not proof of
security isolation or owner authorization. A future privileged dispatcher must
validate the actual workflow/job/runner and acceptance record independently.
No private host is a fallback. Child environments exclude tokens, agent sockets,
Git/Python overrides and GitHub command-file paths. The attestation verifier has
its separate read credential; probes never receive it.

Docker observes a prepared immutable image via an explicit local daemon socket.
It checks the actual running image ID and isolation configuration, caps startup
attempts and resources, and removes only the uniquely labeled owned container.
Any failed/unverified cleanup blocks overall operational acceptance, independently
of observed test behavior. No host mounts, media, registry credentials or external
network are given to candidate code. The standard/browser import checks are
bounded observations, not a complete plugin or browser-service test.

Windows source probes require a clean exact checkout and separate reports under
the disposable runner temporary root. Interpreters/dependencies are provisioned
outside this library. JUnit is private, bounded and converted by the existing
collector to ordinal outcomes. The fixed suite is focused, not full application
acceptance. The executable probe verifies actual EXE bytes and its behavioral
proof; source revision is independently verified, never inferred from a success
boolean or file name. Any timeout, missing proof, package mismatch or unsupported
environment preserves blocked/failed evidence rather than triggering a rebuild,
production retry or implicit fallback. Candidate artifacts and prior receipts are
never overwritten to repair a reporting failure.

## Interoperability, provenance and verification

Read-only interoperability review used official `BlizzHacker/romarr` at
`3d2bc6cc2ede0cd555e49e44b3fc84bf7e9f2f1a`: `AGENTS.md`, the Docker/Windows
workflows, both Dockerfiles, entrypoint and build_info interface. The Docker
workflow disables build attestations; self-reported labels therefore cannot
close CP-03. Windows smoke proof fields and focused-suite paths are compatibility
interfaces, not copied maintainer CI. This controller does not adopt release
packaging, publishing, credentials, screenshots or raw-log upload behavior.

All new source is independently implemented under this controller's MIT license;
no substantial maintainer source is copied. Existing first-party JUnit accounting
is reused. Tool contracts were checked against official Docker run/tmpfs and
GitHub CLI attestation documentation and the locally installed CLI help.

Local contract tests use simulated Docker/process/provider boundaries and real
canonical archives/JUnit. They do not prove Docker daemon behavior, ROMarr Python
3.11/3.13 compatibility, actual EXE startup or cryptographic network acceptance.
The dedicated hosted matrix additionally tests the controller's real Python
compatibility; detailed exact-head runs/reviews/security evidence belong in its
review PR and the existing project backlog companion.
