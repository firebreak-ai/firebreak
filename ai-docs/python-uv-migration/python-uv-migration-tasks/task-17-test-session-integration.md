---
id: task-17
type: test
wave: 2
covers: [AC-02]
files_to_create:
  - tests/sdl-workflow/test-session-integration-python.sh
completion_gate: "tests compile and fail before implementation"
---

## Objective

Create bash integration tests verifying `python3 fbk.py session-logger` and `python3 fbk.py session-manager` work through the dispatcher.

## Context

The spec's user verification step UV-5 requires: `python3 fbk.py session-logger init test-session --tier quick --task "test"` creates session log at expected location. The spec also requires: `python3 fbk.py session-manager register <id> quick` creates a session registry entry, and `session-manager unregister <id>` removes it.

## Instructions

1. Create `tests/sdl-workflow/test-session-integration-python.sh`
2. Set `DISPATCHER="$PROJECT_ROOT/assets/fbk-scripts/fbk.py"`
3. Use `mktemp -d` for working directory
4. Write Test 1: `python3 "$DISPATCHER" session-logger init test-session --tier quick --task "test"` → assert exit 0, then assert the session log file exists at the expected location (`$TMPDIR/council-logs/test-session/session.log` or equivalent from `session-logger.py`'s `--output-dir` argument)
5. Write Test 2: `python3 "$DISPATCHER" session-manager register test-session quick` → assert exit 0, then assert the registry file contains `test-session` (grep for `test-session` in the registry JSON)
6. Write Test 3: `python3 "$DISPATCHER" session-manager unregister test-session` → assert exit 0, then assert the registry file does NOT contain `test-session` (grep returns no match)

## Files to create/modify

- **Create**: `tests/sdl-workflow/test-session-integration-python.sh`

## Test requirements

| Level | Behavior | Expected assertion |
|-------|----------|--------------------|
| Integration | session-logger init creates log file | exit 0, session log file exists at expected path |
| Integration | session-manager register creates entry | exit 0, registry JSON contains "test-session" |
| Integration | session-manager unregister removes entry | exit 0, registry JSON does not contain "test-session" |

## Acceptance criteria

- AC-02: council modules relocated and callable through dispatcher

## Model

Haiku

## Wave

2
