# Proposed manual canary criterion: verified sibling updates

Status: PROPOSED / NOT APPROVED FOR INSTALLATION OR LIVE EXECUTION.

The owner-run canary 44181621002 on controller 3238861d created eight commits,
recorded one successful writer and seven PATCH 422 messages whose fingerprints
match `Reference cannot be updated`. The installed strict message classifier
blocked before simulated response-loss recovery. That result remains historical
BLOCKED; this proposal does not retroactively turn it into PASS.

## Proposed change

Preserve explicit non-fast-forward conflicts as their own category. Recognize the
exact generic message only from a completely read, identity-encoded PATCH 422
JSON response. Associate each rejected request with its validated target commit.
Before proceeding, independently GET all eight distinct candidate commits and
require their returned identities, exact canonical disabled-state tree and sole
seed parent. Require one successful writer, complete outcome coverage equal to
the created commit set, and independent canonical winner readback.

This would accept **observed single-winner sibling exclusivity**, without claiming
that the generic message proves the cause of rejection. Explicit and generic
rejections remain separate report counts. Unknown responses, other statuses,
incomplete/encoded bodies, malformed or foreign/duplicate candidates, extra or
wrong parents, changed winner refs and read failures block recovery. The existing
simulated lost-response step remains a single child write after successful
verification, never a transport retry or a naturally occurring failure claim.

Operational acceptance remains NOT TESTED. No production state, source dispatcher,
workflow inputs, credential scope, rulesets, retries, force/delete/reset behavior,
or unattended execution is changed. Failed canaries remain retained. Installing
this criterion requires explicit owner approval after exact-head tests, security
scans, hosted CI and CodeRabbit review. A further bounded manual live validation
needs separate owner authorization; do not dispatch it automatically.

## Online research and alternatives

GitHub documents `force=false` fast-forward enforcement, but HTTP 422 also covers
validation/spam failures and the generic message is not a documented specific
non-fast-forward signal:
https://docs.github.com/en/rest/git/refs

GitHub recommends serial requests and pacing mutation-heavy integrations. The
bounded race here deliberately tests contention; it is not the normal writer
scheduling model:
https://docs.github.com/en/rest/using-the-rest-api/best-practices-for-using-the-rest-api

The documented GraphQL `createCommitOnBranch` input has `expectedHeadOid`, making
the expected starting revision explicit. Grafana's commit action uses that field:
https://docs.github.com/en/graphql/reference/commits
https://github.com/grafana/github-api-commit-action/blob/main/action.yml

GraphQL is a separate possible backend redesign, not implemented here. Its
credential, response-error, identity/readback, recovery and stale-head behavior
would need independent review and tests. This proposal does not copy third-party
code or introduce dependencies. Existing backend and publication gates remain.

## Validation boundary and recovery

Disposable real-Git tests cover both explicit and generic rejected siblings,
identity/tree/parent corruption, duplicate/missing/foreign outcomes, multiple
winners, changed final refs, unknown HTTP errors and strict generic-message
recognition. Local focused tests pass. The local full-suite attempt was blocked
by missing pytest in the selected interpreter (including pytest-child/JUnit
failures); it is not a passing full-suite result. Required hosted full-suite and
exact-head review results belong in the implementation PR and authoritative
backlog. Live behavior of this proposal is NOT TESTED.

Until approved, leave the implementation PR unmerged and current main unchanged.
If an approved installed revision later fails, preserve evidence and stop further
manual canary runs. Do not reset/delete refs or weaken protections as recovery;
prepare a reviewed follow-up correction while retaining disabled operation.
