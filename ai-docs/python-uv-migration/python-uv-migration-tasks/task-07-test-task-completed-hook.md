---
id: task-07
type: test
wave: 1
covers: [AC-01, AC-08]
files_to_create:
  - assets/fbk-scripts/tests/test_hooks_task_completed.py
completion_gate: "tests compile and fail before implementation"
---

## Objective

Create pytest unit tests for `fbk.hooks.task_completed` test runner and linter detection.

## Context

`task-completed.sh` (lines 20-55) implements `detect_test_cmd()` and `detect_lint_cmd()` which detect project test runners and linters by checking for marker files (`package.json` → `npm test`, `Cargo.toml` → `cargo test`, etc.). The Python module must expose these as testable functions. Tests verify detection returns the correct command string for each supported project type.

## Instructions

1. Create `assets/fbk-scripts/tests/test_hooks_task_completed.py`
2. Import `detect_test_cmd` and `detect_lint_cmd` from `fbk.hooks.task_completed`
3. Write tests for `detect_test_cmd` using `tmp_path`:
   - Create `package.json` → assert returns `"npm test"`
   - Create `Cargo.toml` → assert returns `"cargo test"`
   - Create `go.mod` → assert returns `"go test ./..."`
   - Create `pyproject.toml` with `[tool.pytest` → assert returns `"python -m pytest"`
   - Create `Makefile` with `test:` target → assert returns `"make test"`
   - Empty directory → assert returns empty string
4. Write tests for `detect_lint_cmd` using `tmp_path`:
   - Create `.eslintrc.json` → assert returns a string containing `eslint`
   - Create `pyproject.toml` with `[tool.ruff]` → assert returns a string containing `ruff`
   - Empty directory → assert returns empty string

## Files to create/modify

- **Create**: `assets/fbk-scripts/tests/test_hooks_task_completed.py`

## Test requirements

| Level | Behavior | Expected assertion |
|-------|----------|--------------------|
| Unit | npm project detected | returns "npm test" |
| Unit | cargo project detected | returns "cargo test" |
| Unit | go project detected | returns "go test ./..." |
| Unit | pytest project detected | returns "python -m pytest" |
| Unit | makefile test target detected | returns "make test" |
| Unit | no test runner returns empty | returns "" |
| Unit | eslint detected | returns string containing "eslint" |
| Unit | ruff detected | returns string containing "ruff" |
| Unit | no linter returns empty | returns "" |

## Acceptance criteria

- AC-01: validates task-completed hook detection logic converted to Python
- AC-08: detection functions return correct commands for each project type

## Model

Haiku

## Wave

1
