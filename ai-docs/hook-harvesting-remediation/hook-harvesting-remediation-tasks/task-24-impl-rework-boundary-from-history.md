---
id: task-24
type: implementation
wave: 6
covers: [AC-06]
files_to_modify:
  - assets/fbk-scripts/fbk/report.py
test_tasks: [task-14]
dependencies: [task-14, task-23]
completion_gate: "task-14 tests pass (rebuilt test_attempt_after_ready_reentry_classifies_after_rework, rebuilt test_rework_derived_from_repeated_stage_entry, new test_two_parks_boundary_is_first_park); the rest of tests/test_report_arithmetic.py and tests/test_capture_report_integration.py's gate-rate test stay green"
---

## Objective

Derive the after-rework boundary from the first park recorded in the append-only `error_history`, replacing the last-write-wins `stage_timestamps["READY"]` read that misclassifies attempts when READY holds another stage's re-entry timestamp.

## Context

Slice: rework-boundary-from-history. In `classify_gate_attempts` (fbk/report.py), the boundary logic reads `st.get("stage_timestamps", {}).get("READY")` (the `reentry_ts` at line 63 of the pre-fix file) — a single key the state engine overwrites on EVERY park/re-entry across all stages (`fbk/state.py:transition_state` writes `stage_timestamps[new_state] = now`). When READY holds an earlier stage's re-entry, an attempt made before the current stage's own first park satisfies `ev_ts >= reentry_ts` and is misclassified `after_rework`. `error_history`, by contrast, is append-only: every park appends `{"stage": prev_state, "error": reason, "timestamp": now}` (state.py:128-132) and nothing ever rewrites it.

**Boundary contract (copied verbatim from task-14 — do not paraphrase):** the after-rework boundary for a stage is the timestamp of the FIRST entry in the append-only `error_history` whose `stage` matches (the re-entry follows the park; `error_history` records parks, not re-entries). Attempts strictly before that boundary are `first_try`; attempts at-or-after it are `after_rework`. The `READY` timestamp is not consulted. With no park recorded for the stage, every attempt is `first_try`.

Sequencing note: task-23 (wave 5) already reshaped the attempt-collection block above this logic (two event types, type-dependent `passed`). This task touches only the boundary derivation and the phase branches below it — the code that computes `first_park_ts`, `reentry_ts`, and the four-way `if/elif` classification. Anchor on the logic, not pre-fix line numbers.

Invariants to preserve: `first_park_ts` is already correctly taken from the first matching `error_history` entry (keep that loop); `derive_parks` and `derive_rework` are untouched (they already read `error_history`); the report still renders with an empty or missing `error_history`.

Constraints: do NOT modify any test file; file scope is exactly `fbk/report.py`. Path relative to `/home/rahvin/context-assets/assets/fbk-scripts/`.

## Instructions

1. In `classify_gate_attempts`, delete the `reentry_ts` derivation (the comment block and the `reentry_ts = st.get("stage_timestamps", {}).get("READY")` line). Done when the function contains no read of the `READY` key.
2. Replace the four-branch phase classification in the per-event loop with the two-branch first-park rule:
   ```python
   if first_park_ts is None or ev_ts < first_park_ts:
       # No park recorded for this stage, or the attempt precedes the
       # stage's first park: first try.
       phase = "first_try"
   else:
       # At-or-after the stage's first park: the re-entry follows the park,
       # so everything from the first park onward is after-rework — stable
       # across second parks and later transitions.
       phase = "after_rework"
   ```
   Done when the boundary is the first park's timestamp and nothing else.
3. Update the function docstring's phase paragraph (the "A 'first try' attempt..." text): the boundary is the first park recorded for the stage in the append-only `error_history`; attempts strictly before it are first-try, attempts at-or-after it are after-rework; the structure records parks (the re-entry follows the park), so the boundary is stable when a stage parks and resumes more than once. Done when the docstring matches the implemented rule.
4. Run the gating tests. Expected arithmetic (task-14): stale-READY fixture → phases exactly `["first_try", "after_rework"]`; two-park fixture → `["first_try", "after_rework", "after_rework"]` with `derive_rework == 2`.

## Files to create/modify

- `assets/fbk-scripts/fbk/report.py` (modify)

## Test requirements

- Gating: task-14's three tests in `tests/test_report_arithmetic.py`.
- Must stay green: the rest of `tests/test_report_arithmetic.py`; `tests/test_capture_report_integration.py::test_gate_outcomes_drive_exact_first_try_fraction` (its single-park fixture classifies identically under both boundary rules); task-03's strengthened injector test (same property).

## Acceptance criteria

- AC-06: the after-rework boundary is derived from the first park recorded in the append-only `error_history`, so a stage that parks and resumes more than once classifies its attempts correctly.

## Model

Sonnet

## Wave

Wave 6
