---
id: task-05
type: test
wave: 1
covers: [AC-01, AC-08]
files_to_create:
  - assets/fbk-scripts/tests/test_gates_task_reviewer.py
completion_gate: "tests compile and fail before implementation"
---

## Objective

Create pytest unit tests for `fbk.gates.task_reviewer` validation logic.

## Context

`task-reviewer-gate.sh` (lines 27-219) validates: required frontmatter fields (`id`, `type`, `wave`, `covers`, `completion_gate`), `files_to_create` or `files_to_modify` presence, type enum (`test`|`implementation`), AC identifier format (`AC-NN`), implementation tasks requiring `test_tasks`, `files_to_modify` path existence, AC coverage across test/impl tasks, file scope conflicts within same wave, and `test_tasks` reference validity. Uses PyYAML for frontmatter parsing.

## Instructions

1. Create `assets/fbk-scripts/tests/test_gates_task_reviewer.py`
2. Import the validation function from `fbk.gates.task_reviewer`
3. Write a test with a task file missing the `id` field — assert failure includes "missing required field"
4. Write a test with a task file having `type: unknown` — assert failure includes "type must be"
5. Write a test with an implementation task missing `test_tasks` — assert failure includes "missing 'test_tasks'"
6. Write a test with two tasks in the same wave claiming the same file — assert failure includes "File scope conflict"
7. Write a test with a valid task set covering all spec ACs — assert result passes

## Files to create/modify

- **Create**: `assets/fbk-scripts/tests/test_gates_task_reviewer.py`

## Test requirements

| Level | Behavior | Expected assertion |
|-------|----------|--------------------|
| Unit | missing required field detected | failure contains "missing required field" |
| Unit | invalid type enum detected | failure contains "type must be" |
| Unit | implementation task missing test_tasks | failure contains "missing 'test_tasks'" |
| Unit | file scope conflict in same wave | failure contains "File scope conflict" |
| Unit | valid task set passes | result is pass |

## Acceptance criteria

- AC-01: validates task reviewer gate converted to Python
- AC-08: gate produces correct pass/fail for known inputs

## Model

Haiku

## Wave

1
