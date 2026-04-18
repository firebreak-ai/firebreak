---
id: task-26
type: implementation
wave: 2
covers: [AC-10]
files_to_modify:
  - tests/sdl-workflow/test-pipeline-to-markdown.sh
  - tests/sdl-workflow/test-pipeline-integration.sh
  - tests/sdl-workflow/test-type-severity-matrix.sh
  - tests/sdl-workflow/test-guide-precision-alignment.sh
  - tests/sdl-workflow/test-orchestrator-pipeline-integration.sh
test_tasks: [task-28]
completion_gate: "task-28 tests pass"
---

## Objective

Update 3 remaining pipeline tests and 2 integration grep tests to use the dispatcher.

## Context

This task touches 5 files because the first 3 are identical mechanical `uv run` swaps, and the last 2 are grep pattern updates. All are trivial changes — splitting would create artificial boundaries.

## Instructions

1. In `test-pipeline-to-markdown.sh`: replace `PIPELINE=...` with `DISPATCHER="$PROJECT_ROOT/assets/fbk-scripts/fbk.py"`, replace all `uv run "$PIPELINE"` with `python3 "$DISPATCHER" pipeline`
2. In `test-pipeline-integration.sh`: same PIPELINE→DISPATCHER variable and `uv run` invocation replacements
3. In `test-type-severity-matrix.sh`: same PIPELINE→DISPATCHER variable and `uv run` invocation replacements
4. In `test-guide-precision-alignment.sh` Test 11: change grep pattern from `pipeline\.py|uv run` to `fbk\.py.*pipeline|python3.*pipeline`
5. In `test-orchestrator-pipeline-integration.sh`: Test 1 change `grep -q 'fbk-pipeline.py'` to `grep -q 'fbk.py'`; Test 2 change `grep -q 'uv run'` to `grep -q 'python3'`

## Files to create/modify

- **Modify**: `tests/sdl-workflow/test-pipeline-to-markdown.sh`
- **Modify**: `tests/sdl-workflow/test-pipeline-integration.sh`
- **Modify**: `tests/sdl-workflow/test-type-severity-matrix.sh`
- **Modify**: `tests/sdl-workflow/test-guide-precision-alignment.sh`
- **Modify**: `tests/sdl-workflow/test-orchestrator-pipeline-integration.sh`

## Test requirements

| Level | Behavior | Expected assertion |
|-------|----------|--------------------|
| Existing | all 5 test scripts pass with updated paths/patterns | all tests pass |

## Acceptance criteria

- AC-10: existing tests pass after path and pattern updates

## Model

Sonnet

## Wave

2
