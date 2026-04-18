---
id: task-51
type: implementation
wave: 1
covers: [AC-02]
files_to_create:
  - assets/fbk-scripts/fbk/council/session_manager.py
test_tasks: [task-36]
completion_gate: "task-36 tests pass"
---

## Objective

Relocate `assets/skills/fbk-council/session-manager.py` to `assets/fbk-scripts/fbk/council/session_manager.py` with cross-platform file locking.

## Context

`session-manager.py` (231 lines) manages concurrent council sessions using `fcntl.flock()` for file locking, which is Unix-only. The conversion introduces a platform-conditional locking abstraction per the spec (lines 278-293). The CLI uses `sys.argv` directly (not argparse): commands are `register`, `unregister`, `is-active`, `list`.

Key functions: `register_session(session_id, tier)`, `unregister_session(session_id)`, `is_any_session_active()`, `get_active_sessions()`, `atomic_write_json(file_path, data)`, `read_json_safe(file_path, default)`, `is_process_alive(pid)`.

## Instructions

1. Create `assets/fbk-scripts/fbk/council/session_manager.py` by copying `assets/skills/fbk-council/session-manager.py`
2. Replace the bare `import fcntl` with the platform-conditional locking abstraction from the spec:
   ```python
   import sys as _sys
   if _sys.platform == "win32":
       import msvcrt
       def lock_file(f):
           msvcrt.locking(f.fileno(), msvcrt.LK_LOCK, 1)
       def unlock_file(f):
           msvcrt.locking(f.fileno(), msvcrt.LK_UNLCK, 1)
   else:
       import fcntl
       def lock_file(f):
           fcntl.flock(f, fcntl.LOCK_EX)
       def unlock_file(f):
           fcntl.flock(f, fcntl.LOCK_UN)
   ```
3. Replace `fcntl.flock(f, fcntl.LOCK_EX)` calls with `lock_file(f)` and `fcntl.flock(f, fcntl.LOCK_UN)` with `unlock_file(f)` in `register_session` and `unregister_session`
4. The existing `main()` function uses `sys.argv` directly — keep this pattern (do not convert to argparse)
5. Keep all function signatures identical

## Files to create/modify

- **Create**: `assets/fbk-scripts/fbk/council/session_manager.py`

## Test requirements

- task-36: conftest.py loads, session-manager importable from `fbk.council.session_manager`

## Acceptance criteria

- AC-02: session-manager.py relocated with cross-platform locking

## Model

Haiku

## Wave

1
