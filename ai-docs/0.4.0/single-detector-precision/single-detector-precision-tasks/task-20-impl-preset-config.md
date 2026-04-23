---
id: task-20
type: implementation
wave: 1
covers: [AC-09]
files_to_create:
  - assets/config/presets.json
test_tasks: [task-04]
completion_gate: "bash tests/sdl-workflow/test-preset-config.sh exits 0"
---

## Objective

Create the detection preset configuration file that defines four named presets with type allow-lists and default severity thresholds.

## Context

Detection presets are the user-facing abstraction for domain scoping. The orchestrator resolves a preset at review start and passes it to `pipeline.py` for domain filtering. The preset file is standard JSON, read by Python's `json` module.

## Instructions

Create `assets/config/presets.json` as a flat JSON object with four keys. Each key is a preset name. Each value is an object with two fields: `allowed_types` (array of strings) and `default_severity_threshold` (string).

Write exactly this content:

```json
{
  "behavioral-only": {
    "allowed_types": ["behavioral"],
    "default_severity_threshold": "minor"
  },
  "structural": {
    "allowed_types": ["structural"],
    "default_severity_threshold": "minor"
  },
  "test-only": {
    "allowed_types": ["test-integrity"],
    "default_severity_threshold": "minor"
  },
  "full": {
    "allowed_types": ["behavioral", "structural", "test-integrity", "fragile"],
    "default_severity_threshold": "minor"
  }
}
```

The `full` preset `allowed_types` array must list all four types in this order: `behavioral`, `structural`, `test-integrity`, `fragile`.

All four presets use `"minor"` as `default_severity_threshold`. This means info-level sightings are dropped by default.

No trailing commas. No comments. Valid JSON parseable by `python3 -c "import json, sys; json.load(sys.stdin)"`.

## Files to create/modify

Create: `assets/config/presets.json`

## Test requirements

Test task-04 validates: file existence, valid JSON, presence of all four presets, correct `allowed_types` per preset, correct `default_severity_threshold` per preset, exactly four presets.

## Acceptance criteria

- `assets/config/presets.json` exists with exactly four presets
- Each preset has `allowed_types` and `default_severity_threshold` fields
- `behavioral-only` allows `["behavioral"]`, `structural` allows `["structural"]`, `test-only` allows `["test-integrity"]`, `full` allows all four types
- All thresholds are `"minor"`
- File is valid JSON

## Model

sonnet

## Wave

1
