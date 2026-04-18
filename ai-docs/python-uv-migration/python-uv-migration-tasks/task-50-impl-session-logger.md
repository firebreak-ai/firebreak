---
id: task-50
type: implementation
wave: 1
covers: [AC-02]
files_to_create:
  - assets/fbk-scripts/fbk/council/session_logger.py
test_tasks: [task-36]
completion_gate: "task-36 tests pass"
---

## Objective

Relocate `assets/skills/fbk-council/session-logger.py` to `assets/fbk-scripts/fbk/council/session_logger.py` as an importable module.

## Context

`session-logger.py` (648 lines) is already pure Python with argparse subcommands: `init`, `phase-start`, `phase-end`, `contribution`, `tool-use`, `permission-request`, `outcome`, `self-eval`, `finalize`, `show`. It uses `Path.home() / '.claude' / 'council-logs'` for log storage. The existing `if __name__ == '__main__':` block calls `main()` which is already defined as a function. Module-level constants: `SCHEMA_VERSION = 2`, `LOG_DIR`, `PERMISSIONS_LOG`.

Key functions: `get_log_path(session_id)`, `load_session(session_id)`, `save_session(session_id, data)`, `add_timeline_event(data, event)`, `update_token_summary(data, agent, input_tokens, output_tokens)`, `merge_permissions_log(data)`.

## Instructions

1. Create `assets/fbk-scripts/fbk/council/session_logger.py` by copying `assets/skills/fbk-council/session-logger.py`
2. The `main()` function already exists — verify the `if __name__` block calls it
3. Keep all function signatures, constants, and command handlers identical
4. No changes needed to `LOG_DIR` or `PERMISSIONS_LOG` paths — they use `Path.home()` which is portable
5. Preserve `os.chmod(temp_path, 0o600)` for restrictive permissions

## Files to create/modify

- **Create**: `assets/fbk-scripts/fbk/council/session_logger.py`

## Test requirements

- task-36: conftest.py loads, session-logger importable from `fbk.council.session_logger`

## Acceptance criteria

- AC-02: session-logger.py relocated and importable as `fbk.council.session_logger`

## Model

Haiku

## Wave

1
