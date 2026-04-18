---
id: task-21
type: test
wave: 3
covers: [AC-07]
files_to_create:
  - tests/sdl-workflow/test-old-locations-empty.sh
completion_gate: "tests compile and fail before implementation"
---

## Objective

Create bash integration test verifying old script locations contain no `.sh` or `.py` files.

## Context

AC-07 requires no bash scripts or Python modules remain at old locations after migration. `assets/hooks/fbk-sdl-workflow/` must contain no `.sh` or `.py` files. `assets/scripts/` must be empty or absent. `assets/skills/fbk-council/` must contain no `.py` files (only SKILL.md).

## Instructions

1. Create `tests/sdl-workflow/test-old-locations-empty.sh`
2. Write Test 1: `find assets/hooks/fbk-sdl-workflow/ -name '*.sh'` — assert zero results
3. Write Test 2: `find assets/hooks/fbk-sdl-workflow/ -name '*.py'` — assert zero results
4. Write Test 3: assert `assets/scripts/` is empty or does not exist
5. Write Test 4: `find assets/skills/fbk-council/ -name '*.py'` — assert zero results
6. Write Test 5: assert `assets/skills/fbk-council/SKILL.md` exists (retained)

## Files to create/modify

- **Create**: `tests/sdl-workflow/test-old-locations-empty.sh`

## Test requirements

| Level | Behavior | Expected assertion |
|-------|----------|--------------------|
| Integration | no .sh files in hooks/fbk-sdl-workflow | find count == 0 |
| Integration | no .py files in hooks/fbk-sdl-workflow | find count == 0 |
| Integration | assets/scripts/ empty or absent | directory empty or not found |
| Integration | no .py files in skills/fbk-council | find count == 0 |
| Integration | council SKILL.md retained | file exists |

## Acceptance criteria

- AC-07: no bash scripts or Python modules at old locations

## Model

Haiku

## Wave

2
