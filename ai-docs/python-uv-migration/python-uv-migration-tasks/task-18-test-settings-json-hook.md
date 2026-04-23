---
id: task-18
type: test
wave: 2
covers: [AC-05]
files_to_create:
  - tests/sdl-workflow/test-settings-hook-command.sh
completion_gate: "tests compile and fail before implementation"
---

## Objective

Create bash integration test verifying `assets/settings.json` contains the new dispatcher hook command.

## Context

AC-05 requires `assets/settings.json` hook commands use `python3 "$HOME"/.claude/fbk-scripts/fbk.py <command>` format. The current `settings.json` has `"$HOME"/.claude/hooks/fbk-sdl-workflow/task-completed.sh`. After migration, it must contain `python3 "$HOME"/.claude/fbk-scripts/fbk.py task-completed`.

## Instructions

1. Create `tests/sdl-workflow/test-settings-hook-command.sh`
2. Set `SETTINGS="$PROJECT_ROOT/assets/settings.json"`
3. Write Test 1: assert `settings.json` contains the string `fbk-scripts/fbk.py task-completed`
4. Write Test 2: assert `settings.json` does NOT contain `hooks/fbk-sdl-workflow/task-completed.sh`
5. Write Test 3: assert `settings.json` contains `python3`

## Files to create/modify

- **Create**: `tests/sdl-workflow/test-settings-hook-command.sh`

## Test requirements

| Level | Behavior | Expected assertion |
|-------|----------|--------------------|
| Integration | settings.json has new dispatcher command | grep matches "fbk-scripts/fbk.py task-completed" |
| Integration | settings.json has no old hook path | grep does not match "hooks/fbk-sdl-workflow/task-completed.sh" |
| Integration | settings.json uses python3 invocation | grep matches "python3" |

## Acceptance criteria

- AC-05: settings.json hook commands use dispatcher format

## Model

Haiku

## Wave

2
