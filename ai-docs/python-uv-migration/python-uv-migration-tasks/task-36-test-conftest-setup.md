---
id: task-36
type: test
wave: 1
covers: [AC-01, AC-02]
files_to_create:
  - assets/fbk-scripts/tests/__init__.py
  - assets/fbk-scripts/tests/conftest.py
completion_gate: "tests compile and fail before implementation"
---

## Objective

Create the pytest test infrastructure: `conftest.py` with shared fixtures for the `fbk-scripts` test suite.

## Context

The spec's test infrastructure section requires creating `tests/` directory in `assets/fbk-scripts/` with `conftest.py`. This provides shared fixtures used across all unit tests: sample spec strings, sample task manifests, sample state JSON, and `tmp_path`-based environment variable helpers.

The `pyproject.toml` (spec lines 115-131) configures `testpaths = ["tests"]`.

## Instructions

1. Create `assets/fbk-scripts/tests/__init__.py` (empty)
2. Create `assets/fbk-scripts/tests/conftest.py` with:
   - A `project_root` fixture returning the path to the `assets/fbk-scripts` directory
   - A `set_log_dir` fixture that sets `LOG_DIR` env var to a `tmp_path` subdirectory via `monkeypatch`
   - A `set_state_dir` fixture that sets `STATE_DIR` env var to a `tmp_path` subdirectory via `monkeypatch`
   - A `valid_spec_text` fixture returning a minimal valid feature spec string (containing all required sections: Problem, Goals, User-facing behavior, Technical approach, Testing strategy with AC-01 reference, Documentation impact, Acceptance criteria with AC-01, Dependencies, Open questions)
   - A `valid_sighting` fixture returning a dict with all required pipeline sighting fields (id, title, location, type, severity, mechanism, consequence, evidence)

## Files to create/modify

- **Create**: `assets/fbk-scripts/tests/__init__.py`
- **Create**: `assets/fbk-scripts/tests/conftest.py`

## Test requirements

| Level | Behavior | Expected assertion |
|-------|----------|--------------------|
| Infrastructure | conftest.py loads without errors | pytest discovers fixtures |
| Infrastructure | fixtures provide valid test data | each fixture returns expected structure |

## Acceptance criteria

- AC-01: test infrastructure supports gate module testing
- AC-02: test infrastructure supports shared module testing

## Model

Haiku

## Wave

1
