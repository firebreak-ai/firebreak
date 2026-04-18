---
id: task-22
type: test
wave: 2
covers: [AC-08]
files_to_create:
  - tests/sdl-workflow/test-e2e-spec-gate-parity.sh
  - tests/fixtures/specs/golden-spec-gate-valid.json
  - tests/fixtures/specs/golden-spec-gate-missing.txt
  - tests/fixtures/specs/golden-spec-gate-injection.txt
completion_gate: "tests compile and fail before implementation"
---

## Objective

Capture golden reference output from the bash spec-gate and create an e2e parity test comparing Python output against those fixtures.

## Context

The bash originals are deleted by task-71 later in Wave 2. To enable repeatable parity testing, this task first captures the bash spec-gate's output as golden fixtures, then writes tests that compare the Python dispatcher's output against those fixtures. This decouples the tests from the bash scripts' existence.

## Instructions

1. Run `bash assets/hooks/fbk-sdl-workflow/spec-gate.sh tests/fixtures/specs/valid-spec.md` and capture stdout to `tests/fixtures/specs/golden-spec-gate-valid.json` and exit code
2. Run `bash assets/hooks/fbk-sdl-workflow/spec-gate.sh tests/fixtures/specs/missing-sections-spec.md` and capture stderr to `tests/fixtures/specs/golden-spec-gate-missing.txt` and exit code
3. Run `bash assets/hooks/fbk-sdl-workflow/spec-gate.sh tests/fixtures/specs/injection-attempt-spec.md` and capture stderr WARNING lines to `tests/fixtures/specs/golden-spec-gate-injection.txt` and exit code
4. Create `tests/sdl-workflow/test-e2e-spec-gate-parity.sh`
5. Set `DISPATCHER="$PROJECT_ROOT/assets/fbk-scripts/fbk.py"` and `GOLDEN="$PROJECT_ROOT/tests/fixtures/specs"`
6. Write Test 1 (valid spec): run `python3 "$DISPATCHER" spec-gate "$GOLDEN/../valid-spec.md"`, assert exit 0, assert stdout JSON contains same `"result"` value as `golden-spec-gate-valid.json`
7. Write Test 2 (missing sections): run on `missing-sections-spec.md`, assert exit 2, assert stderr contains "Missing section" (same key phrases as golden file)
8. Write Test 3 (injection markers): run on `injection-attempt-spec.md`, assert exit 0, assert stderr WARNING count matches golden file count

## Files to create/modify

- **Create**: `tests/fixtures/specs/golden-spec-gate-valid.json`
- **Create**: `tests/fixtures/specs/golden-spec-gate-missing.txt`
- **Create**: `tests/fixtures/specs/golden-spec-gate-injection.txt`
- **Create**: `tests/sdl-workflow/test-e2e-spec-gate-parity.sh`

## Test requirements

| Level | Behavior | Expected assertion |
|-------|----------|--------------------|
| E2e | valid spec: same result as golden | exit 0, result:pass matches golden |
| E2e | missing sections: same error as golden | exit 2, "Missing section" present |
| E2e | injection markers: same warning count as golden | exit 0, WARNING count matches |

## Acceptance criteria

- AC-08: behavioral parity between Python and bash versions verified against golden reference

## Model

Sonnet

## Wave

2
