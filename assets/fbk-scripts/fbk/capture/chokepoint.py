"""Dispatch chokepoint: wraps each run_fn call with stdout capture and event recording.

When the project is instrumented, this module:
  - saves real stdout and installs an in-memory buffer before calling run_fn
  - in a finally block: restores real stdout and flushes buffered bytes to it
  - after flushing: writes exactly one PIPELINE_COMMAND event
  - re-raises the original SystemExit (same code) or returns the int result

When the project is not instrumented, run_fn is called directly — no buffer
installed, nothing recorded.

If any capture step fails (gate, writer, state read, redirect install), the
failure is discarded and run_fn's output and exit code are never suppressed.
"""

import io
import os
import sys
import time
from typing import Callable

from fbk.capture import event_writer, gate_check


def _resolve_spec_stage(cwd: str):
    """Return (spec, stage) from the active state store under cwd, or (None, None).

    Reads state files from <cwd>/.claude/automation/state/ and finds the most
    recently modified one that is not in a terminal state (DONE, FAILED, PARKED).
    Returns (None, None) on any error or when no run is active.
    """
    try:
        state_dir = os.path.join(cwd, ".claude", "automation", "state")
        if not os.path.isdir(state_dir):
            return None, None

        import json

        candidates = []
        for entry in os.listdir(state_dir):
            if not entry.endswith(".json"):
                continue
            path = os.path.join(state_dir, entry)
            if not os.path.isfile(path):
                continue
            try:
                mtime = os.path.getmtime(path)
                candidates.append((mtime, path))
            except OSError:
                continue

        # Try the most recently touched file first.
        candidates.sort(reverse=True)
        for _, path in candidates:
            try:
                with open(path, "r") as fh:
                    state = json.load(fh)
                spec = state.get("spec_name")
                stage = state.get("current_state")
                if spec and stage and stage not in ("DONE", "FAILED"):
                    return spec, stage
            except Exception:
                continue

        return None, None
    except Exception:
        return None, None


def record_dispatch(
    command_name: str,
    args: list[str],
    run_fn: Callable[[], "int | None"],
    cwd: str,
) -> int:
    """Wrap run_fn with stdout capture and PIPELINE_COMMAND event recording.

    Not-instrumented fast path: calls run_fn() directly and propagates its
    return value or any SystemExit it raises — no buffer, no event.

    Instrumented path: installs an in-memory stdout buffer, calls run_fn(),
    restores real stdout in a finally (flushing buffered bytes), then writes
    one PIPELINE_COMMAND event. Re-raises the original SystemExit or returns
    the int result. Any capture failure is discarded; run_fn's output and
    exit code are never suppressed.

    Args:
        command_name: The name of the command being dispatched (e.g. "gate_check").
        args:         The command-line arguments passed to the command.
        run_fn:       A zero-argument callable that runs the command and either
                      returns an int (or None) or raises SystemExit.
        cwd:          The project root directory; used for instrumentation checks
                      and event file path resolution.

    Returns:
        The int return value of run_fn (0 when run_fn returns None), or
        re-raises the SystemExit run_fn raised.
    """
    # Not-instrumented fast path — call through, record nothing.
    try:
        instrumented = gate_check.project_is_instrumented(cwd)
    except Exception:
        instrumented = False

    if not instrumented:
        return run_fn()

    # Instrumented path — try to install a stdout redirect.
    saved = sys.stdout
    buffer = None
    redirect_installed = False

    try:
        buffer = io.StringIO()
        sys.stdout = buffer
        redirect_installed = True
    except Exception:
        # Redirect install failed: run directly with real stdout, record nothing.
        return run_fn()

    # Run run_fn with the buffer in place.
    start = time.monotonic()
    exit_code = None
    original_exit = None
    result = None
    raised = False

    try:
        result = run_fn()
        # Normal return: treat None as 0 for outcome purposes.
        exit_code = result if result is not None else 0
    except SystemExit as se:
        raised = True
        original_exit = se
        code = se.code
        exit_code = code if isinstance(code, int) else (0 if code is None else 1)
    finally:
        # Always restore real stdout and flush the buffer — capture failure
        # must never suppress run_fn's output.
        sys.stdout = saved
        if buffer is not None:
            try:
                saved.write(buffer.getvalue())
            except Exception:
                pass

    duration = time.monotonic() - start

    # Write exactly one PIPELINE_COMMAND event — any failure is discarded.
    try:
        outcome = "pass" if exit_code == 0 else "fail"
        gate_result = buffer.getvalue() if buffer is not None else ""

        data = {
            "command_name": command_name,
            "args": args,
            "outcome": outcome,
            "exit_code": exit_code,
            "duration": duration,
            "output": gate_result,
        }

        try:
            spec, stage = _resolve_spec_stage(cwd)
        except Exception:
            spec, stage = None, None

        try:
            level = gate_check.resolve_capture_level(cwd)
        except Exception:
            level = "standard"

        events_path = os.path.join(cwd, ".fbk-capture", "events.jsonl")
        event_writer.write(
            "PIPELINE_COMMAND",
            "chokepoint",
            data,
            spec,
            stage,
            level,
            events_path,
        )
    except Exception:
        # Capture failure: already flushed stdout, now just propagate exit.
        pass

    # Re-raise the original SystemExit or return the int result.
    if raised:
        raise original_exit
    return exit_code
