---
id: task-20
type: test
wave: 2
covers: [AC-06]
files_to_create:
  - tests/sdl-workflow/test-council-skill-references.sh
completion_gate: "tests compile and fail before implementation"
---

## Objective

Create bash integration test verifying `assets/skills/fbk-council/SKILL.md` contains new dispatcher references and no old script paths.

## Context

The council SKILL.md has 22 references to update. After migration it must contain `python3 "$HOME"/.claude/fbk-scripts/fbk.py session-manager` and `python3 "$HOME"/.claude/fbk-scripts/fbk.py session-logger`, with zero references to `~/.claude/skills/fbk-council/session-`.

## Instructions

1. Create `tests/sdl-workflow/test-council-skill-references.sh`
2. Set `SKILL="$PROJECT_ROOT/assets/skills/fbk-council/SKILL.md"`
3. Write Test 1: grep for `fbk-scripts/fbk.py session-manager` — assert at least 1 match
4. Write Test 2: grep for `fbk-scripts/fbk.py session-logger` — assert at least 1 match
5. Write Test 3: grep for `~/.claude/skills/fbk-council/session-` — assert zero matches
6. Write Test 4: grep for `~/.claude/skills/fbk-council/ralph-` — assert zero matches

## Files to create/modify

- **Create**: `tests/sdl-workflow/test-council-skill-references.sh`

## Test requirements

| Level | Behavior | Expected assertion |
|-------|----------|--------------------|
| Integration | SKILL.md has session-manager dispatcher ref | grep count >= 1 |
| Integration | SKILL.md has session-logger dispatcher ref | grep count >= 1 |
| Integration | SKILL.md has no old session- script refs | grep count == 0 |
| Integration | SKILL.md has no old ralph- script refs | grep count == 0 |

## Acceptance criteria

- AC-06: council SKILL.md references updated to dispatcher

## Model

Haiku

## Wave

2
