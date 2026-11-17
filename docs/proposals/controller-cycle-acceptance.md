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

Before operational acceptance: independently validate a complete trusted receipt
contract and isolated full-scope source runner; source/job/artifact/skip policy;
owner arm/disarm entrypoint and deployment record; state-branch permissions and
actual cross-run races/readback; immutable ref protection; nonce-correlated live
dispatch/recovery; credential expiry/renewal and least-privilege installation;
real provider delivery and delivery reconciliation; native/fallback collision,
sustained cadence, missed/failed-run alerts, interruption and retention recovery.
Then obtain separate owner authorization for one bounded unattended trial and
explicit primary-method acceptance. Preserve the independent manual fallback.

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
