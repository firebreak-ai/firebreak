"""Shared fixture builders for metrics-plane tests.

Each function is a pure builder: it takes a base directory (or no directory for
in-memory objects) and returns either a dict / string or a written-file path.
No pytest fixtures here — import this module by name from test files:

    from tests import capture_fixtures
"""

import json
import os
import stat
import subprocess
import sys

# ---------------------------------------------------------------------------
# Event envelope helpers
# ---------------------------------------------------------------------------

_FIXED_TIMESTAMP = "2026-01-01T00:00:00+00:00"

# The six event types the metrics plane recognises.
EVENT_TYPES = {
    "PIPELINE_COMMAND",
    "VERIFICATION_RESULT",
    "CODE_REVIEW_ROUNDS",
    "TOOL_USE",
    "SUBAGENT_STOP",
    "LIFECYCLE",
}


def build_event(
    event_type,
    source,
    spec,
    stage,
    capture_level="standard",
    data=None,
    timestamp=None,
):
    """Return a dict with all eight event-envelope fields.

    schema_version is always "1.0".  data defaults to {}.  timestamp defaults
    to a fixed ISO-8601 string so tests that compare timestamps are stable.
    """
    return {
        "schema_version": "1.0",
        "event_type": event_type,
        "timestamp": timestamp if timestamp is not None else _FIXED_TIMESTAMP,
        "spec": spec,
        "stage": stage,
        "source": source,
        "capture_level": capture_level,
        "data": data if data is not None else {},
    }


def write_events(path, events):
    """Write each event dict as one JSON line to path, creating parent dirs."""
    os.makedirs(os.path.dirname(os.path.abspath(path)), exist_ok=True)
    with open(path, "w") as f:
        for ev in events:
            f.write(json.dumps(ev) + "\n")


# ---------------------------------------------------------------------------
# State file helpers
# ---------------------------------------------------------------------------


def build_state(
    spec,
    stage_timestamps,
    error_history=None,
    parked_info=None,
    current_state=None,
):
    """Return a state dict matching the shape fbk/state.py writes.

    current_state defaults to the last key in stage_timestamps.
    error_history defaults to [].  parked_info defaults to {}.
    """
    last_stage = list(stage_timestamps.keys())[-1] if stage_timestamps else "QUEUED"
    return {
        "spec_name": spec,
        "current_state": current_state if current_state is not None else last_stage,
        "stage_timestamps": stage_timestamps,
        "agent_ids": [],
        "verification_results": {},
        "error_history": error_history if error_history is not None else [],
        "parked_info": parked_info if parked_info is not None else {},
    }


def write_state(state_dir, state):
    """Write <state_dir>/<spec_name>.json as indented JSON; return the path."""
    os.makedirs(state_dir, exist_ok=True)
    path = os.path.join(state_dir, f"{state['spec_name']}.json")
    with open(path, "w") as f:
        json.dump(state, f, indent=2)
    return path


# ---------------------------------------------------------------------------
# Transcript helpers
# ---------------------------------------------------------------------------


def build_transcript(turns):
    """Return a list of assistant JSONL record dicts from a list of turn dicts.

    Each turn dict has keys:
        timestamp (str ISO-8601)
        model     (str)
        input_tokens  (int)
        output_tokens (int)
        tools     (list[str])   — tool names used in the turn
        sidechain (bool)

    The returned records match the Claude Code session-transcript shape that
    the harvester reads:
        type = "assistant"
        message.usage  — input_tokens / output_tokens /
                         cache_read_input_tokens / cache_creation_input_tokens
        message.model
        message.content[] — tool_use blocks (one per name in tools)
        timestamp
        isSidechain
    """
    records = []
    for turn in turns:
        content = []
        for tool_name in turn.get("tools", []):
            content.append(
                {
                    "type": "tool_use",
                    "id": f"tool_{tool_name}",
                    "name": tool_name,
                    "input": {},
                }
            )
        record = {
            "type": "assistant",
            "timestamp": turn["timestamp"],
            "isSidechain": turn.get("sidechain", False),
            "message": {
                "model": turn["model"],
                "usage": {
                    "input_tokens": turn["input_tokens"],
                    "output_tokens": turn["output_tokens"],
                    "cache_read_input_tokens": 0,
                    "cache_creation_input_tokens": 0,
                },
                "content": content,
            },
        }
        records.append(record)
    return records


def write_transcript(path, turns):
    """Write a JSONL transcript to path; return the path."""
    os.makedirs(os.path.dirname(os.path.abspath(path)), exist_ok=True)
    records = build_transcript(turns)
    with open(path, "w") as f:
        for record in records:
            f.write(json.dumps(record) + "\n")
    return path


def write_unreadable_transcript(path):
    """Create a file then chmod it to 0o000 so opening it raises OSError.

    Returns the path.  On platforms where chmod is a no-op the file still
    exists but is readable; callers that need the unavailable path should
    also accept a path that simply does not exist (see the companion helper
    nonexistent_transcript_path).
    """
    os.makedirs(os.path.dirname(os.path.abspath(path)), exist_ok=True)
    with open(path, "w") as f:
        f.write("")
    os.chmod(path, 0o000)
    return path


def nonexistent_transcript_path(base_dir, name="missing.jsonl"):
    """Return a path under base_dir that is guaranteed not to exist."""
    return os.path.join(base_dir, name)


# ---------------------------------------------------------------------------
# Project tree helpers
# ---------------------------------------------------------------------------

_SENTINEL_REL = ".claude/automation/.fbk-managed"
_AUTOMATION_REL = ".claude/automation"
_CAPTURE_CFG_REL = ".fbk-capture/capture.cfg"


def make_project(base, instrumented=True, marked=False, capture_cfg=None):
    """Build a temporary project tree under base; return the project root path.

    instrumented — when True, creates .claude/automation/
    marked       — when True (requires instrumented), also creates the sentinel
                   .claude/automation/.fbk-managed
    capture_cfg  — when set to a level string, writes
                   .fbk-capture/capture.cfg with capture_level=<level>
    """
    root = os.path.join(base, "project")
    os.makedirs(root, exist_ok=True)

    if instrumented:
        automation_dir = os.path.join(root, _AUTOMATION_REL)
        os.makedirs(automation_dir, exist_ok=True)

        if marked:
            sentinel = os.path.join(root, _SENTINEL_REL)
            with open(sentinel, "w") as f:
                f.write("")

    if capture_cfg is not None:
        cfg_path = os.path.join(root, _CAPTURE_CFG_REL)
        os.makedirs(os.path.dirname(cfg_path), exist_ok=True)
        with open(cfg_path, "w") as f:
            f.write(f"capture_level={capture_cfg}\n")

    return root


# ---------------------------------------------------------------------------
# Router stdin payload helper
# ---------------------------------------------------------------------------


def hook_payload(
    hook_event_name,
    cwd=None,
    tool_name=None,
    tool_input=None,
    agent_type=None,
    extra=None,
):
    """Return a JSON string suitable to feed the hook router on stdin.

    Carries hook_event_name plus any supplied optional fields.
    """
    payload = {"hook_event_name": hook_event_name}
    if cwd is not None:
        payload["cwd"] = cwd
    if tool_name is not None:
        payload["tool_name"] = tool_name
    if tool_input is not None:
        payload["tool_input"] = tool_input
    if agent_type is not None:
        payload["agent_type"] = agent_type
    if extra:
        payload.update(extra)
    return json.dumps(payload)


# ---------------------------------------------------------------------------
# Real-producer drivers
# ---------------------------------------------------------------------------

FBK_PY = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "fbk.py")

# Source of truth for a gate-passing spec is _make_minimal_spec() in
# tests/test_gates_spec.py — the header plus _MINIMAL_VALID_SECTIONS.
MINIMAL_VALID_SPEC_MD = """\
# Feature Specification

## Problem
Describes the issue or gap being addressed.

## Goals
- Primary objective of the feature

## User-facing behavior
Describes how end users interact with the feature.

## Technical approach
Details the implementation strategy.

## Testing strategy
- AC-01: Test criterion 1

## Documentation impact
Expected changes to user documentation.

## Acceptance criteria
- AC-01: Feature works as specified

## Dependencies
None

## Open questions
None
"""

BROKEN_SPEC_MD = "# Feature Specification\n\n## Problem\nOnly one section present.\n"


def run_fbk(args, project_root, state_dir, stdin_text=None):
    """Run fbk.py with args in project_root, STATE_DIR set to state_dir.

    Identical in shape to _run_fbk in tests/test_capture_report_integration.py.
    Returns a CompletedProcess with captured text stdout/stderr.
    """
    env = {**os.environ, "STATE_DIR": str(state_dir)}
    return subprocess.run(
        [sys.executable, FBK_PY] + args,
        input=stdin_text,
        capture_output=True,
        text=True,
        cwd=str(project_root),
        env=env,
        timeout=30,
    )


def drive_gate_fail_park_recover(project_root, state_dir, spec):
    """Drive a complete gate-fail → park → recover cycle via real fbk.py producers.

    Performs the following steps in order, asserting the expected return code
    after each one:

    1. state create <spec>                                  — rc 0
    2. state transition <spec> VALIDATING                  — rc 0
    3. Write task-01.md; task-completed (stdin JSON)       — rc 0
    4. Write broken-spec.md; spec-gate broken-spec.md      — rc 2
    5. state transition <spec> PARKED --reason ...         — rc 0
    6. state transition <spec> READY                       — rc 0
       state transition <spec> VALIDATING                  — rc 0 (re-entry)
    7. Write sample-spec.md; spec-gate sample-spec.md      — rc 0

    Returns the parsed event dicts from <project_root>/.fbk-capture/events.jsonl.
    """
    # Step 1 — create the state record.
    r = run_fbk(["state", "create", spec], project_root, state_dir)
    assert r.returncode == 0, f"state create failed (rc {r.returncode}): {r.stderr!r}"

    # Step 2 — enter the VALIDATING working stage.
    r = run_fbk(["state", "transition", spec, "VALIDATING"], project_root, state_dir)
    assert r.returncode == 0, (
        f"transition to VALIDATING failed (rc {r.returncode}): {r.stderr!r}"
    )

    # Step 3 — record a passing verification result before the park.
    task_dir = os.path.join(project_root, "ai-docs", spec, "tasks")
    os.makedirs(task_dir, exist_ok=True)
    with open(os.path.join(task_dir, "task-01.md"), "w") as fh:
        fh.write("# Task 01\n\nDo the thing.\n")

    stdin_payload = json.dumps({
        "task_description": f"Implement ai-docs/{spec}/tasks/task-01.md",
        "cwd": project_root,
    })
    r = run_fbk(["task-completed"], project_root, state_dir, stdin_text=stdin_payload)
    assert r.returncode == 0, (
        f"task-completed failed (rc {r.returncode}): {r.stderr!r}"
    )

    # Step 4 — write a broken spec and run spec-gate so it records a fail.
    broken_path = os.path.join(project_root, "broken-spec.md")
    with open(broken_path, "w") as fh:
        fh.write(BROKEN_SPEC_MD)
    r = run_fbk(["spec-gate", "broken-spec.md"], project_root, state_dir)
    assert r.returncode == 2, (
        f"spec-gate on broken spec should exit 2 (rc {r.returncode}): {r.stderr!r}"
    )

    # Step 5 — park the stage (records first error_history entry).
    r = run_fbk(
        ["state", "transition", spec, "PARKED", "--reason", "spec gate failed"],
        project_root,
        state_dir,
    )
    assert r.returncode == 0, (
        f"transition to PARKED failed (rc {r.returncode}): {r.stderr!r}"
    )

    # Step 6 — recover: PARKED → READY → VALIDATING (re-entry).
    r = run_fbk(["state", "transition", spec, "READY"], project_root, state_dir)
    assert r.returncode == 0, (
        f"transition to READY failed (rc {r.returncode}): {r.stderr!r}"
    )
    r = run_fbk(["state", "transition", spec, "VALIDATING"], project_root, state_dir)
    assert r.returncode == 0, (
        f"re-entry to VALIDATING failed (rc {r.returncode}): {r.stderr!r}"
    )

    # Step 7 — write a valid spec and run spec-gate so it records a pass after the park.
    sample_path = os.path.join(project_root, "sample-spec.md")
    with open(sample_path, "w") as fh:
        fh.write(MINIMAL_VALID_SPEC_MD)
    r = run_fbk(["spec-gate", "sample-spec.md"], project_root, state_dir)
    assert r.returncode == 0, (
        f"spec-gate on valid spec failed (rc {r.returncode}): {r.stderr!r}"
    )

    # Return all captured events for the caller to assert on.
    events_path = os.path.join(project_root, ".fbk-capture", "events.jsonl")
    if not os.path.exists(events_path):
        return []
    with open(events_path) as fh:
        return [json.loads(line) for line in fh if line.strip()]
