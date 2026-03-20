## Objective

Write bash test scripts that validate the test hash gate's manifest creation, comparison, and tamper detection behavior.

## Context

The test hash gate (`test-hash-gate.sh`) computes SHA-256 hashes of test files for a feature, writes a manifest JSON to `ai-docs/<feature>/test-hashes.json`, and on subsequent runs detects modifications, deletions, or additions. It is a standalone gate script — it does not require the verification execution engine (Phase 2).

The gate takes one argument: `<feature-dir>` (path to `ai-docs/<feature>/`). It finds test files within the feature's scope, computes SHA-256 hashes using `sha256sum`, and manages the manifest.

Manifest format: `{"files": {"relative/path": "sha256hex", ...}, "computed_at": "ISO8601"}`.

Exit conventions: 0 = pass (JSON to stdout), 2 = fail (errors to stderr listing each discrepancy).

## Instructions

1. Create directory `tests/fixtures/hash-gate/` if it does not exist.

2. Create sample test files for hashing:
   - `tests/fixtures/hash-gate/sample-tests/test-alpha.sh` — a short bash script (5-10 lines) with a comment and an echo statement.
   - `tests/fixtures/hash-gate/sample-tests/test-beta.sh` — a different short bash script.
   - `tests/fixtures/hash-gate/sample-tests/helpers/test-utils.sh` — a helper file in a subdirectory.

3. Create `tests/sdl-workflow/test-hash-gate.sh` as a bash test script. Use `set -uo pipefail`. Define test counter and pass/fail tracking. TAP format output.

4. Define `GATE` variable pointing to `home/dot-claude/hooks/sdl-workflow/test-hash-gate.sh` relative to project root. Determine project root using `cd "$(dirname "$0")/../.." && pwd`.

5. Define a setup function that creates a temporary directory structure simulating `ai-docs/<feature>/`. Copy the sample test files from `tests/fixtures/hash-gate/sample-tests/` into a `tests/` subdirectory within the temp feature dir. Register cleanup with `trap cleanup EXIT`.

6. Write test: first run creates manifest. Run `$GATE "$TEMP_FEATURE_DIR"`. Assert exit 0. Assert `$TEMP_FEATURE_DIR/test-hashes.json` exists. Parse the manifest JSON with Python and verify: `files` key exists and contains 3 entries, each value is a 64-character hex string, `computed_at` key exists and matches ISO8601 format.

7. Write test: subsequent run with no changes passes. Run `$GATE "$TEMP_FEATURE_DIR"` twice (first creates manifest, second compares). Assert second run exits 0. Assert stdout of second run contains `"result":"pass"` or a no-changes indicator.

8. Write test: modified file detected. Run `$GATE` to create manifest. Then append a line to one of the test files. Run `$GATE` again. Assert exit 2. Assert stderr names the modified file.

9. Write test: deleted file detected. Run `$GATE` to create manifest. Then delete one test file. Run `$GATE` again. Assert exit 2. Assert stderr names the missing file.

10. Write test: new file detected. Run `$GATE` to create manifest. Then create a new file `test-gamma.sh` in the test directory. Run `$GATE` again. Assert exit 2. Assert stderr names the unexpected file.

11. Write test: manifest JSON structure. Run `$GATE` to create manifest. Read the manifest file. Parse with Python and verify the exact structure: top-level keys are exactly `files` and `computed_at`, `files` is a dict, `computed_at` is a string. Verify file paths in manifest are relative (not absolute).

12. Write test: empty test directory. Create a temp feature dir with no test files. Run `$GATE`. Assert it handles gracefully (either exit 0 with empty manifest or exit 2 with informative error — document which behavior is expected).

13. End the script with a summary line and appropriate exit code.

## Files to create/modify

- `tests/sdl-workflow/test-hash-gate.sh` (create)
- `tests/fixtures/hash-gate/sample-tests/test-alpha.sh` (create)
- `tests/fixtures/hash-gate/sample-tests/test-beta.sh` (create)
- `tests/fixtures/hash-gate/sample-tests/helpers/test-utils.sh` (create)

Justification for multiple files: the hash gate needs a realistic file tree with nested directories to test hash computation across subdirectories.

## Test requirements

This is a test task. Tests to write (all in `test-hash-gate.sh`):
1. Unit: first run creates manifest with correct JSON structure and SHA-256 hashes
2. Unit: subsequent run with unchanged files exits 0
3. Unit: modified file detected with exit 2 and file named in stderr
4. Unit: deleted file detected with exit 2 and file named in stderr
5. Unit: new file detected with exit 2 and file named in stderr
6. Unit: manifest JSON has correct structure with relative paths
7. Edge: empty test directory handled gracefully

## Acceptance criteria

AC-09: Test hash gate script (`test-hash-gate.sh`) computes SHA-256 manifest and detects test file modifications.

## Model

Haiku

## Wave

2
