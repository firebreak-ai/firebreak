---
id: task-14
type: test
wave: 2
covers: [AC-06]
files_to_modify:
  - assets/fbk-scripts/tests/test_report_arithmetic.py
completion_gate: "Rebuilt rework-boundary tests collect cleanly at the current tree and FAIL (pre-park attempt misclassified after_rework via the stale READY read) from a second git worktree at the pre-fix commit (40ec021 at spec time) with the file copied in; failing output captured in the rework-boundary slice's completion notes."
---

## Objective

Rebuild the two re-entry classification tests against the first-park boundary and add the two-park boundary-stability guard.

## Context

Slice: rework-boundary-from-history (contract-evolving; retires the `stage_timestamps["READY"]` read encoded in `test_attempt_after_ready_reentry_classifies_after_rework` and `test_rework_derived_from_repeated_stage_entry`). `classify_gate_attempts` (fbk/report.py:61-86) reads `stage_timestamps["READY"]` — a last-write-wins key shared by every park/re-entry in the state file. The demonstrable failure: when READY holds a timestamp from an EARLIER stage's re-entry, an attempt made before the current stage's own first park satisfies `ev_ts >= reentry_ts` and is misclassified `after_rework`.

**Declared contract (the implementation task copies this):** the after-rework boundary for a stage is the timestamp of the FIRST entry in the append-only `error_history` whose `stage` matches (the re-entry follows the park; `error_history` records parks, not re-entries). Attempts strictly before that boundary are `first_try`; attempts at-or-after it are `after_rework`. The `READY` timestamp is not consulted. With no park recorded for the stage, every attempt is `first_try`.

Wave note: wave 2 because task-02 owns `tests/test_report_arithmetic.py` in wave 1.

Timeline notation below uses `T1 = 2026-01-01T00:01:00+00:00`, `T2 = ...T00:02:00...`, etc. (one minute apart); write them as full ISO strings in the fixtures.

## Instructions

1. Rebuild `test_attempt_after_ready_reentry_classifies_after_rework` (keep the name) with the stale-READY fixture:
   - `error_history = [{"stage": "VALIDATING", "error": "early park", "timestamp": T1}, {"stage": "REVIEWING", "error": "gate failed", "timestamp": T5}]`.
   - `stage_timestamps = {"VALIDATING": T0, "READY": T2, "REVIEWING": T3, "PARKED": T5}`, `current_state="REVIEWING"` — READY (T2) is VALIDATING's re-entry, stale and EARLIER than REVIEWING's own first park (T5). Comment every field's role; this is the production state shape after two stages and two parks.
   - Events for stage `"REVIEWING"` (production `VERIFICATION_RESULT` shape, `source="task_completed"`, `data={"tests_passed": <bool>, ...}`): fail at T4 (after stale READY, before REVIEWING's park) and pass at T6 (after the park).
   - Assert `classify_gate_attempts(events, state, "REVIEWING")` returns, in order, exactly phases `["first_try", "after_rework"]` with passed `[False, True]`.
   - Docstring red mechanics: pre-fix, the T4 attempt satisfies `T4 >= READY(T2)` and is labelled `after_rework`; the first-park boundary (T5) labels it `first_try`.
   Done when the exact phase-list assertion is present.
2. Rebuild `test_rework_derived_from_repeated_stage_entry` (keep the name) on the same stale-READY fixture (duplicate the fixture locally; fresh state per test):
   - Assert `derive_rework(state, "REVIEWING") == 1` exactly (one park entry for the stage).
   - Assert the classification of the same two events as in step 1 (the load-bearing first_try-at-T4 assertion repeats here because this test guards the derive+classify pairing).
   Done when both exact assertions are present.
3. Add `test_two_parks_boundary_is_first_park`:
   - `error_history = [{"stage": "VALIDATING", "error": "early park", "timestamp": T1}, {"stage": "IMPLEMENTING", "error": "first park", "timestamp": T3}, {"stage": "IMPLEMENTING", "error": "second park", "timestamp": T7}]`; `stage_timestamps = {"VALIDATING": T0, "IMPLEMENTING": T2, "PARKED": T7, "READY": T8}`, `current_state="IMPLEMENTING"`.
   - Events for `"IMPLEMENTING"`: pass at `T2.5` (use 00:02:30 — before the stage's first park), fail at T5 (between the re-entry and the second park), pass at T9 (after the second park).
   - Assert exact phases in order: `["first_try", "after_rework", "after_rework"]` — the boundary is the FIRST park (T3) and is stable across the second park and later transitions; the T5 attempt between re-entry and second park is `after_rework`.
   - Assert `derive_rework(state, "IMPLEMENTING") == 2` exactly.
   - Docstring note: this test pins the boundary-stability contract; it may be green at the pre-fix commit (the pre-fix fallback also labels post-park attempts after_rework) — the red demonstration for AC-06 is carried by the two rebuilds above. Record that note in the completion notes.
   Done when the exact phase-list and rework-count assertions are present.
4. Red run: from the pre-fix worktree with this file copied in, run the two rebuilt tests; capture the failing output in the slice's completion notes (and the expected-green note for the two-park test).

## Files to create/modify

- `assets/fbk-scripts/tests/test_report_arithmetic.py` (modify)

## Test requirements

- Unit — stale-READY fixture: phases exactly `["first_try", "after_rework"]`, passed `[False, True]`.
- Unit — derive+classify pairing: `derive_rework == 1` exactly, same phase pinning.
- Unit — two parks: phases exactly `["first_try", "after_rework", "after_rework"]`; `derive_rework == 2` exactly.

## Acceptance criteria

- AC-06: the after-rework boundary is derived from the first park recorded in the append-only `error_history`, so a stage that parks and resumes more than once classifies its attempts correctly.

## Model

Sonnet

## Wave

Wave 2
