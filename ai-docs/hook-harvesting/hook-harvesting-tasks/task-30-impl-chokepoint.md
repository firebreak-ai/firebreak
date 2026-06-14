---
id: task-30
type: implementation
wave: 4
covers: [AC-03, AC-01, AC-11, AC-15]
files_to_create:
  - assets/fbk-scripts/fbk/capture/chokepoint.py
test_tasks: [task-13]
completion_gate: "task-13 tests pass"
dependencies: [task-27]
---

# 1 Objective

Produce the dispatch chokepoint: a wrapper around a command's `run_fn` that, when the project is instrumented, captures the command's stdout through an in-memory buffer (surviving a `SystemExit` raised inside `run_fn`), flushes it back to the real stdout in a `finally`, then records one `PIPELINE_COMMAND` event before re-raising the `SystemExit` (same code) or returning the int — and that records nothing and changes nothing when the project is not instrumented or when capture machinery fails.

# 2 Context

Gates print a single JSON result to stdout and then raise `SystemExit` from inside `main()`, which short-circuits `with`-block and `atexit` cleanup. The chokepoint cannot rely on `run_fn()` returning normally. The fixed mechanism: save the real stdout, install an in-memory buffer (e.g. `io.StringIO`), call `run_fn()` inside a `try` that catches BOTH a normal return AND `SystemExit`, and in a `finally` restore the real stdout and flush the buffered bytes to it. Only AFTER the buffer is flushed does the wrapper write the event, then re-raise the original `SystemExit` (same exit code) or return the normal int result. When not instrumented, it calls `run_fn()` and returns/propagates directly, recording nothing. If the redirect cannot be installed or any capture step fails, the failure is discarded and the gate's output and exit code are NEVER suppressed.

The event's outcome is `pass` for exit code 0 / a 0-or-None return and `fail` for a non-zero exit code; it records the command name, args, outcome, the exit code, a duration, and a gate-result payload (summarized at standard via the writer's redaction, verbatim at full). The writer (task-27) handles redaction and fail-silence of the write itself, but the chokepoint must also be robust: a writer/capture failure never affects `run_fn`'s output or exit code.

# 3 Instructions

1. Create `fbk/capture/chokepoint.py`. Import `from fbk.capture import event_writer, gate_check` and `io`, `sys`, `time`, `os`.
2. Implement `record_dispatch(command_name: str, args: list[str], run_fn: Callable[[], int | None], cwd: str) -> int`.
3. Not-instrumented fast path: if `not gate_check.project_is_instrumented(cwd)`, call `run_fn()` and return its result (propagating any `SystemExit` it raises) WITHOUT installing the buffer or recording anything. Completion: in a bare project the wrapper returns `run_fn`'s result and creates no events file.
4. Instrumented path: record a start time. Try to install the stdout redirect (`saved = sys.stdout; sys.stdout = io.StringIO()`). If installing the redirect itself fails, fall back to calling `run_fn()` directly (never suppress output). Completion: a redirect-install failure still runs `run_fn` with its real stdout.
5. Call `run_fn()` inside a `try` that captures a normal return (`result`) AND catches `SystemExit as se` (capture `se.code`), recording the outcome/exit code. In a `finally`, restore `sys.stdout = saved` and write the buffered bytes (`saved.write(buffer.getvalue())`) so the command's stdout reaches the real terminal byte-for-byte (including multi-line indented JSON). Completion: the stub's printed JSON reaches real stdout; for the real `state transition` (task-18) the multi-line JSON is re-emitted byte-for-byte.
6. After restoring/flushing stdout, write exactly one `PIPELINE_COMMAND` event via `event_writer.write("PIPELINE_COMMAND", "chokepoint", <data>, spec, stage, level, <cwd>/.fbk-capture/events.jsonl)`. Resolve the level via `gate_check.resolve_capture_level(cwd)`; resolve spec/stage best-effort from the state store under `cwd` (None when no run active). The `data` carries `command_name`, `args`, `outcome` (`pass`/`fail`), `exit_code`, `duration`, and the gate-result payload (the captured stdout summary). Wrap the event write so a capture failure is discarded. Completion: exactly one `PIPELINE_COMMAND` event is written recording the command name and outcome; on `SystemExit(2)` the recorded outcome is `fail` and exit code 2.
7. After writing the event, RE-RAISE the original `SystemExit` with the same code (when `run_fn` raised one) or RETURN the int result (0 when None). Completion: `SystemExit(0)` re-raised with code 0; `SystemExit(2)` re-raised with code 2; a normal int return propagates unchanged.
8. Fail-silence under the seam: if any capture step (gate, writer, state read) raises, swallow it — the command's stdout must already be flushed and its exit code/return preserved. Completion: a forced capture-machinery failure still flushes the stub's JSON to stdout and preserves exit code 2.

# 4 Files to create/modify

- Create `fbk/capture/chokepoint.py`

# 5 Test requirements

Makes task-13 (`tests/test_capture_chokepoint.py`) pass: `SystemExit(0)` → stdout re-emitted, one `PIPELINE_COMMAND` event, exit 0 re-raised; `SystemExit(2)` → exit 2 preserved, outcome `fail` recorded; uninstrumented → run_fn returned, nothing recorded; capture failure → stdout flushed, exit code preserved. (The real-producer multi-line path is task-18, wired by the fbk.py wrap in task-35.)

# 6 Acceptance criteria

Primary: task-13's tests pass. Covers AC-03 (stdout-and-exit seam + outcome capture), AC-01 (gated chokepoint), AC-11 (fail-silent under the seam), AC-15 (chokepoint events join the router's in one stream).

# 7 Model

Sonnet

# 8 Wave

4
