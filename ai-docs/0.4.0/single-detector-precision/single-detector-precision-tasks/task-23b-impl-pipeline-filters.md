---
id: task-23b
type: implementation
wave: 2
covers: [AC-09, AC-10]
files_to_modify:
  - assets/scripts/pipeline.py
test_tasks: [task-09, task-10]
completion_gate: "bash tests/sdl-workflow/test-pipeline-domain-filter.sh exits 0 && bash tests/sdl-workflow/test-pipeline-severity-filter.sh exits 0"
---

## Objective

Add the `domain-filter` and `severity-filter` subcommands to `pipeline.py`. These replace the placeholder functions created in task-23.

## Context

`assets/scripts/pipeline.py` already exists with the `validate` subcommand, constants, preset loading, and argparse skeleton (from task-23). The `domain-filter` and `severity-filter` placeholders exit with "Not yet implemented." This task replaces those placeholders with working implementations.

The `domain-filter` reads a preset from `assets/config/presets.json` (created in task-20) and drops sightings whose `type` is not in the preset's `allowed_types`. The `severity-filter` drops sightings below a minimum severity threshold.

## Instructions

In `assets/scripts/pipeline.py`, replace the placeholder `cmd_domain_filter` function with:

```python
def cmd_domain_filter(args):
    presets = load_presets()
    preset_name = args.preset
    if preset_name not in presets:
        print(f"ERROR: unknown preset '{preset_name}'. Available: {', '.join(sorted(presets.keys()))}", file=sys.stderr)
        sys.exit(1)

    allowed = set(presets[preset_name]["allowed_types"])
    sightings = read_stdin_json()
    filtered = []

    for s in sightings:
        if s.get("type") in allowed:
            filtered.append(s)
        else:
            print(f"DROPPED (domain): type={s.get('type')} id={s.get('id')} title={s.get('title', '')}", file=sys.stderr)

    write_json(filtered)
```

Replace the placeholder `cmd_severity_filter` function with:

```python
def cmd_severity_filter(args):
    min_sev = args.min_severity
    if min_sev not in VALID_SEVERITIES:
        print(f"ERROR: invalid severity '{min_sev}'. Valid: {', '.join(sorted(VALID_SEVERITIES, key=lambda x: SEVERITY_ORDER[x]))}", file=sys.stderr)
        sys.exit(1)

    threshold = SEVERITY_ORDER[min_sev]
    sightings = read_stdin_json()
    filtered = []

    for s in sightings:
        sev = s.get("severity", "info")
        if SEVERITY_ORDER.get(sev, 0) >= threshold:
            filtered.append(s)
        else:
            print(f"DROPPED (severity): severity={sev} id={s.get('id')} title={s.get('title', '')}", file=sys.stderr)

    write_json(filtered)
```

Both functions handle empty input `[]` by outputting `[]` (the loop body never executes, `filtered` stays empty).

## Files to create/modify

Modify: `assets/scripts/pipeline.py`

## Test requirements

- task-09: domain-filter with each of 4 presets, stderr logging of dropped sightings, unknown preset exits non-zero, empty array input
- task-10: severity-filter at all 4 threshold levels (info/minor/major/critical), stderr logging, empty array, field preservation

## Acceptance criteria

- `domain-filter --preset behavioral-only` keeps only behavioral sightings
- `domain-filter --preset structural` keeps only structural
- `domain-filter --preset test-only` keeps only test-integrity
- `domain-filter --preset full` keeps all types
- Unknown preset exits non-zero with error on stderr
- `severity-filter --min-severity minor` drops info
- `severity-filter --min-severity major` drops info and minor
- `severity-filter --min-severity critical` drops everything below critical
- `severity-filter --min-severity info` keeps all
- Both log dropped sightings to stderr
- Empty input produces `[]`

## Model

sonnet

## Wave

2
