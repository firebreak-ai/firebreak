---
id: task-15
type: implementation
wave: 2
covers: [AC-05, AC-06]
files_to_modify:
  - assets/fbk-docs/fbk-sdl-workflow/task-compilation.md
test_tasks: [task-08]
completion_gate: "task-08 tests 4-5 pass"
---

## Objective

Adds 2 compilation rules to `task-compilation.md`: E2E harness exception and per-site completion conditions.

## Context

The task compilation guide governs how specs are broken into task files. Two additions address observed friction:

- AC-05: The "Test/Implementation Task Separation" section (lines 157-167) mandates separate test and implementation tasks for every change. E2E test harnesses are an exception — the harness setup and the tests that use it are tightly coupled and separating them creates artificial boundaries. The new rule allows combining test+impl into a single task when the task creates an E2E test harness.

- AC-06: The "Instructions" format (section 3 in the task file structure) requires numbered steps but does not address tasks that modify multiple sites in the same file or across files. The new rule requires per-site completion conditions — tasks with multiple mutation sites must have numbered steps with per-site completion conditions so the agent can verify progress incrementally.

## Instructions

1. In the `## Test/Implementation Task Separation` section, after the paragraph ending "...a test task must complete before its paired implementation task begins.", add:

```
**E2E harness exception**: When a task creates an E2E test harness (test infrastructure setup + the tests that exercise it), combine the harness setup and its tests into a single task. Separating harness creation from harness-dependent tests creates an artificial boundary — the harness has no value without its tests, and the tests cannot compile without the harness. This exception applies only to E2E harness creation, not to standard unit or integration test tasks.
```

2. In the `## Task File Structure` section, in the description of section **3. Instructions**, after the paragraph ending "...If a step requires judgment ('design the interface'), the task is underspecified — resolve in the spec before completing compilation.", add:

```
**Per-site completion conditions**: When a task modifies multiple mutation sites (multiple locations in one file, or locations across two files), each site must have its own numbered step with a concrete completion condition. The agent verifies each site independently rather than treating the task as a single atomic change. Example: "Step 1: In `auth.go` line 45, replace X with Y. Completion: `grep -q 'Y' auth.go` succeeds. Step 2: In `auth_test.go` line 12, update the assertion. Completion: test compiles."
```

## Files to create/modify

- `assets/fbk-docs/fbk-sdl-workflow/task-compilation.md` (modify)

## Test requirements

Tests from task-08: Test 4 (E2E harness exception keyword), Test 5 (per-site completion conditions keyword).

## Acceptance criteria

- AC-05: Task compilation contains E2E harness exception rule.
- AC-06: Task compilation contains per-site completion conditions rule.

## Model

Haiku

## Wave

Wave 2
