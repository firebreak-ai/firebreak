---
id: task-45
type: implementation
wave: 1
covers: [AC-01, AC-08]
files_to_create:
  - assets/fbk-scripts/fbk/gates/breakdown.py
test_tasks: [task-04]
completion_gate: "task-04 tests pass"
---

## Objective

Convert `assets/hooks/fbk-sdl-workflow/breakdown-gate.sh` to `assets/fbk-scripts/fbk/gates/breakdown.py`, extracting the embedded Python heredoc into a proper module.

## Context

`breakdown-gate.sh` (175 lines) has a 23-line bash preamble that builds a JSON map of task file contents, then feeds it to a Python heredoc (lines 24-175). The Python logic implements 8 validation checks: (1) task.json schema validation, (2) AC coverage with test+impl requirement, (3) DAG acyclicity via topological sort, (4) wave ordering, (5) test-before-impl within waves, (6) file reference existence, (7) file count constraint (max 2 without justification), (8) file scope conflicts within same wave. The conversion eliminates the bash preamble by reading task files directly in Python.

The module must expose `validate_breakdown(spec_text, manifest, task_files)` where `manifest` is the parsed `task.json` dict and `task_files` is a dict mapping filename to content string. Return `{"gate": "breakdown", "result": "pass"|"fail", "failures": [...], ...}`.

## Instructions

1. Create `assets/fbk-scripts/fbk/gates/breakdown.py`
2. Port the Python heredoc logic (lines 24-174 of `breakdown-gate.sh`) directly — it's already Python. Key functions to extract as module-level:
   - AC coverage check (spec ACs must be covered by test+impl tasks)
   - DAG acyclicity via `collections.deque` topological sort
   - Wave ordering validation (dependency wave must be strictly less)
   - Test-before-impl ordering within waves
   - File reference existence check (task file names in `task_files` dict)
   - File count constraint (max 2 files without justification text)
   - File scope conflict detection within same wave
   - Test coverage check (code-modifying impl tasks need test tasks)
3. Implement `validate_breakdown(spec_text, manifest, task_files)` that runs all 8 checks. On failure return `{"gate": "breakdown", "result": "fail", "failures": [...]}`. On pass return `{"gate": "breakdown", "result": "pass", "spec_acs": N, "tasks": N, "waves": N}`
4. Implement `main()` with argparse: spec path, tasks directory path. Read task.json from tasks dir, build task_files dict by reading `task-*.md` files. Print JSON result to stdout. Exit 0 on pass, exit 2 on fail (print failures to stderr)
5. Preserve the `category` support from `task.json`: corrective category relaxes AC coverage requirement (test OR impl, not both)

## Files to create/modify

- **Create**: `assets/fbk-scripts/fbk/gates/breakdown.py`

## Test requirements

- task-04: uncovered AC detected, DAG cycle detected, wave ordering violation detected, file scope conflict detected, valid breakdown passes

## Acceptance criteria

- AC-01: breakdown-gate.sh converted to Python module
- AC-08: gate produces correct pass/fail for known inputs

## Model

Sonnet

## Wave

1
