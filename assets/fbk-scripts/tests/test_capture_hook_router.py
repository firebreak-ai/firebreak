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
# Guarded import for finalize_runs — not yet implemented; new tests skip when absent
# ---------------------------------------------------------------------------

try:
    from fbk import finalize as _finalize_module

    _finalize_runs = _finalize_module.finalize_runs
except (ImportError, AttributeError):
    _finalize_module = None
    _finalize_runs = None

_FINALIZE_ABSENT = _finalize_runs is None

_requires_finalize = pytest.mark.skipif(
    _FINALIZE_ABSENT,
    reason="fbk.finalize.finalize_runs not yet implemented",
)

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
    # The router stores the agent identity at data["agent_type"]. The empty
    # identity must be PRESENT-and-EMPTY — the key exists and its value is the
    # empty string — not silently dropped. An absent key would mean the empty
    # identity was lost, which is exactly the failure this test guards against.
    data = event.get("data", {})
    assert "agent_type" in data, (
        f"agent_type key dropped from SubagentStop event; data: {data!r}"
    )
    assert data["agent_type"] == "", (
        f"expected empty agent identity preserved as empty string, got: {data['agent_type']!r}"
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


@pytest.mark.parametrize("hook_event_name", ["UserPromptSubmit", "Notification"])
def test_registered_lifecycle_events_classify_explicitly(tmp_path, hook_event_name):
    """UserPromptSubmit and Notification are registered hook events that classify
    to LIFECYCLE via an explicit map entry — not by falling through to the default.

    These events fire the router (they are registered in settings.json) but carry
    no tool or subagent meaning, so they belong in the lifecycle stream. Locking
    the classification here guards against the explicit entries silently
    disappearing and regressing to the default safety net.
    """
    project = capture_fixtures.make_project(
        str(tmp_path), instrumented=True, marked=True, capture_cfg="standard"
    )

    payload = capture_fixtures.hook_payload(hook_event_name)

    result = run_router(payload, project)

    assert result.returncode == 0, (
        f"router exited {result.returncode}, stderr: {result.stderr!r}"
    )

    events = _read_events(project)
    assert len(events) == 1, f"expected 1 written event, got {len(events)}"
    assert events[0].get("event_type") == "LIFECYCLE", (
        f"{hook_event_name} must classify to LIFECYCLE, "
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


def test_event_source_is_exact_hook_router_literal(tmp_path):
    """The envelope ``source`` is the writer's provenance name; after the subagent
    fix nothing computes metrics from it, so this pin is the regression lock
    against a relabel.
    """
    project = capture_fixtures.make_project(
        str(tmp_path), instrumented=True, marked=True, capture_cfg="standard"
    )

    payload = capture_fixtures.hook_payload("PostToolUse", tool_name="Read")

    result = run_router(payload, project)

    assert result.returncode == 0, (
        f"router exited {result.returncode}, stderr: {result.stderr!r}"
    )

    events = _read_events(project)
    assert len(events) == 1, f"expected 1 written event, got {len(events)}"

    assert events[0]["source"] == "hook_router", (
        f"expected source == 'hook_router' (exact literal), got {events[0].get('source')!r}"
    )


def test_subagent_stop_records_agent_id_and_session_id(tmp_path):
    """A SubagentStop payload carrying agent_id and session_id produces a written
    SUBAGENT_STOP event whose data contains both fields with the original values.

    These are identifier fields used for cross-event correlation; they must NOT
    be stripped by the redaction layer at standard capture level.
    """
    project = capture_fixtures.make_project(
        str(tmp_path), instrumented=True, marked=True, capture_cfg="standard"
    )

    payload = capture_fixtures.hook_payload(
        "SubagentStop",
        agent_type="fbk-implementer",
        extra={
            "agent_id": "agent-abc-123",
            "session_id": "session-xyz-789",
        },
    )

    result = run_router(payload, project)

    assert result.returncode == 0, (
        f"router exited {result.returncode}, stderr: {result.stderr!r}"
    )

    events = _read_events(project)
    subagent_events = [e for e in events if e.get("event_type") == "SUBAGENT_STOP"]
    assert len(subagent_events) >= 1, (
        f"expected a SUBAGENT_STOP event to be written; events: {events!r}"
    )

    data = subagent_events[0].get("data", {})
    assert "agent_id" in data, (
        f"agent_id missing from SUBAGENT_STOP data; data: {data!r}"
    )
    assert data["agent_id"] == "agent-abc-123", (
        f"expected agent_id 'agent-abc-123', got: {data['agent_id']!r}"
    )
    assert "session_id" in data, (
        f"session_id missing from SUBAGENT_STOP data; data: {data!r}"
    )
    assert data["session_id"] == "session-xyz-789", (
        f"expected session_id 'session-xyz-789', got: {data['session_id']!r}"
    )


def test_subagent_stop_identifiers_survive_standard_redaction(tmp_path):
    """agent_id and session_id on a SubagentStop event are NOT stripped at
    the default standard capture level.

    The redaction layer strips a fixed set of free-text keys (e.g. tool_input).
    Identifier fields like agent_id and session_id must pass through untouched
    so events can be correlated after capture.
    """
    project = capture_fixtures.make_project(
        str(tmp_path), instrumented=True, marked=True, capture_cfg="standard"
    )

    payload = capture_fixtures.hook_payload(
        "SubagentStop",
        agent_type="fbk-reviewer",
        extra={
            "agent_id": "agent-redact-check",
            "session_id": "session-redact-check",
        },
    )

    result = run_router(payload, project)

    assert result.returncode == 0, (
        f"router exited {result.returncode}, stderr: {result.stderr!r}"
    )

    events = _read_events(project)
    subagent_events = [e for e in events if e.get("event_type") == "SUBAGENT_STOP"]
    assert len(subagent_events) >= 1, (
        f"expected a SUBAGENT_STOP event at standard level; events: {events!r}"
    )

    data = subagent_events[0].get("data", {})
    # At standard level the redaction layer must leave identifier fields intact.
    assert data.get("agent_id") == "agent-redact-check", (
        f"agent_id was stripped or altered at standard level; data: {data!r}"
    )
    assert data.get("session_id") == "session-redact-check", (
        f"session_id was stripped or altered at standard level; data: {data!r}"
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


# ---------------------------------------------------------------------------
# finalize_runs resilience tests (red phase — skips until finalize_runs is wired in)
#
# Each test is individually guarded with _requires_finalize so the existing
# tests above are never affected.  All three are subprocess-driven: the router
# process calls finalize_runs after its event write; the test observes the
# observable outcomes (exit code, event file, run record file).
# ---------------------------------------------------------------------------


@_requires_finalize
def test_router_exits_0_and_writes_event_after_workflow_finalize(tmp_path, monkeypatch):
    """Router exits 0, writes the TOOL_USE event, and produces the run record after finalize.

    Drives the router with a PostToolUse payload for the Workflow tool against an
    instrumented project.  A closed run directory is planted under a tmp projects
    root; the payload's tool response names that run's id.  After the router runs:
    - exit code must be 0 (finalize must not break the router)
    - the TOOL_USE event must be present in events.jsonl (the write path is intact)
    - the run record must exist at .fbk-capture/runs/<run_id>.json (finalize was
      invoked and did real work, proving the wiring is live)
    """
    projects_root = str(tmp_path / "projects")
    project = capture_fixtures.make_project(
        str(tmp_path), instrumented=True, marked=True, capture_cfg="standard"
    )

    run_id = "run-router-finalize-001"
    capture_fixtures.make_workflow_run(
        projects_root,
        run_id,
        [
            {
                "agent_id": "agent-alpha",
                "first_message": "Run agent alpha.",
                "turns": [],
                "result": {"outcome": "success"},
            }
        ],
    )

    # The tool response text that finalize_runs parses to extract the run id.
    tool_response_text = f"Transcript dir: {projects_root}/proj/sess/subagents/workflows/{run_id}"

    payload = capture_fixtures.hook_payload(
        "PostToolUse",
        tool_name="Workflow",
        extra={"tool_response": tool_response_text},
    )

    monkeypatch.setenv("FBK_PROJECTS_ROOT", projects_root)

    result = run_router(payload, project)

    assert result.returncode == 0, (
        f"router exited {result.returncode} after finalize call; stderr: {result.stderr!r}"
    )

    events = _read_events(project)
    tool_use_events = [e for e in events if e.get("event_type") == "TOOL_USE"]
    assert len(tool_use_events) >= 1, (
        f"expected at least one TOOL_USE event after finalize; events: {events!r}"
    )

    run_record_path = os.path.join(project, ".fbk-capture", "runs", f"{run_id}.json")
    assert os.path.exists(run_record_path), (
        f"expected run record at {run_record_path} after finalize_runs; "
        "this means finalize_runs was not invoked or did not produce a record"
    )


@_requires_finalize
def test_router_exits_0_with_unreadable_transcript_in_run_dir(tmp_path, monkeypatch):
    """Router exits 0 on SessionStart when the run directory contains an unreadable transcript.

    An instrumented project has a closed run directory whose agent transcript file
    is chmod 0o000.  The router must absorb the OS error from finalize_runs and
    still exit 0.
    """
    projects_root = str(tmp_path / "projects")
    project = capture_fixtures.make_project(
        str(tmp_path), instrumented=True, marked=True, capture_cfg="standard"
    )

    run_id = "run-router-unreadable-001"
    run_dir = capture_fixtures.make_workflow_run(
        projects_root,
        run_id,
        [
            {
                "agent_id": "agent-beta",
                "first_message": "Run agent beta.",
                "turns": [],
                "result": {"outcome": "success"},
            }
        ],
    )

    # Make the agent transcript unreadable so finalize_runs hits an OSError.
    unreadable_path = os.path.join(run_dir, "agent-agent-beta.jsonl")
    capture_fixtures.write_unreadable_transcript(unreadable_path)

    payload = capture_fixtures.hook_payload("SessionStart")

    monkeypatch.setenv("FBK_PROJECTS_ROOT", projects_root)

    try:
        result = run_router(payload, project)
    finally:
        # Restore read permission so pytest can clean up tmp_path.
        os.chmod(unreadable_path, stat.S_IRUSR | stat.S_IWUSR)

    assert result.returncode == 0, (
        f"router exited {result.returncode} with unreadable transcript; "
        f"stderr: {result.stderr!r}"
    )


@_requires_finalize
def test_router_exits_0_and_writes_lifecycle_when_finalize_fails_internally(
    tmp_path, monkeypatch
):
    """Router exits 0 and still writes its lifecycle event when finalize_runs fails internally.

    The run directory contains a journal.jsonl that is not valid JSONL, so any
    attempt to parse it will raise.  The router must isolate that failure and:
    - still exit 0
    - still write its own LIFECYCLE event (the event write happens before finalize,
      so finalize failure must not unwrite it)

    This proves finalize failure is quarantined inside the router's outer try/except.
    """
    projects_root = str(tmp_path / "projects")
    project = capture_fixtures.make_project(
        str(tmp_path), instrumented=True, marked=True, capture_cfg="standard"
    )

    run_id = "run-router-malformed-001"
    run_dir = capture_fixtures.make_workflow_run(
        projects_root,
        run_id,
        [
            {
                "agent_id": "agent-gamma",
                "first_message": "Run agent gamma.",
                "turns": [],
                "result": {"outcome": "success"},
            }
        ],
    )

    # Overwrite journal.jsonl with content that is not valid JSONL.
    journal_path = os.path.join(run_dir, "journal.jsonl")
    with open(journal_path, "w") as fh:
        fh.write("this is not valid json\n{also broken\n")

    payload = capture_fixtures.hook_payload("SessionStart")

    monkeypatch.setenv("FBK_PROJECTS_ROOT", projects_root)

    result = run_router(payload, project)

    assert result.returncode == 0, (
        f"router exited {result.returncode} when finalize_runs failed internally; "
        f"stderr: {result.stderr!r}"
    )

    events = _read_events(project)
    lifecycle_events = [e for e in events if e.get("event_type") == "LIFECYCLE"]
    assert len(lifecycle_events) >= 1, (
        f"expected at least one LIFECYCLE event even when finalize fails; "
        f"events: {events!r}"
    )
