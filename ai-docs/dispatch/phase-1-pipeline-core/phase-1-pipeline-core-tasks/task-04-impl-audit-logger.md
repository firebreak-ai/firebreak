## Objective

Implement the audit logger as a Python script that appends structured JSON lines to per-spec log files.

## Context

The audit logger provides append-only structured logging for the pipeline. Each spec has its own log file. Every pipeline action (state transitions, gate results, errors) is recorded as a JSON line. The logger never truncates or rotates logs. It must handle concurrent appends safely (file append mode) and create directories/files as needed.

The script must be standalone Python 3 (stdlib only). It is invoked as a CLI tool by other pipeline components.

If the `LOG_DIR` environment variable is set, use it instead of `.claude/automation/logs/`.

## Instructions

1. Create `home/dot-claude/hooks/sdl-workflow/audit-logger.py`. Add shebang `#!/usr/bin/env python3` and module docstring.

2. Implement `get_log_dir()`: return `os.environ.get("LOG_DIR", ".claude/automation/logs")`.

3. Implement `get_log_path(spec_name)`: return `os.path.join(get_log_dir(), f"{spec_name}.log")`.

4. Implement `log_event(spec_name, event_type, json_data_str)`:
   - Parse `json_data_str` as JSON. If invalid JSON, print error to stderr and exit 1.
   - Build the log entry dict: `timestamp` = UTC ISO8601 now, `spec` = spec_name, `event_type` = event_type, `data` = parsed JSON data.
   - Create log directory with `os.makedirs(exist_ok=True)`.
   - Open log file in append mode (`"a"`).
   - Write `json.dumps(entry)` followed by `"\n"`. Use compact JSON (no indent) so each entry is one line.
   - Do not write to stdout on success. Exit 0.

5. Implement `read_log(spec_name)`:
   - If log file doesn't exist, print error to stderr and exit 1.
   - Read the file and print contents to stdout (all lines).
   - Exit 0.

6. Implement `main()` with `argparse`:
   - Subcommands: `log`, `read`.
   - `log` takes positional `spec-name`, `event-type`, `json-data`.
   - `read` takes positional `spec-name`.
   - Route to corresponding function.

7. Use `datetime.datetime.now(datetime.timezone.utc).isoformat()` for timestamps.

8. Guard with `if __name__ == "__main__": main()`.

## Files to create/modify

- `home/dot-claude/hooks/sdl-workflow/audit-logger.py` (create)

## Test requirements

Tests from task-03 must pass. Run `bash tests/sdl-workflow/test-audit-logger.sh` from project root and verify all tests pass.

## Acceptance criteria

AC-02: Audit logger records all dispatcher actions, gate results (structured JSON), and errors as append-only entries per spec. Gate pass and rejection events are both captured.

Primary AC: all tests from task-03 pass.

## Model

Haiku

## Wave

1
