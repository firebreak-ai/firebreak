---
id: task-12
type: test
wave: 1
covers: [AC-02]
files_to_create:
  - assets/fbk-scripts/tests/test_pipeline.py
completion_gate: "tests compile and fail before implementation"
---

## Objective

Create pytest unit tests for `fbk.pipeline` type-severity matrix validation.

## Context

`fbk-pipeline.py` defines `VALID_COMBINATIONS` mapping types to allowed severities and `validate_sighting()` which checks required fields, minimum lengths, enum values, and the type-severity matrix. After relocation to `fbk.pipeline`, it loads presets from `fbk/data/fbk-presets.json` instead of `../config/fbk-presets.json`. Tests verify the validation contract.

## Instructions

1. Create `assets/fbk-scripts/tests/test_pipeline.py`
2. Import `validate_sighting`, `VALID_COMBINATIONS`, `VALID_TYPES`, `VALID_SEVERITIES` from `fbk.pipeline`
3. Write a test: valid sighting with type="behavioral", severity="critical" → assert `validate_sighting()` returns `None`
4. Write a test: sighting with type="behavioral", severity="minor" → assert returns error string containing "invalid type-severity"
5. Write a test: sighting with type="structural", severity="critical" → assert returns error string containing "invalid type-severity"
6. Write a test: sighting missing `title` field → assert returns error containing "missing field"
7. Write a test: sighting with `title` shorter than 10 characters → assert returns error containing "minimum length"
8. Write a test: sighting with invalid type "performance" → assert returns error containing "invalid type"

## Files to create/modify

- **Create**: `assets/fbk-scripts/tests/test_pipeline.py`

## Test requirements

| Level | Behavior | Expected assertion |
|-------|----------|--------------------|
| Unit | valid behavioral+critical passes | returns None |
| Unit | invalid behavioral+minor rejected | error contains "invalid type-severity" |
| Unit | invalid structural+critical rejected | error contains "invalid type-severity" |
| Unit | missing required field detected | error contains "missing field" |
| Unit | below minimum length detected | error contains "minimum length" |
| Unit | invalid type detected | error contains "invalid type" |

## Acceptance criteria

- AC-02: validates fbk-pipeline.py relocated and importable as `fbk.pipeline`

## Model

Haiku

## Wave

1
