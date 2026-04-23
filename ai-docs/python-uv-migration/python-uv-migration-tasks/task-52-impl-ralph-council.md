---
id: task-52
type: implementation
wave: 1
covers: [AC-02]
files_to_create:
  - assets/fbk-scripts/fbk/council/ralph.py
test_tasks: [task-36]
completion_gate: "task-36 tests pass"
---

## Objective

Relocate `assets/skills/fbk-council/ralph-council.py` to `assets/fbk-scripts/fbk/council/ralph.py` as an importable module.

## Context

`ralph-council.py` (281 lines) provides Ralph + Council integration helper commands: `status`, `abort`, `pause`, `resume`, `clean`, `stuck`. It uses `Path.home() / '.claude'` for state file paths. The `main()` function already exists and uses argparse with subcommands. No code changes needed beyond the relocation.

Key functions: `read_json_safe(file_path, default)`, `write_json_safe(file_path, data)`, `is_signal_active(file_path)`, and command handlers `cmd_status`, `cmd_abort`, `cmd_pause`, `cmd_resume`, `cmd_clean`, `cmd_stuck`.

## Instructions

1. Create `assets/fbk-scripts/fbk/council/ralph.py` by copying `assets/skills/fbk-council/ralph-council.py`
2. The `main()` function already exists — verify the `if __name__` block calls it
3. Keep all function signatures, constants, and paths identical
4. No code changes needed — this is a pure relocation

## Files to create/modify

- **Create**: `assets/fbk-scripts/fbk/council/ralph.py`

## Test requirements

- task-36: conftest.py loads, ralph importable from `fbk.council.ralph`

## Acceptance criteria

- AC-02: ralph-council.py relocated and importable as `fbk.council.ralph`

## Model

Haiku

## Wave

1
