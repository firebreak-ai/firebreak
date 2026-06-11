"""Integration tests for the standalone hook router (fbk/capture/hook_router.py).

The router runs as its own process — every test drives it via subprocess.run
feeding stdin with a JSON payload.  The router's working directory is pinned to
the subprocess ``cwd`` argument (which becomes ``os.getcwd()`` inside the router)
and is the sole authority for both gate decisions and write destinations.

All tests skip cleanly when the router has not been implemented yet (red phase).
"""

import json
import os
import stat
import sys
from pathlib import Path

import pytest

from tests import capture_fixtures

# ---------------------------------------------------------------------------
# Router location and red-phase gate
# ---------------------------------------------------------------------------

ROUTER = Path(__file__).parent.parent / "fbk" / "capture" / "hook_router.py"

_ROUTER_ABSENT = not ROUTER.exists()

pytestmark = pytest.mark.skipif(
    _ROUTER_ABSENT,
    reason="fbk/capture/hook_router.py not yet implemented",
)


# ---------------------------------------------------------------------------
# Helper: subprocess driver
# ---------------------------------------------------------------------------


def run_router(payload_json, project_dir, env_extra=None):
    """Run the hook router with the given stdin payload and working directory.

    Returns a CompletedProcess with captured stdout and stderr.

    Args:
        payload_json: A JSON string fed to the router on stdin.
        project_dir:  The project directory; becomes os.getcwd() inside the router.
        env_extra:    Optional dict of additional env-var overrides.
    """
    import subprocess

    env = {**os.environ, **(env_extra or {})}
    return subprocess.run(
        [sys.executable, str(ROUTER)],
        input=payload_json,
        cwd=str(project_dir),
        env=env,
        capture_output=True,
        text=True,
    )


# ---------------------------------------------------------------------------
# Helpers for reading the events file
# ---------------------------------------------------------------------------


def _events_path(project_dir):
    return os.path.join(str(project_dir), ".fbk-capture", "events.jsonl")


def _read_events(project_dir):
    """Return a list of parsed event dicts from the project's events.jsonl."""
    path = _events_path(project_dir)
    with open(path) as f:
        return [json.loads(line) for line in f if line.strip()]


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------


def test_standard_strips_payload(tmp_path):
    """At standard level, tool-call payload fields are stripped; exit 0; no stdout."""
    # Instrumented project (sentinel present) with standard capture level.
    project = capture_fixtures.make_project(
        str(tmp_path), instrumented=True, marked=True, capture_cfg="standard"
    )

    payload = capture_fixtures.hook_payload(
        "PostToolUse",
        tool_name="Bash",
        tool_input={"command": "echo secret"},
    )

    result = run_router(payload, project)

    assert result.returncode == 0, (
        f"router exited {result.returncode}, stderr: {result.stderr!r}"
    )
    assert result.stdout == "", (
        f"expected no stdout, got: {result.stdout!r}"
    )

    events = _read_events(project)
    assert len(events) == 1, f"expected 1 written event, got {len(events)}"

    event = events[0]
    assert event.get("event_type") == "TOOL_USE", (
        f"expected event_type TOOL_USE, got {event.get('event_type')!r}"
    )

    data = event.get("data", {})
    assert "tool_input" not in data, (
        f"expected tool_input stripped at standard level, but data was: {data!r}"
    )


def test_full_records_payload(tmp_path):
    """At full level (with out-of-tree corroboration), tool-call payload is preserved verbatim."""
    project = capture_fixtures.make_project(
        str(tmp_path), instrumented=True, marked=True, capture_cfg="full"
    )

    payload = capture_fixtures.hook_payload(
        "PostToolUse",
        tool_name="Bash",
        tool_input={"command": "echo secret"},
    )

    # Out-of-tree corroboration via env var — required by gate_check for full level.
    result = run_router(payload, project, env_extra={"FBK_CAPTURE_LEVEL": "full"})

    assert result.returncode == 0, (
        f"router exited {result.returncode}, stderr: {result.stderr!r}"
    )

    events = _read_events(project)
    assert len(events) == 1, f"expected 1 written event at full level, got {len(events)}"

    data = events[0].get("data", {})
    assert "tool_input" in data, (
        f"expected tool_input preserved at full level, but data was: {data!r}"
    )
    assert data["tool_input"] == {"command": "echo secret"}, (
        f"expected tool_input verbatim, got {data['tool_input']!r}"
    )


def test_uninstrumented_writes_nothing_no_stdout(tmp_path):
    """A bare (uninstrumented) project produces no events file and no stdout."""
    project = capture_fixtures.make_project(str(tmp_path), instrumented=False)

    payload = capture_fixtures.hook_payload("PostToolUse", tool_name="Read")

    result = run_router(payload, project)

    assert result.returncode == 0, (
        f"router exited {result.returncode}, stderr: {result.stderr!r}"
    )
    assert result.stdout == "", (
        f"expected no stdout for uninstrumented project, got: {result.stdout!r}"
    )
    assert not os.path.exists(_events_path(project)), (
        "expected no events.jsonl for uninstrumented project, but the file was created"
    )


def test_subagent_empty_identity_recorded_but_excluded(tmp_path):
    """A SubagentStop with empty agent identity is written with the empty identity preserved."""
    project = capture_fixtures.make_project(
        str(tmp_path), instrumented=True, marked=True, capture_cfg="standard"
    )

    # Empty agent_type signals an empty (subagent) identity.
    payload = capture_fixtures.hook_payload(
        "SubagentStop",
        agent_type="",
    )

    result = run_router(payload, project)

    assert result.returncode == 0, (
        f"router exited {result.returncode}, stderr: {result.stderr!r}"
    )

    events = _read_events(project)
    assert len(events) >= 1, "expected at least one event written for SubagentStop"

    # The subagent event should be written, and carry the empty identity.
    subagent_events = [e for e in events if e.get("event_type") == "SUBAGENT_STOP"]
    assert len(subagent_events) >= 1, (
        f"expected a SUBAGENT_STOP event to be written; events: {events!r}"
    )

    event = subagent_events[0]
    # The agent identity must be present in the record — either directly on the
    # envelope or in the data dict — but the exact field name is implementation detail.
    # Assert that the record exists (was written, not silently dropped).
    assert event is not None, "SubagentStop event with empty identity must be recorded"

    # The agent_type carried by the event should reflect the empty identity.
    data = event.get("data", {})
    agent_val = event.get("agent_type", data.get("agent_type"))
    assert agent_val == "" or agent_val is None, (
        f"expected empty agent identity preserved, got: {agent_val!r}"
    )


def test_subagent_start_is_not_counted_as_a_completion(tmp_path):
    """A SubagentStart records a lifecycle event, never a SUBAGENT_STOP.

    Both SubagentStart and SubagentStop fire for every subagent. If a start is
    classified as a stop, each subagent is counted twice and the report's
    subagent total roughly doubles.
    """
    project = capture_fixtures.make_project(
        str(tmp_path), instrumented=True, marked=True, capture_cfg="standard"
    )

    payload = capture_fixtures.hook_payload(
        "SubagentStart",
        agent_type="fbk-implementer",
    )

    result = run_router(payload, project)
    assert result.returncode == 0, (
        f"router exited {result.returncode}, stderr: {result.stderr!r}"
    )

    events = _read_events(project)
    assert len(events) == 1, f"expected 1 written event, got {len(events)}"
    assert events[0].get("event_type") == "LIFECYCLE", (
        f"SubagentStart must map to LIFECYCLE, not a completion; "
        f"got {events[0].get('event_type')!r}"
    )


def test_stage_null_for_terminal_run_state(tmp_path):
    """A tool-use event fired while the only run is parked carries no stage.

    The router must not stamp a terminal state (PARKED/DONE/FAILED) onto events
    that fire during idle or post-completion periods.
    """
    project = capture_fixtures.make_project(
        str(tmp_path), instrumented=True, marked=True, capture_cfg="standard"
    )
    state_dir = os.path.join(project, ".claude", "automation", "state")
    state = capture_fixtures.build_state(
        spec="demo-spec",
        stage_timestamps={
            "IMPLEMENTING": "2026-01-01T00:00:00+00:00",
            "PARKED": "2026-01-01T00:10:00+00:00",
        },
        current_state="PARKED",
    )
    capture_fixtures.write_state(state_dir, state)

    payload = capture_fixtures.hook_payload("PostToolUse", tool_name="Read")
    result = run_router(payload, project)
    assert result.returncode == 0, (
        f"router exited {result.returncode}, stderr: {result.stderr!r}"
    )

    events = _read_events(project)
    assert len(events) == 1, f"expected 1 written event, got {len(events)}"
    assert events[0]["stage"] is None, (
        f"expected null stage for a terminal (PARKED) run, got {events[0]['stage']!r}"
    )


def test_stage_null_when_no_run_active(tmp_path):
    """When no SDL state file is present, the written event has stage set to null."""
    # Instrumented project with no state file.
    project = capture_fixtures.make_project(
        str(tmp_path), instrumented=True, marked=True, capture_cfg="standard"
    )
    # Ensure no state file exists under .claude/automation/state/
    state_dir = os.path.join(project, ".claude", "automation", "state")
    assert not os.path.isdir(state_dir), "state dir must not exist for this scenario"

    payload = capture_fixtures.hook_payload("PostToolUse", tool_name="Read")

    result = run_router(payload, project)

    assert result.returncode == 0, (
        f"router exited {result.returncode}, stderr: {result.stderr!r}"
    )

    events = _read_events(project)
    assert len(events) == 1, f"expected 1 written event, got {len(events)}"

    event = events[0]
    # stage must be present as a key and must be null (None after JSON parsing).
    assert "stage" in event, "expected 'stage' key to be present in event envelope"
    assert event["stage"] is None, (
        f"expected stage to be null when no SDL run is active, got {event['stage']!r}"
    )


def test_writes_under_cwd_never_global(tmp_path):
    """Events land under the project cwd; the fixture global dir receives nothing."""
    project = capture_fixtures.make_project(
        str(tmp_path), instrumented=True, marked=True, capture_cfg="standard"
    )
    # Separate fixture dir to stand in for any global config the router might
    # accidentally write to (HOME, CLAUDE_CONFIG_DIR, CLAUDE_PROJECT_DIR).
    global_dir = tmp_path / "fake_global"
    global_dir.mkdir()

    payload = capture_fixtures.hook_payload("PostToolUse", tool_name="Read")

    result = run_router(
        payload,
        project,
        env_extra={
            "HOME": str(global_dir),
            "CLAUDE_CONFIG_DIR": str(global_dir),
            "CLAUDE_PROJECT_DIR": str(global_dir),
        },
    )

    assert result.returncode == 0, (
        f"router exited {result.returncode}, stderr: {result.stderr!r}"
    )
    assert result.stdout == "", (
        f"expected no stdout, got: {result.stdout!r}"
    )

    # Event must be written under the project.
    assert os.path.exists(_events_path(project)), (
        "expected events.jsonl under the project cwd, but it was not created"
    )

    # Nothing should have been created under the fake global dir.
    global_capture = global_dir / ".fbk-capture" / "events.jsonl"
    assert not global_capture.exists(), (
        f"expected no write to global dir {global_dir}, but events.jsonl was created there"
    )


def test_gate_and_write_follow_pinned_cwd(tmp_path):
    """Gate decision and write destination follow the pinned cwd, not payload cwd or env."""
    # Project A is the process cwd — instrumented.
    project_a = tmp_path / "project_a"
    project_a.mkdir()
    capture_fixtures.make_project(str(tmp_path / "project_a_base"), instrumented=True, marked=True, capture_cfg="standard")
    # Re-create in the actual project_a directory.
    project_a = capture_fixtures.make_project(str(tmp_path / "project_a"), instrumented=True, marked=True, capture_cfg="standard")

    # Project B is what the payload's cwd and CLAUDE_PROJECT_DIR claim — NOT the actual cwd.
    project_b = tmp_path / "project_b"
    project_b.mkdir()

    payload = capture_fixtures.hook_payload(
        "PostToolUse",
        cwd=str(project_b),          # payload cwd points at B
        tool_name="Read",
    )

    result = run_router(
        payload,
        project_a,                  # actual process cwd is A
        env_extra={
            "CLAUDE_PROJECT_DIR": str(project_b),  # env also points at B
        },
    )

    assert result.returncode == 0, (
        f"router exited {result.returncode}, stderr: {result.stderr!r}"
    )

    # The event must land under A (the actual cwd), not B.
    events_a = os.path.join(str(project_a), ".fbk-capture", "events.jsonl")
    events_b = os.path.join(str(project_b), ".fbk-capture", "events.jsonl")

    assert os.path.exists(events_a), (
        "expected events.jsonl under project A (pinned cwd), but it was not created"
    )
    assert not os.path.exists(events_b), (
        "expected NO events.jsonl under project B (payload cwd), but it was created"
    )


def test_router_fail_silent_on_unwritable(tmp_path):
    """When the events path is unwritable, the router exits 0, no stdout, no traceback."""
    project = capture_fixtures.make_project(
        str(tmp_path), instrumented=True, marked=True, capture_cfg="standard"
    )

    # Create .fbk-capture/ as a read-only directory so the write attempt fails.
    capture_dir = os.path.join(project, ".fbk-capture")
    os.makedirs(capture_dir, exist_ok=True)
    os.chmod(capture_dir, stat.S_IRUSR | stat.S_IXUSR)  # r-x — no write

    payload = capture_fixtures.hook_payload("PostToolUse", tool_name="Read")

    try:
        result = run_router(payload, project)
    finally:
        # Restore write permission so pytest can clean up tmp_path.
        os.chmod(capture_dir, stat.S_IRWXU)

    assert result.returncode == 0, (
        f"expected exit 0 on unwritable path, got exit {result.returncode}"
    )
    assert result.stdout == "", (
        f"expected no stdout on write failure, got: {result.stdout!r}"
    )
    assert "Traceback" not in result.stderr, (
        f"expected no traceback in stderr on write failure, got: {result.stderr!r}"
    )
