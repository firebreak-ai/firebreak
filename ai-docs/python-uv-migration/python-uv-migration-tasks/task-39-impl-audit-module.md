---
id: task-39
type: implementation
wave: 1
covers: [AC-02]
files_to_create:
  - assets/fbk-scripts/fbk/audit.py
test_tasks: [task-09]
completion_gate: "task-09 tests pass"
---

## Objective

Relocate `assets/hooks/fbk-sdl-workflow/audit-logger.py` to `assets/fbk-scripts/fbk/audit.py` as an importable module with a `main()` entry point.

## Context

`audit-logger.py` is already pure Python (73 lines). It exposes `log_event(spec_name, event_type, json_data_str)`, `read_log(spec_name)`, `get_log_path(spec_name)`, and `get_log_dir()`. The existing `if __name__ == "__main__"` block uses argparse with `log` and `read` subcommands. After relocation, callers import functions directly instead of subprocess invocation. The `main()` function replaces the `if __name__` block.

## Instructions

1. Create `assets/fbk-scripts/fbk/audit.py` by copying the content of `assets/hooks/fbk-sdl-workflow/audit-logger.py`
2. Replace the `if __name__ == "__main__":` block with a `main()` function that contains the same argparse logic
3. Keep all function signatures identical: `get_log_dir()`, `get_log_path(spec_name)`, `log_event(spec_name, event_type, json_data_str)`, `read_log(spec_name)`
4. Preserve the `LOG_DIR` env var behavior: `os.environ.get("LOG_DIR", ".claude/automation/logs")`
5. Preserve exit codes: `sys.exit(1)` for invalid JSON in `log_event`, `sys.exit(1)` for missing log in `read_log`, `sys.exit(2)` for unknown command

## Files to create/modify

- **Create**: `assets/fbk-scripts/fbk/audit.py`

## Test requirements

- task-09: `log_event` appends structured JSON line, multiple calls produce independent lines, existing entries preserved, nested JSON preserved, invalid JSON exits with code 1

## Acceptance criteria

- AC-02: audit-logger.py relocated and importable as `fbk.audit`

## Model

Haiku

## Wave

1
