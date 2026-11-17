# Stage 6 local dispatch ledger prototype

This offline library tests one part of an owner-controlled dispatcher design. It
has no network adapter, workflow trigger, credentials, receipt acceptance or test
runner. No existing workflow imports it. The policy starts disabled and only an
explicit caller action can change it in the private prototype database.

The implementation reuses the existing exact PR/head/base and base-tip checks,
and excludes draft, closed, foreign, backlog and review candidates. Authenticated,
fresh snapshots remain the future trusted caller's responsibility.

A SQLite immediate transaction permits one global outstanding reservation. The
revision key contains PR number, head and base; changing the controller does not
permit a duplicate. A policy generation and random ticket bind progression to
the original reservation. Disarm invalidates old tickets; rearming cannot revive
them. A future POST boundary must recheck current policy and source separately.

Before any future network attempt, `begin_dispatch` commits
`DISPATCH_UNCERTAIN`. Crashes, missing run IDs, POST timeouts and rejected requests
all retain that state. Neither restart nor policy changes delete it or authorize
another attempt. The prototype deliberately stops after one reservation: run-ID
binding, completion and recovery actions still need a separately reviewed design.
It does not automatically release reservations, expire leases or delete claims.

## Coverage and limits

Tests exercise real independent SQLite connections racing for one reservation,
restart persistence, duplicate work, stale source/base, candidate exclusions,
ticket forgery, disarm/rearm, corrupt storage and interrupted/uncertain dispatch.
Existing source/artifact/transport tests remain the evidence for their unchanged
logic. This is local-file atomicity, not distributed-scheduler acceptance.

Before installing any unattended adapter, independently validate authenticated
owner-only arm/disarm, durable storage permissions and recovery, cross-run atomic
claims, unique run-ID/source correlation, completion and reconciliation, bounded
rate/concurrency, failure alerts and notification delivery, credential expiry,
source movement at dispatch, uncertain POST handling, and trusted complete receipt
acceptance. Disarm prevents future attempts, but cannot undo an already-issued
network request. A real adapter must define and test this in-flight boundary.

One separately accepted live unattended trial is still required. Preserve the
manual fallback. This prototype does not authorize unattended pytest, automatic
ROMarr remediation, deployment or fallback retirement.
