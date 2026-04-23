---
id: task-54
type: implementation
wave: 2
covers: [AC-06]
files_to_modify:
  - assets/skills/fbk-code-review/SKILL.md
  - assets/skills/fbk-code-review/references/existing-code-review.md
  - assets/skills/fbk-council/SKILL.md
test_tasks: [task-19, task-20]
completion_gate: "task-19 and task-20 tests pass"
---

## Objective

Update all script references in code-review SKILL.md, existing-code-review.md, and council SKILL.md to use the dispatcher.

## Context

This task touches 3 files because they share the same migration pattern (old paths → dispatcher format). The council SKILL.md has 22 references but they are all mechanical find-replace of 2 patterns. Splitting would create artificial boundaries.

## Instructions

1. In `assets/skills/fbk-code-review/SKILL.md`: replace all 3 `uv run "$HOME/.claude/scripts/fbk-pipeline.py"` references with `python3 "$HOME"/.claude/fbk-scripts/fbk.py pipeline`
2. In `assets/skills/fbk-code-review/references/existing-code-review.md`: replace `spec-gate.sh` reference with `python3 "$HOME"/.claude/fbk-scripts/fbk.py spec-gate`
3. In `assets/skills/fbk-council/SKILL.md`:
   - Replace all `python3 ~/.claude/skills/fbk-council/session-manager.py` with `python3 "$HOME"/.claude/fbk-scripts/fbk.py session-manager`
   - Replace all `python3 ~/.claude/skills/fbk-council/session-logger.py` with `python3 "$HOME"/.claude/fbk-scripts/fbk.py session-logger`
   - Replace inline `session-logger.py self-eval` with `fbk.py session-logger self-eval`
   - Replace `**Logger location**` path with `"$HOME"/.claude/fbk-scripts/fbk.py session-logger`
4. Verify no `~/.claude/skills/fbk-council/session-` or `uv run` patterns remain

## Files to create/modify

- **Modify**: `assets/skills/fbk-code-review/SKILL.md`
- **Modify**: `assets/skills/fbk-code-review/references/existing-code-review.md`
- **Modify**: `assets/skills/fbk-council/SKILL.md`

## Test requirements

- task-19: grep for old path patterns returns zero matches
- task-20: council SKILL.md contains dispatcher references, no old council script paths

## Acceptance criteria

- AC-06: all references in these 3 files use dispatcher format

## Model

Sonnet

## Wave

2
