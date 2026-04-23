---
id: task-04
type: test
wave: 1
covers: [AC-01, AC-08]
files_to_create:
  - assets/fbk-scripts/tests/test_gates_breakdown.py
completion_gate: "tests compile and fail before implementation"
---

## Objective

Create pytest unit tests for `fbk.gates.breakdown` validation logic.

## Context

`breakdown-gate.sh` (lines 24-175) validates: AC coverage (each spec AC covered by test+impl tasks), DAG acyclicity via topological sort, wave ordering (dependencies must precede dependents), test-before-impl within each wave, file reference existence, file count constraint (max 2 without justification), and file scope conflicts within same wave. The Python heredoc already implements this logic — the conversion moves it to `fbk.gates.breakdown`.

## Instructions

1. Create `assets/fbk-scripts/tests/test_gates_breakdown.py`
2. Import the validation function from `fbk.gates.breakdown`
3. Write a test with an AC in the spec not covered by any task — assert failure includes "AC coverage"
4. Write a test with a circular dependency (task-01 depends on task-02, task-02 depends on task-01) — assert failure includes "cycle"
5. Write a test with a dependency in a later wave than its dependent — assert failure includes "Wave ordering"
6. Write a test with two tasks in the same wave touching the same file — assert failure includes "File conflict"
7. Write a test with an implementation task listed before a test task in the same wave — assert failure includes "Test ordering"
8. Write a test with a valid breakdown (all ACs covered, no cycles, correct wave ordering, test-before-impl, no conflicts) — assert result is "pass"

## Files to create/modify

- **Create**: `assets/fbk-scripts/tests/test_gates_breakdown.py`

## Test requirements

| Level | Behavior | Expected assertion |
|-------|----------|--------------------|
| Unit | uncovered AC detected | failure contains "AC coverage" |
| Unit | DAG cycle detected | failure contains "cycle" |
| Unit | wave ordering violation detected | failure contains "Wave ordering" |
| Unit | file scope conflict detected | failure contains "File conflict" |
| Unit | test-before-impl violation detected | failure contains "Test ordering" |
| Unit | valid breakdown passes | result == "pass" |

## Acceptance criteria

- AC-01: validates breakdown gate logic converted to Python
- AC-08: gate produces correct pass/fail for known inputs

## Model

Haiku

## Wave

1
