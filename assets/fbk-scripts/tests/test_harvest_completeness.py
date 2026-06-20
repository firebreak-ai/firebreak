"""Integration tests for harvest completeness classification.

Covers completeness classification (clean-complete vs truncated), absent-not-invented
gap recording, crashed-unit attribution preservation (decision D-17), and the two
harvest error paths from the interface contract for harvest failure handling:
- missing journal yields truncated with zero fabricated units and no raise
- unreadable events.jsonl returns error and writes nothing

All tests skip while fbk.harvest is absent (red phase). Once harvest is
implemented, every test is expected to pass without modification.
"""

import json
import os
import pytest

try:
    from fbk import harvest
    from fbk.harvest import HarvestResult
    HARVEST_AVAILABLE = True
except ImportError:
    HARVEST_AVAILABLE = False

from tests import capture_fixtures

pytestmark = pytest.mark.skipif(
    not HARVEST_AVAILABLE,
    reason="fbk.harvest module not yet implemented",
)


# ---------------------------------------------------------------------------
# Shared agent definitions
# ---------------------------------------------------------------------------

_TURN = {
    "timestamp": "2026-01-01T00:01:00+00:00",
    "model": "claude-sonnet-4-6",
    "input_tokens": 10,
    "output_tokens": 5,
    "tools": [],
    "sidechain": False,
}

# A valid attribution descriptor — used to verify crashed-unit attribution
# survives independently of the missing result.
_VALID_ATTR_DESCRIPTOR = '<!--fbk-attr {"cardinality": "single", "stance": "collaborative"}-->'

_RESULT_SUCCESS = {"status": "success", "output": "done"}


# ---------------------------------------------------------------------------
# Helper: build an instrumented project with an events.jsonl stub
# ---------------------------------------------------------------------------


def _make_instrumented_project(tmp_path, name="project"):
    """Create an instrumented project tree with a stub events.jsonl."""
    project_root = capture_fixtures.make_project(
        str(tmp_path / name),
        instrumented=True,
        marked=True,
        capture_cfg="standard",
    )
    events_path = os.path.join(project_root, ".fbk-capture", "events.jsonl")
    os.makedirs(os.path.dirname(events_path), exist_ok=True)
    with open(events_path, "w") as fh:
        fh.write("")
    return project_root


# ---------------------------------------------------------------------------
# Test: all-results run is clean-complete
# ---------------------------------------------------------------------------


class TestCleanCompleteRun:
    """harvest classifies a run where every started agent has a result as clean-complete."""

    def test_all_results_yields_clean_complete(self, tmp_path, monkeypatch):
        """A run with a result for every started agent produces completeness == 'clean-complete'."""
        projects_root = str(tmp_path / "projects")
        project_root = _make_instrumented_project(tmp_path)
        run_id = "run-clean-001"

        capture_fixtures.make_workflow_run(
            projects_root,
            run_id=run_id,
            agents=[
                {
                    "agent_id": "agent-alpha",
                    "first_message": _VALID_ATTR_DESCRIPTOR + "\nDo task A.",
                    "turns": [_TURN],
                    "result": _RESULT_SUCCESS,
                },
                {
                    "agent_id": "agent-beta",
                    "first_message": _VALID_ATTR_DESCRIPTOR + "\nDo task B.",
                    "turns": [_TURN],
                    "result": _RESULT_SUCCESS,
                },
            ],
        )

        monkeypatch.setenv("FBK_PROJECTS_ROOT", projects_root)
        result = harvest.harvest(run_id, project_root)

        assert result.completeness == "clean-complete"


# ---------------------------------------------------------------------------
# Test: run with a missing result is truncated
# ---------------------------------------------------------------------------


class TestTruncatedRun:
    """harvest classifies a run where one started agent has no result as truncated."""

    def _build_truncated_run(self, tmp_path, monkeypatch):
        """Build a two-agent run where the second agent has no result; return (result, record)."""
        projects_root = str(tmp_path / "projects")
        project_root = _make_instrumented_project(tmp_path)
        run_id = "run-trunc-001"

        capture_fixtures.make_workflow_run(
            projects_root,
            run_id=run_id,
            agents=[
                {
                    "agent_id": "agent-gamma",
                    "first_message": _VALID_ATTR_DESCRIPTOR + "\nDo task C.",
                    "turns": [_TURN],
                    "result": _RESULT_SUCCESS,
                },
                {
                    "agent_id": "agent-delta",
                    "first_message": _VALID_ATTR_DESCRIPTOR + "\nDo task D.",
                    "turns": [_TURN],
                    "result": None,  # no result — simulates a truncated run
                },
            ],
        )

        monkeypatch.setenv("FBK_PROJECTS_ROOT", projects_root)
        harvest_result = harvest.harvest(run_id, project_root)

        record_path = os.path.join(
            project_root, ".fbk-capture", "runs", f"{run_id}.json"
        )
        with open(record_path) as fh:
            record = json.load(fh)

        return harvest_result, record

    def test_missing_result_yields_truncated(self, tmp_path, monkeypatch):
        """A run with one result-less started agent produces completeness == 'truncated'."""
        harvest_result, _record = self._build_truncated_run(tmp_path, monkeypatch)
        assert harvest_result.completeness == "truncated"

    def test_gapped_unit_journal_result_present_false(self, tmp_path, monkeypatch):
        """The result-less agent's unit entry records journal_result_present as false."""
        _harvest_result, record = self._build_truncated_run(tmp_path, monkeypatch)
        units_by_id = {u["agent_id"]: u for u in record["units"]}
        gapped_unit = units_by_id["agent-delta"]
        assert gapped_unit["journal_result_present"] is False

    def test_gapped_unit_journal_result_null(self, tmp_path, monkeypatch):
        """The result-less agent's unit entry records journal_result as null, not a fabricated value."""
        _harvest_result, record = self._build_truncated_run(tmp_path, monkeypatch)
        units_by_id = {u["agent_id"]: u for u in record["units"]}
        gapped_unit = units_by_id["agent-delta"]
        assert gapped_unit["journal_result"] is None

    def test_gapped_unit_is_present_not_dropped(self, tmp_path, monkeypatch):
        """The result-less agent appears in units — it is recorded, not removed."""
        _harvest_result, record = self._build_truncated_run(tmp_path, monkeypatch)
        agent_ids_in_record = {u["agent_id"] for u in record["units"]}
        assert "agent-delta" in agent_ids_in_record

    def test_unit_count_equals_roster_size(self, tmp_path, monkeypatch):
        """unit_count equals the full roster size — the gapped agent is recorded, not removed."""
        harvest_result, _record = self._build_truncated_run(tmp_path, monkeypatch)
        # Two agents in the roster (one with result, one without).
        assert harvest_result.unit_count == 2


# ---------------------------------------------------------------------------
# Test: crashed-unit attribution survives (decision D-17)
# ---------------------------------------------------------------------------


class TestCrashedUnitAttributionPreserved:
    """A crashed unit (started, no result) keeps the attribution parsed from its own launch message."""

    def test_crashed_unit_attribution_absent_is_false(self, tmp_path, monkeypatch):
        """A result-less agent with a valid descriptor has attribution_absent == false.

        A missing journal result must NOT force attribution_absent to true — the
        descriptor parse result and the journal result are independent facts (D-17).
        """
        projects_root = str(tmp_path / "projects")
        project_root = _make_instrumented_project(tmp_path)
        run_id = "run-attr-001"

        # The crashed agent carries a valid descriptor in its first message.
        capture_fixtures.make_workflow_run(
            projects_root,
            run_id=run_id,
            agents=[
                {
                    "agent_id": "agent-complete",
                    "first_message": _VALID_ATTR_DESCRIPTOR + "\nDo task E.",
                    "turns": [_TURN],
                    "result": _RESULT_SUCCESS,
                },
                {
                    "agent_id": "agent-crashed",
                    "first_message": _VALID_ATTR_DESCRIPTOR + "\nDo task F.",
                    "turns": [_TURN],
                    "result": None,  # crashed — no result line
                },
            ],
        )

        monkeypatch.setenv("FBK_PROJECTS_ROOT", projects_root)
        harvest.harvest(run_id, project_root)

        record_path = os.path.join(
            project_root, ".fbk-capture", "runs", f"{run_id}.json"
        )
        with open(record_path) as fh:
            record = json.load(fh)

        units_by_id = {u["agent_id"]: u for u in record["units"]}
        crashed_unit = units_by_id["agent-crashed"]

        # The missing result is recorded faithfully.
        assert crashed_unit["journal_result_present"] is False
        assert crashed_unit["journal_result"] is None
        # But attribution from the descriptor parse succeeded — it must not be suppressed.
        assert crashed_unit["attribution_absent"] is False


# ---------------------------------------------------------------------------
# Test: missing journal yields truncated with zero fabricated units (IF-D-03)
# ---------------------------------------------------------------------------


class TestMissingJournalErrorPath:
    """harvest returns truncated with no fabricated units when journal.jsonl is absent."""

    def test_missing_journal_yields_truncated_no_fabricated_units_no_raise(
        self, tmp_path, monkeypatch
    ):
        """A run directory with no journal.jsonl produces truncated with zero fabricated units.

        harvest must not raise and must not invent units it cannot source from
        the journal.
        """
        projects_root = str(tmp_path / "projects")
        project_root = _make_instrumented_project(tmp_path)
        run_id = "run-nojrn-001"

        run_dir = capture_fixtures.make_workflow_run(
            projects_root,
            run_id=run_id,
            agents=[
                {
                    "agent_id": "agent-eta",
                    "first_message": "Do task G.",
                    "turns": [_TURN],
                    "result": _RESULT_SUCCESS,
                },
            ],
        )

        # Remove the journal to simulate the missing-journal error path.
        journal_path = os.path.join(run_dir, "journal.jsonl")
        os.remove(journal_path)

        monkeypatch.setenv("FBK_PROJECTS_ROOT", projects_root)

        # harvest must not raise.
        result = harvest.harvest(run_id, project_root)

        assert result.completeness == "truncated"
        # The record must invent zero units — it has no roster to source them from.
        assert result.unit_count == 0


# ---------------------------------------------------------------------------
# Test: unreadable events.jsonl returns error and writes nothing (IF-D-03)
# ---------------------------------------------------------------------------


class TestUnreadableEventsErrorPath:
    """harvest returns an error result and writes no record when events.jsonl is unreadable."""

    def test_unreadable_events_returns_error_no_record_written(
        self, tmp_path, monkeypatch
    ):
        """An unreadable events.jsonl causes harvest to return result.error set and write nothing.

        The absence of a record file is asserted directly — harvest must write
        nothing when the events stream cannot be read.
        """
        projects_root = str(tmp_path / "projects")
        project_root = _make_instrumented_project(tmp_path)
        run_id = "run-badevt-001"

        capture_fixtures.make_workflow_run(
            projects_root,
            run_id=run_id,
            agents=[
                {
                    "agent_id": "agent-theta",
                    "first_message": "Do task H.",
                    "turns": [_TURN],
                    "result": _RESULT_SUCCESS,
                },
            ],
        )

        # Make events.jsonl unreadable (mirrors write_unreadable_transcript pattern).
        events_path = os.path.join(project_root, ".fbk-capture", "events.jsonl")
        os.chmod(events_path, 0o000)

        monkeypatch.setenv("FBK_PROJECTS_ROOT", projects_root)

        try:
            result = harvest.harvest(run_id, project_root)
        finally:
            # Restore permissions so tmp_path cleanup can remove the file.
            os.chmod(events_path, 0o644)

        assert result.error, "result.error must be truthy when events.jsonl is unreadable"

        record_path = os.path.join(
            project_root, ".fbk-capture", "runs", f"{run_id}.json"
        )
        assert not os.path.exists(record_path), (
            "harvest must write no record file when events.jsonl is unreadable"
        )
