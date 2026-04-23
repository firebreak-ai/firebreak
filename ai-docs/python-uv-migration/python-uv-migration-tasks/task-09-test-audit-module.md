---
id: task-09
type: test
wave: 1
covers: [AC-02]
files_to_create:
  - assets/fbk-scripts/tests/test_audit.py
completion_gate: "tests compile and fail before implementation"
---

## Objective

Create pytest unit tests for `fbk.audit` `log_event()` structured logging.

## Context

`audit-logger.py` (lines 19-37) implements `log_event(spec_name, event_type, json_data_str)` which parses JSON data, creates a structured entry with timestamp/spec/event_type/data, and appends it as a JSON line to `{LOG_DIR}/{spec_name}.log`. Follow test scenarios from `tests/sdl-workflow/test-audit-logger.sh` (tests 1-8).

The function already exists as `log_event()` in `audit-logger.py` — after relocation to `fbk.audit`, the function signature and behavior must be identical.

## Instructions

1. Create `assets/fbk-scripts/tests/test_audit.py`
2. Import `log_event`, `read_log`, `get_log_path` from `fbk.audit`
3. Write a test using `tmp_path` + `monkeypatch` to set `LOG_DIR` env var: call `log_event("myspec", "start", '{"key":"val"}')`, read the log file, parse as JSON, assert fields `timestamp`, `spec == "myspec"`, `event_type == "start"`, `data == {"key": "val"}`
4. Write a test: call `log_event` three times with same spec, assert log file has exactly 3 lines, each valid JSON
5. Write a test: pre-populate a log file with one line, call `log_event`, assert original line preserved and new line appended (2 total)
6. Write a test: call `log_event` with nested JSON data `{"outer":{"inner":[1,2]}}` — assert nested structure preserved in log
7. Write a test: call `log_event` with invalid JSON string — assert `SystemExit` raised with code 1

## Files to create/modify

- **Create**: `assets/fbk-scripts/tests/test_audit.py`

## Test requirements

| Level | Behavior | Expected assertion |
|-------|----------|--------------------|
| Unit | single log event produces valid JSON with correct fields | parsed entry has timestamp, spec, event_type, data |
| Unit | multiple log calls produce independent lines | 3 lines, each valid JSON |
| Unit | existing entries preserved on append | 2 total lines, first is original |
| Unit | nested JSON preserved | data.outer.inner == [1,2] |
| Unit | invalid JSON exits with error | SystemExit code 1 |

## Acceptance criteria

- AC-02: validates audit-logger.py relocated and importable as `fbk.audit`

## Model

Haiku

## Wave

1
