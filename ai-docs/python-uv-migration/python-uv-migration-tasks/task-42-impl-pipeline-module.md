---
id: task-42
type: implementation
wave: 1
covers: [AC-02]
files_to_create:
  - assets/fbk-scripts/fbk/pipeline.py
test_tasks: [task-12]
completion_gate: "task-12 tests pass"
---

## Objective

Relocate `assets/scripts/fbk-pipeline.py` to `assets/fbk-scripts/fbk/pipeline.py` with updated preset path resolution.

## Context

`fbk-pipeline.py` (316 lines) implements the code review sighting pipeline with `validate_sighting(s)`, `load_presets()`, and subcommands `validate`, `domain-filter`, `severity-filter`, `to-markdown`, `run`. The `VALID_COMBINATIONS` dict maps types to allowed severities. `REQUIRED_FIELDS`, `MIN_LENGTH_FIELDS`, `DEFAULTS`, `VALID_TYPES`, `VALID_SEVERITIES`, `SEVERITY_ORDER` are module-level constants. The preset path changes from `Path(__file__).parent.parent / "config" / "fbk-presets.json"` to `Path(__file__).parent / "data" / "fbk-presets.json"` (the data file is relocated by task-37).

## Instructions

1. Create `assets/fbk-scripts/fbk/pipeline.py` by copying `assets/scripts/fbk-pipeline.py`
2. Update `load_presets()`: change path from `pathlib.Path(__file__).parent.parent / "config" / "fbk-presets.json"` to `pathlib.Path(__file__).parent / "data" / "fbk-presets.json"`
3. Replace the `if __name__ == "__main__":` block with a `main()` function containing the same argparse logic
4. Keep all function signatures and constants identical: `validate_sighting(s)`, `VALID_COMBINATIONS`, `VALID_TYPES`, `VALID_SEVERITIES`, `SEVERITY_ORDER`, `REQUIRED_FIELDS`, `MIN_LENGTH_FIELDS`, `DEFAULTS`
5. Preserve all exit codes and stderr output patterns

## Files to create/modify

- **Create**: `assets/fbk-scripts/fbk/pipeline.py`

## Test requirements

- task-12: valid behavioral+critical passes, invalid behavioral+minor rejected, invalid structural+critical rejected, missing field detected, below minimum length detected, invalid type detected

## Acceptance criteria

- AC-02: fbk-pipeline.py relocated and importable as `fbk.pipeline`

## Model

Haiku

## Wave

1
