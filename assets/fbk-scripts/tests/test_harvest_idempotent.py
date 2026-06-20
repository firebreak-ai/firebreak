"""Integration tests for harvest atomicity and finalized-run idempotency.

Tests cover:
- Atomic write: harvest leaves no temp file residue in runs/ after completing.
- Finalized no-op: a second harvest after a run-directory mutation preserves
  harvested_at (from the first harvest) and leaves the attributed units unchanged.

The de-vacuum requirement: the idempotency test mutates the run directory
between the two harvests and asserts both that harvested_at is the first
harvest's value (not the second clock value) and that the attributed content
is byte-for-byte the same — proving the finalized no-op actually fired rather
than the fixture being deterministic by coincidence.

The only justified mock is the wall clock (harvest._utcnow), because
harvested_at varies on every real run and must be controlled to assert
idempotency. All file I/O uses real tmp_path files.
"""

import json
import os

import pytest

try:
    from fbk import harvest
    HARVEST_AVAILABLE = True
except ImportError:
    HARVEST_AVAILABLE = False

pytestmark = pytest.mark.skipif(
    not HARVEST_AVAILABLE,
    reason="fbk.harvest module not yet implemented",
)

from tests import capture_fixtures


# ---------------------------------------------------------------------------
# Shared fixture: an instrumented project with one clean-complete run
# ---------------------------------------------------------------------------

_AGENT_ID = "agent-a"
_RUN_ID = "run-idempotent-01"

# Two different UTC datetimes used to prove the second clock value is NOT
# written when the finalized no-op fires.
import datetime

_T1 = datetime.datetime(2026, 1, 15, 10, 0, 0, tzinfo=datetime.timezone.utc)
_T2 = datetime.datetime(2026, 1, 15, 11, 0, 0, tzinfo=datetime.timezone.utc)

# A valid attribution descriptor so the unit has deterministic attributed fields.
_ATTR_DESCRIPTOR = '<!--fbk-attr {"cardinality": "single", "stance": "collaborative"}-->'


def _build_project_and_run(tmp_path):
    """Build an instrumented project and one finalizable closed run.

    Returns (project_cwd, run_dir, journal_path, runs_dir) so callers can
    inspect and mutate the run directory between harvests.
    """
    projects_root = str(tmp_path / "projects")

    # Instrumented project at standard capture level.
    project_cwd = capture_fixtures.make_project(
        tmp_path,
        instrumented=True,
        marked=True,
        capture_cfg="standard",
    )

    # One agent with a result — a clean-complete, finalizable run.
    run_dir = capture_fixtures.make_workflow_run(
        projects_root,
        _RUN_ID,
        agents=[
            {
                "agent_id": _AGENT_ID,
                "first_message": _ATTR_DESCRIPTOR + "\nDo the work.",
                "turns": [],
                "result": {"status": "success"},
            }
        ],
    )

    # Write a SubagentStop event for the agent so the join has data.
    events_path = os.path.join(project_cwd, ".fbk-capture", "events.jsonl")
    events = [
        capture_fixtures.build_event(
            "SUBAGENT_STOP",
            source="hook_router",
            spec="test-spec",
            stage="IMPLEMENT",
            capture_level="standard",
            data={"agent_id": _AGENT_ID},
        )
    ]
    capture_fixtures.write_events(events_path, events)

    journal_path = os.path.join(run_dir, "journal.jsonl")
    runs_dir = os.path.join(project_cwd, ".fbk-capture", "runs")
    return project_cwd, run_dir, journal_path, runs_dir


# ---------------------------------------------------------------------------
# Test: first harvest writes harvested_at equal to the mocked clock value
# ---------------------------------------------------------------------------


class TestFirstHarvestTimestamp:
    """harvest writes harvested_at equal to _utcnow() on the first call."""

    def test_first_harvest_sets_harvested_at_to_clock(self, tmp_path, monkeypatch):
        """harvested_at in the written record equals T1, the first mocked clock value."""
        projects_root = str(tmp_path / "projects")
        monkeypatch.setenv("FBK_PROJECTS_ROOT", projects_root)
        monkeypatch.setattr(harvest, "_utcnow", lambda: _T1)

        project_cwd, _run_dir, _journal_path, _runs_dir = _build_project_and_run(tmp_path)

        result = harvest.harvest(_RUN_ID, project_cwd)

        assert result.error is None, f"harvest failed: {result.error}"
        record_path = os.path.join(project_cwd, ".fbk-capture", "runs", f"{_RUN_ID}.json")
        with open(record_path) as fh:
            record = json.load(fh)

        assert record["harvested_at"] == _T1.isoformat(), (
            f"harvested_at should equal the first clock value T1={_T1.isoformat()!r}; "
            f"got {record['harvested_at']!r}"
        )


# ---------------------------------------------------------------------------
# Test: finalized no-op preserves harvested_at after a run-directory mutation
# ---------------------------------------------------------------------------


class TestFinalizedNoOpPreservesHarvestedAt:
    """A second harvest after a run-directory mutation preserves harvested_at from the first harvest."""

    def test_second_harvest_preserves_harvested_at_despite_different_clock(
        self, tmp_path, monkeypatch
    ):
        """harvested_at stays equal to T1 after a mutation + second harvest at T2.

        The de-vacuum step: mutate the run's journal.jsonl before the second
        harvest so that a naive re-derive would produce different content — but
        the finalized no-op must fire and leave the record unchanged.
        """
        projects_root = str(tmp_path / "projects")
        monkeypatch.setenv("FBK_PROJECTS_ROOT", projects_root)

        project_cwd, _run_dir, journal_path, runs_dir = _build_project_and_run(tmp_path)

        # First harvest at T1.
        monkeypatch.setattr(harvest, "_utcnow", lambda: _T1)
        result_first = harvest.harvest(_RUN_ID, project_cwd)
        assert result_first.error is None, f"first harvest failed: {result_first.error}"

        record_path = os.path.join(project_cwd, ".fbk-capture", "runs", f"{_RUN_ID}.json")
        with open(record_path) as fh:
            record_after_first = json.load(fh)

        harvested_at_first = record_after_first["harvested_at"]
        assert harvested_at_first == _T1.isoformat(), (
            f"first harvest: expected harvested_at={_T1.isoformat()!r}; "
            f"got {harvested_at_first!r}"
        )

        # --- De-vacuum mutation: append an extra result line to journal.jsonl ---
        # This changes the run directory on disk between the two harvests.
        extra_line = json.dumps({"type": "result", "agentId": "injected-extra", "result": {}})
        with open(journal_path, "a") as fh:
            fh.write(extra_line + "\n")

        # Confirm the mutation landed.
        with open(journal_path) as fh:
            journal_lines = [line for line in fh if line.strip()]
        assert any("injected-extra" in line for line in journal_lines), (
            "de-vacuum mutation did not append to journal.jsonl"
        )

        # Second harvest at T2 — a different clock value.
        monkeypatch.setattr(harvest, "_utcnow", lambda: _T2)
        result_second = harvest.harvest(_RUN_ID, project_cwd)
        assert result_second.error is None, f"second harvest failed: {result_second.error}"

        with open(record_path) as fh:
            record_after_second = json.load(fh)

        harvested_at_second = record_after_second["harvested_at"]
        assert harvested_at_second == _T1.isoformat(), (
            f"finalized no-op should preserve harvested_at={_T1.isoformat()!r}; "
            f"got {harvested_at_second!r} (T2={_T2.isoformat()!r} was incorrectly written)"
        )


# ---------------------------------------------------------------------------
# Test: attributed content (units) is identical across both reads
# ---------------------------------------------------------------------------


class TestFinalizedNoOpPreservesAttributedContent:
    """Attributed units in the record are identical before and after the no-op re-harvest."""

    def test_units_identical_across_harvests_despite_run_directory_mutation(
        self, tmp_path, monkeypatch
    ):
        """units list is value-identical across the two reads despite the intervening mutation.

        This proves the finalized no-op did not re-derive content from the
        mutated run directory — the record is read from the existing file,
        not recomputed.
        """
        projects_root = str(tmp_path / "projects")
        monkeypatch.setenv("FBK_PROJECTS_ROOT", projects_root)

        project_cwd, _run_dir, journal_path, _runs_dir = _build_project_and_run(tmp_path)

        # First harvest.
        monkeypatch.setattr(harvest, "_utcnow", lambda: _T1)
        result_first = harvest.harvest(_RUN_ID, project_cwd)
        assert result_first.error is None, f"first harvest failed: {result_first.error}"

        record_path = os.path.join(project_cwd, ".fbk-capture", "runs", f"{_RUN_ID}.json")
        with open(record_path) as fh:
            units_first = json.load(fh)["units"]

        # Mutate the run directory before the second harvest.
        with open(journal_path, "a") as fh:
            fh.write(json.dumps({"type": "result", "agentId": "injected-extra", "result": {}}) + "\n")

        # Second harvest at a different clock.
        monkeypatch.setattr(harvest, "_utcnow", lambda: _T2)
        result_second = harvest.harvest(_RUN_ID, project_cwd)
        assert result_second.error is None, f"second harvest failed: {result_second.error}"

        with open(record_path) as fh:
            units_second = json.load(fh)["units"]

        assert units_second == units_first, (
            "attributed units changed after re-harvest of a finalized record; "
            "the finalized no-op should have preserved the record unchanged"
        )


# ---------------------------------------------------------------------------
# Test: no temp file residue after harvest
# ---------------------------------------------------------------------------


class TestAtomicWriteLeavesNoTempResidue:
    """harvest uses a unique temp name + os.replace; no temp file remains in runs/ afterwards."""

    def test_runs_dir_contains_only_final_record_after_harvest(self, tmp_path, monkeypatch):
        """After harvest completes, runs/ holds exactly <run-id>.json and no temp siblings.

        Atomicity guarantee: the writer stages to a unique per-writer temp name
        (pid/uuid based) then os.replace to the final path, so the only file
        that survives in runs/ is the final record.
        """
        projects_root = str(tmp_path / "projects")
        monkeypatch.setenv("FBK_PROJECTS_ROOT", projects_root)
        monkeypatch.setattr(harvest, "_utcnow", lambda: _T1)

        project_cwd, _run_dir, _journal_path, runs_dir = _build_project_and_run(tmp_path)

        result = harvest.harvest(_RUN_ID, project_cwd)
        assert result.error is None, f"harvest failed: {result.error}"

        # runs/ must exist and hold exactly one file.
        assert os.path.isdir(runs_dir), f"runs/ directory was not created at {runs_dir!r}"

        entries = os.listdir(runs_dir)
        expected_filename = f"{_RUN_ID}.json"

        assert entries == [expected_filename], (
            f"runs/ should contain exactly [{expected_filename!r}] after harvest; "
            f"got {entries!r} — temp residue or missing record"
        )

        # The record itself must be valid JSON with the expected run_id.
        record_path = os.path.join(runs_dir, expected_filename)
        with open(record_path) as fh:
            record = json.load(fh)

        assert record.get("run_id") == _RUN_ID, (
            f"record run_id should be {_RUN_ID!r}; got {record.get('run_id')!r}"
        )
