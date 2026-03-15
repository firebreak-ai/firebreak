## Objective

Implement the task reviewer's deterministic layer as a gate script that validates task file structure, cross-task consistency, and AC coverage.

## Context

The task reviewer gate validates structured task files (Markdown with YAML frontmatter) individually and as a set. It takes a spec path and a tasks directory, parses YAML frontmatter from each task file, and runs per-task and cross-task checks.

Task frontmatter fields: `id`, `type` (test|implementation), `wave` (integer), `covers` (list of AC-NN strings), `files_to_create` and/or `files_to_modify` (lists of paths), `completion_gate` (string). Implementation tasks additionally require `test_tasks` (list of task IDs).

The gate follows the existing pattern: bash argument handling + embedded Python3 for YAML/JSON parsing and cross-referencing. See `breakdown-gate.sh` for the heredoc pattern.

Exit conventions: 0 = pass (JSON to stdout), 2 = fail (errors to stderr listing each defect).

## Instructions

1. Create `home/.claude/hooks/sdl-workflow/task-reviewer-gate.sh`. Start with `#!/usr/bin/env bash` and `set -euo pipefail`.

2. Parse arguments: `SPEC="${1:-}"` and `TASKS_DIR="${2:-}"`. Validate both: spec file must exist, tasks dir must be a directory. Print usage and exit 2 if invalid. Require `python3` is available.

3. Build a task file content map as JSON (following the breakdown-gate.sh pattern): iterate over `"$TASKS_DIR"/task-*.md`, read each file's content, encode as JSON string via Python one-liner, and assemble into a JSON object `{"filename": "content", ...}`.

4. Delegate all validation to embedded Python3 via heredoc. Pass `$SPEC`, `$TASKS_DIR`, and the task JSON map as arguments.

5. In the Python block, implement YAML frontmatter parsing: for each task file, extract content between the first `---` and second `---`. Parse as YAML using PyYAML (`import yaml`). PyYAML is an accepted project dependency. Store parsed frontmatter per task.

6. **Per-task validation** — for each task file, check:
   a. Required fields present: `id`, `type`, `wave`, `covers`, `completion_gate`. Add failure message per missing field with task filename.
   b. `files_to_create` or `files_to_modify` (or both) must be present and non-empty. Add failure if neither is present or both are empty.
   c. `type` must be `test` or `implementation`. Add failure if other value.
   d. `covers` must be a non-empty list. Each entry must match `AC-\d+`. Add failure per invalid entry.
   e. If `type` is `implementation`: `test_tasks` must be present and non-empty. Add failure if missing.
   f. For each path in `files_to_modify`: check that the file exists relative to the project root. Derive the project root from the tasks_dir parent (i.e., `os.path.dirname(os.path.dirname(tasks_dir))`). Add failure per non-existent path, with the specific path named.

7. **Cross-task validation** — after all per-task checks:
   a. Extract all AC identifiers from the spec file (regex `AC-\d+` in the Acceptance criteria section).
   b. Collect all `covers` values from all tasks, grouped by task type (test vs implementation).
   c. For each spec AC: verify at least one test task covers it AND at least one implementation task covers it. Add failure per uncovered AC, specifying whether test coverage or implementation coverage is missing.
   d. Check file scope conflicts: group tasks by wave. Within each wave, collect all `files_to_create` and `files_to_modify` paths. If any path appears in more than one task, add failure naming both tasks and the conflicting path.
   e. Validate `test_tasks` references: for each implementation task, verify every ID in its `test_tasks` list matches an `id` field from an existing task file. Add failure per unresolvable reference.

8. If any failures: print each to stderr, one per line. Exit 2.

9. If no failures: print JSON to stdout: `{"gate":"task-reviewer","result":"pass","tasks":<count>,"acs_covered":<count>,"waves":<max-wave>}`. Exit 0.

10. After producing the final JSON result (pass or fail), log the result to the audit log. Accept the spec name from the spec path argument (extract filename, strip extension). Call `audit-logger.py log <spec-name> gate_result '<json>'` where `<json>` is the same JSON emitted to stdout (on pass) or a `{"gate":"task-reviewer","result":"fail","errors":[...]}` summary (on fail). Locate `audit-logger.py` relative to the script at `home/.claude/hooks/sdl-workflow/audit-logger.py`. If the logger is not available (file not found), skip logging silently — do not fail the gate.

11. Make the script executable (add chmod comment at top).

## Files to create/modify

- `home/.claude/hooks/sdl-workflow/task-reviewer-gate.sh` (create)

## Test requirements

Tests from task-11 (`tests/sdl-workflow/test-task-reviewer.sh`) must pass:
- Valid task set passes with exit 0
- Missing required fields rejected with exit 2
- Implementation task missing test_tasks rejected with exit 2
- Overlapping file boundaries rejected with exit 2
- Uncovered spec AC rejected with exit 2
- Invalid test_tasks reference rejected with exit 2
- Non-existent files_to_modify path rejected with exit 2
- Valid full-coverage task set passes without false rejections

## Acceptance criteria

AC-08: Task reviewer runs two layers (deterministic checks, test task quality). Deterministic layer rejects tasks with structural defects. Failing review returns to breakdown with specific feedback.

Primary AC: tests from task-11 pass.

## Model

Sonnet

## Wave

2
