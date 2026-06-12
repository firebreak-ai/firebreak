---
id: task-19
type: implementation
wave: 2
covers: [AC-01, AC-02]
files_to_modify:
  - assets/fbk-scripts/fbk/state.py
  - assets/fbk-scripts/fbk/capture/active_stage.py
  - assets/fbk-scripts/fbk/report.py
test_tasks: [task-01]
dependencies: [task-01]
completion_gate: "task-01 tests pass (tests/test_capture_active_stage.py); tests/test_capture_hook_router.py::test_stage_null_for_terminal_run_state and ::test_stage_null_when_no_run_active stay green; existing suite green on the touched modules"
---

## Objective

Define the one authoritative "not an active working stage" set in `fbk/state.py` and make both consumers — the active-stage resolver and the report — import it, eliminating the resolver's wrong hardcoded tuple and the report's parallel literal.

## Context

Slice: stage-attribution-shared-constant. `fbk/capture/active_stage.py:19` hardcodes `TERMINAL_STATES = ("DONE", "FAILED", "PARKED")` — `DONE` and `FAILED` do not exist in the state machine, and `COMPLETED` (the real terminal state) plus every checkpoint/idle state are missing, so events after a finished cycle are misfiled under phantom stages. `fbk/report.py:371-377` independently hardcodes a different, correct list. One definition, two importers, checked by identity, means the two can never drift again.

Ownership sits in `state.py` deliberately: `state.py` already imports the capture package at the top level (`from fbk.capture import retro_injector`, line 10), so a constant homed in the capture package and imported back by the reporting chain would close an import cycle. Defining it beside `WORKING_STAGES` keeps every import edge one-directional. (`retro_injector` imports nothing from `fbk` at module level — its `report` import is function-level — so `active_stage` importing `fbk.state` creates no cycle.)

Invariants to preserve: the resolver stays fail-silent (returns `(None, None)` on any error, never raises); no behavioral change to `state.py` beyond the new pure constant.

**Interface symbol (copied verbatim from task-01 — do not paraphrase).** In `fbk/state.py`, immediately below the `WORKING_STAGES` definition at line 38:

```python
# States that are not an active working stage — every state that is not in
# WORKING_STAGES (checkpoint, idle, parked, and terminal states). Derived from
# the same transition map so the two sets can never drift. frozenset so both
# consumers share one immutable object and can be checked by identity.
NON_ACTIVE_STATES = frozenset(ALL_STATES - WORKING_STAGES)
```

This resolves to exactly the eleven states `{"COMPLETED", "PARKED", "QUEUED", "READY", "VALIDATED", "REVIEWED", "BROKEN_DOWN", "TASKS_READY", "TESTS_WRITTEN", "TESTS_READY", "IMPLEMENTED"}` (verified against `VALID_TRANSITIONS`). Both consumers bind it as a module-level name via `from fbk.state import NON_ACTIVE_STATES` — the guard test asserts `active_stage.NON_ACTIVE_STATES is state.NON_ACTIVE_STATES` and `report.NON_ACTIVE_STATES is state.NON_ACTIVE_STATES`, so an attribute re-export is required in each consumer, not an aliased local copy.

Three-files justification: one shared constant and its two consumers must land atomically — replacing the resolver tuple without the constant breaks imports, and adding the constant without retiring the report literal leaves the drift the criterion exists to kill; splitting them leaves the suite red across waves.

Constraints: do NOT modify any test file; file scope is exactly the three files listed. Paths are relative to `/home/rahvin/context-assets/assets/fbk-scripts/`.

## Instructions

1. In `fbk/state.py`, insert the verbatim constant block above immediately after line 38 (`WORKING_STAGES = ...`). No other change to the file. Done when `python -c "import fbk.state as s; assert s.NON_ACTIVE_STATES == s.ALL_STATES - s.WORKING_STAGES and isinstance(s.NON_ACTIVE_STATES, frozenset)"` passes.
2. In `fbk/capture/active_stage.py`:
   - Add `from fbk.state import NON_ACTIVE_STATES` to the imports (below `import os`).
   - Delete the `TERMINAL_STATES` definition (lines 17-19, including its comment) entirely — do not alias the old name; the guard test asserts `active_stage.TERMINAL_STATES` raises `AttributeError`.
   - At line 56, change the condition to `if spec and stage and stage not in NON_ACTIVE_STATES:`.
   - Update the module docstring's terminal-state paragraph (lines 10-12) and the function docstring's "not terminal" wording (line 35) to say the resolver returns a stage only for an active working stage; events during checkpoint, idle, parked, or terminal periods carry no stage.
   Done when the file contains no occurrence of `TERMINAL_STATES`, `DONE`, or `FAILED`.
3. In `fbk/report.py`:
   - Add `from fbk.state import NON_ACTIVE_STATES` below the existing `import fbk.state as state_module` (line 22) — keep the existing alias import; the new name must be module-level on `report` for the identity guard.
   - Replace the `extra_ran` comprehension's hardcoded tuple (lines 371-377) with:
     ```python
     extra_ran = [
         k for k in stage_timestamps
         if k not in _PIPELINE_STAGES
         and k not in NON_ACTIVE_STATES
     ]
     ```
     (Behavior-identical: the deleted literal is exactly the eleven members of `NON_ACTIVE_STATES`.)
   Done when no hardcoded list of checkpoint/terminal state names remains anywhere in `fbk/report.py` outside `_PIPELINE_STAGES` (which lists working stages, a different set).
4. Run the gating tests: `tests/test_capture_active_stage.py` (all of task-01's tests), then the two hook-router null-stage tests named in the completion gate, then the full suite minus known later-wave reds. Done when the resolver returns `(None, None)` for all eleven non-active states and `("demo-spec", <stage>)` for all eight working stages.

## Files to create/modify

- `assets/fbk-scripts/fbk/state.py` (modify)
- `assets/fbk-scripts/fbk/capture/active_stage.py` (modify)
- `assets/fbk-scripts/fbk/report.py` (modify)

## Test requirements

- Gating: task-01's `tests/test_capture_active_stage.py` — all three tests (non-active parametrization, working-stage parametrization, identity guard) must pass.
- Must stay green: `tests/test_capture_hook_router.py::test_stage_null_for_terminal_run_state`, `::test_stage_null_when_no_run_active` (the only pre-existing indirect resolver coverage); `tests/test_report_rendering.py` and `tests/test_report_arithmetic.py` (the `extra_ran` replacement is behavior-identical).

## Acceptance criteria

- AC-01: `resolve_active_stage` returns no stage for `COMPLETED` and every checkpoint/idle state, and returns the stage only for a true working stage.
- AC-02: the non-active set is defined once in `fbk/state.py`, consumed by both `active_stage.py` and `report.py` by identity, with no parallel literal or local copy remaining.

## Model

Sonnet

## Wave

Wave 2
