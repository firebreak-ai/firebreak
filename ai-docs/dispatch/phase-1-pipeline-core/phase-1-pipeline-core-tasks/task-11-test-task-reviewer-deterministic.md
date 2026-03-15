## Objective

Write bash test scripts and fixture task files that validate the task reviewer's deterministic layer for frontmatter validation, cross-task consistency, and AC coverage.

## Context

The task reviewer's deterministic layer (`task-reviewer-gate.sh`) validates individual task files and cross-task consistency. It takes two arguments: `<spec-path>` and `<tasks-dir>`.

Task files are Markdown with YAML frontmatter (between `---` markers). Required frontmatter fields: `id`, `type` (test|implementation), `wave`, `covers` (list of AC identifiers), `completion_gate`. Either `files_to_create` or `files_to_modify` (or both) must be present and non-empty. Implementation tasks (type=implementation) must also have `test_tasks` (list of test task IDs they depend on).

Cross-task validation: every AC in the spec must be covered by at least one test task and one implementation task. No two tasks in the same wave may modify the same file. Implementation task `test_tasks` references must point to existing task IDs.

Exit conventions: 0 = pass (JSON to stdout), 2 = fail (errors to stderr listing each defect).

## Instructions

1. Create directory `tests/fixtures/tasks/` if it does not exist.

2. Create `tests/fixtures/tasks/valid-spec.md` — a minimal but complete feature spec with 3 ACs: AC-01, AC-02, AC-03. Include all required sections (Problem, Goals, User-facing behavior, Technical approach, Testing strategy, Documentation impact, Acceptance criteria, Dependencies). ~30 lines. This spec is used to verify AC coverage.

3. Create `tests/fixtures/tasks/valid/` directory containing a valid task set:
   - `task-01-test-feature-alpha.md` — type: test, wave: 1, covers: [AC-01], files_to_create: [tests/alpha-test.sh], completion_gate: "tests compile and fail"
   - `task-02-test-feature-beta.md` — type: test, wave: 1, covers: [AC-02, AC-03], files_to_create: [tests/beta-test.sh], completion_gate: "tests compile and fail"
   - `task-03-impl-feature-alpha.md` — type: implementation, wave: 1, covers: [AC-01], files_to_modify: [src/alpha.py], test_tasks: [task-01], completion_gate: "task-01 tests pass"
   - `task-04-impl-feature-beta.md` — type: implementation, wave: 2, covers: [AC-02, AC-03], files_to_create: [src/beta.py], test_tasks: [task-02], completion_gate: "task-02 tests pass"
   Each file must have YAML frontmatter between `---` markers and a markdown body with Objective, Instructions, etc. Make the body brief (5-10 lines) but present.

4. Create `tests/fixtures/tasks/missing-fields/task-bad.md` — a task file missing `completion_gate` and `covers` fields. All other fields present.

5. Create `tests/fixtures/tasks/impl-no-test-tasks/task-bad-impl.md` — type: implementation, has all required fields except `test_tasks`.

6. Create fixture for file overlap test: `tests/fixtures/tasks/overlap/` directory with two tasks in the same wave that both list `src/shared.py` in `files_to_modify`.

7. Create fixture for uncovered AC test: `tests/fixtures/tasks/uncovered-ac/` directory with tasks that cover AC-01 and AC-02 but not AC-03 (using the valid-spec.md that has AC-01, AC-02, AC-03).

8. Create fixture for invalid test_tasks reference: `tests/fixtures/tasks/bad-test-ref/` directory with an implementation task whose `test_tasks` lists `task-99` which does not exist in the task set.

9. Create fixture for missing file lists: `tests/fixtures/tasks/no-files/task-no-files.md` — a task file with all required fields (`id`, `type`, `wave`, `covers`, `completion_gate`) but neither `files_to_create` nor `files_to_modify` present. This tests the requirement that at least one must be present and non-empty.

10. Create fixture for files_to_modify with non-existent path: `tests/fixtures/tasks/bad-path/task-bad-path.md` — type: implementation, `files_to_modify: [src/nonexistent-file-that-does-not-exist.py]`, all other fields valid.

11. Create `tests/sdl-workflow/test-task-reviewer.sh` as a bash test script. Use `set -uo pipefail`. TAP format. Define `GATE` pointing to `home/.claude/hooks/sdl-workflow/task-reviewer-gate.sh` relative to project root. Define `FIXTURES` pointing to `tests/fixtures/tasks/`.

12. Write test: valid task set passes. Run `$GATE "$FIXTURES/valid-spec.md" "$FIXTURES/valid/"`. Assert exit 0. Assert stdout contains `"result":"pass"`.

13. Write test: missing required fields rejected. Run `$GATE "$FIXTURES/valid-spec.md" "$FIXTURES/missing-fields/"` (place task-bad.md in that dir alongside enough valid tasks to make it runnable). Assert exit 2. Assert stderr mentions "missing" and references the absent field names.

14. Write test: implementation task without test_tasks rejected. Run `$GATE "$FIXTURES/valid-spec.md" "$FIXTURES/impl-no-test-tasks/"` (include valid test tasks so AC coverage isn't the failure). Assert exit 2. Assert stderr mentions "test_tasks".

15. Write test: overlapping file boundaries rejected. Run `$GATE "$FIXTURES/valid-spec.md" "$FIXTURES/overlap/"`. Assert exit 2. Assert stderr mentions the conflicting file path.

16. Write test: uncovered AC rejected. Run `$GATE "$FIXTURES/valid-spec.md" "$FIXTURES/uncovered-ac/"`. Assert exit 2. Assert stderr mentions `AC-03`.

17. Write test: invalid test_tasks reference rejected. Run `$GATE "$FIXTURES/valid-spec.md" "$FIXTURES/bad-test-ref/"`. Assert exit 2. Assert stderr mentions `task-99` or "invalid" test task reference.

18. Write test: missing file lists rejected. Run `$GATE "$FIXTURES/valid-spec.md" "$FIXTURES/no-files/"` (place task-no-files.md in that dir alongside enough valid tasks to make it runnable). Assert exit 2. Assert stderr mentions "files_to_create" or "files_to_modify".

19. Write test: files_to_modify with non-existent path rejected. Run `$GATE "$FIXTURES/valid-spec.md" "$FIXTURES/bad-path/"` (ensure the task set is otherwise valid). Assert exit 2. Assert stderr mentions the non-existent file path.

20. Write test: valid task set with all ACs covered passes. Rerun with the valid/ fixture set and verify every AC in the spec appears in the pass output or that exit is 0 with no AC warnings.

21. End the script with summary and exit code.

## Files to create/modify

- `tests/sdl-workflow/test-task-reviewer.sh` (create)
- `tests/fixtures/tasks/valid-spec.md` (create)
- `tests/fixtures/tasks/valid/task-01-test-feature-alpha.md` (create)
- `tests/fixtures/tasks/valid/task-02-test-feature-beta.md` (create)
- `tests/fixtures/tasks/valid/task-03-impl-feature-alpha.md` (create)
- `tests/fixtures/tasks/valid/task-04-impl-feature-beta.md` (create)
- `tests/fixtures/tasks/missing-fields/task-bad.md` (create)
- `tests/fixtures/tasks/impl-no-test-tasks/task-bad-impl.md` (create)
- `tests/fixtures/tasks/overlap/task-01-test-overlap.md` (create)
- `tests/fixtures/tasks/overlap/task-02-impl-overlap-a.md` (create)
- `tests/fixtures/tasks/overlap/task-03-impl-overlap-b.md` (create)
- `tests/fixtures/tasks/uncovered-ac/task-01-test-partial.md` (create)
- `tests/fixtures/tasks/uncovered-ac/task-02-impl-partial.md` (create)
- `tests/fixtures/tasks/bad-test-ref/task-01-test-ref.md` (create)
- `tests/fixtures/tasks/bad-test-ref/task-02-impl-bad-ref.md` (create)
- `tests/fixtures/tasks/no-files/task-no-files.md` (create)
- `tests/fixtures/tasks/bad-path/task-bad-path.md` (create)

Justification for multiple files: the task reviewer validates cross-task consistency, requiring multiple fixture task sets (valid set, missing fields, no file lists, overlapping scopes, uncovered ACs, bad references, bad paths) to test each defect category in isolation.

## Test requirements

This is a test task. Tests to write (all in `test-task-reviewer.sh`):
1. Unit: valid task set passes with exit 0
2. Unit: task missing required frontmatter fields rejected with exit 2
3. Unit: implementation task missing test_tasks rejected with exit 2
4. Unit: overlapping file boundaries in same wave rejected with exit 2
5. Unit: uncovered spec AC rejected with exit 2, naming the missing AC
6. Unit: invalid test_tasks reference rejected with exit 2
7. Unit: task with neither files_to_create nor files_to_modify rejected with exit 2
8. Unit: files_to_modify referencing non-existent path rejected with exit 2
9. Integration: valid task set with full AC coverage passes without false rejections

## Acceptance criteria

AC-08: Task reviewer runs two layers (deterministic checks, test task quality). Deterministic layer rejects tasks with structural defects.

## Model

Opus

## Wave

2
