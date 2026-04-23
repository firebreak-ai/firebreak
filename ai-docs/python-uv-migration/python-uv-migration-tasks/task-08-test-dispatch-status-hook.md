---
id: task-08
type: test
wave: 1
covers: [AC-01, AC-08]
files_to_create:
  - assets/fbk-scripts/tests/test_hooks_dispatch_status.py
completion_gate: "tests compile and fail before implementation"
---

## Objective

Create pytest unit tests for `fbk.hooks.dispatch_status` output formatting.

## Context

`dispatch-status.sh` (lines 18-56) reads a pipeline state JSON file and formats human-readable output: feature name, current status, last transition timestamp, stage history, PARKED info (if applicable), and error history. The Python module `fbk.hooks.dispatch_status` must expose a formatting function. Tests verify output format for each pipeline state.

Follow the test scenarios from `tests/sdl-workflow/test-status-command.sh` (tests 1-7): queued shows name+QUEUED+timestamp, reviewing shows stage history, parked shows failed stage and reason, completed shows COMPLETED, output is human-readable (not JSON).

## Instructions

1. Create `assets/fbk-scripts/tests/test_hooks_dispatch_status.py`
2. Import the formatting function from `fbk.hooks.dispatch_status` (e.g., `format_status`)
3. Write a test with QUEUED state JSON — assert output contains spec name, "QUEUED", and a timestamp
4. Write a test with REVIEWING state JSON (multiple stage timestamps) — assert output contains "REVIEWING" and prior stages
5. Write a test with PARKED state JSON (with `parked_info`) — assert output contains "PARKED", failed stage, and reason
6. Write a test with COMPLETED state JSON — assert output contains "COMPLETED"
7. Write a test asserting the output does not start with `{` (human-readable, not JSON)

## Files to create/modify

- **Create**: `assets/fbk-scripts/tests/test_hooks_dispatch_status.py`

## Test requirements

| Level | Behavior | Expected assertion |
|-------|----------|--------------------|
| Unit | queued state formatted correctly | output contains spec name, "QUEUED", timestamp |
| Unit | reviewing state shows history | output contains "REVIEWING" and prior stages |
| Unit | parked state shows failure details | output contains "PARKED", failed stage, reason |
| Unit | completed state formatted | output contains "COMPLETED" |
| Unit | output is human-readable | first character is not `{` |

## Acceptance criteria

- AC-01: validates dispatch-status hook converted to Python
- AC-08: formatting function produces correct output for each state

## Model

Haiku

## Wave

1
