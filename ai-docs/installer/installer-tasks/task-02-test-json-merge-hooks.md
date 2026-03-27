---
id: T-02
type: test
wave: 2
covers: [AC-01, AC-02]
files_to_create: [tests/installer/test-json-merge-hooks.sh]
completion_gate: "Tests compile and fail before implementation begins"
---

## Objective

Write tests for the Python 3 JSON merge script's hook-merging behavior: adding hooks to empty settings, appending to existing hook arrays, deduplicating by full matcher-group comparison, and preserving permissions untouched.

## Context

The installer delegates JSON merging to an inline Python 3 script. The merge script takes two arguments: the path to the existing `settings.json` and the path to the firebreak settings entries JSON. It writes the merged result to stdout. The merge script lives at `installer/merge-settings.py`.

Merging rules for hooks:
- For each hook event key, append firebreak's matcher groups to the existing array.
- Deduplicate by comparing the full matcher-group object (the combination of `matcher` pattern + `hooks` array contents), not just the command string.
- Do not remove or reorder existing entries.

Merging rules for permissions: not touched. The merge script preserves existing `permissions` exactly as-is and does not add new permission entries.

Test fixtures from T-01 provide the input files: `settings-empty.json`, `settings-existing-hooks.json`, `settings-with-permissions.json`, and `firebreak-settings.json`.

Follow the TAP format pattern in `tests/sdl-workflow/test-spec-validator.sh`: `#!/usr/bin/env bash` with `set -uo pipefail`, `PASS`/`FAIL`/`TOTAL` counters, `ok()`/`not_ok()` helpers, `echo "TAP version 13"` header, final `echo "1..$TOTAL"` and exit based on FAIL count.

## Instructions

1. Create `tests/installer/test-json-merge-hooks.sh`. Set up the TAP boilerplate: shebang, `set -uo pipefail`, counters, `ok()`/`not_ok()` helpers, `TAP version 13` header.

2. Define variables:
   - `SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"`
   - `PROJECT_ROOT="$(cd "$SCRIPT_DIR/../.." && pwd)"`
   - `MERGE_SCRIPT="$PROJECT_ROOT/installer/merge-settings.py"`
   - `FIXTURES="$PROJECT_ROOT/tests/fixtures/installer"`

3. Create a setup function that creates a temp directory (`mktemp -d`) and registers a cleanup trap (`trap cleanup EXIT`). Each test copies fixture files into the temp directory to avoid modifying originals.

4. Write test: **merge hooks into empty settings**. Copy `settings-empty.json` to temp dir as `settings.json`. Run `python3 "$MERGE_SCRIPT" "$TMPDIR/settings.json" "$FIXTURES/firebreak-settings.json"`. Capture stdout. Parse the output with `python3 -c` to assert: the output contains a `hooks` key, `hooks.TaskCompleted` is an array with exactly 1 entry, and that entry's `hooks[0].command` contains `fbk-sdl-workflow/task-completed.sh`.

5. Write test: **append hooks to existing hook events**. Copy `settings-existing-hooks.json` to temp dir. Run the merge script. Parse output to assert: `hooks.PreToolUse` still has the original entry (command contains `my-bash-guard.sh`), AND `hooks.TaskCompleted` exists with the firebreak entry. Verify the original `PreToolUse` entry was not removed or reordered.

6. Write test: **deduplicate identical matcher groups**. Copy `settings-empty.json` to temp dir. Run the merge script once, capture the output, write it back to `settings.json`. Run the merge script a second time with the updated `settings.json`. Parse the second output to assert: `hooks.TaskCompleted` still has exactly 1 entry (not 2). Re-merging the same entries does not create duplicates.

7. Write test: **different matchers with same command are preserved**. Create a temp `settings.json` that already has a `TaskCompleted` entry with a different `matcher` field but the same command string as the firebreak entry. Run the merge script. Parse output to assert: `hooks.TaskCompleted` has 2 entries (the original with the different matcher, plus the firebreak entry without a matcher). Different matcher-group objects are not deduplicated even if the command matches.

8. Write test: **permissions not modified**. Copy `settings-with-permissions.json` to temp dir. Run the merge script. Parse output to assert: `permissions.allow` equals `["Read", "Glob"]`, `permissions.deny` equals `["Bash"]`. The permissions object is byte-for-byte identical to the input.

9. End with summary: `echo "# $PASS/$TOTAL tests passed"`, `echo "1..$TOTAL"`, exit based on FAIL count.

## Files to create/modify

- `tests/installer/test-json-merge-hooks.sh` (create)

No existing file is the right location because `tests/installer/` does not exist yet, and installer tests are a separate test suite from the existing `tests/sdl-workflow/` tests.

## Test requirements

Tests to write (all in `test-json-merge-hooks.sh`):
1. Merge hooks into empty settings produces correct hooks structure
2. Append hooks preserves existing hook entries and adds firebreak entries
3. Re-merging identical matcher groups does not create duplicates
4. Different matchers with same command are preserved as separate entries
5. Permissions object is not modified by the merge

## Acceptance criteria

- AC-01: The merge script does not modify `permissions.allow`, `permissions.deny`, or `permissions.ask` in the target `settings.json`.
- AC-02: After merge, `hooks` in target `settings.json` contain all firebreak entries AND all pre-existing entries.

## Model

Haiku

## Wave

1
