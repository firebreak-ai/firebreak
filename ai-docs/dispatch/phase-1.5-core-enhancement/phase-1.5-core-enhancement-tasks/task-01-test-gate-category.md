---
id: T-01
type: test
wave: 1
covers: ["AC-08"]
files_to_create: ["../../tests/fixtures/tasks/corrective/task-01-test-fix.md", "../../tests/fixtures/tasks/corrective/task-02-impl-fix.md", "../../tests/fixtures/tasks/corrective/task.json", "../../tests/fixtures/tasks/corrective-spec.md", "../../tests/fixtures/tasks/testing-infra/task-01-test-infra.md", "../../tests/fixtures/tasks/testing-infra/task.json", "../../tests/fixtures/tasks/testing-infra/testing-infra-spec.md"]
completion_gate: "New test cases added to test-task-reviewer.sh; tests run and fail (category support not yet implemented)"
---

## Objective

Creates test fixtures and test cases for the `category` field in the task reviewer gate, covering corrective and testing-infrastructure categories.

## Context

The task reviewer gate (`home/dot-claude/hooks/sdl-workflow/task-reviewer-gate.sh`) currently enforces that every AC must be covered by both a test task and an implementation task. Phase 1.5 adds a `category` field to the top level of `task.json` that relaxes this invariant for corrective and testing-infrastructure features. The gate currently does not read `task.json` at all — it parses YAML frontmatter from individual task .md files. The implementation task (T-08) will update the gate to also read `task.json` for the `category` field.

## Instructions

1. Create fixture directory `tests/fixtures/tasks/corrective/` with:
   - `corrective-spec.md`: A minimal spec with AC-01 and AC-02 defined.
   - `task-01-test-fix.md`: A test task with frontmatter `covers: ["AC-01", "AC-02"]` — covering both ACs without a paired implementation task.
   - `task-02-impl-fix.md`: An implementation task with frontmatter `covers: ["AC-01"]`, `test_tasks: ["T-01"]` — covering only AC-01 (AC-02 is test-only, valid in corrective).
   - `task.json`: Manifest with `"category": "corrective"` at the top level, referencing both tasks.

2. Create fixture directory `tests/fixtures/tasks/testing-infra/` with:
   - `testing-infra-spec.md`: A minimal spec with AC-01 defined.
   - `task-01-test-infra.md`: A test task with frontmatter `covers: ["AC-01"]` — no implementation task (tests are the product).
   - `task.json`: Manifest with `"category": "testing-infrastructure"` at the top level.

3. Add these test cases to `tests/sdl-workflow/test-task-reviewer.sh`:
   - **Case: corrective category passes with test-only AC coverage** — run gate against `corrective/` fixtures, expect pass.
   - **Case: corrective category rejects AC covered by neither** — modify fixture inline to remove AC-02 from task-01's covers, expect fail.
   - **Case: testing-infrastructure passes with test-only ACs** — run gate against `testing-infra/` fixtures, expect pass.
   - **Case: feature category (default) rejects test-only AC** — run gate against `testing-infra/` fixtures but with `"category": "feature"` in task.json, expect fail.
   - **Case: absent category defaults to feature behavior** — run gate against `testing-infra/` fixtures with category field removed from task.json, expect fail.
   - **Case: unrecognized category rejected** — run gate against `corrective/` fixtures but with `"category": "experimental"` in task.json, expect fail with error message listing valid categories.

## Files to create/modify

Create:
- `tests/fixtures/tasks/corrective/corrective-spec.md`
- `tests/fixtures/tasks/corrective/task-01-test-fix.md`
- `tests/fixtures/tasks/corrective/task-02-impl-fix.md`
- `tests/fixtures/tasks/corrective/task.json`
- `tests/fixtures/tasks/testing-infra/testing-infra-spec.md`
- `tests/fixtures/tasks/testing-infra/task-01-test-infra.md`
- `tests/fixtures/tasks/testing-infra/task.json`

Modify:
- `tests/sdl-workflow/test-task-reviewer.sh`

## Test requirements

6 new test cases as described above. Tests should follow the existing pattern in `test-task-reviewer.sh` (bash functions calling the gate script with fixture directories and asserting exit codes).

## Acceptance criteria

AC-08: Tests verify category-based invariant relaxation. Tests should fail at this point because the gate does not yet support the category field.

## Model

Sonnet

## Wave

Wave 1
