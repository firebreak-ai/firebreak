---
id: task-19
type: test
wave: 2
covers: [AC-06]
files_to_create:
  - tests/sdl-workflow/test-no-old-path-patterns.sh
completion_gate: "tests compile and fail before implementation"
---

## Objective

Create bash integration test verifying all 11 context asset files contain no old path patterns.

## Context

AC-06 requires all 38 script references across 11 context asset files use the dispatcher format. This test greps all 11 files for old path patterns: `hooks/fbk-sdl-workflow`, `scripts/fbk-pipeline`, `uv run.*pipeline`, `~/.claude/skills/fbk-council`. Zero matches expected.

The 11 files are listed in the spec's context asset reference map.

## Instructions

1. Create `tests/sdl-workflow/test-no-old-path-patterns.sh`
2. Define the 11 context asset files as an array:
   - `assets/skills/fbk-spec/SKILL.md`
   - `assets/skills/fbk-spec-review/SKILL.md`
   - `assets/skills/fbk-breakdown/SKILL.md`
   - `assets/skills/fbk-implement/SKILL.md`
   - `assets/skills/fbk-code-review/SKILL.md`
   - `assets/skills/fbk-council/SKILL.md`
   - `assets/skills/fbk-code-review/references/existing-code-review.md`
   - `assets/fbk-docs/fbk-sdl-workflow/code-review-guide.md`
   - `assets/fbk-docs/fbk-sdl-workflow/verify-yml-schema.md`
   - `assets/fbk-docs/fbk-sdl-workflow/corrective-workflow.md`
   - `assets/settings.json`
3. Write Test 1: grep all files for `hooks/fbk-sdl-workflow` — assert zero matches
4. Write Test 2: grep all files for `scripts/fbk-pipeline` — assert zero matches
5. Write Test 3: grep all files for `uv run` — assert zero matches
6. Write Test 4: grep all files for `~/.claude/skills/fbk-council/` — assert zero matches

## Files to create/modify

- **Create**: `tests/sdl-workflow/test-no-old-path-patterns.sh`

## Test requirements

| Level | Behavior | Expected assertion |
|-------|----------|--------------------|
| Integration | no hooks/fbk-sdl-workflow references | grep count == 0 |
| Integration | no scripts/fbk-pipeline references | grep count == 0 |
| Integration | no uv run references | grep count == 0 |
| Integration | no ~/.claude/skills/fbk-council/ references | grep count == 0 |

## Acceptance criteria

- AC-06: all 38 references updated, no old path patterns remain

## Model

Haiku

## Wave

2
