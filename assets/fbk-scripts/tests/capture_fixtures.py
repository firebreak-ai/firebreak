"""Shared fixture builders for metrics-plane tests.

Each function is a pure builder: it takes a base directory (or no directory for
in-memory objects) and returns either a dict / string or a written-file path.
No pytest fixtures here — import this module by name from test files:

    from tests import capture_fixtures
"""

import json
import os
import stat

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
