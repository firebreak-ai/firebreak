---
id: task-32
type: implementation
wave: 4
covers: [AC-04, AC-11]
files_to_modify:
  - assets/fbk-scripts/fbk/hooks/task_completed.py
test_tasks: [task-15]
completion_gate: "task-15 tests pass"
dependencies: [task-27]
---

# 1 Objective

Extend the verification hook so that, before its existing exit, it writes a fail-silent `VERIFICATION_RESULT` event carrying the failing-test count, the lint-error count, and the list of files touched outside the task's declared scope — leaving the hook's exit codes (2 on failure, 0 on pass) unchanged.

# 2 Context

`fbk/hooks/task_completed.py` runs as `fbk.py task-completed`, fed a completion payload on stdin. Its `main()` already: reads `task_description`/`cwd`; locates the task file via the `ai-docs/.../tasks/task-*.md` regex; runs the detected test/lint commands; checks `git diff --name-only HEAD` against the task's declared files; prints warnings to stderr; and exits 2 if there are test/lint failures, else 0. Today the out-of-scope check only prints a warning — this feature also records it as structured data.

The new behavior is a side effect added BEFORE the existing exits: assemble the verification result (failing-test count, lint-error count, out-of-scope file list) and write it via the shared event writer (task-27). The write is fail-silent: an unwritable events path never changes the hook's exit code or output. Exit codes stay exactly as they are.

The events file goes under the hook's resolved project root — the hook already has `cwd` (from the payload, defaulting to `.`); write to `os.path.join(cwd, ".fbk-capture", "events.jsonl")`. The level is `gate_check.resolve_capture_level(cwd)`.

# 3 Instructions

1. In `fbk/hooks/task_completed.py`, add `from fbk.capture import event_writer, gate_check` (a function-level import inside `main()` is fine and keeps the import off paths that don't need it).
2. Track structured counts as the existing checks run, without changing their control flow:
   - Failing-test count: when the test command runs and returns non-zero, capture a failing count. A precise count requires parsing the runner output; a robust minimum is `1` when the test command exited non-zero and `0` when it passed (the test asserts `>= 1` on failure and exactly `0` on pass). Record the count alongside the existing failure-message append. Completion: a failing `make test` yields a failing-test count `>= 1`; a passing run yields `0`.
   - Lint-error count: similarly, `>= 1` when the lint command exited non-zero, `0` when it passed or was skipped. Completion: the event carries a lint-error count field.
   - Out-of-scope file list: reuse the existing `undeclared` list computed from `git diff --name-only HEAD` minus the task's declared files. Capture it as the structured out-of-scope list (present-and-empty when all touched files are declared). Completion: a touched-but-undeclared file appears in the list; an all-declared run yields an empty (present) list.
3. Before EACH existing exit (`sys.exit(2)` on failures and `sys.exit(0)` on pass), write the event fail-silently: `event_writer.write("VERIFICATION_RESULT", "task_completed", {"failing_tests": <int>, "lint_errors": <int>, "out_of_scope_files": <list>, "tests_passed": <bool>}, <spec>, <stage>, gate_check.resolve_capture_level(cwd), os.path.join(cwd, ".fbk-capture", "events.jsonl"))`. Resolve spec/stage best-effort (None acceptable). Wrap the write so any failure is swallowed and never alters the exit. The simplest correct structure: compute the result dict once, write it just before the branch that exits, in both the failure and pass branches. Completion: the `VERIFICATION_RESULT` event is written on both the exit-2 and exit-0 paths.
4. Exit codes unchanged: the hook still exits 2 when there are test/lint failures and 0 otherwise. The out-of-scope list being non-empty does NOT by itself change the exit code (it is a warning today and stays so) — only the structured recording is added. Completion: a failing-tests run exits 2 with the event written; a passing run exits 0 with the event written; an unwritable events path leaves both unchanged with no traceback.

Note on redaction: `out_of_scope_files` is a free-text payload field, so at `standard` the writer's central redactor strips it from the persisted record (the test for the populated list runs the hook so that redaction yields the expected outcome — verify the test's level expectation; if the verification test asserts the file list is present, the project fixture is at `full` or the test reads pre-redaction data — match what task-15 asserts). Pass the raw list to the writer and let central redaction apply by level; do not strip in the hook.

# 4 Files to create/modify

- Modify `fbk/hooks/task_completed.py`

# 5 Test requirements

Makes task-15 (new `TestVerificationResultEvent` in `tests/test_hooks_task_completed.py`) pass: a failing run with an out-of-scope file writes a `VERIFICATION_RESULT` event with the failing count, lint-error count, and the out-of-scope file in the list, still exiting 2; a passing run records failing count `0` and an empty (present) out-of-scope list, exiting 0; an unwritable events path leaves the exit code unchanged with no traceback. Existing detection-helper assertions stay green.

# 6 Acceptance criteria

Primary: task-15's tests pass. Covers AC-04 (verification persistence with counts and out-of-scope list, exit codes unchanged) and AC-11 (fail-silent write).

# 7 Model

Sonnet

# 8 Wave

4
