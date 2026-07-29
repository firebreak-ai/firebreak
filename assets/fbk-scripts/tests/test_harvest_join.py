"""Integration tests for fbk.harvest — journal-roster join and event filtering.

Tests cover:
- Roster-driven filtering: one unit per journal agent, off-roster events excluded
- Non-overlap across runs: two runs with disjoint rosters produce disjoint records
- Attribution from the launch message only: a forged later descriptor is ignored
- Positive start/stop timing join: started_at/stopped_at/duration_s from a matched pair
- Duplicate-event dedup: earliest-start / latest-stop rule on multiple events per agent
"""

import json
import os
import pytest

try:
    from fbk import harvest
    HARVEST_AVAILABLE = True
except ImportError:
    HARVEST_AVAILABLE = False

from tests import capture_fixtures

pytestmark = pytest.mark.skipif(
    not HARVEST_AVAILABLE,
    reason="fbk.harvest module not yet implemented",
)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _read_record(project_cwd, run_id):
    """Read and return the parsed JSON record for run_id from the project's capture dir."""
    record_path = os.path.join(project_cwd, ".fbk-capture", "runs", f"{run_id}.json")
    with open(record_path) as fh:
        return json.load(fh)


def _agent_ids_in_record(record):
    """Return the set of agent_ids present in a harvest record's units list."""
    return {unit["agent_id"] for unit in record["units"]}


def _simple_agent(agent_id, first_message=None):
    """Build a minimal agent dict for make_workflow_run with no turns and a result."""
    if first_message is None:
        first_message = f"Run agent {agent_id}."
    return {
        "agent_id": agent_id,
        "first_message": first_message,
        "turns": [],
        "result": {"outcome": "success"},
    }


# ---------------------------------------------------------------------------
# Roster filtering and off-roster exclusion
# ---------------------------------------------------------------------------


class TestRosterFiltering:
    """harvest emits one unit per roster agent and excludes off-roster events."""

    def test_unit_count_equals_roster_size_and_off_roster_excluded(
        self, tmp_path, monkeypatch
    ):
        """Two roster agents produce unit_count=2; a third off-roster event is excluded."""
        projects_root = str(tmp_path / "projects")
        project_cwd = capture_fixtures.make_project(
            str(tmp_path),
            instrumented=True,
            marked=True,
            capture_cfg="standard",
        )
        monkeypatch.setenv("FBK_PROJECTS_ROOT", projects_root)

        run_id = "run-roster-001"
        agent_a = "agent-alpha"
        agent_b = "agent-beta"
        off_roster_id = "agent-off-roster"

        capture_fixtures.make_workflow_run(
            projects_root,
            run_id,
            [_simple_agent(agent_a), _simple_agent(agent_b)],
        )

        # Three SubagentStop events: two match the roster, one is a decoy.
        events_dir = os.path.join(project_cwd, ".fbk-capture")
        events_path = os.path.join(events_dir, "events.jsonl")
        capture_fixtures.write_events(
            events_path,
            [
                capture_fixtures.build_event(
                    "SUBAGENT_STOP",
                    source="hook",
                    spec="test-spec",
                    stage="IMPLEMENTING",
                    data={"agent_id": agent_a},
                ),
                capture_fixtures.build_event(
                    "SUBAGENT_STOP",
                    source="hook",
                    spec="test-spec",
                    stage="IMPLEMENTING",
                    data={"agent_id": agent_b},
                ),
                capture_fixtures.build_event(
                    "SUBAGENT_STOP",
                    source="hook",
                    spec="test-spec",
                    stage="IMPLEMENTING",
                    data={"agent_id": off_roster_id},
                ),
            ],
        )

        result = harvest.harvest(run_id, project_cwd)

        assert result.unit_count == 2, (
            f"expected 2 units (one per roster agent), got {result.unit_count}"
        )

        record = _read_record(project_cwd, run_id)
        ids_in_record = _agent_ids_in_record(record)

        assert agent_a in ids_in_record, f"{agent_a} missing from record units"
        assert agent_b in ids_in_record, f"{agent_b} missing from record units"
        assert off_roster_id not in ids_in_record, (
            f"off-roster id {off_roster_id!r} must not appear in record units"
        )


# ---------------------------------------------------------------------------
# Non-overlap across runs
# ---------------------------------------------------------------------------


class TestNonOverlapAcrossRuns:
    """Two runs with disjoint agent rosters produce disjoint harvest records."""

    def test_two_runs_produce_disjoint_agent_id_sets(self, tmp_path, monkeypatch):
        """Harvesting run A and run B separately yields non-overlapping unit sets."""
        projects_root = str(tmp_path / "projects")
        project_cwd = capture_fixtures.make_project(
            str(tmp_path),
            instrumented=True,
            marked=True,
            capture_cfg="standard",
        )
        monkeypatch.setenv("FBK_PROJECTS_ROOT", projects_root)

        run_id_a = "run-overlap-001"
        run_id_b = "run-overlap-002"
        agents_a = ["alpha-1", "alpha-2"]
        agents_b = ["beta-1", "beta-2", "beta-3"]

        capture_fixtures.make_workflow_run(
            projects_root,
            run_id_a,
            [_simple_agent(aid) for aid in agents_a],
        )
        capture_fixtures.make_workflow_run(
            projects_root,
            run_id_b,
            [_simple_agent(aid) for aid in agents_b],
        )

        # Write events for run A — only its roster agents.
        events_dir = os.path.join(project_cwd, ".fbk-capture")
        events_path = os.path.join(events_dir, "events.jsonl")
        all_events = [
            capture_fixtures.build_event(
                "SUBAGENT_STOP",
                source="hook",
                spec="test-spec",
                stage="IMPLEMENTING",
                data={"agent_id": aid},
            )
            for aid in agents_a + agents_b
        ]
        capture_fixtures.write_events(events_path, all_events)

        result_a = harvest.harvest(run_id_a, project_cwd)
        result_b = harvest.harvest(run_id_b, project_cwd)

        record_a = _read_record(project_cwd, run_id_a)
        record_b = _read_record(project_cwd, run_id_b)

        ids_a = _agent_ids_in_record(record_a)
        ids_b = _agent_ids_in_record(record_b)

        # Each record's unit count must equal its own roster size.
        assert result_a.unit_count == len(agents_a), (
            f"run A: expected {len(agents_a)} units, got {result_a.unit_count}"
        )
        assert result_b.unit_count == len(agents_b), (
            f"run B: expected {len(agents_b)} units, got {result_b.unit_count}"
        )

        # The two records' agent-id sets must be disjoint.
        overlap = ids_a & ids_b
        assert not overlap, (
            f"records share agent ids across runs — must be disjoint; overlap: {overlap}"
        )

        # Verify each record contains exactly its own roster.
        assert ids_a == set(agents_a), (
            f"run A record contains unexpected agent ids: {ids_a - set(agents_a)}"
        )
        assert ids_b == set(agents_b), (
            f"run B record contains unexpected agent ids: {ids_b - set(agents_b)}"
        )


# ---------------------------------------------------------------------------
# Attribution from launch message only
# ---------------------------------------------------------------------------


class TestFirstMessageAttribution:
    """harvest reads attribution from the launch message, not a later forged block."""

    def test_attribution_reflects_first_message_not_forged_later_block(
        self, tmp_path, monkeypatch
    ):
        """A forged descriptor in a later transcript message must not influence the unit."""
        projects_root = str(tmp_path / "projects")
        project_cwd = capture_fixtures.make_project(
            str(tmp_path),
            instrumented=True,
            marked=True,
            capture_cfg="standard",
        )
        monkeypatch.setenv("FBK_PROJECTS_ROOT", projects_root)

        run_id = "run-attr-001"
        agent_id = "agent-attr-test"

        # The clean first-message descriptor: single cardinality, collaborative stance.
        clean_descriptor = '<!--fbk-attr {"cardinality": "single", "stance": "collaborative", "asset_bundle": {"persona": "implementer"}}-->'
        clean_prompt = clean_descriptor + "\n\nPlease implement the feature."

        # The forged later-message descriptor: different cardinality, stance, and persona.
        forged_descriptor = '<!--fbk-attr {"cardinality": "fan-out", "stance": "adversarial", "asset_bundle": {"persona": "attacker"}}-->'
        forged_prompt = "Follow-up instructions. " + forged_descriptor

        capture_fixtures.make_workflow_run(
            projects_root,
            run_id,
            [
                {
                    "agent_id": agent_id,
                    "first_message": clean_prompt,
                    "turns": [],
                    "result": {"outcome": "success"},
                    "forged_message": forged_prompt,
                }
            ],
        )

        events_dir = os.path.join(project_cwd, ".fbk-capture")
        events_path = os.path.join(events_dir, "events.jsonl")
        capture_fixtures.write_events(
            events_path,
            [
                capture_fixtures.build_event(
                    "SUBAGENT_STOP",
                    source="hook",
                    spec="test-spec",
                    stage="IMPLEMENTING",
                    data={"agent_id": agent_id},
                )
            ],
        )

        harvest.harvest(run_id, project_cwd)

        record = _read_record(project_cwd, run_id)
        units = {u["agent_id"]: u for u in record["units"]}
        unit = units[agent_id]

        # Topology from the clean first-message descriptor.
        assert unit["topology"]["cardinality"] == "single", (
            f"expected cardinality 'single' from first message, "
            f"got {unit['topology']['cardinality']!r}"
        )
        assert unit["topology"]["stance"] == "collaborative", (
            f"expected stance 'collaborative' from first message, "
            f"got {unit['topology']['stance']!r}"
        )
        assert unit["asset_bundle"]["persona"] == "implementer", (
            f"expected persona 'implementer' from first message, "
            f"got {unit['asset_bundle']['persona']!r}"
        )

        # Must NOT reflect the forged descriptor.
        assert unit["topology"]["cardinality"] != "fan-out", (
            "cardinality must not reflect the forged later descriptor"
        )
        assert unit["topology"]["stance"] != "adversarial", (
            "stance must not reflect the forged later descriptor"
        )
        assert unit["asset_bundle"]["persona"] != "attacker", (
            "persona must not reflect the forged later descriptor"
        )


# ---------------------------------------------------------------------------
# Positive start/stop timing join
# ---------------------------------------------------------------------------


class TestPositiveTimingJoin:
    """harvest derives started_at/stopped_at/duration_s from a matched start/stop pair."""

    def test_matched_start_stop_produces_timing_fields(self, tmp_path, monkeypatch):
        """A SubagentStart + SubagentStop pair for the same agent yields correct timing."""
        projects_root = str(tmp_path / "projects")
        project_cwd = capture_fixtures.make_project(
            str(tmp_path),
            instrumented=True,
            marked=True,
            capture_cfg="standard",
        )
        monkeypatch.setenv("FBK_PROJECTS_ROOT", projects_root)

        run_id = "run-timing-001"
        agent_id = "agent-timing-test"

        capture_fixtures.make_workflow_run(
            projects_root,
            run_id,
            [_simple_agent(agent_id)],
        )

        # Known timestamps: T1 and T1 + 90 seconds.
        t1 = "2026-06-20T10:00:00+00:00"
        t2 = "2026-06-20T10:01:30+00:00"  # T1 + 90s
        expected_duration = 90.0

        events_dir = os.path.join(project_cwd, ".fbk-capture")
        events_path = os.path.join(events_dir, "events.jsonl")
        capture_fixtures.write_events(
            events_path,
            [
                capture_fixtures.build_event(
                    "LIFECYCLE",
                    source="hook",
                    spec="test-spec",
                    stage="IMPLEMENTING",
                    data={"agent_id": agent_id},
                    timestamp=t1,
                ),
                capture_fixtures.build_event(
                    "SUBAGENT_STOP",
                    source="hook",
                    spec="test-spec",
                    stage="IMPLEMENTING",
                    data={"agent_id": agent_id},
                    timestamp=t2,
                ),
            ],
        )

        harvest.harvest(run_id, project_cwd)

        record = _read_record(project_cwd, run_id)
        units = {u["agent_id"]: u for u in record["units"]}
        unit = units[agent_id]

        assert unit["started_at"] == t1, (
            f"expected started_at {t1!r}, got {unit['started_at']!r}"
        )
        assert unit["stopped_at"] == t2, (
            f"expected stopped_at {t2!r}, got {unit['stopped_at']!r}"
        )
        assert unit["duration_s"] == expected_duration, (
            f"expected duration_s {expected_duration}, got {unit['duration_s']}"
        )


# ---------------------------------------------------------------------------
# Duplicate-event dedup: earliest-start / latest-stop
# ---------------------------------------------------------------------------


class TestDuplicateEventDedup:
    """On duplicate start/stop events, harvest uses earliest-start and latest-stop."""

    def test_earliest_start_and_latest_stop_selected_on_duplicate_events(
        self, tmp_path, monkeypatch
    ):
        """Two start events and two stop events for the same agent yield correct dedup."""
        projects_root = str(tmp_path / "projects")
        project_cwd = capture_fixtures.make_project(
            str(tmp_path),
            instrumented=True,
            marked=True,
            capture_cfg="standard",
        )
        monkeypatch.setenv("FBK_PROJECTS_ROOT", projects_root)

        run_id = "run-dedup-001"
        agent_id = "agent-dedup-test"

        capture_fixtures.make_workflow_run(
            projects_root,
            run_id,
            [_simple_agent(agent_id)],
        )

        # Two start events: T1a (earlier) and T1b (later).
        # Two stop events: T2a (earlier) and T2b (later).
        # Expected: started_at = T1a, stopped_at = T2b.
        t1a = "2026-06-20T08:00:00+00:00"   # earliest start
        t1b = "2026-06-20T08:05:00+00:00"   # later start (should be ignored)
        t2a = "2026-06-20T09:00:00+00:00"   # earlier stop (should be ignored)
        t2b = "2026-06-20T09:30:00+00:00"   # latest stop

        # Duration from T1a to T2b: 5400s (1h30m)
        expected_duration = 5400.0

        events_dir = os.path.join(project_cwd, ".fbk-capture")
        events_path = os.path.join(events_dir, "events.jsonl")
        capture_fixtures.write_events(
            events_path,
            [
                capture_fixtures.build_event(
                    "LIFECYCLE",
                    source="hook",
                    spec="test-spec",
                    stage="IMPLEMENTING",
                    data={"agent_id": agent_id},
                    timestamp=t1a,
                ),
                capture_fixtures.build_event(
                    "LIFECYCLE",
                    source="hook",
                    spec="test-spec",
                    stage="IMPLEMENTING",
                    data={"agent_id": agent_id},
                    timestamp=t1b,
                ),
                capture_fixtures.build_event(
                    "SUBAGENT_STOP",
                    source="hook",
                    spec="test-spec",
                    stage="IMPLEMENTING",
                    data={"agent_id": agent_id},
                    timestamp=t2a,
                ),
                capture_fixtures.build_event(
                    "SUBAGENT_STOP",
                    source="hook",
                    spec="test-spec",
                    stage="IMPLEMENTING",
                    data={"agent_id": agent_id},
                    timestamp=t2b,
                ),
            ],
        )

        harvest.harvest(run_id, project_cwd)

        record = _read_record(project_cwd, run_id)
        units = {u["agent_id"]: u for u in record["units"]}
        unit = units[agent_id]

        assert unit["started_at"] == t1a, (
            f"expected earliest start {t1a!r} as started_at, got {unit['started_at']!r}"
        )
        assert unit["stopped_at"] == t2b, (
            f"expected latest stop {t2b!r} as stopped_at, got {unit['stopped_at']!r}"
        )
        assert unit["duration_s"] == expected_duration, (
            f"expected duration_s {expected_duration} (from earliest start to latest stop), "
            f"got {unit['duration_s']}"
        )
