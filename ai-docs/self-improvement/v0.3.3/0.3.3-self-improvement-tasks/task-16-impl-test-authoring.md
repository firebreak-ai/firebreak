---
id: task-16
type: implementation
wave: 2
covers: [AC-07, AC-08]
files_to_modify:
  - assets/fbk-docs/fbk-design-guidelines/test-authoring.md
test_tasks: [task-08]
completion_gate: "task-08 tests 6-7 pass"
---

## Objective

Adds 2 test authoring rules to `test-authoring.md`: assertion specificity and test name accuracy.

## Context

The test authoring guide covers production-path exercise, re-implementation detection, self-assignment assertions, non-importable behaviors, e2e tests, and test isolation. Two new rules address observed test quality gaps.

- AC-07: Assertions that check only truthiness or type (e.g., `expect(result).toBeTruthy()`, `assert result is not None`) provide weak regression protection. The new rule requires assertions to check specific values.

- AC-08: Test names describing implementation mechanisms rather than behavior (e.g., "calls the database query function" instead of "returns user by email") mislead reviewers and mask missing coverage. The new rule requires test names to describe the behavior being verified.

The file currently uses `##` headings for each guideline section. New sections follow the same format.

## Instructions

1. After the last section (`## Test isolation` and its content), append:

```
## Assertion specificity

Assert on specific expected values, not truthiness or type alone. `expect(result).toBe(42)` catches regressions that `expect(result).toBeTruthy()` misses — any non-zero value would pass the truthiness check. When the expected value is not a fixed literal (e.g., it depends on input), assert on a derived property that is specific enough to catch behavioral changes: length, key presence, substring, or structural shape.

Weak assertion: `assert result is not None`
Specific assertion: `assert result.status_code == 200 and result.body["user_id"] == expected_id`

## Test name accuracy

Name tests after the behavior they verify, not the implementation mechanism they exercise. A test named "calls the database query function" describes an implementation detail; "returns user by email" describes the behavior. When the implementation changes but the behavior remains the same, implementation-named tests appear broken even though the behavior is intact.

When reviewing test names, check that the name would remain accurate if the implementation were rewritten to produce the same behavior through a different mechanism.
```

## Files to create/modify

- `assets/fbk-docs/fbk-design-guidelines/test-authoring.md` (modify)

## Test requirements

Tests from task-08: Test 6 (assertion specificity keyword), Test 7 (test name accuracy keyword).

## Acceptance criteria

- AC-07: Test authoring contains assertion specificity rule.
- AC-08: Test authoring contains test name accuracy rule.

## Model

Haiku

## Wave

Wave 2
