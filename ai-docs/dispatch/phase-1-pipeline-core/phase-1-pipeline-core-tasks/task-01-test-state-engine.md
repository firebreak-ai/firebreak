## Objective

Write bash test scripts that validate the pipeline state engine's state creation, transition enforcement, persistence, and PARKED/READY lifecycle.

## Context

The state engine is a Python script (`state-engine.py`) that manages per-spec pipeline state as JSON files in `.claude/automation/state/`. It tracks 19 states with defined valid transitions. The engine must reject invalid transitions (exit 1, error to stderr), persist state after every transition, and support the PARKED->READY resume lifecycle where READY transitions back to the failed stage's active state.

Valid transitions (exhaustive):
- QUEUED -> VALIDATING
- VALIDATING -> VALIDATED, PARKED
- VALIDATED -> REVIEWING
- REVIEWING -> REVIEWED, PARKED
- REVIEWED -> BREAKING_DOWN
- BREAKING_DOWN -> BROKEN_DOWN, PARKED
- BROKEN_DOWN -> TASK_REVIEWING
- TASK_REVIEWING -> TASKS_READY, PARKED
- TASKS_READY -> TESTING
- TESTING -> TESTS_WRITTEN, PARKED
- TESTS_WRITTEN -> TEST_REVIEWING
- TEST_REVIEWING -> TESTS_READY, PARKED
- TESTS_READY -> IMPLEMENTING
- IMPLEMENTING -> IMPLEMENTED, PARKED
- IMPLEMENTED -> VERIFYING
- VERIFYING -> COMPLETED, PARKED
- COMPLETED -> (terminal, no transitions)
- PARKED -> READY
- READY -> (the failed stage's active state)

The CLI interface: `python3 state-engine.py <command> <spec-name> [args]`
- `create <spec-name>` — creates state file with QUEUED
- `transition <spec-name> <new-state> [--reason "..."]` — validates and persists
- `read <spec-name>` — outputs current state JSON to stdout
- `get-valid-transitions <spec-name>` — outputs valid next states

State JSON schema:
```json
{
  "spec_name": "string",
  "current_state": "string",
  "stage_timestamps": {"STATE_NAME": "ISO8601"},
  "agent_ids": [],
  "verification_results": {},
  "error_history": [{"stage": "string", "error": "string", "timestamp": "ISO8601"}],
  "parked_info": {"failed_stage": "string", "reason": "string"}
}
```

## Instructions

1. Create `tests/sdl-workflow/test-state-engine.sh` as a bash test script. Use `set -uo pipefail`. Define a test counter and pass/fail tracking at the top. Each test prints `ok <n> - <description>` on pass or `not ok <n> - <description>` on fail (TAP format).

2. Define a setup function that creates a temporary directory for `.claude/automation/state/`, sets `STATE_DIR` to that path, and exports it so `state-engine.py` uses it instead of the default location. Define a cleanup function registered with `trap cleanup EXIT` that removes the temporary directory.

3. Define `ENGINE` variable pointing to `home/dot-claude/hooks/sdl-workflow/state-engine.py` (relative to project root). Each test invocation runs `python3 "$ENGINE" <args>` with the `STATE_DIR` environment variable set.

4. Write test: `create` produces valid JSON. Run `create test-spec`. Capture stdout. Assert exit code 0. Parse output with `python3 -c "import json,sys; d=json.load(sys.stdin); ..."` to verify: `spec_name` equals `test-spec`, `current_state` equals `QUEUED`, `stage_timestamps` has a `QUEUED` key with an ISO8601 value, `agent_ids` is an empty list, `error_history` is an empty list.

5. Write test: `create` persists to file. After `create test-spec`, assert file exists at `$STATE_DIR/test-spec.json`. Read file and parse JSON, verify it matches the stdout output from create.

6. Write test: valid transition QUEUED->VALIDATING. Create spec, then run `transition test-spec VALIDATING`. Assert exit 0. Parse output to verify `current_state` equals `VALIDATING` and `stage_timestamps` has both `QUEUED` and `VALIDATING` keys.

7. Write test: multi-step valid transition chain. Create spec, then run transitions: QUEUED->VALIDATING->VALIDATED->REVIEWING->REVIEWED->BREAKING_DOWN. Assert each exits 0. After the chain, run `read test-spec` and verify `current_state` equals `BREAKING_DOWN` and `stage_timestamps` has all 6 states.

8. Write test: invalid transition rejected. Create spec (state=QUEUED), attempt `transition test-spec COMPLETED`. Assert exit code 1. Assert stderr contains an error message (capture stderr with `2>&1`). Run `read test-spec` and verify state is still `QUEUED` (transition did not persist).

9. Write test: invalid transition QUEUED->REVIEWED rejected. Create spec, attempt `transition test-spec REVIEWED`. Assert exit 1.

10. Write test: state persists and reads back. Create spec, transition to VALIDATING, then run `read test-spec`. Assert output parses as valid JSON with `current_state` equals `VALIDATING`. Also directly read the file `$STATE_DIR/test-spec.json` and compare contents match.

11. Write test: PARKED records failed_stage and reason. Create spec, transition to VALIDATING, then `transition test-spec PARKED --reason "validation failed: missing section"`. Assert exit 0. Parse output to verify: `current_state` equals `PARKED`, `parked_info.failed_stage` equals `VALIDATING`, `parked_info.reason` equals `validation failed: missing section`, `error_history` has one entry with `stage` equals `VALIDATING`.

12. Write test: PARKED->READY->resume lifecycle. Create spec, transition through QUEUED->VALIDATING->PARKED (with reason). Then transition PARKED->READY. Assert exit 0 and `current_state` equals `READY`. Then run `get-valid-transitions test-spec` and assert the output includes `VALIDATING` (the failed stage). Transition READY->VALIDATING. Assert exit 0 and `current_state` equals `VALIDATING`.

13. Write test: timestamps are ISO8601 and increase. Create spec, sleep 1 second, transition to VALIDATING. Parse both timestamps from `stage_timestamps`. Assert both match ISO8601 regex `[0-9]{4}-[0-9]{2}-[0-9]{2}T[0-9]{2}:[0-9]{2}:[0-9]{2}`. Assert VALIDATING timestamp is lexicographically greater than QUEUED timestamp.

14. Write test: `get-valid-transitions` returns correct states. Create spec (QUEUED). Run `get-valid-transitions test-spec`. Assert output contains `VALIDATING` and does not contain `COMPLETED`, `REVIEWED`, or `PARKED`.

15. Write test: `create` for already-existing spec fails. Run `create test-spec` twice. Assert second invocation exits non-zero.

16. End the script with a summary line: `echo "# <pass-count>/<total-count> tests passed"`. Exit 0 if all passed, exit 1 otherwise.

## Files to create/modify

- `tests/sdl-workflow/test-state-engine.sh` (create)

## Test requirements

This is a test task. Tests to write (all in `test-state-engine.sh`):
1. Unit: `create` produces valid JSON with QUEUED state, correct schema fields
2. Unit: `create` persists state file to disk
3. Unit: valid transition advances state and records timestamp
4. Integration: multi-step transition chain preserves all timestamps
5. Unit: invalid transition QUEUED->COMPLETED rejected with exit 1
6. Unit: invalid transition QUEUED->REVIEWED rejected with exit 1
7. Unit: state persists to file and `read` returns matching JSON
8. Unit: PARKED state records failed_stage and failure_reason in parked_info
9. Integration: PARKED->READY->resume-at-failed-stage lifecycle
10. Unit: timestamps are ISO8601 format and monotonically increasing
11. Unit: `get-valid-transitions` returns correct next states
12. Unit: duplicate `create` fails

## Acceptance criteria

AC-01: Pipeline state engine tracks spec progress through stages, persists state as JSON after each transition, and resumes correctly after interruption. PARKED and READY states function as specified.

## Model

Haiku

## Wave

1
