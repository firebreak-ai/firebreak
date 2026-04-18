---
id: task-06
type: test
wave: 1
covers: [AC-01, AC-08]
files_to_create:
  - assets/fbk-scripts/tests/test_gates_test_hash.py
completion_gate: "tests compile and fail before implementation"
---

## Objective

Create pytest unit tests for `fbk.gates.test_hash` manifest creation and modification detection.

## Context

`test-hash-gate.sh` computes SHA-256 hashes of test files using `sha256sum` and `mapfile` (both bash/GNU-specific). The Python conversion uses `hashlib.sha256` and standard file reading. On first run it creates a `test-hashes.json` manifest. On subsequent runs it compares current hashes to the manifest and reports MISSING, UNEXPECTED, or MODIFIED files. Follow the test structure in `tests/sdl-workflow/test-hash-gate.sh` (tests 1-7).

## Instructions

1. Create `assets/fbk-scripts/tests/test_gates_test_hash.py`
2. Import functions from `fbk.gates.test_hash` (e.g., `compute_hashes`, `create_manifest`, `verify_manifest`)
3. Write a test using `tmp_path` fixture: create test files, call manifest creation, assert manifest JSON has correct file count and 64-char hex hashes
4. Write a test: create manifest, call verify with no changes — assert result is "pass"
5. Write a test: create manifest, modify a file, call verify — assert MODIFIED error reported
6. Write a test: create manifest, delete a file, call verify — assert MISSING error reported
7. Write a test: create manifest, add a new file, call verify — assert UNEXPECTED error reported
8. Write a test: empty directory with no test files — assert passes with `files: 0`

## Files to create/modify

- **Create**: `assets/fbk-scripts/tests/test_gates_test_hash.py`

## Test requirements

| Level | Behavior | Expected assertion |
|-------|----------|--------------------|
| Unit | first run creates manifest with correct structure | manifest JSON has expected file count, 64-char hex hashes |
| Unit | no-change verification passes | result == "pass" |
| Unit | modified file detected | error contains "MODIFIED" |
| Unit | deleted file detected | error contains "MISSING" |
| Unit | unexpected new file detected | error contains "UNEXPECTED" |
| Unit | empty directory passes gracefully | result passes, files == 0 |

## Acceptance criteria

- AC-01: validates test-hash gate converted to Python with `hashlib.sha256`
- AC-08: gate produces correct pass/fail for manifest operations

## Model

Haiku

## Wave

1
