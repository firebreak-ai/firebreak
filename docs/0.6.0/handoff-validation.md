# Distilled handoffs and source-bound decisions

Validated 2026-09-07 on `develop/0.6.0-astra`. This record covers the implementation
requested after the handoff analysis. Earlier validation records describe their
own revisions and test inventories.

## Delivered behavior

Continuation and worker packets reconstruct current work from durable sources.
They carry phase, ownership, governing references, dependencies, remaining review
attempts, current findings, and unresolved work. Bounded views disclose omissions
and provide targeted retrieval. Full audit history requires an explicit request.
Session and worker hooks provide routing without injecting the authoring history.
Phase skills load common guidance and their current phase leaf.

Worker assignments bind input and dependency revisions, require accepted
prerequisites, and reserve nonoverlapping ownership. Returns identify changed
files, checks, outcomes, and unresolved issues. Runtime checks detect stale inputs,
unreported changes, later file additions, unfinished workers, and conflicting
ownership. Static directory prefixes conservatively govern parallel glob ownership.

Sourced decisions preserve exact original quotes, content hashes, applicability,
and explicit supersession. An authored PRD cannot silently replace these records.
Damaged source evidence remains visible as an authority problem during resume.
Missing existing information should be retrieved before another human question.

Native review runs in a fresh original-source snapshot through restricted
authenticated `claude -p` invocations. The snapshot excludes managed audit history,
host sessions, memory, settings, and credentials, including explicit attempts to
declare those files as required inputs. Review context reports identify required
inspection, governing dependencies, and missing evidence for the current phase.
Complete snapshot freshness protects in-flight review and cached findings;
governing-source freshness protects durable acceptance while allowing planned
implementation changes. Declared `scope.context` covers additional project contracts.

Council adjudication emits corrected operative findings and retains original
candidates in audit. Every candidate receives a disposition; unresolved blockers
remain blocking. Failed closes include actionable evidence and a route to the
remaining findings without requiring the entire review history.

Recorded standing authority supports bounded routine prose repairs. Deterministic
proof of a broken Markdown fragment repair can preserve current acceptance.
Contradiction repairs require a sourced decision and fresh equivalence check,
invalidate affected acceptance, and retain review attempts. Journals invalidate
evidence before replacement and recover without overwriting unknown newer edits.

## Deterministic verification

The combined `python3 tests/run-tests.py` run passed **836 Python cases** and
**352 shell assessment rows**, with no failures, errors, or skips. The workflow
group contains 163 cases. Ruff and `git diff --check` also passed.
[Recorded suite summary](evidence/handoff-tests.json); full local reports are in
`test-results/run-bf3_vsth/`.

The focused regressions exercise the public CLI, revision and source changes,
worker hooks and ownership, interrupted repairs, council corrections, context
exclusion, omission retrieval, and phase-specific review requirements. An
independent review found prospective glob intersections, explicit host-context
imports, and stale snapshot findings; regression cases cover each fix.

The mutation benchmark detected **13/13 targeted mutations**, with a passing clean
control. Added mutations remove sourced-decision revision binding, ignore a
changed review snapshot, or ignore governing-convention freshness. A retired
mutation is recorded separately and is not counted as detected.
[Mutation evidence](evidence/handoff-mutations.json).

## Live attention evaluation

Five small fixtures cover an already answered question, a late human correction,
a misleading inherited remedy, an existing dependency, and a mechanical reference
repair. Each uses a fresh authenticated read-only session. The evaluator records
source citations, supplied context size, usage, unnecessary questions, unsupported
actions, and response-contract errors.

The initial run passed **2/5 strict contracts**. A shared response schema invited
irrelevant invented fields; the late-correction action was also ambiguous. The
follow-up uses a separate response contract for each task and explicit action
criteria. It passed **5/5**, with zero scored unnecessary questions, unsupported
actions, unsupported fields, or output-contract errors. These are different
contracts, not a controlled model-performance comparison.
[Initial evidence](evidence/handoff-eval-initial.json) and
[focused evidence](evidence/handoff-eval-focused.json).

The actual lifecycle smoke test also exposed phase confusion: an intent reviewer
requested future code, tests, and documentation as prerequisites. The production
prompt now defines the current phase's review decision and later deliverables.
The same fixture's intent close passed on retry without resetting its review
budget. [Initial evidence](evidence/handoff-intent-initial.json) and
[retry evidence](evidence/handoff-intent-retry.json).

A new lifecycle fixture accepted intent, then encountered a nonzero native spec
invocation with empty stderr. The cause was not established; error reporting now
retains stdout diagnostics as well. The unchanged spec passed on retry. Resuming
that fixture completed breakdown and implementation acceptance, verified all four
tests failed behaviorally before locking and passed afterward, and validated the
persisted final hashes and review evidence. No attempt budget was reset: intent
used one attempt, spec two, breakdown one, and implementation one.
[Initial lifecycle evidence](evidence/handoff-lifecycle-initial.json) and
[resumed lifecycle evidence](evidence/handoff-lifecycle-resumed.json).
This was a resumed host/lifecycle integration check with script-authored artifacts,
not an uninterrupted run or a measurement of model authoring quality.

## Reproduction and limits

```sh
python3 tests/run-tests.py
uv run --project assets/fbk-scripts python benchmark/workflow/mutation-check.py
uv run --project assets/fbk-scripts python benchmark/workflow/handoff-eval.py --run
uv run --project assets/fbk-scripts python benchmark/workflow/live-smoke.py --run
```

The last two commands consume normal authenticated Claude capacity. A live
failure preserves evidence and consumes the existing attempt budget; it does not
justify fabricated approval or a silent reset.

This evidence establishes bounded runtime behavior and selected attention cases.
It does not establish general context sufficiency, long-run resistance to drift,
or improved maintainability across projects. Inspection and equivalence remain
model claims, supplemented by deterministic checks and independent phase close.
Recorded source attribution is not cryptographic proof of human consent. Reference
repair currently supports a conservative Markdown-fragment subset; other formats
use normal rework. Fresh-session reconstruction is available at deliberate
boundaries; Firebreak does not automatically clear an active interactive session.

Use repeated runs and real follow-up changes to measure unnecessary-question
rates, missed requirements, repair correctness, and context volume before making
broader reliability claims. See the [workflow guide](../../assets/fbk-docs/state-driven-workflow.md)
for the operational entry point.
