## Objective

Write bash test scripts that validate the audit logger's append-only JSON lines logging and log reading.

## Context

The audit logger is a Python script (`audit-logger.py`) that appends structured JSON lines to per-spec log files in `.claude/automation/logs/`. Each line is a complete JSON object with timestamp, spec name, event_type, and data. The logger must never corrupt existing entries when appending. It creates the log file and directory if they don't exist.

CLI interface: `python3 audit-logger.py <command> <spec-name> [args]`
- `log <spec-name> <event-type> '<json-data>'` — appends one JSON line
- `read <spec-name>` — outputs all log lines to stdout

Log line format:
```json
{"timestamp": "ISO8601", "spec": "spec-name", "event_type": "string", "data": {}}
```

## Instructions

1. Create `tests/sdl-workflow/test-audit-logger.sh` as a bash test script. Use `set -uo pipefail`. Define a test counter and pass/fail tracking. Use TAP output format (`ok <n> - <description>` / `not ok <n> - <description>`).

2. Define a setup function that creates a temporary directory for `.claude/automation/logs/`, sets `LOG_DIR` to that path, and exports it. Register cleanup with `trap cleanup EXIT`.

3. Define `LOGGER` variable pointing to `home/dot-claude/hooks/sdl-workflow/audit-logger.py` (relative to project root).

4. Write test: single log event produces valid JSON line. Run `log test-spec state_change '{"from": "QUEUED", "to": "VALIDATING"}'`. Assert exit 0. Read the log file at `$LOG_DIR/test-spec.log`. Assert file has exactly 1 line. Parse the line as JSON and verify: `timestamp` matches ISO8601 regex, `spec` equals `test-spec`, `event_type` equals `state_change`, `data.from` equals `QUEUED`, `data.to` equals `VALIDATING`.

5. Write test: multiple sequential log calls produce valid JSON lines. Run 3 `log` calls with different event types (`state_change`, `gate_result`, `error`). Assert the log file has exactly 3 lines. Parse each line independently as JSON (each must be valid). Verify each has the correct `event_type`.

6. Write test: existing entries preserved when appending. Write a known JSON line directly to the log file before calling `log`. Run one `log` call. Assert the file has 2 lines. Assert the first line is the pre-existing entry (byte-identical). Assert the second line is the new entry.

7. Write test: log file created if it doesn't exist. Remove any existing log file. Run `log new-spec gate_result '{"gate": "spec-validation", "result": "pass"}'`. Assert the file exists at `$LOG_DIR/new-spec.log` and has 1 line.

8. Write test: log directory created if it doesn't exist. Set `LOG_DIR` to a new path within the temp directory that doesn't exist. Run `log test-spec info '{"message": "test"}'`. Assert the directory was created and the log file exists.

9. Write test: `read` returns all events. Log 3 events to `test-spec`. Run `read test-spec`. Assert exit 0. Assert stdout has 3 lines. Parse each line as valid JSON.

10. Write test: `read` for non-existent spec. Run `read nonexistent-spec`. Assert exit code is non-zero or stdout is empty (either behavior is acceptable — document which one the test expects).

11. Write test: data field accepts nested JSON. Run `log test-spec complex_event '{"nested": {"key": "value", "list": [1, 2, 3]}}'`. Read the log file, parse the line, verify `data.nested.key` equals `value` and `data.nested.list` has 3 elements.

12. End the script with a summary line and appropriate exit code.

## Files to create/modify

- `tests/sdl-workflow/test-audit-logger.sh` (create)

## Test requirements

This is a test task. Tests to write (all in `test-audit-logger.sh`):
1. Unit: single log event produces valid JSON line with correct fields
2. Integration: multiple sequential log calls produce valid independent JSON lines
3. Unit: appending preserves existing entries byte-identically
4. Unit: log file created when it doesn't exist
5. Unit: log directory created when it doesn't exist
6. Integration: `read` returns all logged events as parseable JSON lines
7. Unit: `read` handles non-existent spec gracefully
8. Unit: nested JSON in data field preserved correctly

## Acceptance criteria

AC-02: Audit logger records all dispatcher actions, gate results (structured JSON), and errors as append-only entries per spec. Gate pass and rejection events are both captured.

## Model

Haiku

## Wave

1
