# Read-only protection observations

This dormant library observes the three approved repository rulesets and the
active rules returned for main and controller-state-v1. It installs no transport,
workflow, credentials, permission grant, administration tool or execution hook.
The caller must provide an independently trusted bounded JSON reader. The wrapper
rejects everything except six fixed GET paths before calling that reader.

A configuration observation PASS requires the fixed public repository and owner,
default main branch, active enforcement mode, exact approved target selectors,
empty bypass list and each required restriction. Additional stronger rules are
retained and never printed or modified. Each settings/applicability observation
is read twice, with final repository identity verification. Changed security-field
fingerprints block the result; later successful reads do not erase earlier failures.
Only digests and fixed verdicts are exported, not provider error text or arbitrary
rule parameters, URLs or actor metadata. Denied/missing reads remain collection or
visibility gaps, not proof that protections are absent.

The fixed rulesets are Protect main 27344007 (deletion/non-fast-forward), operational
state 27485340 (deletion/non-fast-forward), and revision tags 27484547 (update/deletion).
Their exact owner-approved selectors are recorded in authoritative backlog #23.
This is an observed baseline, not permission to replace, weaken or delete any
protection. Unexpected baseline changes fail closed and need investigation.

**Configuration/applicability is distinct from refused-write enforcement.** GitHub's
branch-rules endpoint returns active rules that apply, including for a nonexistent
branch. It excludes disabled/evaluate rulesets; its output is not a record of a
rejected operation. No equivalent tag-applicability endpoint is assumed here.
Refused-write enforcement, tag applicability and operational acceptance always
remain NOT TESTED; activation/dispatch remain false, even with configuration PASS.
No deletion/force-update probe, state mutation or automatic repair is performed.
Classic branch protection and rule-suite history remain separate evidence scopes;
this library cannot convert the known administrative read limitation into proof.

Official contracts reviewed:
- https://docs.github.com/en/rest/repos/rules
- https://docs.github.com/en/rest/repos/rulesets
- https://docs.github.com/en/rest/repos/rule-suites
- https://docs.github.com/en/repositories/configuring-branches-and-merges-in-your-repository/managing-rulesets/about-rulesets

No third-party code was copied. Offline tests cover selectors, restrictions,
bypass, stronger rules, exact source identity, denied/missing reads, drift and
write/foreign-path refusal. Required exact-head hosted CI, review and live readback
results are recorded in the implementation PR and backlog. This library does not
supersede the successful manual state canary or authorize another run.

Recovery: preserve raw evidence privately, existing refs/settings and the earlier
known-good implementation. Investigate any failed observation read-only. Correct
only the isolated collector after review; do not change security settings or
reset claims/refs to make an observation pass. No deployment is implied by merge.

Live collection limitation observed November 17: the public unauthenticated
ruleset response omitted bypass_actors. The collector correctly refused to assume
that omission means an empty bypass list. This is incomplete visibility, not
proof of a weakened protection. Connector-backed complete observations require
independent collection and are recorded separately from the public-read attempt.
