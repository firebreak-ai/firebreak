"""Round-trip integration test: real router writes SubagentStop, then harvest joins it.

Drives the production hook router as a subprocess with a SubagentStop payload
carrying agent_id, then calls harvest against the live events.jsonl the router
wrote — proving that the data.agent_id field the router emits joins to the
journal agentId end to end.

The test is expected to SKIP while fbk.harvest is absent (red phase). Once
fbk/harvest.py exists and implements harvest(run_id, project_cwd), this test
should turn green.

This file is kept separate from the pure-tmp_path join tests (test_harvest_join.py)
because it spins up the real router subprocess; combining them would couple the
fast in-process tests to subprocess startup overhead.
"""

import json
import os
import sys
from pathlib import Path

import pytest

from tests import capture_fixtures

# ---------------------------------------------------------------------------
# Guarded import: skip everything when fbk.harvest is not yet implemented.
# ---------------------------------------------------------------------------

try:
    from fbk import harvest
    _HARVEST_AVAILABLE = True
except ImportError:
    _HARVEST_AVAILABLE = False

pytestmark = pytest.mark.skipif(
    not _HARVEST_AVAILABLE,
    reason="fbk.harvest module not yet implemented",
)

# ---------------------------------------------------------------------------
# Router location
# ---------------------------------------------------------------------------

ROUTER = Path(__file__).parent.parent / "fbk" / "capture" / "hook_router.py"


# ---------------------------------------------------------------------------
# Subprocess driver (mirrors the pattern in test_capture_hook_router.py)
# ---------------------------------------------------------------------------


def _run_router(payload_json, project_dir, env_extra=None):
    """Run the hook router as a subprocess with the given stdin payload.

    Args:
        payload_json: JSON string fed to the router on stdin.
        project_dir:  Path whose str becomes os.getcwd() inside the router.
        env_extra:    Optional dict of additional env-var overrides.

    Returns:
        CompletedProcess with captured stdout and stderr.
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
# Event file helpers (mirrors the pattern in test_capture_hook_router.py)
# ---------------------------------------------------------------------------


def _events_path(project_dir):
    return os.path.join(str(project_dir), ".fbk-capture", "events.jsonl")


def _read_events(project_dir):
    """Return parsed event dicts from the project's events.jsonl."""
    path = _events_path(project_dir)
    with open(path) as fh:
        return [json.loads(line) for line in fh if line.strip()]


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------


def test_matching_agent_id_survives_router_to_harvest(tmp_path, monkeypatch):
    """A SubagentStop written by the real router is joined to the matching roster agent.

    Builds an instrumented project and a one-agent run directory whose journal
    roster agentId is 'agent-rt-1'. Drives the router with a SubagentStop
    carrying agent_id='agent-rt-1'. Calls harvest and asserts the single unit
    carries non-null stopped_at, proving the data.agent_id written by the
    production router joins to the journal agentId end to end.
    """
    # --- project tree ---
    project_root = capture_fixtures.make_project(
        str(tmp_path / "proj_base"),
        instrumented=True,
        marked=True,
        capture_cfg="standard",
    )

    # --- run directory with a one-agent roster ---
    projects_root = str(tmp_path / "projects")
    run_id = "run-rt-match"
    agent_id = "agent-rt-1"

    capture_fixtures.make_workflow_run(
        projects_root,
        run_id=run_id,
        agents=[
            {
                "agent_id": agent_id,
                "first_message": "Implement the feature.",
                "turns": [],
                "result": {"status": "success"},
            }
        ],
    )

    # --- drive the real router with a SubagentStop for agent-rt-1 ---
    payload = capture_fixtures.hook_payload(
        "SubagentStop",
        agent_type="fbk-implementer",
        extra={"agent_id": agent_id, "session_id": "s1"},
    )
    result_proc = _run_router(payload, project_root)

    assert result_proc.returncode == 0, (
        f"router exited {result_proc.returncode}, stderr: {result_proc.stderr!r}"
    )

    # Verify the router wrote a SUBAGENT_STOP event carrying the join key.
    events = _read_events(project_root)
    subagent_stop_events = [
        e for e in events
        if e.get("event_type") == "SUBAGENT_STOP"
    ]
    assert len(subagent_stop_events) >= 1, (
        f"expected a SUBAGENT_STOP event after routing SubagentStop payload; "
        f"events written: {events!r}"
    )
    written_agent_id = subagent_stop_events[0].get("data", {}).get("agent_id")
    assert written_agent_id == agent_id, (
        f"expected data.agent_id == {agent_id!r} in the written SUBAGENT_STOP event, "
        f"got {written_agent_id!r}"
    )

    # --- harvest against the live events.jsonl ---
    monkeypatch.setenv("FBK_PROJECTS_ROOT", projects_root)
    harvest_result = harvest.harvest(run_id, project_root)

    assert harvest_result.unit_count == 1, (
        f"expected unit_count == 1 (one roster agent), got {harvest_result.unit_count}"
    )

    # Read the written record to confirm the unit carries event-derived data.
    record_path = harvest_result.record_path
    assert record_path is not None, "harvest returned no record_path"
    with open(record_path) as fh:
        record = json.load(fh)

    units = record.get("units", [])
    assert len(units) == 1, f"expected 1 unit in record, got {len(units)}"

    unit = units[0]
    assert unit.get("agent_id") == agent_id, (
        f"expected unit agent_id == {agent_id!r}, got {unit.get('agent_id')!r}"
    )

    # stopped_at must be non-null: a null here means the join failed (the field
    # name the router emits did not match what harvest reads).
    assert unit.get("stopped_at") is not None, (
        f"expected stopped_at to be non-null for the matched agent — a null value "
        f"means the data.agent_id / agentId join key was lost in transit; "
        f"full unit: {unit!r}"
    )


def test_mismatched_agent_id_yields_null_timing_fields(tmp_path, monkeypatch):
    """A roster agent whose id does not appear in events.jsonl gets null timing.

    Builds a run whose journal roster id ('agent-rt-nomatch') does NOT match the
    router-written event's agent_id ('agent-rt-1'). After harvest, the mismatched
    unit is still present (roster-driven), but its stopped_at and duration_s are
    both None because the SubagentStop event could not be joined to it.

    This is the negative guard: if harvest fabricated timing data even without a
    matching event, this test catches it.
    """
    # --- project tree (same events.jsonl shared) ---
    project_root = capture_fixtures.make_project(
        str(tmp_path / "proj_base"),
        instrumented=True,
        marked=True,
        capture_cfg="standard",
    )

    # --- run directory with a roster id that will NOT match the router event ---
    projects_root = str(tmp_path / "projects")
    run_id_mismatch = "run-rt-mismatch"
    roster_agent_id = "agent-rt-nomatch"   # different from what the router writes
    router_agent_id = "agent-rt-1"         # what the router will write

    capture_fixtures.make_workflow_run(
        projects_root,
        run_id=run_id_mismatch,
        agents=[
            {
                "agent_id": roster_agent_id,
                "first_message": "Implement the feature.",
                "turns": [],
                "result": {"status": "success"},
            }
        ],
    )

    # --- write the router event with a DIFFERENT agent_id ---
    payload = capture_fixtures.hook_payload(
        "SubagentStop",
        agent_type="fbk-implementer",
        extra={"agent_id": router_agent_id, "session_id": "s1"},
    )
    result_proc = _run_router(payload, project_root)

    assert result_proc.returncode == 0, (
        f"router exited {result_proc.returncode}, stderr: {result_proc.stderr!r}"
    )

    # Confirm events.jsonl has the router-written event with the wrong agent_id.
    events = _read_events(project_root)
    written_ids = [
        e.get("data", {}).get("agent_id")
        for e in events
        if e.get("event_type") == "SUBAGENT_STOP"
    ]
    assert router_agent_id in written_ids, (
        f"expected the router to write agent_id {router_agent_id!r}; "
        f"SUBAGENT_STOP data.agent_id values seen: {written_ids!r}"
    )

    # --- harvest: the mismatched roster agent gets no joined event data ---
    monkeypatch.setenv("FBK_PROJECTS_ROOT", projects_root)
    harvest_result = harvest.harvest(run_id_mismatch, project_root)

    assert harvest_result.unit_count == 1, (
        f"expected unit_count == 1 (one roster agent), got {harvest_result.unit_count}"
    )

    record_path = harvest_result.record_path
    assert record_path is not None, "harvest returned no record_path"
    with open(record_path) as fh:
        record = json.load(fh)

    units = record.get("units", [])
    assert len(units) == 1, f"expected 1 unit in record, got {len(units)}"

    unit = units[0]
    assert unit.get("agent_id") == roster_agent_id, (
        f"expected unit agent_id == {roster_agent_id!r}, got {unit.get('agent_id')!r}"
    )

    # stopped_at and duration_s must be null: no matching SubagentStop event was
    # in the event stream for this roster agent.
    assert unit.get("stopped_at") is None, (
        f"expected stopped_at to be None for a mismatched roster agent "
        f"(no matching SubagentStop event for {roster_agent_id!r}); "
        f"full unit: {unit!r}"
    )
    assert unit.get("duration_s") is None, (
        f"expected duration_s to be None for a mismatched roster agent "
        f"(no matching SubagentStop event for {roster_agent_id!r}); "
        f"full unit: {unit!r}"
    )
