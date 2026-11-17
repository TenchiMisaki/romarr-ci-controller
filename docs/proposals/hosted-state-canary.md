# Manual hosted state canary — owner-approved manual workflow

The owner approved installation and one manual run on November 17, 2026
(Pacific), after the exact PR #39 review. The workflow is installed at
`.github/workflows/controller-state-canary.yml`. It has no scheduled or automatic
trigger. This approval covers the concrete repository-write scope below, not
operational controller activation or unattended source testing. A merged workflow
is not evidence that its manual run or live acceptance succeeded.

## Proposed scope

One owner-triggered, main-only, exact-reviewed-SHA GitHub-hosted Linux job obtains
an ephemeral `GITHUB_TOKEN` with repository contents-write permission. That token
is broader than a per-ref permission: the reviewed application adapter constrains
its use, but cannot make a provider-wide credential into a per-branch credential.
Checkout never persists credentials. The job checks trusted run/owner/repository
identity, explicit manual confirmation and matching controller SHA before loading
the token or writing. It accepts no source checkout, test command or target ref
input. There is no source execution, workflow dispatch, owner arming or policy
change, and no alteration to the operational state branch or revision tag.

The only ref it creates is `controller-canary-<run_id>-<attempt>` in the fixed
controller repository. It refuses any existing matching ref, retains the branch
and all history, and writes only the same canonical disabled initial state.
Commits have one parent and fresh unique backend identifiers. No force, delete,
reset, mutation retry or cleanup is implemented. Repository GET observations of
operational state before/after must agree; a changed observation blocks completion
rather than restoring an earlier value.

The job exercises the production `GitHubState` through a mapping adapter that
redirects its exact state paths to the run-owned canary ref. A barrier holds eight
writers before their non-force PATCH; exactly one distinct commit must win.
Only the server's explicit HTTP 422 `Update is not a fast forward` response counts
as an expected losing writer. Authentication, rate limits, transport errors,
unexpected validation responses and uncertain readbacks block the canary.

Afterward a second identical-state transition is actually sent, and the adapter
deliberately drops its successful response. A fresh client reads the retained
state and verifies a sole-parent successor of the race winner. This is injected
response-loss evidence, not a naturally observed network failure or separate
process restart. Source dispatch is impossible through the adapter. The report
contains only fixed status codes, public run-owned ref/commit IDs and counts.

## Bounded failure evidence

A blocked run reports a fixed phase and allowlisted error category, with HTTP
method/status and a fixed reason category where available. It never publishes
raw server responses, exception text, URLs or credentials. Race observations
retain at most eight writer failures, counts of successes/explicit conflicts and
created commit count. Every non-conflict writer failure blocks completion; this
instrumentation adds no retry and accepts no additional conflict response.
The original uncertain retained canary branch is preserved. Another live attempt
requires owner authorization; code review/CI is not evidence of a repaired live
race or a successful response-loss observation.

## Acceptance and recovery

Local tests use actual disposable bare Git repositories behind modeled HTTP.
The duplicate-commit negative control must fail exclusivity. These tests do not
establish live GitHub race/refusal semantics, token permissions, workflow execution
or platform/source acceptance. Even a later hosted success leaves
`operational_acceptance=NOT TESTED`; canary results are only scoped observations.

This canary does not test deletion/force protection on the real operational ref,
revision-tag immutability refusal, actual controller claim/dispatch fencing,
accepted owner deployment, notification delivery or full-source provenance.
Do not weaken rules or perform destructive probes against real refs to fill those
gaps. No new ruleset is proposed for canary branches.

If anything is rejected or interrupted, preserve the exact run ref and all commit
objects; do not rerun a mutating request to hide uncertainty. A new workflow
attempt uses a new retained ref; investigate the preceding one independently.
Review object ancestry and canonical disabled state through read-only GitHub
requests. Removal of retained canary branches is a separate owner-controlled
cleanup decision, not part of this candidate.

Independent first-party implementation reusing the reviewed controller backend,
no third-party source copied. The workflow uses already pinned official actions.
GitHub's [references API](https://docs.github.com/en/rest/git/refs) defines create
and non-force reference updates; real hosted behavior remains to be tested.
