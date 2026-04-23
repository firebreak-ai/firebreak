---
id: task-25
type: implementation
wave: 2
covers: [AC-10]
files_to_modify:
  - tests/sdl-workflow/test-task-reviewer.sh
  - tests/sdl-workflow/test-preset-config.sh
  - tests/sdl-workflow/test-pipeline-validate.sh
  - tests/sdl-workflow/test-pipeline-run.sh
  - tests/sdl-workflow/test-pipeline-severity-filter.sh
  - tests/sdl-workflow/test-pipeline-domain-filter.sh
test_tasks: [task-28]
completion_gate: "task-28 tests pass"
---

## Objective

Update path variables in `test-task-reviewer.sh`, `test-preset-config.sh`, and 4 pipeline test scripts to invoke through the dispatcher.

## Context

This task touches 6 files because each edit follows the same mechanical pattern (variable rename + invocation swap). The pipeline tests additionally change `uv run "$PIPELINE"` to `python3 "$DISPATCHER" pipeline` across multiple invocations per file. Splitting would create artificial boundaries.

## Instructions

1. In `test-task-reviewer.sh`: replace `GATE="$PROJECT_ROOT/assets/hooks/fbk-sdl-workflow/task-reviewer-gate.sh"` with `DISPATCHER="$PROJECT_ROOT/assets/fbk-scripts/fbk.py"`, replace all `bash "$GATE"` with `python3 "$DISPATCHER" task-reviewer-gate`
2. In `test-preset-config.sh`: replace `PRESETS="$PROJECT_ROOT/assets/config/fbk-presets.json"` with `PRESETS="$PROJECT_ROOT/assets/fbk-scripts/fbk/data/fbk-presets.json"`
3. In `test-pipeline-validate.sh`: replace `PIPELINE="$PROJECT_ROOT/assets/scripts/fbk-pipeline.py"` with `DISPATCHER="$PROJECT_ROOT/assets/fbk-scripts/fbk.py"`, replace all `uv run "$PIPELINE"` with `python3 "$DISPATCHER" pipeline`. Test 1: change `[ -s "$PIPELINE" ]` to `[ -s "$DISPATCHER" ] && [ -s "$PROJECT_ROOT/assets/fbk-scripts/fbk/pipeline.py" ]`
4. In `test-pipeline-run.sh`: same PIPELINE→DISPATCHER variable and `uv run` invocation replacements
5. In `test-pipeline-severity-filter.sh`: same PIPELINE→DISPATCHER variable and `uv run` invocation replacements
6. In `test-pipeline-domain-filter.sh`: same PIPELINE→DISPATCHER variable and `uv run` invocation replacements

## Files to create/modify

- **Modify**: `tests/sdl-workflow/test-task-reviewer.sh`
- **Modify**: `tests/sdl-workflow/test-preset-config.sh`
- **Modify**: `tests/sdl-workflow/test-pipeline-validate.sh`
- **Modify**: `tests/sdl-workflow/test-pipeline-run.sh`
- **Modify**: `tests/sdl-workflow/test-pipeline-severity-filter.sh`
- **Modify**: `tests/sdl-workflow/test-pipeline-domain-filter.sh`

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
