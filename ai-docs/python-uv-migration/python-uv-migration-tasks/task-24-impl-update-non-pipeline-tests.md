---
id: task-24
type: implementation
wave: 2
covers: [AC-10]
files_to_modify:
  - tests/sdl-workflow/test-audit-logger.sh
  - tests/sdl-workflow/test-config-loader.sh
  - tests/sdl-workflow/test-hash-gate.sh
  - tests/sdl-workflow/test-spec-validator.sh
  - tests/sdl-workflow/test-state-engine.sh
  - tests/sdl-workflow/test-status-command.sh
test_tasks: [task-28]
completion_gate: "task-28 tests pass"
---

## Objective

Update path variables in 6 non-pipeline test scripts to invoke through the dispatcher instead of direct script paths.

## Context

These 6 tests directly invoke scripts being relocated. Each has a single path variable assignment at the top that needs updating, and all invocations of that variable change accordingly. This task touches 6 files because each edit is a trivial variable rename (~3 lines changed per file) — splitting would create artificial boundaries with no independent value.

## Instructions

1. In `test-audit-logger.sh`: replace `LOGGER="$PROJECT_ROOT/assets/hooks/fbk-sdl-workflow/audit-logger.py"` with `DISPATCHER="$PROJECT_ROOT/assets/fbk-scripts/fbk.py"`, replace all `python3 "$LOGGER"` with `python3 "$DISPATCHER" audit`
2. In `test-config-loader.sh`: replace `LOADER="$PROJECT_ROOT/assets/hooks/fbk-sdl-workflow/config-loader.py"` with `DISPATCHER="$PROJECT_ROOT/assets/fbk-scripts/fbk.py"`, replace all `python3 "$LOADER"` with `python3 "$DISPATCHER" config`
3. In `test-hash-gate.sh`: replace `GATE="$PROJECT_ROOT/assets/hooks/fbk-sdl-workflow/test-hash-gate.sh"` with `DISPATCHER="$PROJECT_ROOT/assets/fbk-scripts/fbk.py"`, replace all `bash "$GATE"` with `python3 "$DISPATCHER" test-hash-gate`
4. In `test-spec-validator.sh`: replace `GATE="$PROJECT_ROOT/assets/hooks/fbk-sdl-workflow/spec-gate.sh"` with `DISPATCHER="$PROJECT_ROOT/assets/fbk-scripts/fbk.py"`, replace all `bash "$GATE"` with `python3 "$DISPATCHER" spec-gate`
5. In `test-state-engine.sh`: replace `ENGINE="$PROJECT_ROOT/assets/hooks/fbk-sdl-workflow/state-engine.py"` with `DISPATCHER="$PROJECT_ROOT/assets/fbk-scripts/fbk.py"`, replace all `python3 "$ENGINE"` with `python3 "$DISPATCHER" state`
6. In `test-status-command.sh`: replace `CMD="$PROJECT_ROOT/assets/hooks/fbk-sdl-workflow/dispatch-status.sh"` with `DISPATCHER="$PROJECT_ROOT/assets/fbk-scripts/fbk.py"`, replace all `bash "$CMD"` with `python3 "$DISPATCHER" dispatch-status`

## Files to create/modify

- **Modify**: `tests/sdl-workflow/test-audit-logger.sh`
- **Modify**: `tests/sdl-workflow/test-config-loader.sh`
- **Modify**: `tests/sdl-workflow/test-hash-gate.sh`
- **Modify**: `tests/sdl-workflow/test-spec-validator.sh`
- **Modify**: `tests/sdl-workflow/test-state-engine.sh`
- **Modify**: `tests/sdl-workflow/test-status-command.sh`

## Test requirements

| Level | Behavior | Expected assertion |
|-------|----------|--------------------|
| Existing | all 6 test scripts pass with dispatcher paths | all tests pass |

## Acceptance criteria

- AC-10: existing tests pass after path updates

## Model

Sonnet

## Wave

2
