## Objective

Implement the dispatch status command that reads pipeline state JSON and formats human-readable output.

## Context

The status command is a bash script that reads a per-spec state JSON file (produced by the Wave 1 state engine) and displays formatted output. It is the primary way developers inspect pipeline progress in Phase 1 (before automated orchestration in Phase 3).

State files live at `.claude/automation/state/<spec-name>.json`. The state JSON schema has fields: `spec_name`, `current_state`, `stage_timestamps` (object mapping state names to ISO8601 strings), `agent_ids`, `verification_results`, `error_history` (array of `{stage, error, timestamp}`), and `parked_info` (`{failed_stage, reason}`).

The command must produce grep-friendly output with labeled fields — not raw JSON.

## Instructions

1. Create `home/.claude/hooks/sdl-workflow/dispatch-status.sh`. Start with `#!/usr/bin/env bash` and `set -uo pipefail`.

2. Parse arguments: accept one positional argument `<spec-name>`. Print usage to stderr and exit 2 if missing.

3. Determine the state file path. Default to `.claude/automation/state/<spec-name>.json` relative to the project/home directory. Support a `STATE_DIR` environment variable override: if `STATE_DIR` is set, use `$STATE_DIR/<spec-name>.json` instead. This enables testing with temporary directories.

4. If the state file does not exist: print `No pipeline state found for '<spec-name>'` to stderr. Exit 1.

5. If the state file exists: parse JSON and format output using embedded Python3 via heredoc. Pass the state file path as an argument to the Python block.

6. The Python block reads and parses the JSON, then prints formatted output to stdout:

   ```
   Feature: <spec_name>
   Status: <current_state>
   Last transition: <most recent timestamp from stage_timestamps>

   Stage history:
     <STATE_1>         <timestamp_1>
     <STATE_2>         <timestamp_2>
     ...
   ```

   Sort stage history entries by timestamp (ascending). Left-pad state names to align timestamps (use at least 20 characters for the state name column).

7. If `current_state` is `PARKED` and `parked_info` is non-empty, append:
   ```

   PARKED at: <parked_info.failed_stage>
   Reason: <parked_info.reason>
   ```

8. If `error_history` is non-empty, append:
   ```

   Errors:
     [<stage>] <error> (<timestamp>)
     ...
   ```

9. The Python block exits 0. The bash script exits 0 after Python completes successfully.

10. After displaying status output, log the status query to the audit log. Call `audit-logger.py log <spec-name> status_query '{"queried_state":"<current_state>"}'`. Locate `audit-logger.py` relative to the script at `home/.claude/hooks/sdl-workflow/audit-logger.py`. If the logger is not available (file not found), skip logging silently.

11. Make the script executable (add chmod comment at top).

## Files to create/modify

- `home/.claude/hooks/sdl-workflow/dispatch-status.sh` (create)

## Test requirements

Tests from task-13 (`tests/sdl-workflow/test-status-command.sh`) must pass:
- Queued spec displays spec name, status, and timestamp
- Reviewing spec shows stage history with multiple stages
- Parked spec shows failed stage and failure reason
- Completed spec shows COMPLETED status
- Non-existent spec exits 1 with not-found message
- Output is human-readable with labeled fields
- Error history entries are displayed

## Acceptance criteria

AC-10: Pipeline state is queryable via status command.

Primary AC: tests from task-13 pass.

## Model

Haiku

## Wave

2
