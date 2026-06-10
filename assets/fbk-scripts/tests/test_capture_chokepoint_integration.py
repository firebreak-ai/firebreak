"""Real-producer integration tests for fbk.capture.chokepoint.

Drives `fbk.py state transition` through the real dispatch path (subprocess)
to exercise the chokepoint normal-return path: multi-line indented JSON is
re-emitted byte-for-byte, integer exit codes propagate, and one
PIPELINE_COMMAND event is written per invocation.

The fbk.py dispatch wrap (task-35) is absent in the red phase, so the event
assertions fail until that wrap is added.  All tests collect cleanly and the
subprocess-only assertions (exit code, stdout shape) demonstrate the state
engine already works correctly.
"""

import json
import os
import subprocess
import sys
from pathlib import Path

import pytest

try:
    from fbk.capture import chokepoint as _chokepoint_module  # noqa: F401
    _CHOKEPOINT_AVAILABLE = True
except ImportError:
    _CHOKEPOINT_AVAILABLE = False

pytestmark = pytest.mark.skipif(
    not _CHOKEPOINT_AVAILABLE,
    reason="fbk.capture.chokepoint not yet implemented",
)

from tests import capture_fixtures  # noqa: E402 — after guard


FBK_PY = Path(__file__).parent.parent / "fbk.py"

_CAPTURE_DIR = ".fbk-capture"
_EVENTS_FILE = "events.jsonl"


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


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


def _clear_events(project_root):
    """Remove the events log so a later assertion measures only the
    invocation under test. The `state create` setup step runs through the same
    wrapped dispatch and records its own PIPELINE_COMMAND event; clearing the
    log after setup isolates the measured `state transition` call.
    """
    path = _events_path(project_root)
    if os.path.exists(path):
        os.remove(path)


def _run_fbk(args, project_root, state_dir):
    """Run fbk.py with args in project_root, with STATE_DIR set to state_dir.

    Returns a CompletedProcess with text stdout/stderr.
    """
    env = {**os.environ, "STATE_DIR": str(state_dir)}
    return subprocess.run(
        [sys.executable, str(FBK_PY)] + args,
        capture_output=True,
        text=True,
        cwd=str(project_root),
        env=env,
        timeout=15,
    )


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------


class TestRealStateTransitionChokepoint:
    """End-to-end tests driving fbk.py state transition through the chokepoint."""

    def test_real_state_transition_reemits_multiline_json_and_propagates_exit(
        self, tmp_path
    ):
        """state transition to VALIDATING: multi-line JSON re-emitted, exit 0 propagated, one PIPELINE_COMMAND event written."""
        project = capture_fixtures.make_project(
            str(tmp_path), instrumented=True, marked=True
        )
        state_dir = os.path.join(project, ".claude", "automation", "state")
        os.makedirs(state_dir, exist_ok=True)

        # Create the spec state so a valid transition is possible.
        create_result = _run_fbk(
            ["state", "create", "demo-spec"],
            project_root=project,
            state_dir=state_dir,
        )
        assert create_result.returncode == 0, (
            f"state create failed: {create_result.stderr!r}"
        )
        _clear_events(project)

        # Run the valid transition QUEUED -> VALIDATING through the full fbk.py dispatch.
        result = _run_fbk(
            ["state", "transition", "demo-spec", "VALIDATING"],
            project_root=project,
            state_dir=state_dir,
        )

        # The integer exit code 0 propagates — not masked to a SystemExit artifact.
        assert result.returncode == 0, (
            f"expected exit code 0 from successful transition, got {result.returncode}; "
            f"stderr: {result.stderr!r}"
        )

        # The state JSON is printed as multi-line indented output.
        stdout = result.stdout
        lines = stdout.strip().splitlines()
        assert len(lines) > 1, (
            f"expected multi-line indented JSON on stdout, got single line: {stdout!r}"
        )

        # The stdout, once stripped, parses as a single clean JSON object with no
        # stray injector output before or after.
        try:
            state_obj = json.loads(stdout.strip())
        except json.JSONDecodeError as exc:
            pytest.fail(
                f"stdout does not parse as JSON (stray lines from injector?): {exc}; "
                f"stdout={stdout!r}"
            )

        # The parsed state reflects the new current_state.
        assert state_obj.get("current_state") == "VALIDATING", (
            f"expected current_state 'VALIDATING', got {state_obj.get('current_state')!r}"
        )

        # Exactly one PIPELINE_COMMAND event was written for the state command.
        events = _read_event_lines(project)
        pipeline_events = [
            e for e in events if e.get("event_type") == "PIPELINE_COMMAND"
        ]
        assert len(pipeline_events) == 1, (
            f"expected exactly one PIPELINE_COMMAND event, got {len(pipeline_events)}: "
            f"{pipeline_events!r}"
        )

        recorded = pipeline_events[0]
        data = recorded.get("data", {})

        # The recorded command name is "state".
        assert data.get("command_name") == "state", (
            f"expected command_name 'state' in event data, got {data.get('command_name')!r}; "
            f"data={data!r}"
        )

        # The outcome field is present and reflects success.
        assert "outcome" in data, (
            f"expected 'outcome' key in PIPELINE_COMMAND event data; data={data!r}"
        )
        assert data["outcome"] == "pass", (
            f"expected outcome 'pass' for exit code 0, got {data['outcome']!r}"
        )

    def test_real_transition_invalid_propagates_nonzero_and_records(
        self, tmp_path
    ):
        """Invalid transition from QUEUED: exit 1 propagated, one PIPELINE_COMMAND event recorded."""
        project = capture_fixtures.make_project(
            str(tmp_path), instrumented=True, marked=True
        )
        state_dir = os.path.join(project, ".claude", "automation", "state")
        os.makedirs(state_dir, exist_ok=True)

        # Create the spec state (initial state is QUEUED).
        create_result = _run_fbk(
            ["state", "create", "demo-spec"],
            project_root=project,
            state_dir=state_dir,
        )
        assert create_result.returncode == 0, (
            f"state create failed: {create_result.stderr!r}"
        )
        _clear_events(project)

        # Attempt an invalid transition QUEUED -> REVIEWED; should return 1.
        result = _run_fbk(
            ["state", "transition", "demo-spec", "REVIEWED"],
            project_root=project,
            state_dir=state_dir,
        )

        # The non-zero exit code is propagated — not masked.
        assert result.returncode == 1, (
            f"expected exit code 1 from invalid transition, got {result.returncode}; "
            f"stderr: {result.stderr!r}"
        )

        # Exactly one PIPELINE_COMMAND event was recorded for the failed attempt.
        events = _read_event_lines(project)
        pipeline_events = [
            e for e in events if e.get("event_type") == "PIPELINE_COMMAND"
        ]
        assert len(pipeline_events) == 1, (
            f"expected exactly one PIPELINE_COMMAND event for invalid transition, "
            f"got {len(pipeline_events)}: {pipeline_events!r}"
        )

        recorded = pipeline_events[0]
        data = recorded.get("data", {})

        # The recorded command name is "state".
        assert data.get("command_name") == "state", (
            f"expected command_name 'state' in event data, got {data.get('command_name')!r}"
        )

        # The outcome reflects failure.
        assert "outcome" in data, (
            f"expected 'outcome' key in PIPELINE_COMMAND event data; data={data!r}"
        )
        assert data["outcome"] == "fail", (
            f"expected outcome 'fail' for exit code 1, got {data['outcome']!r}"
        )
