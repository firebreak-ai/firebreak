---
id: T-03
type: test
wave: 2
covers: [AC-02, AC-09]
files_to_create: [tests/installer/test-json-merge-env.sh]
completion_gate: "Tests compile and fail before implementation begins"
---

## Objective

Write tests for the Python 3 JSON merge script's env-merging behavior, the "actually-added" tracking output for manifest recording, and error handling for malformed JSON input.

## Context

The merge script handles env merging with these rules:
- Add firebreak env entries to the existing `env` object.
- Do not overwrite existing keys with the same name. If a key already exists, skip it.
- Output a secondary JSON blob (on a separate line or via a separate flag) that records only the keys that were actually added, so the manifest can track what to remove on uninstall.

The merge script also validates that the input `settings.json` is well-formed JSON. If it is malformed, the script exits non-zero with an error message and does not produce output.

For settings.json with no pre-existing `env` key, the merge script creates the `env` object with all firebreak entries.

Test fixtures from T-01 provide: `settings-empty.json`, `settings-existing-env.json`, `settings-malformed.json`, `firebreak-settings.json`.

Follow the TAP format pattern in `tests/sdl-workflow/test-spec-validator.sh`.

## Instructions

1. Create `tests/installer/test-json-merge-env.sh`. Set up TAP boilerplate matching the pattern in `tests/sdl-workflow/test-spec-validator.sh`.

2. Define the same variables as T-02: `SCRIPT_DIR`, `PROJECT_ROOT`, `MERGE_SCRIPT`, `FIXTURES`. Create setup/cleanup with temp directory.

3. Write test: **add env to empty settings**. Copy `settings-empty.json` to temp dir. Run the merge script. Parse output to assert: `env.CLAUDE_CODE_EXPERIMENTAL_AGENT_TEAMS` equals `"1"`.

4. Write test: **do not overwrite existing env keys**. Copy `settings-existing-env.json` to temp dir (contains `CLAUDE_CODE_EXPERIMENTAL_AGENT_TEAMS` set to `"0"` and `MY_CUSTOM_VAR` set to `"my-value"`). Run the merge script. Parse output to assert: `env.CLAUDE_CODE_EXPERIMENTAL_AGENT_TEAMS` still equals `"0"` (not overwritten), `env.MY_CUSTOM_VAR` still equals `"my-value"` (preserved).

5. Write test: **actually-added keys tracking — new key recorded**. Copy `settings-empty.json` to temp dir. Run the merge script. Parse the "added" output to assert: the added-keys record includes `CLAUDE_CODE_EXPERIMENTAL_AGENT_TEAMS` with value `"1"`.

6. Write test: **actually-added keys tracking — pre-existing key not recorded**. Copy `settings-existing-env.json` to temp dir (already has `CLAUDE_CODE_EXPERIMENTAL_AGENT_TEAMS`). Run the merge script. Parse the "added" output to assert: the added-keys record does NOT include `CLAUDE_CODE_EXPERIMENTAL_AGENT_TEAMS` (it was skipped because the key already existed).

7. Write test: **malformed JSON input exits with error**. Copy `settings-malformed.json` to temp dir. Run the merge script, capturing stderr. Assert: exit code is non-zero, stderr contains an error message (check for "malformed" or "JSON" or "parse" case-insensitively), stdout is empty (no partial output produced).

8. Write test: **no pre-existing settings.json creates new env object**. Run the merge script with a `settings.json` path that does not exist (or contains just `{}`). Parse output to assert: `env` key exists with firebreak entries.

9. End with summary and exit.

## Files to create/modify

- `tests/installer/test-json-merge-env.sh` (create)

No existing file is the right location — this is a new test file in the new `tests/installer/` directory.

## Test requirements

Tests to write (all in `test-json-merge-env.sh`):
1. Add env to empty settings creates env object with firebreak entries
2. Existing env key with same name is not overwritten
3. Actually-added tracking records new keys
4. Actually-added tracking omits pre-existing keys
5. Malformed JSON input exits non-zero with error message and no stdout
6. Missing/empty settings.json creates env with firebreak entries

## Acceptance criteria

- AC-02: After merge, `env` in target `settings.json` contains all firebreak entries AND all pre-existing entries. Existing keys are not overwritten.
- AC-09: The merge script exits with a clear error and makes no changes when target settings.json is malformed.

## Model

Haiku

## Wave

1
