---
id: task-01
type: test
wave: 1
covers: [AC-01, AC-02]
files_to_create:
  - assets/fbk-scripts/tests/test_capture_active_stage.py
completion_gate: "New resolver tests collect cleanly at the current tree and are demonstrated to FAIL from a second git worktree at the pre-fix commit recorded at implementation start (40ec021 at spec time) with the test file copied in; failing output captured in the stage-attribution slice's completion notes."
---

## Objective

Author the first direct test coverage for `fbk.capture.active_stage.resolve_active_stage` and the identity guard for the shared non-active-state constant.

## Context

Slice: stage-attribution-shared-constant (contract-evolving). `fbk/capture/active_stage.py` currently hardcodes `TERMINAL_STATES = ("DONE", "FAILED", "PARKED")` — two names that do not exist in the state machine, and missing `COMPLETED`, the real terminal state. `fbk/report.py:374` independently hardcodes a different list. The fix defines one authoritative constant in `fbk/state.py` and both modules import it. The resolver has zero direct coverage today; the only indirect coverage is two router tests asserting the null-stage cases the buggy tuple happens to get right.

**Declared new interface (the implementation task copies this verbatim).** In `fbk/state.py`, immediately below the existing `WORKING_STAGES` definition (line 38):

```python
# States that are not an active working stage — every state that is not in
# WORKING_STAGES (checkpoint, idle, parked, and terminal states). Derived from
# the same transition map so the two sets can never drift. frozenset so both
# consumers share one immutable object and can be checked by identity.
NON_ACTIVE_STATES = frozenset(ALL_STATES - WORKING_STAGES)
```

Both consumers bind it as a module-level name via `from fbk.state import NON_ACTIVE_STATES`:
- `fbk/capture/active_stage.py` — replaces `TERMINAL_STATES` (the old name is deleted, not aliased).
- `fbk/report.py` — replaces the parallel literal at line 374.

The resolver reads state files from `<cwd>/.claude/automation/state/*.json` and returns `(spec_name, current_state)` of the newest non-terminal file, else `(None, None)`. Use `tests.capture_fixtures.build_state` / `write_state` to lay down state files (they match the shape `fbk/state.py` writes).

## Instructions

1. Create `tests/test_capture_active_stage.py` with the module guard pattern used by `tests/test_capture_gate_check.py` (try-import `from fbk.capture import active_stage`, module-level `pytestmark = pytest.mark.skipif(...)`). Done when the file collects under pytest with zero errors.
2. Add `test_resolver_returns_no_stage_for_non_active_states`, parametrized over this pinned literal list (do NOT derive it from the production constant — a wrong constant must not steer the test):
   `["COMPLETED", "PARKED", "QUEUED", "READY", "VALIDATED", "REVIEWED", "BROKEN_DOWN", "TASKS_READY", "TESTS_WRITTEN", "TESTS_READY", "IMPLEMENTED"]`.
   Per case: write one state file for spec `"demo-spec"` with `current_state=<state>` under `<tmp_path>/.claude/automation/state/` via `capture_fixtures.write_state(state_dir, capture_fixtures.build_state("demo-spec", {<state>: "2026-01-01T00:00:00+00:00"}, current_state=<state>))`, then assert `active_stage.resolve_active_stage(str(tmp_path)) == (None, None)`. Done when all eleven cases are present.
3. Add `test_resolver_returns_stage_for_each_working_stage`, parametrized over the pinned literal list `["VALIDATING", "REVIEWING", "BREAKING_DOWN", "TASK_REVIEWING", "TESTING", "TEST_REVIEWING", "IMPLEMENTING", "VERIFYING"]`; same fixture shape; assert the result equals exactly `("demo-spec", <stage>)`. Done when all eight cases are present.
4. Add `test_non_active_set_is_one_object_consumed_by_identity`:
   - `import fbk.state as state_module`, `from fbk.capture import active_stage`, `import fbk.report as report`.
   - Assert `state_module.NON_ACTIVE_STATES == frozenset({"COMPLETED", "PARKED", "QUEUED", "READY", "VALIDATED", "REVIEWED", "BROKEN_DOWN", "TASKS_READY", "TESTS_WRITTEN", "TESTS_READY", "IMPLEMENTED"})` (pinned value check).
   - Assert `active_stage.NON_ACTIVE_STATES is state_module.NON_ACTIVE_STATES` and `report.NON_ACTIVE_STATES is state_module.NON_ACTIVE_STATES` (identity — value-equality alone passes against two drifting copies, the exact failure mode this guards).
   - Assert the old local tuple is gone: `with pytest.raises(AttributeError): active_stage.TERMINAL_STATES`.
   Done when all four assertions are present.
5. Verification step (no modification): run `tests/test_capture_hook_router.py::test_stage_null_for_terminal_run_state` and `::test_stage_null_when_no_run_active` and confirm they stay green — they are the only pre-existing indirect resolver coverage.
6. Red run: from a second worktree at the recorded pre-fix commit with this new file copied in, run the file; capture the failing output (COMPLETED/checkpoint cases return a stage; `NON_ACTIVE_STATES` import fails) in the slice's completion notes. Done when both runs are captured.

## Files to create/modify

- `assets/fbk-scripts/tests/test_capture_active_stage.py` (create)

New file rationale: the resolver has no test file anywhere in the suite — the coverage absence is itself part of the defect; no existing file owns this module.

## Test requirements

- Unit — `resolve_active_stage` returns exactly `(None, None)` for each of the eleven pinned non-active states; returns exactly `("demo-spec", <stage>)` for each of the eight pinned working stages.
- Unit — `state.NON_ACTIVE_STATES` equals the pinned eleven-member frozenset; `active_stage` and `report` each expose the same object by `is` identity; `active_stage.TERMINAL_STATES` raises `AttributeError`.

## Acceptance criteria

- AC-01: the resolver returns no stage for the terminal state (`COMPLETED`) and every checkpoint/idle state, and the stage only for a true working stage.
- AC-02: the not-an-active-working-stage set is defined once in `fbk/state.py` and consumed by both modules by identity, with no parallel literal remaining.

## Model

Sonnet

## Wave

Wave 1
