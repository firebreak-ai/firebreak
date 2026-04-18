---
id: task-28
type: test
wave: 2
covers: [AC-10]
files_to_create:
  - tests/sdl-workflow/test-verify-test-paths-updated.sh
completion_gate: "tests compile and fail before implementation"
---

## Objective

Create a bash test that verifies no old script paths remain in any test file after the migration.

## Context

AC-10 requires all 24 existing test scripts pass after path updates. This verification test greps all test files for old path patterns that should no longer exist after migration. It serves as the completion gate for the 4 test-path-update implementation tasks.

## Instructions

1. Create `tests/sdl-workflow/test-verify-test-paths-updated.sh`
2. Write Test 1: grep `tests/sdl-workflow/` and `tests/installer/` for `hooks/fbk-sdl-workflow` — assert zero matches
3. Write Test 2: grep `tests/sdl-workflow/` for `uv run` — assert zero matches
4. Write Test 3: grep `tests/sdl-workflow/` and `tests/installer/` for `scripts/fbk-pipeline.py` — assert zero matches
5. Write Test 4: grep `tests/installer/` for `task-completed.sh` — assert zero matches
6. Write Test 5: grep `tests/sdl-workflow/test-preset-config.sh` for `assets/config/fbk-presets.json` — assert zero matches

## Files to create/modify

- **Create**: `tests/sdl-workflow/test-verify-test-paths-updated.sh`

## Test requirements

| Level | Behavior | Expected assertion |
|-------|----------|--------------------|
| Integration | no old hook paths in test files | grep returns zero matches |
| Integration | no uv run in test files | grep returns zero matches |
| Integration | no old pipeline path in test files | grep returns zero matches |
| Integration | no old installer paths in test files | grep returns zero matches |
| Integration | no old preset path in test files | grep returns zero matches |

## Acceptance criteria

- AC-10: all old path patterns eliminated from test files

## Model

Haiku

## Wave

2
