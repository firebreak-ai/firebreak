Task files are Markdown with YAML frontmatter between `---` markers.

## Required frontmatter fields (all tasks)

- `id`: string. Task identifier (e.g., `task-01`).
- `type`: `test` or `implementation`.
- `wave`: integer. Execution wave number.
- `covers`: list of `AC-NN` strings. Acceptance criteria this task satisfies.
- `completion_gate`: string. What proves this task is done.

At least one of `files_to_create` (list of paths) or `files_to_modify` (list of paths) must be present and non-empty.

## Implementation task fields

Implementation tasks (`type: implementation`) additionally require:

- `test_tasks`: list of task ID strings referencing test tasks this implementation depends on.

## Markdown body sections

- Objective
- Context
- Instructions
- Files to create/modify
- Test requirements
- Acceptance criteria
- Model
- Wave

## Examples

### Test task

```markdown
---
id: task-01
type: test
wave: 1
covers: [AC-01]
files_to_create:
  - tests/feature/test-alpha.sh
completion_gate: "tests compile and fail before implementation"
---

## Objective

Write tests for the alpha feature.

## Instructions

1. Create test-alpha.sh with TAP format output.
2. Test that alpha processes input correctly.

## Files to create/modify

- `tests/feature/test-alpha.sh` (create)

## Test requirements

1. Unit: alpha accepts valid input
2. Unit: alpha rejects invalid input

## Acceptance criteria

AC-01: Alpha feature processes input and produces correct output.

## Model

Haiku

## Wave

1
```

### Implementation task

```markdown
---
id: task-02
type: implementation
wave: 1
covers: [AC-01]
files_to_create:
  - src/alpha.py
test_tasks: [task-01]
completion_gate: "task-01 tests pass"
---

## Objective

Implement the alpha feature.

## Instructions

1. Create src/alpha.py implementing the alpha processor.
2. Ensure all task-01 tests pass.

## Files to create/modify

- `src/alpha.py` (create)

## Test requirements

Tests from task-01 must pass.

## Acceptance criteria

AC-01: Alpha feature processes input and produces correct output.

## Model

Sonnet

## Wave

1
```
