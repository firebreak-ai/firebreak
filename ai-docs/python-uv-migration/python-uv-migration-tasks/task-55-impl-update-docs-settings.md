---
id: task-55
type: implementation
wave: 2
covers: [AC-05, AC-06]
files_to_modify:
  - assets/fbk-docs/fbk-sdl-workflow/code-review-guide.md
  - assets/fbk-docs/fbk-sdl-workflow/verify-yml-schema.md
  - assets/fbk-docs/fbk-sdl-workflow/corrective-workflow.md
  - assets/settings.json
test_tasks: [task-18, task-19]
completion_gate: "task-18 and task-19 tests pass"
---

## Objective

Update script references in 3 fbk-docs files and `settings.json` to use the dispatcher.

## Context

This task touches 4 files because each contains 1-2 simple string replacements. Splitting would create artificial boundaries.

## Instructions

1. In `assets/fbk-docs/fbk-sdl-workflow/code-review-guide.md`: replace both `uv run fbk-pipeline.py` references with `python3 "$HOME"/.claude/fbk-scripts/fbk.py pipeline`
2. In `assets/fbk-docs/fbk-sdl-workflow/verify-yml-schema.md`: replace `bash .claude/hooks/fbk-sdl-workflow/test-hash-gate.sh` with `python3 "$HOME"/.claude/fbk-scripts/fbk.py test-hash-gate`
3. In `assets/fbk-docs/fbk-sdl-workflow/corrective-workflow.md`: replace `.claude/hooks/fbk-sdl-workflow/task-reviewer-gate.sh` with `python3 "$HOME"/.claude/fbk-scripts/fbk.py task-reviewer-gate`
4. In `assets/settings.json`: replace `"\"$HOME\"/.claude/hooks/fbk-sdl-workflow/task-completed.sh"` with `"python3 \"$HOME\"/.claude/fbk-scripts/fbk.py task-completed"`

## Files to create/modify

- **Modify**: `assets/fbk-docs/fbk-sdl-workflow/code-review-guide.md`
- **Modify**: `assets/fbk-docs/fbk-sdl-workflow/verify-yml-schema.md`
- **Modify**: `assets/fbk-docs/fbk-sdl-workflow/corrective-workflow.md`
- **Modify**: `assets/settings.json`

## Test requirements

- task-18: settings.json contains `fbk-scripts/fbk.py task-completed` and `python3`
- task-19: grep for old path patterns returns zero matches in fbk-docs files

## Acceptance criteria

- AC-05: settings.json hook commands use dispatcher format
- AC-06: all doc file references use dispatcher format

## Model

Haiku

## Wave

2
