---
id: task-03
type: test
wave: 1
covers: [AC-01, AC-08]
files_to_create:
  - assets/fbk-scripts/tests/test_gates_review.py
completion_gate: "tests compile and fail before implementation"
---

## Objective

Create pytest unit tests for `fbk.gates.review` validation logic.

## Context

`review-gate.sh` validates: (1) perspective coverage — each perspective name appears in the review, (2) severity tags — at least one `blocking|important|informational` per perspective section and overall, (3) threat model determination section with a yes/no/skip decision and rationale >= 10 words, (4) testing strategy with three required categories (new tests, existing tests, test infrastructure).

## Instructions

1. Create `assets/fbk-scripts/tests/test_gates_review.py`
2. Import the validation function from `fbk.gates.review` (e.g., `validate_review`)
3. Write a test with a review missing a declared perspective — assert failure includes "Missing perspective"
4. Write a test with a review missing severity tags — assert failure includes "severity"
5. Write a test with a review missing `## Threat Model` section — assert failure includes "Threat Model"
6. Write a test with a threat model section containing only "yes" without rationale (< 10 words) — assert failure includes "rationale"
7. Write a test with a valid review containing all perspectives, severity tags, threat model with decision+rationale, and testing strategy — assert no failures and result is "pass"

## Files to create/modify

- **Create**: `assets/fbk-scripts/tests/test_gates_review.py`

## Test requirements

| Level | Behavior | Expected assertion |
|-------|----------|--------------------|
| Unit | missing perspective detected | failure list contains "Missing perspective" |
| Unit | missing severity tags detected | failure list contains "severity" |
| Unit | missing threat model section detected | failure list contains "Threat Model" |
| Unit | threat model without rationale detected | failure list contains "rationale" |
| Unit | valid review passes | result == "pass", failures empty |

## Acceptance criteria

- AC-01: validates review gate logic converted to Python
- AC-08: gate produces correct pass/fail for known inputs

## Model

Haiku

## Wave

1
