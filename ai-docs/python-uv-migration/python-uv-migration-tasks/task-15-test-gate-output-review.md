---
id: task-15
type: test
wave: 2
covers: [AC-08]
files_to_create:
  - tests/sdl-workflow/test-gate-output-review-python.sh
completion_gate: "tests compile and fail before implementation"
---

## Objective

Create bash integration tests verifying `python3 fbk.py review-gate` produces correct pass/fail output.

## Context

The spec requires testing that `python3 fbk.py review-gate <valid-fixture> <perspectives>` produces correct pass/fail JSON. Use fixtures from `tests/fixtures/reviews/` if they exist, or create minimal fixtures inline in the test. Follow the bash test conventions from `tests/sdl-workflow/test-spec-validator.sh`.

## Instructions

1. Create `tests/sdl-workflow/test-gate-output-review-python.sh`
2. Set `DISPATCHER="$PROJECT_ROOT/assets/fbk-scripts/fbk.py"`
3. Create a valid review fixture inline (using heredoc to tmpfile) containing: perspectives (Security, Architecture), severity tags, threat model section with decision+rationale, testing strategy with all three categories
4. Write Test 1: `python3 "$DISPATCHER" review-gate "$REVIEW_FIXTURE" "Security,Architecture"` → assert exit 0, stdout contains `"result": "pass"`
5. Write Test 2: create an invalid review fixture missing perspectives → assert exit 2, stderr contains "Missing perspective"
6. Write Test 3: test with missing arguments → assert exit 2

## Files to create/modify

- **Create**: `tests/sdl-workflow/test-gate-output-review-python.sh`

## Test requirements

| Level | Behavior | Expected assertion |
|-------|----------|--------------------|
| Integration | valid review with all perspectives passes | exit 0, result is pass |
| Integration | review missing perspective fails | exit 2, stderr has "Missing perspective" |
| Integration | missing arguments exits 2 | exit 2 |

## Acceptance criteria

- AC-08: review gate produces correct pass/fail for known inputs

## Model

Haiku

## Wave

2
