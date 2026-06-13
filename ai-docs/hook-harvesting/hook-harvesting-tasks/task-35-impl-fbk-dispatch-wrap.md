---
id: task-35
type: implementation
wave: 5
covers: [AC-03]
files_to_modify:
  - assets/fbk-scripts/fbk.py
test_tasks: [task-18]
completion_gate: "task-18 tests pass"
dependencies: [task-30]
---

# 1 Objective

Wrap `fbk.py`'s single dispatch call in the chokepoint so every dispatched command (gate, hook, state command) records one `PIPELINE_COMMAND` event when the project is instrumented — preserving the existing exit-code contract exactly, including the print-JSON-then-`SystemExit` gate path and the print-multi-line-JSON-then-return-int state path. This is an ORCHESTRATOR task: see the Wiring checklist.

# 2 Context

`fbk.py` is the single entry point. Today lines 40–43 do: `module = importlib.import_module(module_path)` → set `sys.argv` → `result = module.main()` → `sys.exit(result if result is not None else 0)`. The chokepoint (task-30) interposes between `import_module` and the result/exit handling: it wraps the `module.main()` call so the command's stdout is captured and re-emitted (surviving a `SystemExit` raised inside `main()`), then one `PIPELINE_COMMAND` event is recorded, then the original `SystemExit` is re-raised or the int returned — leaving the exit-code contract intact. When the project is not instrumented, the chokepoint calls `main()` and returns directly, recording nothing.

`cwd` is `os.getcwd()` — the project root where fbk is always invoked. The chokepoint signature is `record_dispatch(command_name, args, run_fn, cwd) -> int`.

# 3 Instructions

## Wiring checklist (orchestrator)

- **What to import:** add `from fbk.capture import chokepoint` after the existing `from fbk import COMMAND_MAP` (the `sys.path` bootstrap at the top of `fbk.py` already makes `fbk.capture` importable). Guard the import defensively if desired, but the capture subsystem ships with the package so a plain import is acceptable.
- **What to interpose:** replace `result = module.main()` (line 42) with `result = chokepoint.record_dispatch(command_name, remaining_args, module.main, os.getcwd())`. Pass `module.main` (the bound function, NOT called) as `run_fn`, the already-computed `command_name` and `remaining_args`, and `os.getcwd()` as `cwd`.
- **What to preserve:** keep line 41 (`sys.argv = [command_name] + remaining_args`) BEFORE the wrapped call so `main()` still sees the right argv. Keep line 43 unchanged: `sys.exit(result if result is not None else 0)`. The chokepoint re-raises a `SystemExit` from inside `main()` with the same code (so a gate's `sys.exit(2)` still exits 2) and returns the int for the normal-return path (so the state command's int return still flows to line 43). Do NOT add a second exit path.
- **What to clean up:** nothing extra — the chokepoint owns the stdout redirect and restores it in its own `finally`.
- **Contract preserved:** for instrumented and uninstrumented projects alike, the exit code and stdout of every command are identical to today; the only difference is that an instrumented project also gets one recorded `PIPELINE_COMMAND` event per command.

## Steps

1. Add the `chokepoint` import. Completion: `fbk.py` imports `fbk.capture.chokepoint` without error.
2. Replace the line-42 direct call with the `record_dispatch(...)` wrap as specified. Completion: `result = chokepoint.record_dispatch(command_name, remaining_args, module.main, os.getcwd())` is the dispatch site.
3. Leave the argv setup (line 41) and the final `sys.exit(...)` (line 43) intact. Completion: the exit-code contract is byte-identical — gates that `sys.exit(2)` exit 2; the state command's int return propagates to `sys.exit`.

# 4 Files to create/modify

- Modify `fbk.py` (interpose the chokepoint at the line-42 dispatch site)

# 5 Test requirements

Makes task-18's chokepoint-integration tests pass (`tests/test_capture_chokepoint_integration.py`): a real `fbk.py state transition` re-emits its multi-line indented JSON byte-for-byte, propagates the int exit code (0 on valid, 1 on invalid), and writes exactly one `PIPELINE_COMMAND` event in an instrumented project, with no stray injector output on stdout. The dispatcher count/command update in task-18 (`COMMAND_MAP` → 19 with `report`) is delivered by task-28's registration, not this task — but the existing exit-code dispatcher tests in `tests/test_dispatcher.py` must remain green through this wrap. Do not modify the tests.

# 6 Acceptance criteria

Primary: task-18's chokepoint-integration tests pass and the existing dispatcher exit-code tests stay green. Covers AC-03 (chokepoint normal-return + multi-line-stdout path via the real dispatch wrap).

# 7 Model

Sonnet

# 8 Wave

5
