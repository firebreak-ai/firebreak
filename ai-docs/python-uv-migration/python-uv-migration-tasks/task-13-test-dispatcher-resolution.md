---
id: task-13
type: test
wave: 1
covers: [AC-03, AC-04]
files_to_create:
  - assets/fbk-scripts/tests/test_dispatcher.py
completion_gate: "tests compile and fail before implementation"
---

## Objective

Create pytest unit tests for `fbk.py` dispatcher command resolution and Python version check.

## Context

The dispatcher `fbk.py` maps 14 command names to module paths (e.g., `"spec-gate"` → `"fbk.gates.spec"`), dynamically imports the target module, and calls its `main()` function. It checks `sys.version_info >= (3, 11)` and exits with code 2 if too old. Unrecognized commands print available commands to stderr and exit 2.

## Instructions

1. Create `assets/fbk-scripts/tests/test_dispatcher.py`
2. The dispatcher `fbk.py` has side effects at module level (sys.path manipulation, version check). To test the command map without triggering entry-point side effects, use `subprocess.run` for behavioral tests and extract the `COMMAND_MAP` dict by parsing the source file or by importing it after the dispatcher exposes `COMMAND_MAP` as a module-level constant (the implementation task must structure the dispatcher so that `COMMAND_MAP` is defined before the `if __name__ == "__main__"` guard). Import `fbk` as a module and access `fbk.COMMAND_MAP` (fbk.py must define the map outside `__main__` for testability).
3. Write a test: assert `COMMAND_MAP` contains all 14 commands listed in the spec: `spec-gate`, `review-gate`, `breakdown-gate`, `task-reviewer-gate`, `test-hash-gate`, `task-completed`, `dispatch-status`, `pipeline`, `audit`, `config`, `state`, `session-logger`, `session-manager`, `ralph`
4. Write a test: for each command in `COMMAND_MAP`, assert that `importlib.import_module(module_path)` succeeds without `ImportError` (this validates AC-04 — all commands callable without import errors). Since modules don't exist yet, this will fail as expected for the completion gate.
5. Write a test: invoke `subprocess.run(["python3", dispatcher_path, "nonexistent-command"])` and assert exit code is 2
6. Write a test: invoke `subprocess.run(["python3", dispatcher_path, "spec-gate", "--help"], env={...PYTHON_VERSION_OVERRIDE...})` or use `unittest.mock.patch("sys.version_info", (3, 10))` to test the version check exits with code 2

## Files to create/modify

- **Create**: `assets/fbk-scripts/tests/test_dispatcher.py`

## Test requirements

| Level | Behavior | Expected assertion |
|-------|----------|--------------------|
| Unit | command map contains all 14 commands | all command names present as keys |
| Unit | every command resolves to importable module | importlib.import_module succeeds for each |
| Unit | unrecognized command exits 2 | SystemExit with code 2 |
| Unit | Python < 3.11 exits 2 | SystemExit with code 2 |
| Integration | stdin passthrough to module | pipe JSON into `python3 fbk.py task-completed`, verify module receives it |

## Acceptance criteria

- AC-03: dispatcher maps all 14 commands to their modules
- AC-04: every command callable via dispatcher without import errors

## Model

Haiku

## Wave

1
