# Selectable design and spec reviews

Validated 2026-09-07 on `develop/0.6.0-astra`. This extends the initial
[validation record](validation.md); those earlier counts describe the earlier revision.

## Delivered behavior

Design and spec each have a persisted `single` or `council` choice. Project defaults
can supply a choice; otherwise closure requires an explicit selection reflecting
the user's preference. Optional design remains independent of review mode. A
design council neither requires a spec council nor replaces spec review.

The authoring agent requests `phase-close`. The runtime then supplies instructions
and launches fresh, read-only headless Claude Code sessions. Hooks expose the
saved choice and guard workflow entry; they do not themselves run long reviews.
Managed council and spec-review skills route through this runtime. Standalone
council consultation remains advisory and agent-mediated.

Council execution uses two or three independent perspectives. If they produce
findings, one challenge session and one fresh adjudicator assess every candidate.
Zero findings short-circuits those two stages. Supported minority findings remain;
unresolved blockers prevent acceptance. A failed member cannot silently degrade
the selected council into a single review. Each attempt consumes the existing
persisted review budget. Selection changes invalidate cached reviews and approvals
without resetting that budget, and cannot occur during an active close.

## Verification

- Python regression suite: **926 passed**, including **24 new behavior cases** in
  `assets/fbk-scripts/tests/test_workflow_review.py`.
- Targeted mutations: **11/11 detected**, unchanged control passed. The five new
  mutations remove review-choice revision binding, accept a single result for a
  council, drop unresolved blockers, ignore failed members, or allow selection
  changes during a running close. [Recorded failures](evidence/council-mutations.json).
- Live authenticated Claude Code council: architect and guardian independently
  reviewed the isolated cancellation fixture, followed by challenge and adjudication.
  Seven candidates received seven dispositions: six supported, one refuted.
  All retained findings were suggestions, so the spec was accepted. Independent
  sessions took 135.146 and 95.457 seconds concurrently; challenge took 114.374
  seconds and adjudication 74.443 seconds. [Full result](evidence/live-council.json).
- A separate read-only implementation review timed out after 240 seconds without
  a verdict. It is not counted as successful independent verification.

Reproduce deterministic checks from `assets/fbk-scripts`:

```sh
uv run pytest -q
uv run python ../../benchmark/workflow/mutation-check.py
uv run ruff check fbk/workflow tests/test_workflow_review.py
```

For a configured unit with accepted prerequisites, select the live council before
entering/closing spec (replace the unit and session placeholders):

```sh
uv run fbk.py review-plan UNIT --phase spec --mode council --members architect guardian --reason "User-selected review perspectives"
uv run fbk.py phase-enter spec UNIT --session SESSION
uv run fbk.py phase-close spec UNIT --session SESSION
```

## What this evidence does not establish

The deterministic tests verify orchestration and refusal paths with controlled
model responses. The live run verifies integration, not superiority over a single
reviewer, equal-budget effectiveness, or longitudinal maintainability. It produced
some questionable suggestions as well as useful observations; acceptance does not
automatically adopt suggestions.

The live reviewers read prior verdicts from the fixture's state file. The shared
prompt now explicitly excludes state files, review logs, and earlier outputs;
this instruction was added after the live run. Fresh sessions and bounded supplied
findings reduce context accumulation, but file access is not isolated to prevent
reading review history. That remains a limitation, not a demonstrated guarantee.

Completed stage results are retained when normal failures return to the coordinator.
Abrupt coordinator termination can lose in-memory stage outputs; the durable close
reservation still requires recovery and prevents acceptance of incomplete work.

Current deterministic checks and diagnostic reports are described in [testing](../testing.md). Earlier compatibility suites and their audits remain in git history.
