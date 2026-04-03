---
id: task-13
type: implementation
wave: 2
covers: [AC-49, AC-50, AC-51, AC-52, AC-53, AC-54]
files_to_modify:
  - assets/agents/fbk-test-reviewer.md
test_tasks: [task-07]
completion_gate: "task-07 tests pass"
---

## Objective

Adds 6 new test reviewer criteria to `fbk-test-reviewer.md`: 3 Tier 1 additions and 3 checkpoint additions.

## Context

The test reviewer agent has a Tier 1 section (lines 18-25) with 1 criterion (silent failure detection) and Tier 2 (lines 27-39) with 4 criteria. Six new items are added:

Tier 1 additions are non-overridable mechanical checks placed in the `### Tier 1 — Mechanical (non-overridable)` section after existing Criterion 1. They get sequential criterion numbers (2, 3, 4).

Checkpoint additions are applied at specific checkpoints. They integrate into the existing checkpoint structure. AC-52 and AC-53 go into Checkpoint 3 (test code review). AC-54 goes into Checkpoint 1 (spec review) as a structural consistency check.

The file's Tier 1 section ends with "Tier 1 has no override. Silent failure tests must be corrected." — new criteria are inserted before this closing statement.

## Instructions

1. In the `### Tier 1 — Mechanical (non-overridable)` section, after the existing Criterion 1 block (after the "- At CP3:" bullet and before the blank line preceding "Tier 1 has no override."), insert:

```

**Criterion 2: Stale failure annotations.** Flag any test marked as expected-to-fail (e.g., `xfail`, `expectedFailure`, `TODO: expected to fail`) that now passes. A stale failure annotation masks a test that should be actively enforcing its behavior.

- At CP3: flag test implementations with failure annotations where the test body passes when run.

**Criterion 3: Empty gate tests.** Flag any test that exists but contains zero assertion calls. An empty gate test occupies a test slot and appears in pass counts without verifying any behavior.

- At CP3: flag test implementations whose body contains no assertion calls (assert, expect, should, verify, or framework-equivalent).

**Criterion 4: Advisory assertions.** Flag any test that logs, prints, or writes a behavioral check result to output but does not assert on it. A non-failing output for a behavioral check provides no regression protection.

- At CP3: flag test implementations that compute a behavioral result and output it (console.log, print, fmt.Println, or equivalent) without a corresponding assertion on the same value.
```

2. Update the closing statement from "Tier 1 has no override. Silent failure tests must be corrected." to "Tier 1 has no override. Silent failure tests, stale failure annotations, empty gate tests, and advisory assertions must be corrected."

3. In the `## Checkpoint 3 — Test code review` section, after the line "Verify tests catch real regressions — they test observable behavior, not implementation artifacts.", add:

```

Check for unconditionally skipped tests with behavioral names. Flag tests that are `skip`ped or `xit`/`xdescribe`d unconditionally (no runtime condition) but have names suggesting behavioral verification (e.g., "validates input," "rejects expired tokens"). Unconditionally skipped behavioral tests provide zero coverage while appearing in the test inventory.

Check for phantom assertion strings. Flag test assertions that reference string values (error messages, status codes, format patterns) absent from the production code being tested. These assertions pass trivially because the production code never produces the matched string.
```

4. In the `## Checkpoint 1 — Spec review` section, after the line "Verify proposed tests validate behavior, not implementation details. Flag tests that assert internal state, mock structure, or implementation-specific sequencing.", add:

```

Check for build-tag consistency in infrastructure-dependent tests. When the spec's testing strategy includes tests requiring specific build tags, compilation flags, or environment constraints, verify those tags are consistent with the project's actual build configuration. Flag tests that specify build tags not present in the project's CI pipeline or build system.
```

## Files to create/modify

- `assets/agents/fbk-test-reviewer.md` (modify)

## Test requirements

Tests from task-07: Test 1 (stale failure annotation in Tier 1), Test 2 (empty gate test in Tier 1), Test 3 (advisory assertion in Tier 1), Test 4 (unconditionally skipped keyword), Test 5 (phantom assertion keyword), Test 6 (build-tag keyword).

## Acceptance criteria

- AC-49: Tier 1 contains stale failure annotation criterion.
- AC-50: Tier 1 contains empty gate test criterion.
- AC-51: Tier 1 contains advisory assertion criterion.
- AC-52: Checkpoint contains unconditionally skipped test check.
- AC-53: Checkpoint contains phantom assertion string check.
- AC-54: Checkpoint contains build-tag consistency check.

## Model

Haiku

## Wave

Wave 2
