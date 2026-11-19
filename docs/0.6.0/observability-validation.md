# Observability and evidence-backed improvement

Validated 2026-09-07 on `develop/0.6.0-astra`. This extends the
[handoff work](handoff-validation.md) by connecting the managed workflow's audit
records to retrospectives and evaluated improvement proposals.

## Delivered behavior

`workflow-report` exposes capture health. Optional capture records distinguish
disabled, not observed, recording, capped, degraded and unknown states without
claiming complete coverage. Packet metadata records canonical hashes, versions,
sizes, omissions, source revisions and section requests. These records describe
emission by an adapter or command, not receipt, reading or understanding. Ambiguous
unit attribution stays unknown. Capture has its own bounded, nonblocking append
path and cannot determine whether a workflow operation is accepted.

Close-attempt events record the final outcome after verification, review and source
freshness checks. Operation identities join attempts to their review rounds,
including cached-round reuse, failed preflight and interrupted-close recovery.
Failure to persist audit storage preserves the original operational exception;
it cannot manufacture a successful close.

`retrospective` supplies a bounded historical index and targeted original evidence.
JSON Pointer selection reaches an individual old finding or check without loading
the entire state history. Observations preserve evidence references, explanations
and uncertainty separately. Question classifications and earlier-phase attribution
are explicitly reported judgments, with unknown denominators. Original-evidence
freshness is checked through indirect observation references as well as direct ones.
Temporary requests and exports stay under `.fbk/runtime/`; durable records stay in
the unit state, outside authoring and acceptance-review context.

`fbk-improve` routes managed units through this evidence. It investigates bounded related issues, considers runtime and host
causes, and supports instruction removal and no-change findings. Its ledger records
a hypothesis, baseline and planned check before adoption; actual target hashes at
adoption; then assessment, evidence, limitations and follow-up results. Changed
targets or evaluated evidence require re-evaluation. Retain, defer and rollback
decisions are audited without editing files or granting authority.

## Verification

The final combined runner passed **879 Python cases** and **353 shell assessment
rows**, with no failures, errors or skips. The workflow group contains 206 cases.
Ruff, the improvement skill validator and `git diff --check` passed.
[Recorded suite summary](evidence/observability-tests.json); full local reports are
in `test-results/run-qfd21j6j/`.

The tests exercise the public CLI and module boundaries: capture failure isolation,
cap disclosure, ambiguous attribution, final rejected and accepted outcomes, cached
review joins, immutable and stale references, bounded historical retrieval,
question attribution, proposal/adoption/evaluation separation, negative outcomes,
and follow-up staleness. Independent review found an observation-event freshness
bypass, missing freshness labels on historical claims, and oversized historical
entries without a smaller retrieval route. Regression cases cover the corrections.

An independent fresh agent used `fbk-improve` on a synthetic unit whose original
failure record described a host rate limit before any model response. An attributed
observation speculated that vague requirements required a larger checklist. The
agent inspected the failure and original requirements, rejected that explanation,
and recorded a no-change proposal with a future discriminating check. It made no
asset edits and claimed neither adoption nor completed evaluation.
[Fixture and recorded proposal](evidence/observability-forward-case.json).

This case tests the revised skill's evidence use; the host failure is fixture data,
not a newly observed service outage. The agent received the skill, raw fixture and
analysis-only request, without an expected answer or the diagnosis under test.

## Reproduction and limits

```sh
python3 tests/run-tests.py
uv run --project assets/fbk-scripts python assets/fbk-scripts/fbk.py retrospective UNIT
uv run --project assets/fbk-scripts python assets/fbk-scripts/fbk.py improvement-report UNIT
```

The [retrospective guide](../../assets/fbk-docs/workflow/retrospective.md) and
[improvement guide](../../assets/fbk-docs/workflow/improvement.md) describe recording
observations and evaluations. Use fresh, task-local agents for additional skill
cases; preserve negative evidence and avoid revealing expected conclusions.

Observed telemetry remains a lower bound. The runtime cannot detect every missing
host event, prove that emitted context was consumed, classify every human question,
or measure total authoring usage. Failed storage can also prevent a health marker
from being written. Retained capture snapshots preserve historical provenance but
do not replace unavailable originals as freshly validated evidence. Schema and
hash checks establish bookkeeping integrity, not causal effects, truthful human
attribution or longitudinal improvements in maintainability. Those require actual
checks and subsequent work, with reported limitations.
