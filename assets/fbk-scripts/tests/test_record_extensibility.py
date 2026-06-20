"""Seam tests: canonical run record carries schema_version, and the reader
tolerates an unknown top-level key without error.

These tests pin the forward-compatibility contract across the record store
(IF-D-05) and the reader (IF-D-06).  They are red-phase seam tests — they
skip while fbk.run_retro is absent and run once it is implemented.

The schema_version presence test reads the fixture JSON directly without
calling harvest; it pins that a hand-written canonical record carries the
correct schema_version value.

The unknown-key tolerance test feeds the same record — which also carries an
extra top-level key the reader does not recognise — to run_retro and asserts
that it renders without raising and still emits known canonical fields.
"""

import json
import os

import pytest

try:
    from fbk.run_retro import run_retro
    RUN_RETRO_AVAILABLE = True
except ImportError:
    run_retro = None
    RUN_RETRO_AVAILABLE = False


# ---------------------------------------------------------------------------
# Fixture builder
# ---------------------------------------------------------------------------

_RUN_ID = "run-extensibility-001"

# Canonical unit shape matching the record-schema field names described in
# the task spec (topology, asset_bundle, timing, tokens, gate_outcome).
_CANONICAL_UNIT = {
    "agent_id": "agent-ext-test",
    "shape": "single",
    "topology": {
        "cardinality": "single",
        "stance": "collaborative",
    },
    "asset_bundle": {
        "persona": "implementer",
    },
    "started_at": "2026-06-20T10:00:00+00:00",
    "stopped_at": "2026-06-20T10:01:30+00:00",
    "duration_s": 90.0,
    "tokens": {
        "input": 1000,
        "output": 200,
        "cache_read": 0,
        "cache_creation": 0,
    },
    "gate_outcome": "pass",
}


def _write_canonical_record(runs_dir, *, with_unknown_key=False):
    """Write a finalized canonical run record under runs_dir/<run-id>.json.

    When with_unknown_key is True, also writes an extra top-level key
    ("future_field") that the reader does not know.  Returns the written
    record dict.
    """
    record = {
        "schema_version": "1.0",
        "run_id": _RUN_ID,
        "finalized": True,
        "completeness": 1.0,
        "units": [_CANONICAL_UNIT],
    }

    if with_unknown_key:
        record["future_field"] = {"x": 1}

    record_path = os.path.join(runs_dir, f"{_RUN_ID}.json")
    with open(record_path, "w") as fh:
        json.dump(record, fh, indent=2)

    return record


def _runs_dir(project_cwd):
    """Return the .fbk-capture/runs/ path, creating it if absent."""
    path = os.path.join(project_cwd, ".fbk-capture", "runs")
    os.makedirs(path, exist_ok=True)
    return path


# ---------------------------------------------------------------------------
# Schema-version presence (no run_retro call needed)
# ---------------------------------------------------------------------------


class TestSchemaVersionPresence:
    """A canonical run record carries schema_version set to '1.0'."""

    def test_canonical_record_carries_schema_version_one_dot_zero(self, tmp_path):
        """Reading a hand-written canonical record yields schema_version == '1.0'."""
        runs_dir = _runs_dir(str(tmp_path))
        _write_canonical_record(runs_dir)

        record_path = os.path.join(runs_dir, f"{_RUN_ID}.json")
        with open(record_path) as fh:
            record = json.load(fh)

        assert "schema_version" in record, (
            "canonical record must carry a schema_version key"
        )
        assert record["schema_version"] == "1.0", (
            f"expected schema_version '1.0', got {record['schema_version']!r}"
        )


# ---------------------------------------------------------------------------
# Unknown-key tolerance (requires run_retro)
# ---------------------------------------------------------------------------


@pytest.mark.skipif(
    not RUN_RETRO_AVAILABLE,
    reason="fbk.run_retro not yet implemented",
)
class TestUnknownKeyTolerance:
    """run_retro renders a record that carries an unknown top-level key without raising."""

    def test_run_retro_renders_known_fields_despite_unknown_key(
        self, tmp_path, capsys
    ):
        """run_retro does not raise and emits a known canonical field when the
        record carries an extra top-level key the reader does not recognise."""
        project_cwd = str(tmp_path)
        runs_dir = _runs_dir(project_cwd)
        _write_canonical_record(runs_dir, with_unknown_key=True)

        # run_retro must not raise on an unknown top-level key.
        run_retro(_RUN_ID, project_cwd)

        captured = capsys.readouterr()
        output = captured.out + captured.err

        assert _CANONICAL_UNIT["agent_id"] in output, (
            f"expected canonical agent_id {_CANONICAL_UNIT['agent_id']!r} in "
            f"run_retro output; got:\n{output}"
        )

    def test_existing_keys_unchanged_alongside_unknown_key(
        self, tmp_path, capsys
    ):
        """Adding the unknown top-level key does not suppress rendering of existing fields.

        The reader reads known keys and ignores the unknown one; known structural
        markers must still appear in the rendered output.
        """
        project_cwd = str(tmp_path)
        runs_dir = _runs_dir(project_cwd)
        _write_canonical_record(runs_dir, with_unknown_key=True)

        run_retro(_RUN_ID, project_cwd)

        captured = capsys.readouterr()
        output = captured.out + captured.err

        agent_id = _CANONICAL_UNIT["agent_id"]
        assert agent_id in output, (
            f"known canonical field agent_id {agent_id!r} must appear in output "
            f"alongside the unknown key being ignored; got:\n{output}"
        )
