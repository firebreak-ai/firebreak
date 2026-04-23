---
id: task-38
type: implementation
wave: 1
covers: [AC-03, AC-04]
files_to_create:
  - assets/fbk-scripts/fbk.py
test_tasks: [task-13]
completion_gate: "task-13 tests pass"
---

## Objective

Create the `fbk.py` dispatcher script that maps 14 command names to Python module paths and dynamically imports and calls each module's `main()` function.

## Context

The dispatcher is the single entry point for all context asset invocations. It resolves its own location via `os.path.realpath(__file__)`, inserts the parent directory into `sys.path[1]`, checks Python version `>= 3.11`, maps command names to module paths, dynamically imports the target module, sets `sys.argv` appropriately, and calls `main()`. Unrecognized commands print available commands to stderr and exit 2.

## Instructions

1. Create `assets/fbk-scripts/fbk.py` with the following:
2. Add `sys.path` setup: `script_dir = os.path.dirname(os.path.realpath(__file__))` then `sys.path.insert(1, script_dir)`
3. Add Python version check: if `sys.version_info < (3, 11)`, print `"Error: Python 3.11+ required (found {sys.version})"` to stderr and `sys.exit(2)`
4. Define `COMMAND_MAP` dict with all 14 entries:
   - `"spec-gate"` → `"fbk.gates.spec"`
   - `"review-gate"` → `"fbk.gates.review"`
   - `"breakdown-gate"` → `"fbk.gates.breakdown"`
   - `"task-reviewer-gate"` → `"fbk.gates.task_reviewer"`
   - `"test-hash-gate"` → `"fbk.gates.test_hash"`
   - `"task-completed"` → `"fbk.hooks.task_completed"`
   - `"dispatch-status"` → `"fbk.hooks.dispatch_status"`
   - `"pipeline"` → `"fbk.pipeline"`
   - `"audit"` → `"fbk.audit"`
   - `"config"` → `"fbk.config"`
   - `"state"` → `"fbk.state"`
   - `"session-logger"` → `"fbk.council.session_logger"`
   - `"session-manager"` → `"fbk.council.session_manager"`
   - `"ralph"` → `"fbk.council.ralph"`
5. If no arguments or unrecognized command: print available commands to stderr, exit 2
6. Import using `importlib.import_module(module_path)`
7. Set `sys.argv = [command_name] + remaining_args` before calling `module.main()`
8. Exit with the return code from `main()` (default 0 if `main()` returns `None`)

## Files to create/modify

- **Create**: `assets/fbk-scripts/fbk.py`

## Test requirements

- task-13: command map contains all 14 commands, every command resolves to importable module, unrecognized command exits 2, Python < 3.11 exits 2

## Acceptance criteria

- AC-03: dispatcher maps all 14 commands to their modules
- AC-04: every command callable via dispatcher without import errors

## Model

Sonnet

## Wave

1
