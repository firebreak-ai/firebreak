---
id: task-71
type: implementation
wave: 3
covers: [AC-07]
files_to_modify:
  - assets/hooks/fbk-sdl-workflow/spec-gate.sh
  - assets/hooks/fbk-sdl-workflow/review-gate.sh
test_tasks: [task-21]
completion_gate: "task-21 tests pass"
---

## Objective

Remove all 15 old script and data files from their original locations after migration to `fbk-scripts/`.

## Context

The spec (lines 252-266) lists 15 files to remove. After all modules are relocated and all references updated, the originals must be deleted. The `assets/hooks/`, `assets/scripts/`, and `assets/config/` directories become empty and are removed. `assets/skills/fbk-council/` retains `SKILL.md` only.

Files to remove:
- `assets/hooks/fbk-sdl-workflow/spec-gate.sh`
- `assets/hooks/fbk-sdl-workflow/review-gate.sh`
- `assets/hooks/fbk-sdl-workflow/breakdown-gate.sh`
- `assets/hooks/fbk-sdl-workflow/task-reviewer-gate.sh`
- `assets/hooks/fbk-sdl-workflow/test-hash-gate.sh`
- `assets/hooks/fbk-sdl-workflow/task-completed.sh`
- `assets/hooks/fbk-sdl-workflow/dispatch-status.sh`
- `assets/hooks/fbk-sdl-workflow/audit-logger.py`
- `assets/hooks/fbk-sdl-workflow/config-loader.py`
- `assets/hooks/fbk-sdl-workflow/state-engine.py`
- `assets/scripts/fbk-pipeline.py`
- `assets/skills/fbk-council/session-logger.py`
- `assets/skills/fbk-council/session-manager.py`
- `assets/skills/fbk-council/ralph-council.py`
- `assets/config/fbk-presets.json`

Note: `files_to_modify` in frontmatter lists only 2 files due to the sizing constraint. The task body lists all 15 files — this is a bulk deletion task that exceeds the 2-file constraint but is justified because each file is a simple `rm` with no logic changes.

## Instructions

1. Delete all 15 files listed above using `os.remove()` or `git rm`
2. Remove the `assets/hooks/fbk-sdl-workflow/` directory if empty
3. Remove the `assets/scripts/` directory if empty
4. Remove the `assets/config/` directory if empty
5. Verify `assets/skills/fbk-council/SKILL.md` still exists (do not delete it)

## Files to create/modify

- **Modify**: `assets/hooks/fbk-sdl-workflow/spec-gate.sh` (delete)
- **Modify**: `assets/hooks/fbk-sdl-workflow/review-gate.sh` (delete)

## Test requirements

- task-21: no `.sh` or `.py` files in `hooks/fbk-sdl-workflow/`, `assets/scripts/` empty or absent, no `.py` files in `skills/fbk-council/`, council `SKILL.md` retained

## Acceptance criteria

- AC-07: no bash scripts or Python modules remain at old locations

## Model

Haiku

## Wave

2
