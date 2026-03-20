## Objective

Write bash test scripts and fixture state files that validate the dispatch status command's output formatting across pipeline states.

## Context

The dispatch status command (`dispatch-status.sh`) reads a pipeline state JSON file and formats it as human-readable output. It takes one argument: `<spec-name>`. It reads from `.claude/automation/state/<spec-name>.json` (the state files produced by the Wave 1 state engine).

State JSON schema:
```json
{
  "spec_name": "string",
  "current_state": "string",
  "stage_timestamps": {"STATE_NAME": "ISO8601", ...},
  "agent_ids": [],
  "verification_results": {},
  "error_history": [{"stage": "string", "error": "string", "timestamp": "ISO8601"}],
  "parked_info": {"failed_stage": "string", "reason": "string"}
}
```

The command exits 0 on success (state file found and formatted), exit 1 when no state file exists. Output is human-readable text to stdout, not JSON.

## Instructions

1. Create directory `tests/fixtures/state/` if it does not exist.

2. Create `tests/fixtures/state/queued-spec.json` — state file with `current_state: "QUEUED"`, `stage_timestamps: {"QUEUED": "2026-03-14T10:00:00Z"}`, empty `error_history`, empty `parked_info`.

3. Create `tests/fixtures/state/reviewing-spec.json` — state file with `current_state: "REVIEWING"`, `stage_timestamps` containing QUEUED, VALIDATING, VALIDATED, REVIEWING with increasing timestamps. Empty error_history, empty parked_info.

4. Create `tests/fixtures/state/parked-spec.json` — state file with `current_state: "PARKED"`, `stage_timestamps` containing QUEUED through VALIDATING. `parked_info: {"failed_stage": "VALIDATING", "reason": "missing required section: Testing strategy"}`. `error_history` with one entry: `{"stage": "VALIDATING", "error": "spec validation failed", "timestamp": "2026-03-14T10:01:30Z"}`.

5. Create `tests/fixtures/state/completed-spec.json` — state file with `current_state: "COMPLETED"`, `stage_timestamps` containing a full pipeline run (QUEUED through COMPLETED, 10+ timestamps). Empty error_history, empty parked_info.

6. Create `tests/sdl-workflow/test-status-command.sh` as a bash test script. Use `set -uo pipefail`. TAP format output.

7. Define `CMD` pointing to `home/dot-claude/hooks/sdl-workflow/dispatch-status.sh` relative to project root. Define a setup function that creates a temporary `.claude/automation/state/` directory and copies fixture state files into it. Export `STATE_DIR` so the status command uses the temp directory. Register cleanup with `trap`.

8. Write test: queued spec displays status. Copy `queued-spec.json` to temp state dir as `my-feature.json`. Run `$CMD my-feature`. Assert exit 0. Assert stdout contains "my-feature" (the spec name). Assert stdout contains "QUEUED". Assert stdout contains "2026-03-14" (timestamp substring).

9. Write test: reviewing spec shows stage history. Copy `reviewing-spec.json` as `review-feature.json`. Run `$CMD review-feature`. Assert exit 0. Assert stdout contains "REVIEWING". Assert stdout contains "QUEUED" and "VALIDATING" and "VALIDATED" (stage history entries).

10. Write test: parked spec shows failure info. Copy `parked-spec.json` as `parked-feature.json`. Run `$CMD parked-feature`. Assert exit 0. Assert stdout contains "PARKED". Assert stdout contains "VALIDATING" (failed stage). Assert stdout contains "missing required section" (reason substring).

11. Write test: completed spec shows full history. Copy `completed-spec.json` as `done-feature.json`. Run `$CMD done-feature`. Assert exit 0. Assert stdout contains "COMPLETED".

12. Write test: non-existent spec reports error. Run `$CMD nonexistent-feature`. Assert exit 1. Assert stderr or stdout contains "No pipeline state found" or similar not-found message.

13. Write test: output is human-readable. Run `$CMD` against the reviewing fixture. Capture stdout. Assert the output does NOT start with `{` (not raw JSON). Assert it contains labeled fields (e.g., "Status:" or "Feature:").

14. Write test: error history displayed. Copy `parked-spec.json` as `error-feature.json`. Run `$CMD error-feature`. Assert stdout contains "spec validation failed" (the error message from error_history).

15. End the script with summary and exit code.

## Files to create/modify

- `tests/sdl-workflow/test-status-command.sh` (create)
- `tests/fixtures/state/queued-spec.json` (create)
- `tests/fixtures/state/reviewing-spec.json` (create)
- `tests/fixtures/state/parked-spec.json` (create)
- `tests/fixtures/state/completed-spec.json` (create)

## Test requirements

This is a test task. Tests to write (all in `test-status-command.sh`):
1. Unit: queued spec displays spec name, status, and timestamp
2. Unit: reviewing spec shows stage history with multiple stages
3. Unit: parked spec shows failed stage and failure reason
4. Unit: completed spec shows COMPLETED status
5. Unit: non-existent spec exits 1 with not-found message
6. Unit: output is human-readable (not raw JSON), with labeled fields
7. Unit: error history entries are displayed

## Acceptance criteria

AC-10: Pipeline state is queryable via status command.

## Model

Haiku

## Wave

2
