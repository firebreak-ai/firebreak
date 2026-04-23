---
id: task-49
type: implementation
wave: 1
covers: [AC-01, AC-08]
files_to_create:
  - assets/fbk-scripts/fbk/hooks/dispatch_status.py
test_tasks: [task-08]
completion_gate: "task-08 tests pass"
---

## Objective

Convert `assets/hooks/fbk-sdl-workflow/dispatch-status.sh` to `assets/fbk-scripts/fbk/hooks/dispatch_status.py`, extracting the embedded Python heredoc.

## Context

`dispatch-status.sh` (65 lines) reads a pipeline state JSON file and formats human-readable output. The bash wrapper handles argument parsing and audit logging; the Python heredoc (lines 18-56) does all formatting. Output includes: feature name, current status, last transition timestamp, stage history (sorted by timestamp), PARKED info (failed stage + reason), and error history. Output is human-readable text (not JSON).

## Instructions

1. Create `assets/fbk-scripts/fbk/hooks/dispatch_status.py`
2. Implement `format_status(state_dict)` — accept a parsed state dict, return formatted string with:
   - `Feature: {spec_name}`
   - `Status: {current_state}`
   - `Last transition: {latest_timestamp}`
   - `Stage history:` with each stage name and timestamp, sorted chronologically
   - If PARKED: `PARKED at: {failed_stage}` and `Reason: {reason}`
   - If error_history: `Errors:` with `[{stage}] {error} ({timestamp})` for each
3. Implement `main()` with argparse: spec name positional arg. Read `STATE_DIR` env var (default `.claude/automation/state`). Load `{STATE_DIR}/{spec_name}.json`. If file not found: print error to stderr, exit 1. Call `format_status`, print result to stdout. Log to `fbk.audit.log_event` if importable
4. Output must not start with `{` — it is human-readable, not JSON

## Files to create/modify

- **Create**: `assets/fbk-scripts/fbk/hooks/dispatch_status.py`

## Test requirements

- task-08: QUEUED state shows name+QUEUED+timestamp, REVIEWING state shows stage history, PARKED state shows failed stage+reason, COMPLETED state shows COMPLETED, output does not start with `{`

## Acceptance criteria

- AC-01: dispatch-status.sh converted to Python module
- AC-08: formatting function produces correct output for each state

## Model

Haiku

## Wave

1
