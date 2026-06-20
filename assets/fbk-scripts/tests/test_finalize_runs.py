"""Integration tests for fbk.finalize — finalize_runs event-name gating.

Tests cover:
- PostToolUse targeted finalize: run id parsed from payload, only that run finalized, no sweep
- PostToolUse without parseable run id: no record written (no sweep on unparseable payload)
- SessionStart sweep: closed run finalized by glob-match sweep on SessionStart
- Newest-only bound and catch-up: SessionStart finalizes at most one run per trigger,
  newest first; the skipped older run is caught on the next trigger
- Non-trigger event gate: a non-PostToolUse, non-SessionStart event writes nothing
- Never-raises: malformed or absent run directory does not propagate an exception
"""

import json
import os
import time
import pytest

try:
    from fbk import finalize
    FINALIZE_AVAILABLE = hasattr(finalize, "finalize_runs")
except ImportError:
    FINALIZE_AVAILABLE = False

from tests import capture_fixtures

pytestmark = pytest.mark.skipif(
    not FINALIZE_AVAILABLE,
    reason="fbk.finalize.finalize_runs not yet implemented",
)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _record_path(project_cwd, run_id):
    """Return the expected record path for run_id under the project's capture dir."""
    return os.path.join(project_cwd, ".fbk-capture", "runs", f"{run_id}.json")


def _record_exists(project_cwd, run_id):
    """Return True when the finalized record for run_id exists on disk."""
    return os.path.exists(_record_path(project_cwd, run_id))


def _read_record(project_cwd, run_id):
    """Read and return the parsed JSON record for run_id."""
    with open(_record_path(project_cwd, run_id)) as fh:
        return json.load(fh)


def _simple_agent(agent_id):
    """Minimal agent dict: no attribution descriptor, no turns, has a result."""
    return {
        "agent_id": agent_id,
        "first_message": f"Run agent {agent_id}.",
        "turns": [],
        "result": {"outcome": "success"},
    }


def _post_tool_use_payload_with_run_id(run_id):
    """Construct a PostToolUse payload whose Workflow tool response names run_id.

    The response text carries the canonical 'Transcript dir: …/subagents/workflows/<run_id>'
    line that finalize_runs parses to identify the targeted run.
    """
    return {
        "hook_event_name": "PostToolUse",
        "tool_name": "Workflow",
        "tool_response": {
            "content": [
                {
                    "type": "text",
                    "text": f"Transcript dir: /x/subagents/workflows/{run_id}\nDone.",
                }
            ]
        },
    }


def _post_tool_use_payload_no_run_id():
    """Construct a PostToolUse payload whose Workflow response carries no parseable run id."""
    return {
        "hook_event_name": "PostToolUse",
        "tool_name": "Workflow",
        "tool_response": {
            "content": [
                {
                    "type": "text",
                    "text": "Workflow completed. No transcript dir line present.",
                }
            ]
        },
    }


def _make_instrumented_project(tmp_path):
    """Build an instrumented project at capture_level=standard; return its cwd path."""
    return capture_fixtures.make_project(
        str(tmp_path),
        instrumented=True,
        marked=True,
        capture_cfg="standard",
    )


# ---------------------------------------------------------------------------
# PostToolUse targeted finalize
# ---------------------------------------------------------------------------


class TestPostToolUseTargetedFinalize:
    """finalize_runs on PostToolUse parses the run id from the payload and finalizes only that run."""

    def test_post_tool_use_with_run_id_writes_record_for_that_run(
        self, tmp_path, monkeypatch
    ):
        """PostToolUse payload naming run-A produces a record at .fbk-capture/runs/run-A.json
        whose run_id field equals 'run-A', proving the record is attributable to the parsed run.
        """
        projects_root = str(tmp_path / "projects")
        project_cwd = _make_instrumented_project(tmp_path)
        monkeypatch.setenv("FBK_PROJECTS_ROOT", projects_root)

        run_id = "run-A"
        capture_fixtures.make_workflow_run(
            projects_root,
            run_id=run_id,
            agents=[_simple_agent("agent-1")],
        )

        payload = _post_tool_use_payload_with_run_id(run_id)
        result = finalize.finalize_runs("PostToolUse", project_cwd, payload)

        assert result is None, "finalize_runs must return None"
        assert _record_exists(project_cwd, run_id), (
            f"expected record at .fbk-capture/runs/{run_id}.json but it was not written"
        )
        record = _read_record(project_cwd, run_id)
        assert record["run_id"] == run_id, (
            f"record run_id must equal {run_id!r}, got {record['run_id']!r}"
        )


# ---------------------------------------------------------------------------
# PostToolUse without parseable run id — no sweep
# ---------------------------------------------------------------------------


class TestPostToolUseNoRunId:
    """finalize_runs on PostToolUse with no parseable run id writes nothing and never sweeps."""

    def test_post_tool_use_without_run_id_writes_no_record(
        self, tmp_path, monkeypatch
    ):
        """An unparseable payload leaves the run unfinalized; no sweep occurs on PostToolUse."""
        projects_root = str(tmp_path / "projects")
        project_cwd = _make_instrumented_project(tmp_path)
        monkeypatch.setenv("FBK_PROJECTS_ROOT", projects_root)

        run_id = "run-no-id"
        capture_fixtures.make_workflow_run(
            projects_root,
            run_id=run_id,
            agents=[_simple_agent("agent-1")],
        )

        payload = _post_tool_use_payload_no_run_id()
        finalize.finalize_runs("PostToolUse", project_cwd, payload)

        assert not _record_exists(project_cwd, run_id), (
            f"PostToolUse without parseable run id must not write a record "
            f"(no sweep allowed); found unexpected record at .fbk-capture/runs/{run_id}.json"
        )


# ---------------------------------------------------------------------------
# SessionStart sweep
# ---------------------------------------------------------------------------


class TestSessionStartSweep:
    """finalize_runs on SessionStart sweeps closed runs and finalizes via glob-match."""

    def test_session_start_finalizes_closed_run_via_sweep(
        self, tmp_path, monkeypatch
    ):
        """SessionStart with no payload sweeps the projects root and finalizes a closed run."""
        projects_root = str(tmp_path / "projects")
        project_cwd = _make_instrumented_project(tmp_path)
        monkeypatch.setenv("FBK_PROJECTS_ROOT", projects_root)

        run_id = "run-session-sweep"
        capture_fixtures.make_workflow_run(
            projects_root,
            run_id=run_id,
            agents=[_simple_agent("agent-1")],
        )

        finalize.finalize_runs("SessionStart", project_cwd, None)

        assert _record_exists(project_cwd, run_id), (
            f"SessionStart sweep must finalize a closed run; "
            f"expected record at .fbk-capture/runs/{run_id}.json"
        )


# ---------------------------------------------------------------------------
# Newest-only bound and catch-up
# ---------------------------------------------------------------------------


class TestNewestOnlyBoundAndCatchup:
    """SessionStart finalizes at most the newest closed-unfinalized run per trigger.

    On the first call, exactly one record is written for the newer run.
    On the second call, the older run's record is written (catch-up).
    """

    def test_first_session_start_finalizes_newest_run_only(
        self, tmp_path, monkeypatch
    ):
        """After one SessionStart call, only the newer run has a record; the older does not."""
        projects_root = str(tmp_path / "projects")
        project_cwd = _make_instrumented_project(tmp_path)
        monkeypatch.setenv("FBK_PROJECTS_ROOT", projects_root)

        older_run_id = "run-older"
        newer_run_id = "run-newer"

        capture_fixtures.make_workflow_run(
            projects_root,
            run_id=older_run_id,
            agents=[_simple_agent("agent-old")],
        )
        # Ensure distinguishable modification times: older run directory is touched first,
        # then a small delay, then the newer run is created.
        older_run_dir = os.path.join(
            projects_root, "proj", "sess", "subagents", "workflows", older_run_id
        )
        # Backdate the older run directory so mtime is clearly earlier.
        old_mtime = time.time() - 10
        os.utime(older_run_dir, (old_mtime, old_mtime))

        capture_fixtures.make_workflow_run(
            projects_root,
            run_id=newer_run_id,
            agents=[_simple_agent("agent-new")],
        )
        # The newer run directory retains its current mtime (more recent than older_run_dir).

        finalize.finalize_runs("SessionStart", project_cwd, None)

        # Only the newer run should have a record after the first call.
        assert _record_exists(project_cwd, newer_run_id), (
            f"first SessionStart must finalize the newest run; "
            f"expected record at .fbk-capture/runs/{newer_run_id}.json"
        )
        assert not _record_exists(project_cwd, older_run_id), (
            f"first SessionStart must finalize at most one run (the newest); "
            f"older run {older_run_id!r} must not have a record yet"
        )

    def test_second_session_start_catches_up_older_run(
        self, tmp_path, monkeypatch
    ):
        """After two SessionStart calls, both runs have records — the second call catches up."""
        projects_root = str(tmp_path / "projects")
        project_cwd = _make_instrumented_project(tmp_path)
        monkeypatch.setenv("FBK_PROJECTS_ROOT", projects_root)

        older_run_id = "run-older-cu"
        newer_run_id = "run-newer-cu"

        capture_fixtures.make_workflow_run(
            projects_root,
            run_id=older_run_id,
            agents=[_simple_agent("agent-old")],
        )
        older_run_dir = os.path.join(
            projects_root, "proj", "sess", "subagents", "workflows", older_run_id
        )
        old_mtime = time.time() - 10
        os.utime(older_run_dir, (old_mtime, old_mtime))

        capture_fixtures.make_workflow_run(
            projects_root,
            run_id=newer_run_id,
            agents=[_simple_agent("agent-new")],
        )

        # First call: newest run is finalized.
        finalize.finalize_runs("SessionStart", project_cwd, None)

        # Second call: older run is caught up.
        finalize.finalize_runs("SessionStart", project_cwd, None)

        assert _record_exists(project_cwd, newer_run_id), (
            f"newer run {newer_run_id!r} must still have a record after the second call"
        )
        assert _record_exists(project_cwd, older_run_id), (
            f"second SessionStart must catch up the older run; "
            f"expected record at .fbk-capture/runs/{older_run_id}.json"
        )


# ---------------------------------------------------------------------------
# Event-gate: non-trigger event does nothing
# ---------------------------------------------------------------------------


class TestEventGate:
    """finalize_runs on a non-trigger event name does nothing and writes no record."""

    def test_non_trigger_event_writes_no_record(self, tmp_path, monkeypatch):
        """A SubagentStop event is a no-op: the event-name gate keeps it from sweeping."""
        projects_root = str(tmp_path / "projects")
        project_cwd = _make_instrumented_project(tmp_path)
        monkeypatch.setenv("FBK_PROJECTS_ROOT", projects_root)

        run_id = "run-gated"
        capture_fixtures.make_workflow_run(
            projects_root,
            run_id=run_id,
            agents=[_simple_agent("agent-1")],
        )

        finalize.finalize_runs("SubagentStop", project_cwd, None)

        assert not _record_exists(project_cwd, run_id), (
            f"SubagentStop is a non-trigger event and must write no record; "
            f"found unexpected record at .fbk-capture/runs/{run_id}.json"
        )


# ---------------------------------------------------------------------------
# Never-raises
# ---------------------------------------------------------------------------


class TestNeverRaises:
    """finalize_runs never propagates an exception into the router."""

    def test_malformed_run_directory_does_not_raise(self, tmp_path, monkeypatch):
        """finalize_runs returns None without raising when the target run directory is absent."""
        projects_root = str(tmp_path / "projects")
        project_cwd = _make_instrumented_project(tmp_path)
        monkeypatch.setenv("FBK_PROJECTS_ROOT", projects_root)

        # Payload names a run whose directory does not exist.
        absent_run_id = "run-does-not-exist"
        payload = _post_tool_use_payload_with_run_id(absent_run_id)

        # Must not raise; must return None.
        result = finalize.finalize_runs("PostToolUse", project_cwd, payload)

        assert result is None, (
            "finalize_runs must return None even when the target run directory is absent"
        )
