"""Integration tests for fbk.capture.chokepoint — the dispatch chokepoint seam.

The chokepoint wraps each module.main() dispatch in fbk.py.  It:
  - saves real stdout, installs an in-memory buffer, calls run_fn inside a try
  - in a finally block: restores real stdout and flushes buffered bytes to it
  - after flushing: writes one PIPELINE_COMMAND event, then re-raises the
    original SystemExit (or returns the normal int result)
  - when the project is not instrumented: calls run_fn() directly, records nothing
  - when capture machinery fails: discards the failure, never suppresses run_fn's
    stdout or exit code

Module is not yet implemented; all four tests skip in the red phase.
"""

import json
import os
import pytest

try:
    from fbk.capture import chokepoint
except ImportError:
    chokepoint = None

from tests import capture_fixtures


pytestmark = pytest.mark.skipif(
    chokepoint is None,
    reason="fbk.capture.chokepoint not yet implemented",
)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

_CAPTURE_DIR = ".fbk-capture"
_EVENTS_FILE = "events.jsonl"


def _events_path(project_root):
    """Return the canonical events.jsonl path for a project root string."""
    return os.path.join(project_root, _CAPTURE_DIR, _EVENTS_FILE)


def _read_event_lines(project_root):
    """Return parsed JSON objects for each non-empty line in events.jsonl."""
    path = _events_path(project_root)
    if not os.path.exists(path):
        return []
    with open(path) as f:
        return [json.loads(line) for line in f if line.strip()]


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------


def test_systemexit_zero_reemits_stdout_records_event_reraises(tmp_path, capsys):
    """SystemExit(0) from run_fn: stdout re-emitted, one PIPELINE_COMMAND recorded, exit 0 re-raised."""
    project = capture_fixtures.make_project(str(tmp_path), instrumented=True, marked=True)

    stub_output = json.dumps({"gate": "stub", "result": "pass"})

    def run_fn():
        print(stub_output)
        raise SystemExit(0)

    with pytest.raises(SystemExit) as exc:
        chokepoint.record_dispatch("stub-gate", [], run_fn, project)

    # The original exit code is preserved.
    assert exc.value.code == 0, (
        f"expected exit code 0 re-raised, got {exc.value.code!r}"
    )

    # The stub's JSON was re-emitted to real stdout (visible via capsys).
    captured = capsys.readouterr()
    assert stub_output in captured.out, (
        f"expected stub JSON in real stdout after re-emission, got: {captured.out!r}"
    )

    # Exactly one PIPELINE_COMMAND event was written to the project's events file.
    events = _read_event_lines(project)
    pipeline_events = [e for e in events if e.get("event_type") == "PIPELINE_COMMAND"]
    assert len(pipeline_events) == 1, (
        f"expected exactly one PIPELINE_COMMAND event, got {len(pipeline_events)}: {pipeline_events!r}"
    )


def test_systemexit_two_preserves_code_and_records_fail(tmp_path, capsys):
    """SystemExit(2) from run_fn: exit 2 preserved, PIPELINE_COMMAND recorded with outcome 'fail' and exit code 2."""
    project = capture_fixtures.make_project(str(tmp_path), instrumented=True, marked=True)

    stub_output = json.dumps({"gate": "stub", "result": "fail"})

    def run_fn():
        print(stub_output)
        raise SystemExit(2)

    with pytest.raises(SystemExit) as exc:
        chokepoint.record_dispatch("stub-gate", [], run_fn, project)

    # Exit code 2 is preserved.
    assert exc.value.code == 2, (
        f"expected exit code 2 re-raised, got {exc.value.code!r}"
    )

    # One PIPELINE_COMMAND event was written.
    events = _read_event_lines(project)
    pipeline_events = [e for e in events if e.get("event_type") == "PIPELINE_COMMAND"]
    assert len(pipeline_events) == 1, (
        f"expected exactly one PIPELINE_COMMAND event, got {len(pipeline_events)}: {pipeline_events!r}"
    )

    recorded = pipeline_events[0]
    data = recorded.get("data", {})

    # The recorded outcome is "fail".
    assert data.get("outcome") == "fail", (
        f"expected outcome 'fail' for exit code 2, got {data.get('outcome')!r}; data={data!r}"
    )

    # The recorded exit code is 2.
    assert data.get("exit_code") == 2, (
        f"expected exit_code 2 in recorded event, got {data.get('exit_code')!r}; data={data!r}"
    )


def test_uninstrumented_calls_runfn_returns_records_nothing(tmp_path, capsys):
    """Uninstrumented project: run_fn is called, its return value is returned, nothing is recorded."""
    # A bare project with no sentinel and no capture.cfg is uninstrumented.
    project = capture_fixtures.make_project(str(tmp_path), instrumented=False)

    stub_output = json.dumps({"gate": "stub", "result": "pass"})
    called = []

    def run_fn():
        called.append(True)
        print(stub_output)
        return 0

    result = chokepoint.record_dispatch("stub-gate", [], run_fn, project)

    # run_fn was called.
    assert called, "expected run_fn to be called in uninstrumented project"

    # The normal return value is passed through.
    assert result == 0, (
        f"expected record_dispatch to return 0 (run_fn's return value), got {result!r}"
    )

    # run_fn's stdout is preserved (not suppressed).
    captured = capsys.readouterr()
    assert stub_output in captured.out, (
        f"expected stub JSON in stdout for uninstrumented project, got: {captured.out!r}"
    )

    # No events file created — nothing recorded.
    assert not os.path.exists(_events_path(project)), (
        "expected no events file created for uninstrumented project"
    )


def test_capture_failure_still_flushes_stdout_and_preserves_exit(
    tmp_path, capsys, monkeypatch
):
    """Capture machinery failure: stub stdout is still flushed to real stdout and exit code is preserved."""
    project = capture_fixtures.make_project(str(tmp_path), instrumented=True, marked=True)

    stub_output = json.dumps({"gate": "stub", "result": "fail"})

    def run_fn():
        print(stub_output)
        raise SystemExit(2)

    # Force the event_writer.write to raise so capture machinery fails.
    from fbk.capture import event_writer

    def _always_raise(*args, **kwargs):
        raise RuntimeError("simulated capture failure")

    monkeypatch.setattr(event_writer, "write", _always_raise)

    with pytest.raises(SystemExit) as exc:
        chokepoint.record_dispatch("stub-gate", [], run_fn, project)

    # Exit code 2 is preserved despite the capture failure.
    assert exc.value.code == 2, (
        f"expected exit code 2 preserved after capture failure, got {exc.value.code!r}"
    )

    # The stub's JSON was still flushed to real stdout — not suppressed.
    captured = capsys.readouterr()
    assert stub_output in captured.out, (
        f"expected stub JSON flushed to real stdout after capture failure, got: {captured.out!r}"
    )
