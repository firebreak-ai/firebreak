---
id: task-23c
type: implementation
wave: 2
covers: [AC-10]
files_to_modify:
  - assets/scripts/pipeline.py
test_tasks: [task-11, task-12, task-14]
completion_gate: "bash tests/sdl-workflow/test-pipeline-to-markdown.sh exits 0 && bash tests/sdl-workflow/test-pipeline-run.sh exits 0 && bash tests/sdl-workflow/test-pipeline-integration.sh exits 0"
---

## Objective

Add the `to-markdown` and `run` subcommands to `pipeline.py`. These replace the placeholder functions created in task-23 and complete the pipeline module.

## Context

`assets/scripts/pipeline.py` already has `validate` (task-23), `domain-filter`, and `severity-filter` (task-23b). This task adds the final two subcommands: `to-markdown` converts JSON to human-readable markdown, and `run` executes the full pipeline (validate, domain-filter, severity-filter) in a single invocation.

## Instructions

In `assets/scripts/pipeline.py`, replace the placeholder `cmd_to_markdown` function with:

```python
def cmd_to_markdown(args):
    items = read_stdin_json()
    output = []

    for item in items:
        # Skip rejected and rejected-as-nit
        status = item.get("status")
        if status in ("rejected", "rejected-as-nit"):
            continue

        # Use finding_id if present, otherwise id
        display_id = item.get("finding_id", item.get("id", "?"))
        title = item.get("title", "")

        loc = item.get("location", {})
        loc_file = loc.get("file", "")
        start = loc.get("start_line", "")
        end = loc.get("end_line")
        loc_str = f"{loc_file}:{start}" + (f"-{end}" if end else "")

        sev = item.get("severity", "")
        typ = item.get("type", "")
        origin = item.get("origin", "")
        det_source = item.get("detection_source", "")
        pattern = item.get("pattern", "")

        lines = []
        lines.append(f"### {display_id}: {title}")
        lines.append("")
        lines.append(f"- **Location**: `{loc_str}`")
        lines.append(f"- **Type**: {typ} | **Severity**: {sev} | **Origin**: {origin}")
        if det_source or pattern:
            parts = []
            if det_source:
                parts.append(f"**Detection source**: {det_source}")
            if pattern:
                parts.append(f"**Pattern**: `{pattern}`")
            lines.append(f"- {' | '.join(parts)}")
        lines.append("")
        lines.append(f"**Mechanism**: {item.get('mechanism', '')}")
        lines.append("")
        lines.append(f"**Consequence**: {item.get('consequence', '')}")
        lines.append("")
        lines.append(f"**Evidence**: {item.get('evidence', '')}")

        # Verification evidence (findings only)
        ve = item.get("verification_evidence")
        if ve:
            lines.append("")
            lines.append(f"**Verification**: {ve}")

        # Reclassification note
        rc = item.get("reclassified_from", {})
        if rc and isinstance(rc, dict) and rc.get("type"):
            lines.append("")
            lines.append(f"*Reclassified from {rc['type']}/{rc.get('severity', '')}*")

        # Remediation
        rem = item.get("remediation", "")
        if rem:
            lines.append("")
            lines.append(f"**Remediation**: {rem}")

        output.append("\n".join(lines))

    sys.stdout.write("\n\n".join(output))
    if output:
        sys.stdout.write("\n")
```

Replace the placeholder `cmd_run` function with:

```python
def cmd_run(args):
    # Step 1: Validate
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
        for key, default in DEFAULTS.items():
            if key not in s or s[key] is None:
                s[key] = default
        valid.append(s)

    for i, s in enumerate(valid, 1):
        s["id"] = f"S-{i:02d}"

    if total > 0 and rejected / total > 0.30:
        pct = rejected / total * 100
        print(f"WARNING: {rejected}/{total} sightings rejected ({pct:.0f}%) — check prompt compliance", file=sys.stderr)

    # Step 2: Domain filter
    presets = load_presets()
    preset_name = args.preset
    if preset_name not in presets:
        print(f"ERROR: unknown preset '{preset_name}'. Available: {', '.join(sorted(presets.keys()))}", file=sys.stderr)
        sys.exit(1)

    allowed = set(presets[preset_name]["allowed_types"])
    domain_filtered = []
    for s in valid:
        if s.get("type") in allowed:
            domain_filtered.append(s)
        else:
            print(f"DROPPED (domain): type={s.get('type')} id={s.get('id')} title={s.get('title', '')}", file=sys.stderr)

    # Step 3: Severity filter
    min_sev = args.min_severity
    threshold = SEVERITY_ORDER.get(min_sev, 0)
    severity_filtered = []
    for s in domain_filtered:
        sev = s.get("severity", "info")
        if SEVERITY_ORDER.get(sev, 0) >= threshold:
            severity_filtered.append(s)
        else:
            print(f"DROPPED (severity): severity={sev} id={s.get('id')} title={s.get('title', '')}", file=sys.stderr)

    # Reassign IDs after filtering
    for i, s in enumerate(severity_filtered, 1):
        s["id"] = f"S-{i:02d}"

    # Step 4: Output
    if args.output_markdown:
        # Reuse to-markdown logic
        _render_markdown(severity_filtered)
    else:
        write_json(severity_filtered)
```

Add a shared markdown rendering helper (extracted from `cmd_to_markdown` to avoid duplication):

```python
def _render_markdown(items):
    output = []
    for item in items:
        status = item.get("status")
        if status in ("rejected", "rejected-as-nit"):
            continue

        display_id = item.get("finding_id", item.get("id", "?"))
        title = item.get("title", "")

        loc = item.get("location", {})
        loc_file = loc.get("file", "")
        start = loc.get("start_line", "")
        end = loc.get("end_line")
        loc_str = f"{loc_file}:{start}" + (f"-{end}" if end else "")

        sev = item.get("severity", "")
        typ = item.get("type", "")
        origin = item.get("origin", "")
        det_source = item.get("detection_source", "")
        pattern = item.get("pattern", "")

        lines = []
        lines.append(f"### {display_id}: {title}")
        lines.append("")
        lines.append(f"- **Location**: `{loc_str}`")
        lines.append(f"- **Type**: {typ} | **Severity**: {sev} | **Origin**: {origin}")
        if det_source or pattern:
            parts = []
            if det_source:
                parts.append(f"**Detection source**: {det_source}")
            if pattern:
                parts.append(f"**Pattern**: `{pattern}`")
            lines.append(f"- {' | '.join(parts)}")
        lines.append("")
        lines.append(f"**Mechanism**: {item.get('mechanism', '')}")
        lines.append("")
        lines.append(f"**Consequence**: {item.get('consequence', '')}")
        lines.append("")
        lines.append(f"**Evidence**: {item.get('evidence', '')}")

        ve = item.get("verification_evidence")
        if ve:
            lines.append("")
            lines.append(f"**Verification**: {ve}")

        rc = item.get("reclassified_from", {})
        if rc and isinstance(rc, dict) and rc.get("type"):
            lines.append("")
            lines.append(f"*Reclassified from {rc['type']}/{rc.get('severity', '')}*")

        rem = item.get("remediation", "")
        if rem:
            lines.append("")
            lines.append(f"**Remediation**: {rem}")

        output.append("\n".join(lines))

    sys.stdout.write("\n\n".join(output))
    if output:
        sys.stdout.write("\n")
```

Refactor `cmd_to_markdown` to call `_render_markdown`:

```python
def cmd_to_markdown(args):
    items = read_stdin_json()
    _render_markdown(items)
```

### Important: ID reassignment in `run`

The `run` subcommand reassigns IDs after filtering to keep them sequential. The validate step assigns S-01, S-02, etc. based on input order. After domain and severity filtering, the surviving sightings get re-numbered S-01, S-02, etc. This matches the expected behavior in test task-14 (integration test expects `['S-01', 'S-02']` after filtering 6 inputs to 2).

## Files to create/modify

Modify: `assets/scripts/pipeline.py`

## Test requirements

- task-11: to-markdown for sightings (S-NN header), findings (F-NN header with verification evidence, reclassification note), nit exclusion, empty input
- task-12: run subcommand sequential/combined equivalence, behavioral filtering, full preset, markdown output, edge cases (empty, all-filtered, unknown preset, malformed JSON, unicode)
- task-14: deterministic integration test with 6-sighting fixture through full pipeline

## Acceptance criteria

- `to-markdown` renders sightings with S-NN headers and findings with F-NN headers
- `to-markdown` includes verification evidence and reclassification notes for findings
- `to-markdown` excludes `rejected-as-nit` items
- `run` produces same output as sequential validate | domain-filter | severity-filter
- `run --output-markdown` produces markdown output
- `run` with unknown preset exits non-zero
- `run` with malformed JSON exits non-zero
- Unicode preserved in all subcommands
- Empty input produces empty output

## Model

sonnet

## Wave

2
