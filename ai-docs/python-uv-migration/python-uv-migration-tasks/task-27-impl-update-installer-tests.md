---
id: task-27
type: implementation
wave: 2
covers: [AC-10]
files_to_modify:
  - tests/installer/test-install.sh
  - tests/fixtures/installer/firebreak-settings.json
  - tests/installer/test-upgrade-uninstall.sh
  - tests/installer/test-e2e-lifecycle.sh
  - tests/installer/test-json-merge-hooks.sh
test_tasks: [task-28]
completion_gate: "task-28 tests pass"
---

## Objective

Update 4 installer test scripts and 1 test fixture to match the new `fbk-scripts/` layout.

## Context

All installer tests create mock source structures with `setup_mock_source()` that references `hooks/fbk-sdl-workflow/task-completed.sh`. All must change to `fbk-scripts/fbk.py`. This task touches 5 files because all share the same mock structure pattern — splitting would create artificial boundaries.

## Instructions

1. In `test-install.sh` `setup_mock_source()`: replace `mkdir -p "$MOCK_DIR/assets/hooks/fbk-sdl-workflow"` with `mkdir -p "$MOCK_DIR/assets/fbk-scripts"`, replace mock file creation from `task-completed.sh` to `fbk.py`, update settings.json heredoc command to `python3 "$HOME"/.claude/fbk-scripts/fbk.py task-completed`. Test 1: change `[ -f "$TARGET/hooks/fbk-sdl-workflow/task-completed.sh" ]` to `[ -f "$TARGET/fbk-scripts/fbk.py" ]`
2. In `firebreak-settings.json`: change command from `"$HOME"/.claude/hooks/fbk-sdl-workflow/task-completed.sh` to `python3 "$HOME"/.claude/fbk-scripts/fbk.py task-completed`
3. In `test-upgrade-uninstall.sh`: same `setup_mock_source()` update. Test 5: check `fbk-scripts/` absence instead of `task-completed.sh`. Test 10: check `fbk-scripts/` removal instead of `hooks/fbk-sdl-workflow`
4. In `test-e2e-lifecycle.sh`: same `setup_mock_source()` update. Line 108: assert `fbk-scripts/fbk.py` presence instead of `hooks/fbk-sdl-workflow/task-completed.sh`
5. In `test-json-merge-hooks.sh`: Test 1 change match from `fbk-sdl-workflow/task-completed.sh` to `fbk-scripts/fbk.py task-completed`. Test 4 update inline heredoc command to dispatcher format

## Files to create/modify

- **Modify**: `tests/installer/test-install.sh`
- **Modify**: `tests/fixtures/installer/firebreak-settings.json`
- **Modify**: `tests/installer/test-upgrade-uninstall.sh`
- **Modify**: `tests/installer/test-e2e-lifecycle.sh`
- **Modify**: `tests/installer/test-json-merge-hooks.sh`

## Test requirements

| Level | Behavior | Expected assertion |
|-------|----------|--------------------|
| Existing | all 4 installer test scripts pass with new layout | all tests pass |
| Existing | fixture matches new command format | firebreak-settings.json correct |

## Acceptance criteria

- AC-10: installer tests pass after layout updates

## Model

Sonnet

## Wave

2
