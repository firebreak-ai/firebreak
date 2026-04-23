---
id: task-53
type: implementation
wave: 2
covers: [AC-06]
files_to_modify:
  - assets/skills/fbk-spec/SKILL.md
  - assets/skills/fbk-spec-review/SKILL.md
  - assets/skills/fbk-breakdown/SKILL.md
  - assets/skills/fbk-implement/SKILL.md
test_tasks: [task-19]
completion_gate: "task-19 tests pass"
---

## Objective

Update all gate script references in 4 SDL workflow SKILL.md files to use the dispatcher.

## Context

These 4 SKILL.md files contain 7 references to hook scripts that are being relocated. All follow the same pattern: replace `.claude/hooks/fbk-sdl-workflow/<gate>.sh` with `python3 "$HOME"/.claude/fbk-scripts/fbk.py <gate>`. This task touches 4 files because each has 1-3 trivial string replacements — splitting would create artificial boundaries.

## Instructions

1. In `assets/skills/fbk-spec/SKILL.md`: replace `.claude/hooks/fbk-sdl-workflow/spec-gate.sh` with `python3 "$HOME"/.claude/fbk-scripts/fbk.py spec-gate`
2. In `assets/skills/fbk-spec-review/SKILL.md`: replace spec-gate and review-gate references with dispatcher format
3. In `assets/skills/fbk-breakdown/SKILL.md`: replace review-gate, task-reviewer-gate, and breakdown-gate references with dispatcher format
4. In `assets/skills/fbk-implement/SKILL.md`: replace breakdown-gate reference with dispatcher format

## Files to create/modify

- **Modify**: `assets/skills/fbk-spec/SKILL.md`
- **Modify**: `assets/skills/fbk-spec-review/SKILL.md`
- **Modify**: `assets/skills/fbk-breakdown/SKILL.md`
- **Modify**: `assets/skills/fbk-implement/SKILL.md`

## Test requirements

- task-19: grep for `hooks/fbk-sdl-workflow` returns zero matches in these files

## Acceptance criteria

- AC-06: all 7 script references in these 4 SKILL.md files use dispatcher format

## Model

Haiku

## Wave

2
