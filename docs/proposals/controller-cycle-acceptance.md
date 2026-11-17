# Durable controller cycle: Stage 6-8 development

This is a dormant implementation for review, not installed automation. No new
workflow calls it, no state branch or revision tag is provisioned, no credentials
are loaded, and no source test is scheduled. The existing manual source workflow
gains only an optional correlation input and deterministic run title.

## Integrated components

`controller_cycle.Controller.cycle` joins persistent tick deduplication, one
outstanding claim, run reconciliation, advisory collection, existing CodeRabbit
review parsing and sanitized failure notification. It uses the existing exact
PR/head/base checks and direct dispatch-response checker. `GitHubPorts` provides
real, restricted API adapters; `GitHubState` supplies cross-run Git persistence.
The older SQLite prototype stays unchanged as historical local-only coverage.

The Git backend requires an independently provisioned dedicated
`controller-state-v1` branch containing only canonical `state.json`, initially
`initial_state()` with policy disabled. Each transition creates a blob, tree and
commit with exactly the previously observed state commit as parent. A non-force
ref update excludes competing sibling writers; independent readback is required
before a dependent side effect. No branch creation, force, reset, deletion,
automatic conflict merge or mutating retry exists. Missing/corrupt/oversized
storage blocks rather than resetting it. All historical claims remain present.
The one-megabyte bound requires a separately reviewed archive plan when reached;
this implementation never silently truncates evidence.

Each state commit includes a fresh per-call random identifier. Identical state
transitions from the same parent in the same second must produce distinct
commits; an idempotent update to a shared identical commit is not an exclusive
dispatch fence. The dedicated competing-writer regression covers that case.

Before POST, the reservation becomes `DISPATCH_UNCERTAIN` durably, source is
re-read, and policy generation is checked again. Dispatch requests direct run
details against a separately provisioned lightweight controller-revision tag,
verified before and after POST. Independent run metadata must match the exact
repository, controller commit, workflow, first attempt, URL and run title. The
title includes the PR/head/base and random claim nonce, preventing old or
unrelated runs on the same controller from satisfying reconciliation. A missing
run ID, timeout, uncertain state write, moved source or rejected POST leaves the
claim for explicit authenticated reconciliation. No newest-run guessing occurs.

Owner control requires independent authenticated user ID and repository-owner
reads. Arming additionally requires a separately supplied operational-acceptance
capability; its default is false. This library parameter is not independent proof
of owner acceptance. A future privileged entrypoint must bind it to an accepted
deployment/authorization record, never PR input, environment truthiness or source
job output. Disarm increments generation, cancels pre-POST reservations and
preserves uncertain/in-flight claims. A request already issued cannot be recalled.

Stage 7 reuses `status.review_status`, including bot identity, exact covered SHA,
actual findings and unresolved threads. Persistent refresh budgets allow at most
20 additional polls, at least 60 seconds apart, with source rechecks on both sides.
Collection errors do not imply clean review. This implementation records findings
and next states; it does not autonomously modify source or call a coding agent.
The cycle schedules pending completed-advisory review refreshes within the
persistent budget; review-ready claims are not repeatedly polled.
An independently verified changed PR/head/base retires its obsolete completed
review as SOURCE_STALE and permits the fresh candidate in the same cycle. Invalid
collection remains blocked; it is never silently reclassified as source change.
Authorized repairs still use the ordinary isolated-branch test/review process.

Stage 8 keeps test acceptance separate from advisory completion. The configured
collector must use existing ordered authenticated provenance and byte checks,
with expectations pinned to the stored claim/controller/run. The existing
70-case advisory is not a complete full-suite receipt. Failed runs and pending
runs remain distinct. Tick deduplication survives restarts and blocks regressed
time. It is not evidence of actual hosted scheduler cadence or fallback collision
acceptance. Alert payloads contain only an opaque ID and fixed reason code.
Delivery requires an authenticated exact idempotency receipt. Unknown delivery
persists and is never blindly retried; confirmed non-delivery permits at most
three attempts spaced at least five minutes apart. No notification provider,
credentials or actual delivery has been provisioned or accepted.
Failed-run transitions persist their alert intent atomically. Later ticks process
pending alerts for terminal claims, including after interruption before the first
send or confirmed non-delivery. Unknown deliveries remain reconciliation-only.

## Credential and API boundaries

Separate reader, state writer, dispatcher and owner identity roles have complete
path/method allowlists. The state writer cannot dispatch; the dispatcher cannot
write state or source. Owner identity access is separately injected. No source
execution occurs in these processes. API redirects are rejected, TLS validation
remains enabled, JSON reads are bounded, and mutations are attempted once.
Transient GET failures have three visible attempts; authentication, authorization,
identity and invalid data are not retried. Raw exceptions and response content
are not included in public progress output. Repository-secret/settings changes,
new services and credential deployment require separate owner authorization.

## Verification and remaining acceptance

Focused offline tests cover the real coordinator/API/backend implementations:
disabled startup, owner/authentication rejection, stale/draft/review/backlog
sources, legacy claims, an eight-worker race, CAS conflict, lost write response,
uncertain dispatch/restart, disarm/rearm and in-flight boundary, wrong run identity
and nonce, actual review-parser integration, cadence/clock guards, delivery
deduplication and uncertain send recovery, redirect rejection and bounded retries.
These use simulated authenticated APIs; they are not live hosted mutation tests.
Exact-head hosted CI, review and security results belong in the linked review PR.

### Real local Git integration coverage

`tests/test_git_state_integration.py` supplements the existing object-map fixtures
with disposable bare repositories and real Git blob/tree/commit IDs, ancestry
checks, expected-old ref transactions and strict object-integrity validation.
Eight writers observe the same parent and fixed timestamp; only one distinct
commit may advance the ref. A controlled nonce collision reproduces eight
idempotent successes, demonstrating sensitivity to the retired duplicate-fence
defect. The modeled REST boundary accepts existing-target updates and rejects
non-fast-forward siblings; it is not an authenticated GitHub server.

Lost fence-response tests reopen the stored uncertain claim in a separate Python
process, and verify that the coordinator never dispatched. Rejected fences retain
their original reservation; stale leases create no additional objects or mutation
attempts. Git-valid but noncanonical state bytes are rejected. No production state
branch, revision tag, credential, workflow permission or source execution changes
are needed for these tests. Real hosted races, transport/authentication and owner
activation remain independent acceptance gates.

Before operational acceptance: independently validate a complete trusted receipt
contract and isolated full-scope source runner; source/job/artifact/skip policy;
owner arm/disarm entrypoint and deployment record; state-branch permissions and
actual cross-run races/readback; immutable ref protection; nonce-correlated live
dispatch/recovery; credential expiry/renewal and least-privilege installation;
real provider delivery and delivery reconciliation; native/fallback collision,
sustained cadence, missed/failed-run alerts, interruption and retention recovery.
Then obtain separate owner authorization for one bounded unattended trial and
explicit primary-method acceptance. Preserve the independent manual fallback.

### Read-only deployment preflight

`deployment_preflight.inspect_deployment` checks the fixed numeric repository and
owner identities, public/nonarchived repository state, the exact lightweight
controller-revision tag, and the existing canonical Git-backed state through the
reviewed parser. It re-reads repository/tag identity after state collection and
blocks on an already-enabled policy. Its wrapper refuses mutations even if a
caller accidentally supplies a write-capable adapter. It never provisions,
initializes, resets, arms, disarms, dispatches or loads credentials.

Reports contain fixed status codes and opaque commit identities/counts, never raw
state claims, tokens, exceptions or API payloads. A GET 404 is reported as
`NOT_FOUND_OR_NOT_VISIBLE`, not proof that a resource is absent; authentication,
transport and collection failures remain distinct from invalid content. An
independent state read can continue after an unavailable tag, but a repository
identity failure blocks all dependent reads.

`prerequisites=PASS` means only these point-in-time observations passed.
`operational_acceptance=NOT TESTED`, `activation_allowed=false` and
`dispatch_allowed=false` remain explicit for every result. Tag identity is not
ref-protection evidence. No owner authorization, credential isolation, live
concurrency/recovery, full-suite receipt or notification acceptance is inferred.
The collector is a dormant library, not an installed entrypoint or workflow.

### Owner-bound single-revision advisory trial

`owner_trial.TrialApproval` validates bounded canonical approval bytes against a
SHA-256 pin supplied independently by a trusted deployment. The record binds
the fixed controller/source repositories, authenticated owner's numeric ID,
controller SHA, manual advisory workflow, exact PR/head/base, and issued/expiry
times. The accepted scope is only `single-revision-advisory-trial-v1`; it does
not approve general unattended operation, test acceptance or publication.
Synthetic tests use an ancient time window and are not live approval records.

`OwnerTrialController` reuses the existing coordinator, owner identity checks,
durable CAS/readback, one-outstanding-claim limit and historical source dedup.
It checks the immutable approval's scope/time before arming, reservation, the
durable dispatch fence and immediately before POST. Expiry after fencing leaves
the claim uncertain with no POST; it never silently frees a claim. Authenticated
disarm and explicit known-run reconciliation remain possible after expiry.
Checks cannot recall a POST already issued or certify future clock accuracy.

The trial supplies a `pre_post` predicate to `GitHubPorts.dispatch`. The adapter
rechecks it after its last pre-POST revision-tag GET, directly before the mutating
request, so approval cannot pass once and then expire during that network lookup.
An adapter that cannot honor this callback must fail rather than drop the guard.
The no-retry rule and uncertain persisted claim remain unchanged on rejection.

The trusted host must obtain actual owner approval independently and protect
the expected digest, controller, clock, source isolation and API roles. A hash
computed from caller-supplied JSON is not authentication. No code here loads
approval from a PR, source-job result, environment flag or workflow input. The
existing base coordinator's default-disabled boolean remains a low-level trusted
host capability, not standalone approval proof. Only the scope-bound subclass
adds this trial binding; a host must not substitute the unbound base class.

This is a dormant library integration, not an installed authenticated owner
entrypoint or accepted deployment. No real approval record, credential service,
state storage, protected tag or scheduled caller is provisioned. Hosted state
protections, authenticated owner execution, expiry/recovery behavior and one
bounded trial still require their independent operational acceptance evidence.

## Recovery

Read the exact stored claim and authenticated run/receipt evidence. Preserve
unknown claims, original state commits, source identity and failed observations.
Disarm through the separately accepted owner path before investigation; do not
delete a claim, reset the state branch or retry POST to make progress. A lost state
PATCH response requires independent commit/ancestry/readback reconciliation.
Provider receipt lookup must resolve unknown notification delivery before resend.
State restoration, credential renewal, rearming and any archive migration require
separate reviewed operational recovery evidence. No production system, protected
security setting or manual fallback is modified by this development.

## Provenance

Independently implemented in this MIT-licensed controller, reusing its existing
first-party identity, dispatch and CodeRabbit parsers. GitHub REST contracts were
checked against the official [Git references API](https://docs.github.com/en/rest/git/refs)
and [workflow dispatch API](https://docs.github.com/en/rest/actions/workflows).
No third-party source tree or private operational material is copied here.
