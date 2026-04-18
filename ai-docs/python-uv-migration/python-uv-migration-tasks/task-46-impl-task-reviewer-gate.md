---
id: task-46
type: implementation
wave: 1
covers: [AC-01, AC-08]
files_to_create:
  - assets/fbk-scripts/fbk/gates/task_reviewer.py
test_tasks: [task-05]
completion_gate: "task-05 tests pass"
---

## Objective

Convert `assets/hooks/fbk-sdl-workflow/task-reviewer-gate.sh` to `assets/fbk-scripts/fbk/gates/task_reviewer.py`, extracting the embedded Python heredoc.

## Context

`task-reviewer-gate.sh` (234 lines) has a bash preamble that builds a task content JSON map (same pattern as breakdown-gate.sh), then feeds it to a Python heredoc (lines 27-219). The Python logic validates individual task files and cross-task constraints. It uses PyYAML for frontmatter parsing. Per AC-09, PyYAML must be import-guarded.

Required validations: (1) required frontmatter fields: `id`, `type`, `wave`, `covers`, `completion_gate`, (2) `files_to_create` or `files_to_modify` must be present, (3) type enum: `test` or `implementation`, (4) AC identifier format `AC-NN`, (5) implementation tasks must have `test_tasks`, (6) `files_to_modify` paths must exist relative to project root, (7) AC coverage (respects category: feature, corrective, testing-infrastructure), (8) file scope conflicts within same wave, (9) `test_tasks` reference validity.

## Instructions

1. Create `assets/fbk-scripts/fbk/gates/task_reviewer.py`
2. Add PyYAML import guard (same pattern as `fbk.config`)
3. Port the `parse_frontmatter(content)` function from the heredoc (lines 63-79)
4. Port `find_project_root(start)` function (lines 41-47)
5. Implement `validate_tasks(spec_path, task_files, project_root=None)` that runs all 9 checks:
   - Per-task: required fields, files_to_create/modify presence, type enum, AC format, impl needs test_tasks, files_to_modify paths exist
   - Cross-task: AC coverage (respects category from task.json manifest), file scope conflicts within same wave, test_tasks reference validity
6. Return `{"gate": "task-reviewer", "result": "pass"|"fail", "tasks": N, "acs_covered": N, "waves": N, "failures": [...]}`
7. Implement `main()` with argparse: spec path, tasks dir, optional project root override. Read task files, run validation, print JSON to stdout. Exit 0 pass, exit 2 fail
8. On pass, log to `fbk.audit.log_event` if importable (wrap in try/except, don't fail if audit unavailable)

## Files to create/modify

- **Create**: `assets/fbk-scripts/fbk/gates/task_reviewer.py`

## Test requirements

- task-05: missing required field detected, invalid type enum, implementation missing test_tasks, file scope conflict, valid task set passes

## Acceptance criteria

- AC-01: task-reviewer-gate.sh converted to Python module
- AC-08: gate produces correct pass/fail for known inputs

## Model

Sonnet

## Wave

1
