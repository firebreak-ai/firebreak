---
id: task-37
type: implementation
wave: 1
covers: [AC-02, AC-03]
files_to_create:
  - assets/fbk-scripts/pyproject.toml
  - assets/fbk-scripts/fbk/__init__.py
  - assets/fbk-scripts/fbk/gates/__init__.py
  - assets/fbk-scripts/fbk/hooks/__init__.py
  - assets/fbk-scripts/fbk/council/__init__.py
  - assets/fbk-scripts/fbk/data/fbk-presets.json
test_tasks: [task-36]
completion_gate: "task-36 tests pass"
---

## Objective

Create the `assets/fbk-scripts/` project directory structure with `pyproject.toml`, package `__init__.py` files, and relocate `fbk-presets.json`.

## Context

The spec defines the source layout at `assets/fbk-scripts/` with a `fbk/` package containing `gates/`, `hooks/`, `council/`, and `data/` subdirectories. Every other implementation task depends on this structure existing. This task touches 6 files because all are empty `__init__.py` boilerplate and one data file copy — splitting would create artificial boundaries with no independent value. The `pyproject.toml` provides project metadata and dev tooling configuration. The `fbk-presets.json` data file relocates from `assets/config/fbk-presets.json` to `assets/fbk-scripts/fbk/data/fbk-presets.json`.

## Instructions

1. Create `assets/fbk-scripts/pyproject.toml` with the exact content from the spec (lines 115-131): project name `fbk-scripts`, version `0.4.0`, `requires-python = ">=3.11"`, dependency on `pyyaml>=6.0`, dev dependency group with `pytest>=8.0`, and `testpaths = ["tests"]`
2. Create empty `assets/fbk-scripts/fbk/__init__.py`
3. Create empty `assets/fbk-scripts/fbk/gates/__init__.py`
4. Create empty `assets/fbk-scripts/fbk/hooks/__init__.py`
5. Create empty `assets/fbk-scripts/fbk/council/__init__.py`
6. Copy `assets/config/fbk-presets.json` to `assets/fbk-scripts/fbk/data/fbk-presets.json` — preserve the JSON content exactly

## Files to create/modify

- **Create**: `assets/fbk-scripts/pyproject.toml`
- **Create**: `assets/fbk-scripts/fbk/__init__.py`
- **Create**: `assets/fbk-scripts/fbk/gates/__init__.py`
- **Create**: `assets/fbk-scripts/fbk/hooks/__init__.py`
- **Create**: `assets/fbk-scripts/fbk/council/__init__.py`
- **Create**: `assets/fbk-scripts/fbk/data/fbk-presets.json`

## Test requirements

- task-36: `conftest.py` loads without errors, `project_root` fixture resolves to `assets/fbk-scripts`

## Acceptance criteria

- AC-02: project structure supports module relocation
- AC-03: package directories exist for dispatcher imports

## Model

Haiku

## Wave

1
