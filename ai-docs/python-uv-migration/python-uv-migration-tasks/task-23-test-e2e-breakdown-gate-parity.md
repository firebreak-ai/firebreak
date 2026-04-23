---
id: task-23
type: test
wave: 2
covers: [AC-08]
files_to_create:
  - tests/sdl-workflow/test-e2e-breakdown-gate-parity.sh
  - tests/fixtures/tasks/golden-breakdown-gate-valid.json
completion_gate: "tests compile and fail before implementation"
---

## Objective

Capture golden reference output from the bash breakdown-gate and create an e2e parity test comparing Python output against that fixture.

## Context

The bash originals are deleted by task-71 later in Wave 2. This task first captures the bash breakdown-gate's output as a golden fixture, then writes tests that compare the Python dispatcher's output against it.

## Instructions

1. Run `bash assets/hooks/fbk-sdl-workflow/breakdown-gate.sh tests/fixtures/tasks/valid-spec.md tests/fixtures/tasks/valid/` and capture stdout JSON to `tests/fixtures/tasks/golden-breakdown-gate-valid.json` and exit code
2. Create `tests/sdl-workflow/test-e2e-breakdown-gate-parity.sh`
3. Set `DISPATCHER="$PROJECT_ROOT/assets/fbk-scripts/fbk.py"` and `GOLDEN="$PROJECT_ROOT/tests/fixtures/tasks"`
4. Write Test 1 (valid breakdown): run `python3 "$DISPATCHER" breakdown-gate "$GOLDEN/valid-spec.md" "$GOLDEN/valid/"`, assert exit 0, assert stdout JSON contains same `"result"` value as golden fixture
5. Write Test 2 (invalid breakdown): if an invalid fixture exists, run the dispatcher and assert exit 2

## Files to create/modify

- **Create**: `tests/fixtures/tasks/golden-breakdown-gate-valid.json`
- **Create**: `tests/sdl-workflow/test-e2e-breakdown-gate-parity.sh`

## Test requirements

| Level | Behavior | Expected assertion |
|-------|----------|--------------------|
| E2e | valid breakdown: same result as golden | exit 0, result key matches golden |
| E2e | invalid breakdown: exits with error | exit 2 |

## Acceptance criteria

- AC-08: behavioral parity between Python and bash versions verified against golden reference

## Model

Sonnet

## Wave

2
