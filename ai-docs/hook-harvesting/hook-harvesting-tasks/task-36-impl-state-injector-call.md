---
id: task-36
type: implementation
wave: 5
covers: [AC-18, AC-11]
files_to_modify:
  - assets/fbk-scripts/fbk/state.py
test_tasks: [task-19]
completion_gate: "task-19 tests pass"
dependencies: [task-34]
---

# 1 Objective

Wire the retrospective injector into `transition_state`: after `save_state()`, call `inject_stage_metrics(spec, prev_state)` guarded so it fires ONLY when the previous state is one of the eight working stages (read from `VALID_TRANSITIONS`, not hardcoded) AND the new state is not `PARKED` — passing the LOCAL `prev_state` — with every injector failure swallowed so a failed injection never blocks the transition. This is an ORCHESTRATOR task (state engine): see the Wiring checklist.

# 2 Context

`fbk/state.py` `transition_state` (line 100) validates a transition, sets the new state, stamps the timestamp, handles park/ready bookkeeping, calls `save_state()` (line 130), prints the state JSON, and returns 0. The local `prev_state = current` is captured at line 113.

A metrics block must be injected for a working stage when it COMPLETES — i.e. it transitions to its checkpoint (e.g. `IMPLEMENTING → IMPLEMENTED`). The correct predicate keys on the PAIR, not the previous state alone: a working stage also goes to `PARKED` on failure with the same working previous state, so keying on the previous state alone would inject a "completed" block on every park. The predicate fires only when BOTH hold:
- `prev_state` is a working stage — defined as a stage whose `VALID_TRANSITIONS` entry contains `"PARKED"` (exactly `VALIDATING`, `REVIEWING`, `BREAKING_DOWN`, `TASK_REVIEWING`, `TESTING`, `TEST_REVIEWING`, `IMPLEMENTING`, `VERIFYING`). Read this set from `VALID_TRANSITIONS`, do NOT hardcode it.
- `new_state != "PARKED"`.

The completed stage passed to the injector is the LOCAL `prev_state` (the working stage that just finished), not the persisted `current_state`. The call is fully fail-silent: a failing injector never prevents the transition (which still returns 0 with the state advanced).

# 3 Instructions

## Wiring checklist (orchestrator)

- **What to import:** add `from fbk.capture import retro_injector` (a module-top import is fine; if a load-order concern arises, a function-level import inside `transition_state` is acceptable — the injector itself uses a function-level `report` import to break its own cycle). Note the test (task-19) patches `fbk.capture.retro_injector.inject_stage_metrics`, so reference the function as `retro_injector.inject_stage_metrics(...)` (attribute access on the module) rather than `from ... import inject_stage_metrics` — that keeps the monkeypatch target correct.
- **What to compute:** derive the working-stage set once from `VALID_TRANSITIONS` — `WORKING_STAGES = {s for s, nexts in VALID_TRANSITIONS.items() if "PARKED" in nexts}` (module-level constant, computed from the existing map). Completion: the set equals the eight named working stages.
- **Where to interpose:** AFTER `save_state(spec_name, state)` (line 130) and before/around the existing `print(...)` + `return 0`. The injector must not change the return value or the printed JSON.
- **What to guard:** call `inject_stage_metrics(spec_name, prev_state)` only when `prev_state in WORKING_STAGES and new_state != "PARKED"`. Wrap the call in `try/except Exception: pass` so a failure never blocks the transition (defense in depth — the injector is itself fail-silent, but the call site must not propagate either).
- **Contract preserved:** transition validation, the state mutations, `save_state`, the printed JSON, and the `return 0` are unchanged; the injector call is purely additive.

## Steps

1. Add `WORKING_STAGES = {s for s, nexts in VALID_TRANSITIONS.items() if "PARKED" in nexts}` near the top after `VALID_TRANSITIONS`. Completion: the constant holds the eight working stages.
2. Add the guarded injector call after `save_state()` in `transition_state`, referencing `retro_injector.inject_stage_metrics(spec_name, prev_state)` via module attribute access, guarded by the pair predicate and wrapped in `try/except Exception: pass`. Completion: a working-stage → checkpoint transition (e.g. `VALIDATING → VALIDATED`) calls the injector once with `(spec, prev_working_stage)`; a working-stage → `PARKED` does not call it; leaving `QUEUED`, a checkpoint, `PARKED`, or `READY` does not call it.
3. Confirm the existing transition semantics are untouched: `transition_state` still returns 0 on success and 1 on an invalid transition, and the saved `current_state` is the new state. Completion: a failing injector → `transition_state` still returns 0 and the saved state's `current_state` is the new state; the existing `test_state.py` assertions stay green.

# 4 Files to create/modify

- Modify `fbk/state.py` (add `WORKING_STAGES`; add the guarded injector call after `save_state`)

# 5 Test requirements

Makes task-19 (new `TestInjectorWiring` in `tests/test_state.py`) pass: injection fires once with `(spec, prev_working_stage)` on a working-stage → checkpoint transition; does not fire on a park, on leaving QUEUED/a checkpoint, or on a READY resume; a raising injector still returns 0 with the state advanced. Existing `test_state.py` assertions remain unmodified and passing.

# 6 Acceptance criteria

Primary: task-19's tests pass. Covers AC-18 (pair-keyed predicate including park-exclusion, prev-state passed) and AC-11 (fail-silent injection inside the transition).

# 7 Model

Sonnet

# 8 Wave

5
