## Objective

Implement the pipeline state engine as a Python script that manages per-spec state files with transition enforcement.

## Context

The state engine tracks each spec's progress through 19 pipeline states. It persists state as JSON files in `.claude/automation/state/`. Every transition must be validated against the legal transition table before persisting. The PARKED state captures which stage failed and why; READY resumes at the failed stage.

The script must be standalone Python 3 (stdlib only, no external dependencies). It is invoked as a CLI tool by other pipeline components and by the developer via status commands.

If the `STATE_DIR` environment variable is set, use it as the state directory instead of `.claude/automation/state/`. This enables test isolation.

## Instructions

1. Create `home/.claude/hooks/sdl-workflow/state-engine.py`. Add a shebang `#!/usr/bin/env python3` and module docstring.

2. Define the complete transition table as a dictionary constant `VALID_TRANSITIONS`. Every state maps to a list of valid target states:
   - `QUEUED`: [`VALIDATING`]
   - `VALIDATING`: [`VALIDATED`, `PARKED`]
   - `VALIDATED`: [`REVIEWING`]
   - `REVIEWING`: [`REVIEWED`, `PARKED`]
   - `REVIEWED`: [`BREAKING_DOWN`]
   - `BREAKING_DOWN`: [`BROKEN_DOWN`, `PARKED`]
   - `BROKEN_DOWN`: [`TASK_REVIEWING`]
   - `TASK_REVIEWING`: [`TASKS_READY`, `PARKED`]
   - `TASKS_READY`: [`TESTING`]
   - `TESTING`: [`TESTS_WRITTEN`, `PARKED`]
   - `TESTS_WRITTEN`: [`TEST_REVIEWING`]
   - `TEST_REVIEWING`: [`TESTS_READY`, `PARKED`]
   - `TESTS_READY`: [`IMPLEMENTING`]
   - `IMPLEMENTING`: [`IMPLEMENTED`, `PARKED`]
   - `IMPLEMENTED`: [`VERIFYING`]
   - `VERIFYING`: [`COMPLETED`, `PARKED`]
   - `COMPLETED`: []
   - `PARKED`: [`READY`]
   - `READY`: [] (dynamic — resolved at runtime from `parked_info.failed_stage`)

3. Define `ALL_STATES` as the set of all keys in `VALID_TRANSITIONS`.

4. Implement `get_state_dir()`: return `os.environ.get("STATE_DIR", ".claude/automation/state")`.

5. Implement `get_state_path(spec_name)`: return `os.path.join(get_state_dir(), f"{spec_name}.json")`.

6. Implement `create_state(spec_name)`:
   - Check if state file already exists. If yes, print error to stderr and return exit code 1.
   - Create the state directory with `os.makedirs(exist_ok=True)`.
   - Build the state dict: `spec_name`, `current_state` = `QUEUED`, `stage_timestamps` = `{"QUEUED": <ISO8601 now>}`, `agent_ids` = [], `verification_results` = {}, `error_history` = [], `parked_info` = {}.
   - Write to file as indented JSON.
   - Print the state dict as JSON to stdout.

7. Implement `read_state(spec_name)`:
   - Read and parse the JSON file. If file doesn't exist, print error to stderr and exit 1.
   - Print the state dict as JSON to stdout.

8. Implement `transition_state(spec_name, new_state, reason=None)`:
   - Load current state from file. If file doesn't exist, error and exit 1.
   - Determine valid transitions for current state. For `READY` state: valid transitions are the list containing the active state that corresponds to `parked_info["failed_stage"]`. Map the failed stage (which is the active/processing state like `VALIDATING`) to itself — READY resumes at the same active state. If `parked_info` is empty or missing `failed_stage`, error and exit 1.
   - If `new_state` not in valid transitions: print error to stderr showing current state, attempted state, and valid options. Exit 1. Do not modify the state file.
   - If valid: update `current_state` to `new_state`. Add `new_state` to `stage_timestamps` with current ISO8601 timestamp.
   - If `new_state` == `PARKED`: set `parked_info` = `{"failed_stage": <previous current_state>, "reason": reason or ""}`. Append to `error_history`: `{"stage": <previous current_state>, "error": reason or "", "timestamp": <ISO8601>}`.
   - If `new_state` == `READY` or any non-PARKED state: clear `parked_info` to `{}` only when transitioning out of READY (i.e., when current state is READY and transitioning to the resume state).
   - Write updated state to file.
   - Print updated state as JSON to stdout.

9. Implement `get_valid_transitions(spec_name)`:
   - Load current state. For READY state, resolve dynamically from `parked_info.failed_stage` as in step 8.
   - Print the list of valid target states as a JSON array to stdout.

10. Implement `main()` with `argparse`:
    - Subcommands: `create`, `transition`, `read`, `get-valid-transitions`.
    - `create` takes positional `spec-name`.
    - `transition` takes positional `spec-name` and `new-state`, optional `--reason`.
    - `read` takes positional `spec-name`.
    - `get-valid-transitions` takes positional `spec-name`.
    - Route to the corresponding function. Use `sys.exit()` with the return code.

11. Use `datetime.datetime.now(datetime.timezone.utc).isoformat()` for timestamps (timezone-aware UTC).

12. All JSON output uses `json.dumps(data, indent=2)` for human readability.

13. Guard with `if __name__ == "__main__": main()`.

## Files to create/modify

- `home/.claude/hooks/sdl-workflow/state-engine.py` (create)

## Test requirements

Tests from task-01 must pass. Run `bash tests/sdl-workflow/test-state-engine.sh` from project root and verify all tests pass.

## Acceptance criteria

AC-01: Pipeline state engine tracks spec progress through stages, persists state as JSON after each transition, and resumes correctly after interruption. PARKED and READY states function as specified.

Primary AC: all tests from task-01 pass.

## Model

Sonnet

## Wave

1
