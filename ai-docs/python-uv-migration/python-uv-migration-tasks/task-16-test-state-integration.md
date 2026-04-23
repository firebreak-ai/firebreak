---
id: task-16
type: test
wave: 2
covers: [AC-02]
files_to_create:
  - tests/sdl-workflow/test-state-integration-python.sh
completion_gate: "tests compile and fail before implementation"
---

## Objective

Create bash integration test verifying `python3 fbk.py state create` creates state file and outputs valid JSON.

## Context

The spec's user verification step UV-3 requires: `python3 fbk.py state create test-feature` creates state file and outputs JSON. This test covers the dispatcher → state module integration path. Follow bash test conventions from `tests/sdl-workflow/test-state-engine.sh`.

## Instructions

1. Create `tests/sdl-workflow/test-state-integration-python.sh`
2. Set `DISPATCHER="$PROJECT_ROOT/assets/fbk-scripts/fbk.py"`
3. Use `mktemp -d` for `STATE_DIR`, export it
4. Write Test 1: `python3 "$DISPATCHER" state create test-feature` → assert exit 0, stdout is valid JSON, parsed JSON has `current_state == "QUEUED"`
5. Write Test 2: `python3 "$DISPATCHER" state transition test-feature VALIDATING` → assert exit 0, parsed output has `current_state == "VALIDATING"`
6. Write Test 3: `python3 "$DISPATCHER" state transition test-feature COMPLETED` → assert exit non-zero (invalid transition from VALIDATING)

## Files to create/modify

- **Create**: `tests/sdl-workflow/test-state-integration-python.sh`

## Test requirements

| Level | Behavior | Expected assertion |
|-------|----------|--------------------|
| Integration | state create outputs valid JSON | exit 0, current_state == "QUEUED" |
| Integration | valid transition succeeds | exit 0, current_state updated |
| Integration | invalid transition rejected | exit non-zero |

## Acceptance criteria

- AC-02: state module relocated and callable through dispatcher

## Model

Haiku

## Wave

2
