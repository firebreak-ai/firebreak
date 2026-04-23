---
id: task-01
type: test
wave: 1
covers: [AC-01, AC-08]
files_to_create:
  - assets/fbk-scripts/tests/test_gates_spec.py
completion_gate: "tests compile and fail before implementation"
---

## Objective

Create pytest unit tests for `fbk.gates.spec` section validation and open-questions logic.

## Context

`spec-gate.sh` (lines 21-63) implements `check_section()` which validates heading presence and non-empty body, and `check_open_questions()` which validates that each bullet has rationale. The Python module `fbk.gates.spec` must expose these as importable functions. Tests verify the behavioral contract: missing sections produce failures, empty sections produce failures, bare questions without rationale produce failures.

Follow the TAP-style behavioral naming from `tests/sdl-workflow/test-spec-validator.sh` for test name conventions.

## Instructions

1. Create `assets/fbk-scripts/tests/test_gates_spec.py`
2. Import `check_section` and `check_open_questions` from `fbk.gates.spec` (these do not exist yet — imports will fail, satisfying the completion gate)
3. Write tests that call `check_section()` with a spec string missing `## Problem` — assert the return includes a failure for "Missing section"
4. Write a test that calls `check_section()` with a spec string containing `## Problem` followed by only whitespace — assert "Empty section" failure
5. Write a test that calls `check_section()` with a spec string containing `## Problem` with body content — assert no failure
6. Write a test that calls `check_open_questions()` with a bullet containing only `- Why?` (no rationale) — assert failure message includes "rationale"
7. Write a test that calls `check_open_questions()` with a bullet containing `- Why? Because X` (inline rationale) — assert no failure
8. Write a test that calls `check_open_questions()` with a bullet followed by an indented continuation line — assert no failure

## Files to create/modify

- **Create**: `assets/fbk-scripts/tests/test_gates_spec.py`

## Test requirements

| Level | Behavior | Expected assertion |
|-------|----------|--------------------|
| Unit | missing section detected | failure list contains "Missing section: ## Problem" |
| Unit | empty section detected | failure list contains "Empty section: ## Problem" |
| Unit | valid section passes | failure list is empty |
| Unit | bare question without rationale fails | failure message includes "rationale" |
| Unit | inline rationale passes | no failure |
| Unit | indented continuation rationale passes | no failure |

## Acceptance criteria

- AC-01: validates spec gate logic is correctly converted to Python
- AC-08: gate produces correct pass/fail for known inputs

## Model

Haiku

## Wave

1
