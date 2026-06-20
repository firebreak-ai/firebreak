"""Integration test for crash-recovery finalization on SessionStart sweep (AC-07).

A run directory left with a started line but no result line — orphaned by a prior
crashed session — must finalize as truncated when the next SessionStart sweep runs.

Distinct behaviors under test (one scenario covers all):
- SessionStart sweep picks up the orphaned run.
- The record's completeness is "truncated", not "clean-complete".
- The crashed unit's missing result is recorded as journal_result_present=False and
  journal_result=null — the gap is noted, not invented or silently dropped.
- The crashed unit's attribution is independent of the missing result (decision D-17):
  because its transcript carried a valid first-message descriptor, attribution_absent
  is False even though the result is absent.

All tests skip cleanly when fbk.finalize.finalize_runs is not yet implemented.
"""

import json
import os

import pytest

try:
    from fbk import finalize
    _FINALIZE_RUNS_AVAILABLE = hasattr(finalize, "finalize_runs")
except ImportError:
    finalize = None  # type: ignore[assignment]
    _FINALIZE_RUNS_AVAILABLE = False

from tests import capture_fixtures


pytestmark = pytest.mark.skipif(
    not _FINALIZE_RUNS_AVAILABLE,
    reason="fbk.finalize.finalize_runs not yet implemented",
)


# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

_CAPTURE_RUNS_DIR = ".fbk-capture/runs"

# A valid fbk-attr descriptor embedded in the crash-orphaned agent's first message.
# Gives the agent parseable attribution so we can prove D-17: the missing result
# does not force attribution_absent=True when the descriptor was present.
_VALID_DESCRIPTOR_FIRST_MESSAGE = (
    'Implement the feature described in task-01.md.\n'
    '<!--fbk-attr {"cardinality": "single", "stance": "collaborative"}-->'
)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _run_record_path(project_root, run_id):
    """Return the expected path for a finalized run record."""
    return os.path.join(project_root, _CAPTURE_RUNS_DIR, f"{run_id}.json")


def _read_run_record(project_root, run_id):
    """Read and return the parsed JSON run record, or raise if absent."""
    path = _run_record_path(project_root, run_id)
    with open(path) as fh:
        return json.load(fh)


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


@pytest.fixture()
def orphaned_run_env(tmp_path, monkeypatch):
    """Build a crash-orphaned run directory and return (project_root, run_id).

    Layout under tmp_path:
        projects/           — FBK_PROJECTS_ROOT redirect target
            proj/sess/subagents/workflows/orphaned-run-A/
                journal.jsonl        — has started line, NO result line
                agent-crashed.jsonl  — valid first-message descriptor, no result
                agent-crashed.meta.json

        project/            — instrumented project with capture_level=standard
            .claude/automation/
            .fbk-capture/capture.cfg

    The monkeypatch sets FBK_PROJECTS_ROOT so finalize_runs' glob resolver scans
    the local tmp_path tree instead of the real ~/.claude/projects/ tree.
    """
    projects_root = str(tmp_path / "projects")
    os.makedirs(projects_root, exist_ok=True)

    # The project the new session runs in. Its runs live under a projects-root
    # folder named after this working directory (the SessionStart sweep scope).
    project_root = capture_fixtures.make_project(
        str(tmp_path / "project"),
        instrumented=True,
        capture_cfg="standard",
    )

    run_id = "orphaned-run-A"
    capture_fixtures.make_workflow_run(
        projects_root,
        run_id=run_id,
        agents=[
            {
                "agent_id": "crashed",
                "first_message": _VALID_DESCRIPTOR_FIRST_MESSAGE,
                "turns": [],
                "result": None,  # no result line — simulates session crash
            }
        ],
        project_hash=project_root.replace("/", "-"),
        session_uuid="sess",
    )

    monkeypatch.setenv("FBK_PROJECTS_ROOT", projects_root)

    return project_root, run_id


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------


class TestCrashRecoveryFinalization:
    """SessionStart sweep finalizes a crash-orphaned run as truncated (AC-07)."""

    def test_record_exists_after_session_start_sweep(self, orphaned_run_env):
        """SessionStart sweep produces a record file for the crash-orphaned run."""
        project_root, run_id = orphaned_run_env
        record_path = _run_record_path(project_root, run_id)

        assert not os.path.exists(record_path), (
            "record must not exist before the sweep (precondition check)"
        )

        finalize.finalize_runs("SessionStart", project_root, None)

        assert os.path.exists(record_path), (
            f"expected run record at {record_path} after SessionStart sweep, but it was not created"
        )

    def test_completeness_is_truncated(self, orphaned_run_env):
        """The finalized record's completeness is 'truncated' for a started-without-result run."""
        project_root, run_id = orphaned_run_env

        finalize.finalize_runs("SessionStart", project_root, None)

        record = _read_run_record(project_root, run_id)
        assert record["completeness"] == "truncated", (
            f"expected completeness 'truncated' for crash-orphaned run, got {record['completeness']!r}"
        )

    def test_crashed_unit_records_absent_result_as_null(self, orphaned_run_env):
        """Crashed agent's missing result is recorded as journal_result_present=False and journal_result=null."""
        project_root, run_id = orphaned_run_env

        finalize.finalize_runs("SessionStart", project_root, None)

        record = _read_run_record(project_root, run_id)

        # Locate the crashed agent's unit record.
        units = record.get("units", [])
        crashed_units = [u for u in units if u.get("agent_id") == "crashed"]
        assert len(crashed_units) == 1, (
            f"expected exactly one unit for agent 'crashed', got {len(crashed_units)}: {crashed_units!r}"
        )
        crashed_unit = crashed_units[0]

        assert crashed_unit["journal_result_present"] is False, (
            f"expected journal_result_present=False for crash-orphaned agent, "
            f"got {crashed_unit.get('journal_result_present')!r}"
        )
        assert crashed_unit["journal_result"] is None, (
            f"expected journal_result=null for crash-orphaned agent, "
            f"got {crashed_unit.get('journal_result')!r}"
        )

    def test_attribution_absent_false_when_descriptor_was_present(self, orphaned_run_env):
        """Missing result does not force attribution_absent — descriptor parse is independent (D-17)."""
        project_root, run_id = orphaned_run_env

        finalize.finalize_runs("SessionStart", project_root, None)

        record = _read_run_record(project_root, run_id)
        units = record.get("units", [])
        crashed_units = [u for u in units if u.get("agent_id") == "crashed"]
        assert len(crashed_units) == 1, (
            f"expected exactly one unit for agent 'crashed', got {len(crashed_units)}: {crashed_units!r}"
        )
        crashed_unit = crashed_units[0]

        # The transcript carried a valid first-message descriptor, so attribution is present.
        assert crashed_unit["attribution_absent"] is False, (
            f"expected attribution_absent=False (valid descriptor was present in transcript), "
            f"got {crashed_unit.get('attribution_absent')!r}; the missing result must not force attribution absent"
        )

    def test_completeness_not_clean_complete(self, orphaned_run_env):
        """A started-without-result run must never finalize as 'clean-complete'."""
        project_root, run_id = orphaned_run_env

        finalize.finalize_runs("SessionStart", project_root, None)

        record = _read_run_record(project_root, run_id)
        assert record["completeness"] != "clean-complete", (
            f"crash-orphaned run must not be classified as 'clean-complete'; "
            f"got completeness={record['completeness']!r}"
        )
