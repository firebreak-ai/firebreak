## Objective

Implement the test hash gate script and create the verify.yml schema documentation.

## Context

The test hash gate is a standalone gate script that computes SHA-256 hashes of test files for a feature, writes a manifest, and detects tampering on subsequent runs. It follows the existing gate script pattern: bash for argument handling and file operations, embedded Python3 for JSON parsing.

The verify.yml schema documentation defines the check interface for Phase 2's verification execution engine. Phase 1 ships the interface definition and one concrete gate (test-hash-gate.sh); the execution engine is deferred.

Exit conventions: 0 = pass (JSON to stdout), 2 = fail (errors to stderr).

## Instructions

1. Create `home/dot-claude/hooks/sdl-workflow/test-hash-gate.sh`. Start with `#!/usr/bin/env bash` and `set -uo pipefail`.

2. Parse arguments: accept one positional argument `<feature-dir>`. Validate the directory exists. Print usage to stderr and exit 2 if missing or invalid.

3. Set `MANIFEST` to `"$FEATURE_DIR/test-hashes.json"`.

4. Find test files: search for files matching `tests/**` within the feature directory. Use `find "$FEATURE_DIR" -type f -path "*/tests/*"` or equivalent. Also match files with `*test*` in the name outside a `tests/` directory. Sort the file list for deterministic ordering. Store paths relative to `$FEATURE_DIR`.

5. If no test files found: print `{"gate":"test-hash","result":"pass","files":0,"note":"no test files found"}` to stdout and exit 0.

6. Compute SHA-256 hash of each file using `sha256sum`. Collect results as `relative_path -> hash` pairs.

7. If manifest does not exist (first run):
   - Build JSON manifest using embedded Python3: `{"files": {"relative/path": "sha256hex", ...}, "computed_at": "ISO8601"}`. Generate the ISO8601 timestamp with `datetime.datetime.utcnow().isoformat() + "Z"`.
   - Write manifest to `$MANIFEST`.
   - Print `{"gate":"test-hash","result":"pass","action":"created","files":<count>}` to stdout.
   - Exit 0.

8. If manifest exists (subsequent run):
   - Load existing manifest JSON with embedded Python3.
   - Compare current file set against manifest:
     a. Files in manifest but missing from disk: report each as `MISSING: <path>` to stderr.
     b. Files on disk but not in manifest: report each as `UNEXPECTED: <path>` to stderr.
     c. Files in both but hash differs: report each as `MODIFIED: <path> (expected: <old-hash>, actual: <new-hash>)` to stderr.
   - If any discrepancies: exit 2.
   - If all match: print `{"gate":"test-hash","result":"pass","action":"verified","files":<count>}` to stdout. Exit 0.

9. After producing the final JSON result (pass or fail), log the result to the audit log. Derive the spec name from the feature directory name (basename of `$FEATURE_DIR`). Call `audit-logger.py log <spec-name> gate_result '<json>'` where `<json>` is the same JSON emitted to stdout. Locate `audit-logger.py` relative to the script at `home/dot-claude/hooks/sdl-workflow/audit-logger.py`. If the logger is not available (file not found), skip logging silently — do not fail the gate.

10. Make the script executable: include a comment at the top reminding to `chmod +x`.

10. Create `home/dot-claude/docs/sdl-workflow/verify-yml-schema.md`. Document the verify.yml check interface:

    - Start with the schema definition: each entry under `checks:` has fields `name` (string, check identifier), `command` (string, shell command to execute), `required` (boolean, true = pipeline-blocking failure, false = advisory/log only), `threshold` (optional numeric, check-specific).
    - Show the YAML structure:
      ```yaml
      checks:
        - name: "string - check identifier"
          command: "string - shell command to execute"
          required: true|false
          threshold: 0.8  # optional, check-specific
      ```
    - Include 3 example check entries:
      1. `test-execution`: `command: "npm test -- --reporter json"`, `required: true`
      2. `linter`: `command: "npm run lint -- --format json"`, `required: true`
      3. `test-hash-immutability`: `command: "bash home/dot-claude/hooks/sdl-workflow/test-hash-gate.sh ai-docs/$FEATURE/"`, `required: true`
    - Document the execution contract: the command runs in the project root, exit 0 = check passed, non-zero = check failed. Stdout should be JSON with at minimum `{"result": "pass"|"fail"}`. Stderr is captured for error reporting.
    - Document the `required` vs advisory distinction: required checks block pipeline advancement and set state to PARKED on failure; advisory checks log results but do not block.
    - Document threshold semantics: when present, the execution engine passes the threshold to the check command (mechanism TBD in Phase 2). Checks that support thresholds document their threshold interpretation.

## Files to create/modify

- `home/dot-claude/hooks/sdl-workflow/test-hash-gate.sh` (create)
- `home/dot-claude/docs/sdl-workflow/verify-yml-schema.md` (create)

## Test requirements

Tests from task-09 (`tests/sdl-workflow/test-hash-gate.sh`) must pass:
- First run creates manifest with correct JSON structure
- Subsequent run with unchanged files exits 0
- Modified file detected with exit 2
- Deleted file detected with exit 2
- New file detected with exit 2
- Manifest has correct structure with relative paths
- Empty test directory handled gracefully

## Acceptance criteria

AC-09: Verification check interface defined in `verify.yml` schema (check name, command, required/advisory, thresholds). Test hash gate script (`test-hash-gate.sh`) computes SHA-256 manifest and detects test file modifications.

Primary AC: tests from task-09 pass.

## Model

Haiku

## Wave

2
