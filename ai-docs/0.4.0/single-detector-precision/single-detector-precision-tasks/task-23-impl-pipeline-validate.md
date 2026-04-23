---
id: task-23
type: implementation
wave: 2
covers: [AC-01, AC-06]
files_to_create:
  - assets/scripts/pipeline.py
test_tasks: [task-07, task-08]
completion_gate: "bash tests/sdl-workflow/test-pipeline-validate.sh exits 0 && bash tests/sdl-workflow/test-type-severity-matrix.sh exits 0"
---

## Objective

Create `assets/scripts/pipeline.py` with the `validate` subcommand, shared constants, preset loading, and the argparse skeleton for all subcommands.

## Context

`assets/scripts/pipeline.py` is a new file. It consolidates all JSON processing for the code review pipeline. This task creates the module with the foundational infrastructure (constants, preset loading, argparse) and the `validate` subcommand. Subsequent tasks add the remaining subcommands. The script runs via `uv run assets/scripts/pipeline.py <subcommand>`. Standard library only: `json`, `sys`, `argparse`, `pathlib`.

## Instructions

Create `assets/scripts/pipeline.py`. No shebang needed (run via `uv run`).

### Imports and constants

```python
import json
import sys
import argparse
import pathlib

VALID_COMBINATIONS = {
    "behavioral": {"critical", "major"},
    "structural": {"minor", "info"},
    "test-integrity": {"critical", "major", "minor"},
    "fragile": {"major", "minor"},
}

VALID_TYPES = set(VALID_COMBINATIONS.keys())
VALID_SEVERITIES = {"critical", "major", "minor", "info"}
SEVERITY_ORDER = {"info": 0, "minor": 1, "major": 2, "critical": 3}

REQUIRED_FIELDS = ["id", "title", "location", "type", "severity", "mechanism", "consequence", "evidence"]
MIN_LENGTH_FIELDS = {"title": 10, "mechanism": 10, "consequence": 10}

DEFAULTS = {
    "origin": "unknown",
    "detection_source": "intent",
    "source_of_truth_ref": "",
    "pattern": "",
    "remediation": "",
}
```

### Preset loading

```python
def load_presets():
    preset_path = pathlib.Path(__file__).parent.parent / "config" / "presets.json"
    with open(preset_path) as f:
        return json.load(f)
```

### JSON I/O helpers

```python
def read_stdin_json():
    try:
        return json.load(sys.stdin)
    except json.JSONDecodeError as e:
        print(f"ERROR: malformed JSON input: {e}", file=sys.stderr)
        sys.exit(1)

def write_json(data):
    json.dump(data, sys.stdout, indent=2, ensure_ascii=False)
    sys.stdout.write('\n')
```

### Validate function

```python
def cmd_validate(args):
    sightings = read_stdin_json()
    valid = []
    rejected = 0
    total = len(sightings)

    for s in sightings:
        reason = validate_sighting(s)
        if reason:
            rejected += 1
            print(f"REJECTED: {reason}: {json.dumps(s, ensure_ascii=False)}", file=sys.stderr)
            continue
        # Fill defaults
        for key, default in DEFAULTS.items():
            if key not in s or s[key] is None:
                s[key] = default
        valid.append(s)

    # Assign sequential IDs
    for i, s in enumerate(valid, 1):
        s["id"] = f"S-{i:02d}"

    if total > 0 and rejected / total > 0.30:
        pct = rejected / total * 100
        print(f"WARNING: {rejected}/{total} sightings rejected ({pct:.0f}%) — check prompt compliance", file=sys.stderr)

    write_json(valid)
```

### Validation logic

```python
def validate_sighting(s):
    # Check required fields
    for field in REQUIRED_FIELDS:
        if field == "location":
            loc = s.get("location")
            if not isinstance(loc, dict) or not loc.get("file") or "start_line" not in loc:
                return f"missing or invalid 'location' (need 'file' and 'start_line')"
            continue
        val = s.get(field)
        if val is None or (isinstance(val, str) and val.strip() == ""):
            return f"missing field '{field}'"

    # Check min lengths
    for field, min_len in MIN_LENGTH_FIELDS.items():
        val = s.get(field, "")
        if len(str(val)) < min_len:
            return f"field '{field}' below minimum length {min_len}"

    # Check enums
    t = s.get("type")
    sev = s.get("severity")
    if t not in VALID_TYPES:
        return f"invalid type '{t}'"
    if sev not in VALID_SEVERITIES:
        return f"invalid severity '{sev}'"

    # Check type-severity matrix
    if sev not in VALID_COMBINATIONS.get(t, set()):
        return f"invalid type-severity combination '{t}+{sev}'"

    return None
```

### Argparse skeleton

Create the main argparse parser with subparsers for all five subcommands. Only `validate` is implemented in this task. The other four (`domain-filter`, `severity-filter`, `to-markdown`, `run`) should be defined as subparsers with placeholder functions that print `"Not yet implemented"` to stderr and exit 1. This allows the test tasks for `validate` to run without errors from missing subcommands.

```python
def main():
    parser = argparse.ArgumentParser(description="Code review sighting pipeline")
    subparsers = parser.add_subparsers(dest="command", required=True)

    subparsers.add_parser("validate")

    p_domain = subparsers.add_parser("domain-filter")
    p_domain.add_argument("--preset", required=True)

    p_severity = subparsers.add_parser("severity-filter")
    p_severity.add_argument("--min-severity", required=True)

    subparsers.add_parser("to-markdown")

    p_run = subparsers.add_parser("run")
    p_run.add_argument("--preset", required=True)
    p_run.add_argument("--min-severity", required=True)
    p_run.add_argument("--output-markdown", action="store_true")

    args = parser.parse_args()

    commands = {
        "validate": cmd_validate,
        "domain-filter": cmd_domain_filter,
        "severity-filter": cmd_severity_filter,
        "to-markdown": cmd_to_markdown,
        "run": cmd_run,
    }
    commands[args.command](args)

if __name__ == "__main__":
    main()
```

Define placeholder functions for the four unimplemented subcommands:

```python
def cmd_domain_filter(args):
    print("Not yet implemented: domain-filter", file=sys.stderr)
    sys.exit(1)

def cmd_severity_filter(args):
    print("Not yet implemented: severity-filter", file=sys.stderr)
    sys.exit(1)

def cmd_to_markdown(args):
    print("Not yet implemented: to-markdown", file=sys.stderr)
    sys.exit(1)

def cmd_run(args):
    print("Not yet implemented: run", file=sys.stderr)
    sys.exit(1)
```

## Files to create/modify

Create: `assets/scripts/pipeline.py`

## Test requirements

- task-07: validate accepts valid sightings, assigns S-NN IDs, preserves fields, rejects missing fields, rejects invalid enums, rejects invalid matrix combinations, fills defaults, writes rejected sightings to stderr
- task-08: exhaustive 16-cell type-severity matrix validation (9 valid, 7 invalid)

## Acceptance criteria

- File exists at `assets/scripts/pipeline.py`
- Runs via `uv run assets/scripts/pipeline.py validate`
- Validates required fields, enum values, type-severity matrix
- Assigns sequential S-NN IDs
- Fills defaults for optional fields
- Rejects malformed sightings to stderr with full JSON content
- Warns when >30% rejection rate
- Empty array input produces `[]`
- Malformed JSON input exits non-zero

## Model

sonnet

## Wave

2
