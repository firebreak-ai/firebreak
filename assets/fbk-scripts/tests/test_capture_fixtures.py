"""Self-check tests for the capture_fixtures helper module.

These tests validate the fixtures themselves — they own no production
dependency, so they pass in the red phase before any metrics-plane
implementation exists.
"""

import json
import os
from tests import capture_fixtures


_ENVELOPE_FIELDS = {
    "schema_version",
    "event_type",
    "timestamp",
    "spec",
    "stage",
    "source",
    "capture_level",
    "data",
}


def test_event_builder_yields_full_envelope():
    """build_event returns a dict whose key set equals the eight envelope field names."""
    ev = capture_fixtures.build_event(
        event_type="LIFECYCLE",
        source="test-source",
        spec="my-spec",
        stage="QUEUED",
    )
    assert set(ev.keys()) == _ENVELOPE_FIELDS


def test_make_project_writes_sentinel_only_when_marked(tmp_path):
    """sentinel exists only under marked=True; it is absent under marked=False."""
    root_unmarked = capture_fixtures.make_project(str(tmp_path / "a"), instrumented=True, marked=False)
    sentinel_unmarked = os.path.join(root_unmarked, ".claude", "automation", ".fbk-managed")
    assert not os.path.exists(sentinel_unmarked)

    root_marked = capture_fixtures.make_project(str(tmp_path / "b"), instrumented=True, marked=True)
    sentinel_marked = os.path.join(root_marked, ".claude", "automation", ".fbk-managed")
    assert os.path.exists(sentinel_marked)


# ---------------------------------------------------------------------------
# make_workflow_run smoke tests
# ---------------------------------------------------------------------------


def test_make_workflow_run_directory_exists(tmp_path):
    """make_workflow_run returns a path that is an existing directory."""
    run_dir = capture_fixtures.make_workflow_run(
        str(tmp_path / "projects"),
        run_id="run-001",
        agents=[
            {
                "agent_id": "agent-a",
                "first_message": "Do task A.",
                "turns": [],
                "result": {"status": "success"},
            }
        ],
    )
    assert os.path.isdir(run_dir)


def test_make_workflow_run_journal_line_counts(tmp_path):
    """journal.jsonl has two started lines and one result line for two agents where one lacks a result."""
    projects_root = str(tmp_path / "projects")
    run_dir = capture_fixtures.make_workflow_run(
        projects_root,
        run_id="run-002",
        agents=[
            {
                "agent_id": "agent-x",
                "first_message": "Do task X.",
                "turns": [],
                "result": {"status": "success"},
            },
            {
                "agent_id": "agent-y",
                "first_message": "Do task Y.",
                "turns": [],
                "result": None,  # truncated run — no result line
            },
        ],
    )

    journal_path = os.path.join(run_dir, "journal.jsonl")
    with open(journal_path) as fh:
        lines = [json.loads(line) for line in fh if line.strip()]

    started_lines = [entry for entry in lines if entry["type"] == "started"]
    result_lines = [entry for entry in lines if entry["type"] == "result"]

    assert len(started_lines) == 2, f"expected 2 started lines, got {len(started_lines)}"
    assert len(result_lines) == 1, f"expected 1 result line, got {len(result_lines)}"


def test_make_workflow_run_first_transcript_line_text(tmp_path):
    """The first line of an agent transcript carries the supplied first_message text."""
    launch_text = "Please implement the feature described in task-01.md."
    projects_root = str(tmp_path / "projects")
    run_dir = capture_fixtures.make_workflow_run(
        projects_root,
        run_id="run-003",
        agents=[
            {
                "agent_id": "agent-z",
                "first_message": launch_text,
                "turns": [
                    {
                        "timestamp": "2026-01-01T00:01:00+00:00",
                        "model": "claude-sonnet-4-6",
                        "input_tokens": 10,
                        "output_tokens": 5,
                        "tools": [],
                        "sidechain": False,
                    }
                ],
                "result": {"status": "success"},
            }
        ],
    )

    transcript_path = os.path.join(run_dir, "agent-agent-z.jsonl")
    with open(transcript_path) as fh:
        first_line = json.loads(fh.readline())

    assert first_line["message"]["content"][0]["text"] == launch_text
