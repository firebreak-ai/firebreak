"""Unit tests for fbk.run_retro — run record reader rendering and determinism.

Tests cover:
- Null canonical fields render as an em dash; populated fields render verbatim
- Byte-identical output across two consecutive reads at different wall-clock instants
- No current-timestamp substring leaked into output
- Stable content-derived unit ordering (by unit/agent id)
- Absent record file prints a line containing "no harvest record"
- Corrupt/unparseable file prints "malformed record" and NOT "no harvest record"
- Truncated-completeness record prints a line containing "partial record"
- Reader renders from record alone; no events.jsonl present or required
"""

import json
import re
from pathlib import Path

import pytest

# ---------------------------------------------------------------------------
# Red-phase guard — skip all tests until fbk.run_retro exists
# ---------------------------------------------------------------------------

try:
    from fbk import run_retro as _run_retro_module
    from fbk.run_retro import run_retro
    _RUN_RETRO_AVAILABLE = True
except ImportError:
    _run_retro_module = None
    run_retro = None
    _RUN_RETRO_AVAILABLE = False

pytestmark = pytest.mark.skipif(
    not _RUN_RETRO_AVAILABLE,
    reason="fbk.run_retro not yet implemented",
)

# ---------------------------------------------------------------------------
# Record path convention
# ---------------------------------------------------------------------------

_RUNS_REL = ".fbk-capture/runs"


def _write_run_record(project_cwd: Path, run_id: str, record: dict) -> Path:
    """Write a run record JSON file at the canonical path; return the file path."""
    runs_dir = project_cwd / _RUNS_REL
    runs_dir.mkdir(parents=True, exist_ok=True)
    record_path = runs_dir / f"{run_id}.json"
    record_path.write_text(json.dumps(record, indent=2))
    return record_path


def _make_finalized_unit(
    unit_id: str,
    agent_id: str,
    shape=None,
    topology_cardinality=None,
    topology_stance=None,
    persona=None,
    started_at=None,
    stopped_at=None,
    duration_s=None,
    tokens_input=None,
    tokens_output=None,
    tokens_cache_read=None,
    tokens_cache_write=None,
    gate_outcome=None,
) -> dict:
    """Return a unit entry using the canonical nested schema shape.

    Fields explicitly passed as None stay None in the record (null in JSON),
    so the reader's em-dash rendering is exercised for those slots.
    """
    return {
        "unit_id": unit_id,
        "agent_id": agent_id,
        "shape": shape,
        "topology": {
            "cardinality": topology_cardinality,
            "stance": topology_stance,
        },
        "asset_bundle": {
            "persona": persona,
        },
        "started_at": started_at,
        "stopped_at": stopped_at,
        "duration_s": duration_s,
        "tokens": {
            "input": tokens_input,
            "output": tokens_output,
            "cache_read": tokens_cache_read,
            "cache_write": tokens_cache_write,
        },
        "gate_outcome": gate_outcome,
    }


def _make_finalized_record(units: list, completeness: str = "complete") -> dict:
    """Return a minimal finalized run record wrapping the given units list."""
    return {
        "finalized": True,
        "completeness": completeness,
        "units": units,
    }


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------


class TestEmDashNullRendering:
    """Null canonical fields render as em dash; populated fields appear verbatim."""

    def test_null_field_renders_em_dash_populated_field_appears_verbatim(
        self, tmp_path, capsys
    ):
        """shape=null renders as em dash; duration_s value appears verbatim in output."""
        run_id = "retro-null-test"
        unit = _make_finalized_unit(
            unit_id="unit-1",
            agent_id="agent-alpha",
            shape=None,                  # null — must render as em dash
            topology_cardinality="1:1",
            topology_stance=None,        # null — must render as em dash
            persona="engineer",
            started_at="2026-01-01T00:00:00+00:00",
            stopped_at="2026-01-01T01:00:00+00:00",
            duration_s=3600,             # populated — must appear verbatim
            tokens_input=1000,
            tokens_output=500,
            tokens_cache_read=0,
            tokens_cache_write=0,
            gate_outcome="pass",
        )
        record = _make_finalized_record([unit])
        _write_run_record(tmp_path, run_id, record)

        run_retro(run_id, str(tmp_path))
        out = capsys.readouterr().out

        assert "—" in out, (
            "em dash missing — null field (shape or topology.stance) must render as —"
        )
        assert "3600" in out, (
            "populated duration_s value 3600 must appear verbatim in output"
        )
        assert "1:1" in out, (
            "populated topology.cardinality value '1:1' must appear verbatim in output"
        )


class TestDeterminism:
    """Two consecutive run_retro calls on the same record produce byte-identical output
    and contain no current-timestamp substring."""

    def test_two_reads_produce_byte_identical_output(self, tmp_path, capsys):
        """Output of read A equals output of read B — no wall-clock value leaks in."""
        run_id = "retro-determinism-test"
        units = [
            _make_finalized_unit(
                unit_id="unit-1",
                agent_id="agent-alpha",
                shape="leaf",
                topology_cardinality="1:1",
                topology_stance="active",
                persona="engineer",
                started_at="2026-01-01T00:00:00+00:00",
                stopped_at="2026-01-01T01:00:00+00:00",
                duration_s=3600,
                tokens_input=1000,
                tokens_output=500,
                tokens_cache_read=100,
                tokens_cache_write=50,
                gate_outcome="pass",
            ),
            _make_finalized_unit(
                unit_id="unit-2",
                agent_id="agent-beta",
                shape="orchestrator",
                topology_cardinality="1:N",
                topology_stance="active",
                persona="reviewer",
                started_at="2026-01-01T02:00:00+00:00",
                stopped_at="2026-01-01T03:00:00+00:00",
                duration_s=3601,
                tokens_input=2000,
                tokens_output=800,
                tokens_cache_read=200,
                tokens_cache_write=100,
                gate_outcome="fail",
            ),
        ]
        record = _make_finalized_record(units)
        _write_run_record(tmp_path, run_id, record)

        run_retro(run_id, str(tmp_path))
        out_a = capsys.readouterr().out

        run_retro(run_id, str(tmp_path))
        out_b = capsys.readouterr().out

        assert out_a == out_b, (
            "run_retro produced different output across two calls on the same record — "
            "output must be a pure function of the record, independent of wall-clock time"
        )

    def test_output_contains_no_current_timestamp(self, tmp_path, capsys):
        """Output must not contain the current wall-clock time (no ISO-8601 'now' leak)."""
        import datetime

        run_id = "retro-no-clock-test"
        unit = _make_finalized_unit(
            unit_id="unit-1",
            agent_id="agent-alpha",
            shape="leaf",
            topology_cardinality="1:1",
            topology_stance="active",
            persona="engineer",
            started_at="2026-01-01T00:00:00+00:00",
            stopped_at="2026-01-01T01:00:00+00:00",
            duration_s=3600,
            tokens_input=1000,
            tokens_output=500,
            tokens_cache_read=0,
            tokens_cache_write=0,
            gate_outcome="pass",
        )
        record = _make_finalized_record([unit])
        _write_run_record(tmp_path, run_id, record)

        before = datetime.datetime.now(datetime.timezone.utc)
        run_retro(run_id, str(tmp_path))
        after = datetime.datetime.now(datetime.timezone.utc)
        out = capsys.readouterr().out

        # An ISO-8601 time pattern with hours/minutes/seconds — T##:##:## — that
        # matches today's date prefix indicates a wall-clock leak.
        today_prefix = before.strftime("%Y-%m-%d")
        # Timestamps written in the fixture record are from 2026-01-01 so they
        # won't match today's date; only a clock-leaked timestamp would match.
        current_day_iso_pattern = re.compile(
            re.escape(today_prefix) + r"T\d{2}:\d{2}:\d{2}"
        )
        assert not current_day_iso_pattern.search(out), (
            "output contains a current-date ISO-8601 timestamp — "
            "the reader must not read the wall clock"
        )


class TestContentDerivedOrdering:
    """Units render in stable content-derived order (by unit_id or agent_id),
    not insertion or clock order."""

    def test_units_render_in_content_sorted_order(self, tmp_path, capsys):
        """Unit ids appear in lexicographic order in the output, regardless of record order."""
        run_id = "retro-ordering-test"
        # Insert units in reverse order so that insertion order != sorted order.
        units = [
            _make_finalized_unit(
                unit_id="unit-z",
                agent_id="agent-z",
                shape="leaf",
                topology_cardinality="1:1",
                topology_stance="active",
                persona="engineer",
                started_at="2026-01-01T00:00:00+00:00",
                stopped_at="2026-01-01T01:00:00+00:00",
                duration_s=3600,
                tokens_input=100,
                tokens_output=50,
                tokens_cache_read=0,
                tokens_cache_write=0,
                gate_outcome="pass",
            ),
            _make_finalized_unit(
                unit_id="unit-a",
                agent_id="agent-a",
                shape="leaf",
                topology_cardinality="1:1",
                topology_stance="active",
                persona="engineer",
                started_at="2026-01-01T02:00:00+00:00",
                stopped_at="2026-01-01T03:00:00+00:00",
                duration_s=3601,
                tokens_input=200,
                tokens_output=80,
                tokens_cache_read=0,
                tokens_cache_write=0,
                gate_outcome="pass",
            ),
            _make_finalized_unit(
                unit_id="unit-m",
                agent_id="agent-m",
                shape="leaf",
                topology_cardinality="1:1",
                topology_stance="active",
                persona="engineer",
                started_at="2026-01-01T04:00:00+00:00",
                stopped_at="2026-01-01T05:00:00+00:00",
                duration_s=3602,
                tokens_input=300,
                tokens_output=120,
                tokens_cache_read=0,
                tokens_cache_write=0,
                gate_outcome="pass",
            ),
        ]
        record = _make_finalized_record(units)
        _write_run_record(tmp_path, run_id, record)

        run_retro(run_id, str(tmp_path))
        out = capsys.readouterr().out

        pos_a = out.find("unit-a")
        pos_m = out.find("unit-m")
        pos_z = out.find("unit-z")

        assert pos_a != -1, "'unit-a' must appear in output"
        assert pos_m != -1, "'unit-m' must appear in output"
        assert pos_z != -1, "'unit-z' must appear in output"
        assert pos_a < pos_m < pos_z, (
            "units must render in content-sorted order (unit-a before unit-m before unit-z); "
            f"found positions: unit-a={pos_a}, unit-m={pos_m}, unit-z={pos_z}"
        )


class TestAbsentRecord:
    """Reader prints a line containing 'no harvest record' for a missing file."""

    def test_absent_record_prints_no_harvest_record(self, tmp_path, capsys):
        """run_retro with a run id that has no record file must not raise and must
        print a line containing the exact substring 'no harvest record'."""
        run_id = "run-does-not-exist"
        # Deliberately do NOT create the record file.
        (tmp_path / _RUNS_REL).mkdir(parents=True, exist_ok=True)

        run_retro(run_id, str(tmp_path))
        out = capsys.readouterr().out

        assert "no harvest record" in out, (
            f"expected 'no harvest record' in output for absent file; got: {out!r}"
        )


class TestMalformedRecord:
    """Reader prints 'malformed record' for a corrupt-JSON file, never 'no harvest record'."""

    def test_corrupt_json_prints_malformed_record(self, tmp_path, capsys):
        """A file that exists but is not valid JSON must print 'malformed record'
        and must NOT print 'no harvest record', keeping corrupt-vs-absent distinct."""
        run_id = "retro-corrupt-test"
        runs_dir = tmp_path / _RUNS_REL
        runs_dir.mkdir(parents=True, exist_ok=True)
        # Write a file that is present but not valid JSON.
        (runs_dir / f"{run_id}.json").write_text("{not valid json")

        run_retro(run_id, str(tmp_path))
        out = capsys.readouterr().out

        assert "malformed record" in out, (
            f"expected 'malformed record' in output for corrupt JSON; got: {out!r}"
        )
        assert "no harvest record" not in out, (
            "corrupt-file case must NOT print 'no harvest record'; "
            "the corrupt-vs-absent distinction must be preserved"
        )


class TestPartialRecord:
    """Reader prints 'partial record' warning for a truncated-completeness record."""

    def test_truncated_completeness_prints_partial_record(self, tmp_path, capsys):
        """A finalized record with completeness='truncated' must print a line containing
        the exact substring 'partial record'."""
        run_id = "retro-truncated-test"
        unit = _make_finalized_unit(
            unit_id="unit-1",
            agent_id="agent-alpha",
            shape="leaf",
            topology_cardinality="1:1",
            topology_stance="active",
            persona="engineer",
            started_at="2026-01-01T00:00:00+00:00",
            stopped_at="2026-01-01T01:00:00+00:00",
            duration_s=3600,
            tokens_input=1000,
            tokens_output=500,
            tokens_cache_read=0,
            tokens_cache_write=0,
            gate_outcome="pass",
        )
        # finalized=True per decision D-16; completeness="truncated" is the realistic trigger.
        record = _make_finalized_record([unit], completeness="truncated")
        _write_run_record(tmp_path, run_id, record)

        run_retro(run_id, str(tmp_path))
        out = capsys.readouterr().out

        assert "partial record" in out, (
            f"expected 'partial record' in output for truncated record; got: {out!r}"
        )


class TestNoAgentInvocation:
    """Reader renders from the run record alone — no events.jsonl present or required."""

    def test_renders_without_events_jsonl(self, tmp_path, capsys):
        """run_retro must succeed and produce output with no events.jsonl in the project tree."""
        run_id = "retro-no-events-test"
        unit = _make_finalized_unit(
            unit_id="unit-1",
            agent_id="agent-alpha",
            shape="leaf",
            topology_cardinality="1:1",
            topology_stance="active",
            persona="engineer",
            started_at="2026-01-01T00:00:00+00:00",
            stopped_at="2026-01-01T01:00:00+00:00",
            duration_s=3600,
            tokens_input=1000,
            tokens_output=500,
            tokens_cache_read=0,
            tokens_cache_write=0,
            gate_outcome="pass",
        )
        record = _make_finalized_record([unit])
        _write_run_record(tmp_path, run_id, record)

        # Confirm events.jsonl is absent — this is the no-agent precondition.
        events_path = tmp_path / ".fbk-capture" / "events.jsonl"
        assert not events_path.exists(), (
            "precondition: events.jsonl must be absent for this test to prove "
            "the reader does not require it"
        )

        run_retro(run_id, str(tmp_path))
        out = capsys.readouterr().out

        # Reader must produce meaningful output, not a failure path.
        assert out.strip(), (
            "run_retro produced no output with events.jsonl absent — "
            "the reader must render from the record alone"
        )
        assert "no harvest record" not in out, (
            "run_retro printed 'no harvest record' even though the record file is present"
        )
        assert "malformed record" not in out, (
            "run_retro printed 'malformed record' even though the record is valid"
        )
