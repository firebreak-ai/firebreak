---
id: task-13
type: test
wave: 4
covers: [AC-03, AC-01, AC-11]
files_to_create:
  - assets/fbk-scripts/tests/test_capture_chokepoint.py
completion_gate: "tests compile and fail before implementation"
---

# Objective

Write the integration tests for the dispatch chokepoint at the stub level: it re-emits a stub `run_fn`'s buffered stdout to the real stdout and re-raises `SystemExit` with the same code while recording one `PIPELINE_COMMAND` event; preserves exit code 2 with outcome `fail`; records nothing in an uninstrumented project; and never suppresses `run_fn`'s output or exit code when capture machinery fails.

# Context

The chokepoint wraps the single `module.main()` dispatch in `fbk.py`. Gates print a single JSON result to stdout then raise `SystemExit` from inside `main()`, which short-circuits normal cleanup. The fixed mechanism: save the real stdout, install an in-memory buffer, call `run_fn()` inside a `try` that catches both a normal return and `SystemExit`, and in a `finally` block restore the real stdout and flush the buffered bytes to it. Only after the buffer is flushed does the wrapper write the event, then re-raise the original `SystemExit` (or return the normal result) with the same exit code. When the project is not instrumented, the wrapper calls `run_fn()` and returns directly, recording nothing. If the redirect cannot be installed or any capture step fails, the failure is discarded and the gate's output and exit code are never suppressed.

This task exercises the chokepoint directly against a stub `run_fn` (the real `fbk.py state transition` normal-return path is a separate Wave-4 task). Import `from fbk.capture import chokepoint` inside `try/except ImportError` with a module-level skipif. Use `tmp_path` for the project, `capsys` to capture the re-emitted stdout, `pytest.raises(SystemExit)` to catch the re-raise. Build the project with `make_project`.

Signature to call verbatim: `chokepoint.record_dispatch(command_name, args, run_fn, cwd) -> int`, where `cwd` is the project root.

# Instructions

1. Create `tests/test_capture_chokepoint.py`; import `chokepoint` inside `try/except ImportError`; module-level skipif.
2. `test_systemexit_zero_reemits_stdout_records_event_reraises`: define a stub `run_fn` that does `print(json.dumps({"gate": "stub", "result": "pass"}))` then `raise SystemExit(0)`. In an instrumented project, call `record_dispatch("stub-gate", [], run_fn, str(project))` inside `pytest.raises(SystemExit) as exc`; assert `exc.value.code == 0`; assert `capsys.readouterr().out` contains the stub's JSON (re-emitted to real stdout); assert exactly one `PIPELINE_COMMAND` event was written to the project's events file.
3. `test_systemexit_two_preserves_code_and_records_fail`: stub `run_fn` prints JSON then `raise SystemExit(2)`; call inside `pytest.raises(SystemExit)`; assert `exc.value.code == 2`; assert the recorded `PIPELINE_COMMAND` event's outcome is `fail` and its recorded exit code is 2 (read the event line and assert the fields).
4. `test_uninstrumented_calls_runfn_returns_records_nothing`: bare project (uninstrumented); stub `run_fn` that returns int `0` (normal return, no SystemExit); call `record_dispatch(...)`; assert it returns `0`, the stub's stdout (if any) is preserved, and NO events file is created (nothing recorded).
5. `test_capture_failure_still_flushes_stdout_and_preserves_exit`: instrumented project, but force a capture-machinery failure inside the wrapper (e.g. monkeypatch `event_writer.write` or the events path to raise/be unwritable); stub `run_fn` prints JSON and raises `SystemExit(2)`; call inside `pytest.raises(SystemExit)`; assert `exc.value.code == 2` AND the stub's JSON still reached real stdout (`capsys` out contains it) — the capture failure is discarded and never suppresses the gate's output or exit code.

# Files to create/modify

- `tests/test_capture_chokepoint.py`

# Test requirements

- `test_systemexit_zero_reemits_stdout_records_event_reraises` (integration): SystemExit(0) → stdout re-emitted, one PIPELINE_COMMAND event, exit 0 re-raised.
- `test_systemexit_two_preserves_code_and_records_fail` (integration): SystemExit(2) → exit 2 preserved, outcome `fail` recorded.
- `test_uninstrumented_calls_runfn_returns_records_nothing` (integration): uninstrumented → run_fn returned, nothing recorded.
- `test_capture_failure_still_flushes_stdout_and_preserves_exit` (integration): capture failure → stdout flushed, exit code preserved.

# Acceptance criteria

AC-03 (stdout-and-exit seam + outcome capture), AC-01 (gated chokepoint), AC-11 (fail-silent under the seam). Gate: tests compile and fail before implementation.

# Model

Sonnet — stdout-redirect-and-exit seam needs careful capsys/SystemExit handling.

# Wave

4
