---
id: task-47
type: implementation
wave: 1
covers: [AC-01, AC-08]
files_to_create:
  - assets/fbk-scripts/fbk/gates/test_hash.py
test_tasks: [task-06]
completion_gate: "task-06 tests pass"
---

## Objective

Convert `assets/hooks/fbk-sdl-workflow/test-hash-gate.sh` to `assets/fbk-scripts/fbk/gates/test_hash.py`, replacing `sha256sum` and `mapfile` with Python stdlib.

## Context

`test-hash-gate.sh` (103 lines) computes SHA-256 hashes of test files using `sha256sum` (GNU coreutils) and `mapfile` (bash 4.0+) — both are GNU/bash-specific and unavailable on macOS default bash. The Python conversion uses `hashlib.sha256` and standard file reading, resolving cross-platform issues. On first run it creates a `test-hashes.json` manifest. On subsequent runs it compares current hashes and reports MISSING, UNEXPECTED, or MODIFIED files.

Test files are found with: `find <dir> -type f \( -path "*/tests/*" -o -name "*test*" \) ! -name "test-hashes.json"`, sorted.

## Instructions

1. Create `assets/fbk-scripts/fbk/gates/test_hash.py`
2. Implement `compute_hashes(feature_dir)` — find test files matching the same criteria as the bash script (path contains `/tests/` or filename contains `test`, excluding `test-hashes.json`), compute SHA-256 hex digest for each, return dict `{relative_path: hex_hash}`
3. Implement `create_manifest(feature_dir)` — call `compute_hashes`, write JSON manifest to `<feature_dir>/test-hashes.json` with `files` and `computed_at` (UTC ISO timestamp) keys. Return `{"gate": "test-hash", "result": "pass", "action": "created", "files": N}`
4. Implement `verify_manifest(feature_dir)` — load existing manifest, compute current hashes, compare:
   - Files in manifest but not current: `"MISSING: {path}"`
   - Files in current but not manifest: `"UNEXPECTED: {path}"`
   - Files with different hash: `"MODIFIED: {path} (expected: {old}, actual: {new})"`
   - On errors: print each to stderr, exit 2
   - On pass: return `{"gate": "test-hash", "result": "pass", "action": "verified", "files": N}`
5. Implement `main()` with argparse: feature directory path. If no manifest exists, create it. If manifest exists, verify against it. If directory has no test files, output `{"gate":"test-hash","result":"pass","files":0,"note":"no test files found"}` and exit 0
6. Hash computation must use `hashlib.sha256` with binary file reading (`rb` mode)

## Files to create/modify

- **Create**: `assets/fbk-scripts/fbk/gates/test_hash.py`

## Test requirements

- task-06: first run creates manifest with correct structure and 64-char hex hashes, no-change verification passes, modified file detected, deleted file detected, unexpected new file detected, empty directory passes

## Acceptance criteria

- AC-01: test-hash-gate.sh converted to Python with `hashlib.sha256`
- AC-08: gate produces correct pass/fail for manifest operations

## Model

Sonnet

## Wave

1
