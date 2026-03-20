---
id: T-08
type: implementation
wave: 2
covers: ["AC-08"]
files_to_modify: ["../../home/dot-claude/hooks/sdl-workflow/task-reviewer-gate.sh"]
test_tasks: ["T-01"]
completion_gate: "All tests in test-task-reviewer.sh pass, including the 6 new category test cases"
---

## Objective

Updates the task reviewer gate script to read the `category` field from `task.json` and apply relaxed invariants for corrective and testing-infrastructure features.

## Context

The gate script at `home/dot-claude/hooks/sdl-workflow/task-reviewer-gate.sh` currently parses YAML frontmatter from individual task .md files. It enforces that every AC must be covered by both a test task and an implementation task. It does NOT currently read `task.json`. The `task.json` manifest lives in the same task directory the gate receives as input.

The change: the gate also reads `task.json` from the task directory to extract the `category` field. Based on category, the AC-coverage invariant is relaxed.

The gate script contains a Python block (approximately lines 26-187) that performs all validation. The category logic should be added to this Python block.

## Instructions

1. In the Python validation block, after reading and parsing the task markdown files, add: read `task.json` from the task directory (the second argument to the script). Extract the `category` field. Default to `"feature"` if `task.json` doesn't exist or `category` is absent.

2. Modify the AC coverage validation. Currently (approximately line 141-146), it checks that every AC appears in `covers` across at least one test task AND one implementation task. Change this to:
   - If `category == "feature"`: current behavior (both test and impl required per AC)
   - If `category == "corrective"`: test tasks can cover ACs without a paired implementation task. Implementation tasks still need `test_tasks` references.
   - If `category == "testing-infrastructure"`: test tasks can cover ACs directly without implementation tasks.

3. Preserve all other existing validations (required fields, file existence, dependency DAG, wave ordering, file scope conflicts, test_tasks references).

4. If `category` is an unrecognized value, reject with an error message listing valid categories.

## Files to create/modify

Modify:
- `home/dot-claude/hooks/sdl-workflow/task-reviewer-gate.sh`

## Test requirements

The 5 test cases from T-01 must pass after this change. Run `tests/sdl-workflow/test-task-reviewer.sh` and verify all existing + new tests pass.

## Acceptance criteria

AC-08: Gate accepts corrective and testing-infrastructure categories with relaxed invariants. Default feature behavior unchanged. Existing tests unbroken.

## Model

Sonnet

## Wave

Wave 2
