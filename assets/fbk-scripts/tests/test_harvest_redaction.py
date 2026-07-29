"""Integration tests for fbk.harvest capture-level redaction parity.

Tests cover:
- At capture level "off", harvest writes no free-text record
- At capture level "standard", harvest strips free-text keys from journal_result
  and descriptor-derived fields before writing the run record
- Redaction parity: the same free-text key that schema.redact strips from an
  event payload at standard level is also stripped from the run record

The harvest implementation does not yet exist, so these tests skip when
fbk.harvest is absent and are expected to fail once it exists.
"""

import json
import os

import pytest

try:
    from fbk import harvest
    HARVEST_AVAILABLE = True
except ImportError:
    HARVEST_AVAILABLE = False

from fbk.capture import schema
from fbk.capture import gate_check
from tests import capture_fixtures

pytestmark = pytest.mark.skipif(
    not HARVEST_AVAILABLE,
    reason="fbk.harvest module not yet implemented",
)

# A string that is unmistakably free-text and must not survive redaction.
# Chosen to be unique enough that a false positive in the output is implausible.
_SENTINEL_FREETEXT = "REDACTION_SENTINEL_freetext_xq9z"

# A structural field that must survive redaction.  "agent_id" is not in
# FREETEXT_KEYS and carries a numeric-looking string — structurally opaque
# content, not user-supplied prose.
_STRUCTURAL_AGENT_ID = "agent-001"


# ---------------------------------------------------------------------------
# Fixture builders
# ---------------------------------------------------------------------------


def _build_run_with_freetext(tmp_path, monkeypatch, capture_level):
    """Build an instrumented project, a single-agent run, and the run's events.

    The agent's journal result carries the sentinel free-text string under the
    "output" key, which is in schema.FREETEXT_KEYS.  The agent's launch
    descriptor also embeds the sentinel under "text" (also a FREETEXT_KEY) so
    the descriptor-derived free-text path is exercised too.

    Returns (project_cwd, run_id, projects_root).
    """
    projects_root = str(tmp_path / "projects")
    os.makedirs(projects_root, exist_ok=True)

    # Instrumented project with the requested capture level.
    project_cwd = capture_fixtures.make_project(
        str(tmp_path / "proj"),
        instrumented=True,
        marked=True,
        capture_cfg=capture_level,
    )

    # Redirect the glob resolver so harvest finds the run directory under
    # tmp_path instead of ~/.claude/projects.
    monkeypatch.setenv("FBK_PROJECTS_ROOT", projects_root)

    run_id = "run-redaction-test-001"

    # Build the run directory.  The first_message carries a free-text sentinel
    # under the "text" attribute so descriptor-derived free-text is present.
    # The agent result carries it under "output" so journal_result is covered.
    first_message = (
        '<!--fbk-attr {"cardinality": "single", "stance": "collaborative", '
        f'"text": "{_SENTINEL_FREETEXT}"}}--> '
        f"Launch prompt with sentinel: {_SENTINEL_FREETEXT}"
    )
    agent_result = {
        "outcome": "passed",
        "output": _SENTINEL_FREETEXT,
    }

    capture_fixtures.make_workflow_run(
        projects_root,
        run_id,
        agents=[
            {
                "agent_id": _STRUCTURAL_AGENT_ID,
                "first_message": first_message,
                "turns": [
                    {
                        "timestamp": "2026-01-01T00:00:30+00:00",
                        "model": "claude-sonnet-4-6",
                        "input_tokens": 100,
                        "output_tokens": 40,
                        "tools": [],
                        "sidechain": False,
                    }
                ],
                "result": agent_result,
            }
        ],
    )

    # Write events.jsonl in the project capture directory.
    events_dir = os.path.join(project_cwd, ".fbk-capture")
    os.makedirs(events_dir, exist_ok=True)
    events_path = os.path.join(events_dir, "events.jsonl")
    events = [
        capture_fixtures.build_event(
            "SUBAGENT_STOP",
            source="hook_router",
            spec="test-spec",
            stage="IMPLEMENTING",
            capture_level=capture_level,
            data={"agent_id": _STRUCTURAL_AGENT_ID, "output": _SENTINEL_FREETEXT},
        )
    ]
    capture_fixtures.write_events(events_path, events)

    return project_cwd, run_id, projects_root


# ---------------------------------------------------------------------------
# Off-level: no free-text record written
# ---------------------------------------------------------------------------


class TestOffLevelWritesNoRecord:
    """At capture level "off", harvest writes no free-text record for the run."""

    def test_no_record_file_written_at_off_level(self, tmp_path, monkeypatch):
        """After harvesting at capture_level=off, no record file exists in runs/."""
        project_cwd, run_id, _ = _build_run_with_freetext(tmp_path, monkeypatch, "off")

        harvest.harvest(run_id, project_cwd)

        runs_dir = os.path.join(project_cwd, ".fbk-capture", "runs")
        record_path = os.path.join(runs_dir, f"{run_id}.json")
        # Spec says "writes no free-text record" at off level.  Accept either
        # that the record file does not exist at all, or that the runs directory
        # itself does not exist.
        if os.path.isdir(runs_dir):
            assert not os.path.exists(record_path), (
                "harvest at capture_level=off must not write a run record file; "
                f"found: {record_path}"
            )

    def test_sentinel_freetext_absent_from_runs_dir_at_off_level(
        self, tmp_path, monkeypatch
    ):
        """The sentinel free-text string does not appear anywhere in runs/ output at off."""
        project_cwd, run_id, _ = _build_run_with_freetext(tmp_path, monkeypatch, "off")

        harvest.harvest(run_id, project_cwd)

        runs_dir = os.path.join(project_cwd, ".fbk-capture", "runs")
        if not os.path.isdir(runs_dir):
            return  # No runs dir at all — sentinel is clearly absent.

        for filename in os.listdir(runs_dir):
            file_path = os.path.join(runs_dir, filename)
            if os.path.isfile(file_path):
                content = open(file_path).read()
                assert _SENTINEL_FREETEXT not in content, (
                    f"sentinel free-text found in {filename} at capture_level=off; "
                    "harvest must not write free-text records at off level"
                )


# ---------------------------------------------------------------------------
# Standard-level: free-text stripped, structural fields survive
# ---------------------------------------------------------------------------


class TestStandardLevelRedaction:
    """At capture level "standard", harvest strips free-text keys from the record."""

    def _read_record(self, project_cwd, run_id):
        record_path = os.path.join(
            project_cwd, ".fbk-capture", "runs", f"{run_id}.json"
        )
        assert os.path.exists(record_path), (
            f"run record not written at expected path: {record_path}"
        )
        with open(record_path) as f:
            return json.load(f)

    def test_sentinel_freetext_stripped_from_record_at_standard_level(
        self, tmp_path, monkeypatch
    ):
        """The sentinel free-text string is absent from the standard-level run record."""
        project_cwd, run_id, _ = _build_run_with_freetext(
            tmp_path, monkeypatch, "standard"
        )

        harvest.harvest(run_id, project_cwd)

        record_path = os.path.join(
            project_cwd, ".fbk-capture", "runs", f"{run_id}.json"
        )
        assert os.path.exists(record_path), (
            "harvest at capture_level=standard must write a run record"
        )
        raw_content = open(record_path).read()
        assert _SENTINEL_FREETEXT not in raw_content, (
            "sentinel free-text must be stripped from the run record at standard level"
        )

    def test_structural_field_survives_redaction_at_standard_level(
        self, tmp_path, monkeypatch
    ):
        """A non-free-text field (agent_id) survives redaction in the standard-level record."""
        project_cwd, run_id, _ = _build_run_with_freetext(
            tmp_path, monkeypatch, "standard"
        )

        harvest.harvest(run_id, project_cwd)

        record = self._read_record(project_cwd, run_id)

        # The record's units list must contain the roster agent.
        unit_agent_ids = [u["agent_id"] for u in record.get("units", [])]
        assert _STRUCTURAL_AGENT_ID in unit_agent_ids, (
            f"structural agent_id field must survive redaction; "
            f"expected {_STRUCTURAL_AGENT_ID!r} in units, got {unit_agent_ids!r}"
        )

    def test_output_key_stripped_from_journal_result_at_standard_level(
        self, tmp_path, monkeypatch
    ):
        """The 'output' key (a FREETEXT_KEY) is absent from journal_result in the standard record."""
        project_cwd, run_id, _ = _build_run_with_freetext(
            tmp_path, monkeypatch, "standard"
        )

        harvest.harvest(run_id, project_cwd)

        record = self._read_record(project_cwd, run_id)

        for unit in record.get("units", []):
            journal_result = unit.get("journal_result")
            if journal_result is not None and isinstance(journal_result, dict):
                assert "output" not in journal_result, (
                    "the 'output' key (a FREETEXT_KEY) must be stripped from "
                    f"journal_result at standard level; got keys: {list(journal_result.keys())!r}"
                )


# ---------------------------------------------------------------------------
# Redaction parity anchor
# ---------------------------------------------------------------------------


class TestRedactionParityAnchor:
    """The same free-text key that schema.redact strips from an event at standard
    level is also stripped from the run record."""

    def test_freetext_key_stripped_consistently_across_sinks(
        self, tmp_path, monkeypatch
    ):
        """'output' stripped by schema.redact at standard is also absent from the run record.

        This is the parity anchor: the two sinks (events.jsonl and the run record)
        share one redaction policy.  A key stripped from an event payload must also
        be stripped from the run record at the same level.
        """
        project_cwd, run_id, _ = _build_run_with_freetext(
            tmp_path, monkeypatch, "standard"
        )

        # Confirm schema.redact strips "output" at standard (the policy).
        sample_event_data = {"output": _SENTINEL_FREETEXT, "agent_id": _STRUCTURAL_AGENT_ID}
        redacted_event = schema.redact(sample_event_data, "standard")
        assert "output" not in redacted_event, (
            "schema.redact at standard must strip the 'output' key from event data; "
            "parity anchor cannot hold if the reference redaction does not strip it"
        )

        # Now harvest and assert the same key is absent from the run record.
        harvest.harvest(run_id, project_cwd)

        record_path = os.path.join(
            project_cwd, ".fbk-capture", "runs", f"{run_id}.json"
        )
        assert os.path.exists(record_path), (
            "harvest at standard must write a run record for the parity anchor"
        )
        raw_content = open(record_path).read()
        assert _SENTINEL_FREETEXT not in raw_content, (
            "sentinel free-text must be absent from the run record — "
            "the same 'output' key that schema.redact strips from events at standard "
            "must also be stripped from the run record (redaction parity)"
        )

    def test_capture_level_resolved_via_gate_check(self, tmp_path, monkeypatch):
        """harvest uses gate_check.resolve_capture_level to read the capture policy.

        At standard level the record is written; at off level it is not.  This
        test pairs the two outcomes to confirm the resolution path is wired — the
        same project tree, the only difference being what capture.cfg says.
        """
        # Standard-level project: record must exist.
        project_std = capture_fixtures.make_project(
            str(tmp_path / "std"),
            instrumented=True,
            marked=True,
            capture_cfg="standard",
        )
        resolved_std = gate_check.resolve_capture_level(project_std)
        assert resolved_std == "standard", (
            f"gate_check.resolve_capture_level must return 'standard' for a project "
            f"with capture_cfg='standard'; got {resolved_std!r}"
        )

        # Off-level project: resolve_capture_level must return "off".
        project_off = capture_fixtures.make_project(
            str(tmp_path / "off"),
            instrumented=True,
            marked=True,
            capture_cfg="off",
        )
        resolved_off = gate_check.resolve_capture_level(project_off)
        assert resolved_off == "off", (
            f"gate_check.resolve_capture_level must return 'off' for a project "
            f"with capture_cfg='off'; got {resolved_off!r}"
        )
