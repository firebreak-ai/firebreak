"""Single-run retrospective reader.

Reads a finalized per-run record from
``<project_cwd>/.fbk-capture/runs/<run-id>.json`` and prints a per-unit
summary table.  The reader is a pure function of the record: no wall-clock
values are added to the output, units are sorted by a content-derived key
(agent_id), null fields render as an em dash, and unknown top-level keys in
the record are silently ignored.

Three distinct output paths for error conditions:
- Absent record file   → line containing ``no harvest record``
- Malformed JSON file  → line containing ``malformed record``
- Truncated or unfinalized record → warning line containing ``partial record``
  (still renders units when the record is otherwise readable)
"""

import json
import os
import sys

_EM_DASH = "—"
_RUNS_REL = os.path.join(".fbk-capture", "runs")


def _fmt(value):
    """Return the value as a string, or an em dash when the value is None."""
    if value is None:
        return _EM_DASH
    return str(value)


def _render_unit(unit):
    """Print one unit block from a record unit dict.

    Reads the canonical schema fields: agent_id, unit_id, shape,
    topology.cardinality, topology.stance, asset_bundle.persona,
    started_at, stopped_at, duration_s, tokens (all sub-keys verbatim),
    and gate_outcome.  Unknown keys inside the unit are ignored.
    """
    agent_id = _fmt(unit.get("agent_id"))
    unit_id = _fmt(unit.get("unit_id"))
    shape = _fmt(unit.get("shape"))

    topology = unit.get("topology") or {}
    cardinality = _fmt(topology.get("cardinality"))
    stance = _fmt(topology.get("stance"))

    asset_bundle = unit.get("asset_bundle") or {}
    persona = _fmt(asset_bundle.get("persona"))

    started_at = _fmt(unit.get("started_at"))
    stopped_at = _fmt(unit.get("stopped_at"))
    duration_s = _fmt(unit.get("duration_s"))

    gate_outcome = _fmt(unit.get("gate_outcome"))

    print(f"  agent_id:    {agent_id}")
    if unit.get("unit_id") is not None:
        print(f"  unit_id:     {unit_id}")
    print(f"  shape:       {shape}")
    print(f"  cardinality: {cardinality}")
    print(f"  stance:      {stance}")
    print(f"  persona:     {persona}")
    print(f"  started_at:  {started_at}")
    print(f"  stopped_at:  {stopped_at}")
    print(f"  duration_s:  {duration_s}")

    tokens = unit.get("tokens") or {}
    if tokens:
        print("  tokens:")
        for key, val in tokens.items():
            print(f"    {key}: {_fmt(val)}")

    print(f"  gate_outcome: {gate_outcome}")


def run_retro(run_id: str, project_cwd: str) -> None:
    """Read and render the durable run record for run_id under project_cwd.

    Prints a per-unit summary table to stdout.  All error conditions print a
    descriptive line and return without raising.

    Args:
        run_id:      The run identifier (maps to <run_id>.json in the runs dir).
        project_cwd: The project root directory containing .fbk-capture/.
    """
    record_path = os.path.join(project_cwd, _RUNS_REL, f"{run_id}.json")

    if not os.path.exists(record_path):
        print(f"no harvest record for run: {run_id}")
        return

    try:
        with open(record_path, encoding="utf-8") as fh:
            record = json.load(fh)
    except (json.JSONDecodeError, ValueError):
        print(f"malformed record: {run_id} — file present but JSON could not be parsed")
        return

    # Partial-record warning: unfinalized OR truncated.
    is_finalized = record.get("finalized", False)
    completeness = record.get("completeness", "")
    if not is_finalized or completeness == "truncated":
        print(f"WARNING: partial record for run {run_id} — data may be incomplete")

    units = record.get("units") or []
    sorted_units = sorted(units, key=lambda u: u.get("agent_id") or "")

    print(f"run: {run_id}")
    print(f"units: {len(sorted_units)}")
    print()

    for unit in sorted_units:
        print("---")
        _render_unit(unit)

    print()


def main():
    """CLI entry point: read run_id from sys.argv[1], project from os.getcwd()."""
    if len(sys.argv) < 2:
        print("Usage: fbk run-retro <run-id>", file=sys.stderr)
        sys.exit(1)

    run_id = sys.argv[1]
    project_cwd = os.getcwd()
    run_retro(run_id, project_cwd)


if __name__ == "__main__":
    main()
