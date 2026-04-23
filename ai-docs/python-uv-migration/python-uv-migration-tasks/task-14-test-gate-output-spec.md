---
id: task-14
type: test
wave: 2
covers: [AC-08]
files_to_create:
  - tests/sdl-workflow/test-gate-output-spec-python.sh
completion_gate: "tests compile and fail before implementation"
---

## Objective

Create bash integration tests verifying `python3 fbk.py spec-gate` produces correct JSON output and exit codes.

## Context

The spec (testing strategy, integration test lines) requires testing that `python3 fbk.py spec-gate <valid-fixture>` produces `{"gate":"spec","result":"pass",...}` on stdout and exits 0, and that `python3 fbk.py spec-gate <invalid-fixture>` produces failure messages on stderr and exits 2. Use fixtures from `tests/fixtures/specs/` which already exist for `test-spec-validator.sh`.

Follow the bash test conventions from `tests/sdl-workflow/test-spec-validator.sh`: TAP format, `ok()`/`not_ok()` helpers, PROJECT_ROOT-relative paths.

## Instructions

1. Create `tests/sdl-workflow/test-gate-output-spec-python.sh`
2. Set `DISPATCHER="$PROJECT_ROOT/assets/fbk-scripts/fbk.py"` and `FIXTURES="$PROJECT_ROOT/tests/fixtures/specs"`
3. Write Test 1: `python3 "$DISPATCHER" spec-gate "$FIXTURES/valid-spec.md"` → assert exit 0, stdout contains `"result":"pass"` and `"scope":"feature"`, stderr is empty
4. Write Test 2: `python3 "$DISPATCHER" spec-gate "$FIXTURES/missing-sections-spec.md"` → assert exit 2, stderr contains "Missing section"
5. Write Test 3: `python3 "$DISPATCHER" spec-gate "$FIXTURES/injection-attempt-spec.md"` → assert exit 0, stderr WARNING count >= 3
6. Write Test 4: `python3 "$DISPATCHER" spec-gate /dev/null` → assert exit 2, stderr contains a descriptive error message (UV-2: zero-byte file exercises a different code path than a spec with missing sections)
7. Write Test 5: `python3 "$DISPATCHER" spec-gate "$FIXTURES/platform-overview.md"` → assert exit 0, stdout contains `"scope":"project"`

## Files to create/modify

- **Create**: `tests/sdl-workflow/test-gate-output-spec-python.sh`

## Test requirements

| Level | Behavior | Expected assertion |
|-------|----------|--------------------|
| Integration | valid spec produces pass JSON | exit 0, stdout has result:pass, scope:feature |
| Integration | missing sections exits 2 | exit 2, stderr has "Missing section" |
| Integration | injection warnings emitted | exit 0, WARNING count >= 3 |
| Integration | empty file exits with error | exit 2, stderr has descriptive error (UV-2) |
| Integration | overview spec recognized | exit 0, stdout has scope:project |

## Acceptance criteria

- AC-08: gate scripts produce identical JSON output and exit codes

## Model

Haiku

## Wave

2
