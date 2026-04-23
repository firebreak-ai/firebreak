---
id: task-11
type: test
wave: 1
covers: [AC-02]
files_to_create:
  - assets/fbk-scripts/tests/test_state.py
completion_gate: "tests compile and fail before implementation"
---

## Objective

Create pytest unit tests for `fbk.state` transition enforcement.

## Context

`state-engine.py` implements `transition_state()` with a `VALID_TRANSITIONS` map. Valid transitions are strictly enforced — e.g., QUEUED can only go to VALIDATING, PARKED stores `parked_info.failed_stage`, and READY resolves dynamically from `parked_info.failed_stage`. Follow test scenarios from `tests/sdl-workflow/test-state-engine.sh`.

## Instructions

1. Create `assets/fbk-scripts/tests/test_state.py`
2. Import `create_state`, `transition_state`, `load_state`, `VALID_TRANSITIONS` from `fbk.state`
3. Write a test using `tmp_path` + `monkeypatch` to set `STATE_DIR`: `create_state("test-spec")` → assert state file exists with `current_state == "QUEUED"`
4. Write a test: create state, transition QUEUED → VALIDATING → assert `current_state == "VALIDATING"` and return code is 0
5. Write a test: create state, attempt transition QUEUED → REVIEWED → assert return code is 1 (invalid transition)
6. Write a test: transition to PARKED with reason → assert `parked_info.failed_stage` is set and `error_history` has an entry
7. Write a test: transition to PARKED then READY, verify next valid transition is `parked_info.failed_stage`
8. Write a test: `create_state` for an already-existing spec → assert return code is 1

## Files to create/modify

- **Create**: `assets/fbk-scripts/tests/test_state.py`

## Test requirements

| Level | Behavior | Expected assertion |
|-------|----------|--------------------|
| Unit | create_state produces QUEUED state | current_state == "QUEUED" |
| Unit | valid transition succeeds | current_state updated, return 0 |
| Unit | invalid transition rejected | return 1, state unchanged |
| Unit | PARKED stores failure info | parked_info.failed_stage set, error_history populated |
| Unit | READY resolves from parked_info | valid transitions == [failed_stage] |
| Unit | duplicate create rejected | return 1 |

## Acceptance criteria

- AC-02: validates state-engine.py relocated and importable as `fbk.state`

## Model

Haiku

## Wave

1
