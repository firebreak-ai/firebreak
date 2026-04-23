---
id: task-41
type: implementation
wave: 1
covers: [AC-02]
files_to_create:
  - assets/fbk-scripts/fbk/state.py
test_tasks: [task-11]
completion_gate: "task-11 tests pass"
---

## Objective

Relocate `assets/hooks/fbk-sdl-workflow/state-engine.py` to `assets/fbk-scripts/fbk/state.py` as an importable module with a `main()` entry point.

## Context

`state-engine.py` (177 lines) implements pipeline state management with `VALID_TRANSITIONS` map, `create_state(spec_name)`, `transition_state(spec_name, new_state, reason=None)`, `load_state(spec_name)`, `read_state(spec_name)`, and `get_valid_transitions(spec_name)`. The `STATE_DIR` env var defaults to `.claude/automation/state`. `create_state` returns 0 on success, 1 if state already exists. `transition_state` returns 0 on success, 1 on invalid transition. PARKED state stores `parked_info.failed_stage` and appends to `error_history`. READY state resolves valid transitions dynamically from `parked_info.failed_stage`.

## Instructions

1. Create `assets/fbk-scripts/fbk/state.py` by copying the content of `assets/hooks/fbk-sdl-workflow/state-engine.py`
2. Replace the `if __name__ == "__main__":` block with a `main()` function containing the same argparse logic with subcommands: `create`, `transition` (with `--reason`), `read`, `get-valid-transitions`
3. Keep all function signatures identical
4. Keep the `VALID_TRANSITIONS` dict, `ALL_STATES`, `now_iso()`, `get_state_dir()`, `get_state_path()`, `load_state()`, `save_state()`, `get_valid_for_state()` functions
5. Preserve all exit codes: `sys.exit(1)` for missing state file, `sys.exit(1)` for READY without `parked_info.failed_stage`

## Files to create/modify

- **Create**: `assets/fbk-scripts/fbk/state.py`

## Test requirements

- task-11: `create_state` produces QUEUED, valid transition succeeds, invalid transition rejected (return 1), PARKED stores failure info, READY resolves from `parked_info`, duplicate create rejected (return 1)

## Acceptance criteria

- AC-02: state-engine.py relocated and importable as `fbk.state`

## Model

Haiku

## Wave

1
