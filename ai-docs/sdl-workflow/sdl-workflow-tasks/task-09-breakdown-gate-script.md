# Task 09: Create Breakdown Gate Validation Script

## Objective

Create a script that validates Stage 3 structural prerequisites: DAG integrity, wave ordering, AC coverage, and file scope conflicts.

## Context

The `/breakdown` skill calls this script during the transition check. This is the most complex gate — it validates the task DAG, coverage map, and wave assignments from `task-overview.md` and the individual task files.

### What to validate

**1. AC coverage completeness**: Every spec acceptance criterion ID (AC-01, AC-02, ...) must appear in the coverage map with both a test task and an implementation task.

To check: parse the spec file for AC-NN patterns in the acceptance criteria section. Parse `task-overview.md` for the coverage map. Verify every AC from the spec appears in the map with entries in both the test and impl columns.

**2. No circular dependencies**: The task DAG must be acyclic. Parse dependency declarations from the task overview and perform a topological sort. If the sort fails (cycle detected), report the cycle.

**3. Wave ordering respects dependencies**: For every dependency edge (Task A blocks Task B), Task A's wave number must be less than Task B's wave number. Parse wave assignments from the task overview.

**4. Test tasks before impl tasks within waves**: Within each wave, test tasks must be ordered before their corresponding implementation tasks. Identify test vs. impl tasks by task type labels in the task overview or by naming convention (task files may indicate type).

**5. No file scope conflicts within same wave**: Tasks in the same wave must not declare overlapping files in their "Files to create/modify" sections. Parse each task file's file list and compare within each wave.

**6. File count constraint**: No task should declare more than 2 files to modify unless it includes a documented justification. Parse each task file's file list and, for those exceeding 2, check for justification text.

**7. Every code-modifying task has a test task**: Cross-reference task types. Every task that creates or modifies code files (not documentation or configuration) must have a corresponding test task in the coverage map.

### Input/output contract

- **Arguments**:
  - `$1`: Path to the spec file (for extracting AC IDs)
  - `$2`: Path to the tasks directory (containing `task-overview.md` and individual task files)
- **Exit 0**: All checks pass. Stdout: JSON summary with check details.
- **Exit 2**: Failures found. Stderr: all failures with specifics (which ACs missing, which cycle, which conflicts).

### Script location

`home/.claude/hooks/sdl-workflow/breakdown-gate.sh`

### Language consideration

The DAG validation (topological sort, cycle detection) is significantly easier in Python than bash. If Python 3 is available (check with `command -v python3`), use Python for the validation logic. Fall back to bash-only if Python is unavailable. Structure: a bash wrapper that checks for Python, then delegates to an inline Python script or a companion `.py` file.

Preferred approach: single bash script that embeds a Python heredoc for the complex validation, with the bash wrapper handling argument parsing and output formatting.

## Instructions

1. Create `home/.claude/hooks/sdl-workflow/breakdown-gate.sh`.
2. Structure the script:

   a. **Argument parsing**: Validate spec path and tasks directory exist.
   b. **AC extraction**: Parse the spec's acceptance criteria section for AC-NN patterns. Collect the set of required AC IDs.
   c. **Task overview parsing**: Parse `task-overview.md` for:
      - Coverage map: a markdown table with columns `| AC | Primary Task | Supporting Tasks |`
      - Dependencies: lines under a `Dependencies:` label matching `- T-NN (description) ← T-NN, T-NN`
      - Wave assignments: markdown tables under `### Wave N` headings with a `Task` column containing `T-NN` identifiers
      These formats are specified in the task compilation guide and must be matched exactly.
   d. **Task file parsing**: For each task file in the directory, parse:
      - Files to create/modify list
      - Task type (test vs. impl — look for "test" in the task name or a type field)
      - Wave assignment (should match task overview)
   e. **Validation checks** (all 7, in order):
      - AC coverage: every extracted AC has a coverage map entry with test + impl
      - DAG acyclicity: topological sort on dependency edges
      - Wave ordering: for each dependency edge, source wave < target wave
      - Test-before-impl: within each wave, test tasks ordered first
      - File scope: no overlapping files in same-wave tasks
      - File count: tasks with >2 files have justification
      - Test coverage: every code-modifying task has a test task
   f. **Output**: Report ALL failures, then exit 2 if any. Otherwise exit 0 with summary JSON.

3. Use Python 3 (via heredoc) for the DAG/graph operations. Use bash for file parsing where simpler.
4. Target: under 200 lines total (bash + embedded Python).

## Files to Create/Modify

- **Create**: `home/.claude/hooks/sdl-workflow/breakdown-gate.sh`

## Acceptance Criteria

- AC-13: Validates all Stage 3 structural prerequisites including DAG validation and AC coverage
- AC-15: Script is focused, clear error reporting, deterministic

## Model

Sonnet

## Wave

1
