---
id: task-15
type: test
wave: 4
covers: [AC-04, AC-11]
files_to_modify:
  - assets/fbk-scripts/tests/test_hooks_task_completed.py
completion_gate: "tests compile and fail before implementation"
---

# Objective

Add new assertions to the verification-hook test file proving that `task_completed`, on a completion with failing tests and an out-of-scope file, writes a `VERIFICATION_RESULT` event carrying the failing-test count, lint-error count, and out-of-scope file list as a fail-silent side effect before its existing exit — and that an unwritable events path leaves the hook's exit code and silence unchanged.

# Context

The verification hook `fbk/hooks/task_completed.py` runs as `fbk.py task-completed`, fed a completion payload on stdin. It already detects test/lint commands and exits 2 on failure, 0 on pass. This feature adds a fail-silent `VERIFICATION_RESULT` event write before that exit, carrying: test pass/fail with failing-test count, lint-error count, and the list of files touched outside the task's declared scope. The hook's exit codes are unchanged. A capture-write failure (unwritable events path) never affects the hook.

The existing test file `tests/test_hooks_task_completed.py` covers the hook's detection helpers (`detect_test_cmd`, `detect_lint_cmd`) and the task-path regex via direct calls and `tmp_path`. The hook's `main()` reads stdin and is reached via subprocess (`fbk.py task-completed`). To make the event write land in a fixture location, run the hook subprocess with `cwd=<instrumented tmp project>` so the writer creates `<project>/.fbk-capture/events.jsonl`. Build the project with `capture_fixtures.make_project`.

Pinned stdin payload and failing-run fixture:
- The completion payload is `{"task_description": "<text containing a path of the form ai-docs/<feature>/<feature>-tasks/task-NN.md>", "cwd": "<tmp project root>"}`. (The `task_description` carries the task path the hook's regex locates and from which it reads the task's declared file scope.)
- To force a DETERMINISTIC FAILING verification: drop a `Makefile` whose `test:` target exits 1 (`detect_test_cmd` returns `"make test"` for a Makefile carrying a `test:` target — confirmed against the existing `test_makefile_test_target_detected` test), run `git init` in the project so the out-of-scope diff is computable, and modify a file that is OUTSIDE the task's declared scope so the out-of-scope list is non-empty.
- CAPTURE LEVEL — the scope-violation file paths are a free-text payload that central redaction strips at `standard` (AC-26). So any test that asserts the out-of-scope file LIST (the paths) must run the project at `full`: write `.fbk-capture/capture.cfg` with `capture_level=full` AND set the out-of-tree corroboration `env={**os.environ, "FBK_CAPTURE_LEVEL": "full"}` on the subprocess call. The non-free-text fields (failing-test count, lint-error count, and a count of out-of-scope files) survive at any level; only the path list requires `full`. (The standard-level redaction of these paths is verified separately by the central-redaction test in the event-writer task.)

# Instructions

1. In `tests/test_hooks_task_completed.py`, add a new test class `TestVerificationResultEvent` guarded to skip when the event writer is absent (`from fbk.capture import event_writer` inside `try/except ImportError`, skipif).
2. Add a subprocess helper running `fbk.py task-completed` with the completion payload on stdin: `subprocess.run([sys.executable, str(FBK_PY), "task-completed"], input=json.dumps({"task_description": <text-with-task-path>, "cwd": str(project)}), cwd=str(project), capture_output=True, text=True)`, `FBK_PY = Path(__file__).parent.parent / "fbk.py"`.
3. `test_verification_event_written_on_failure`: build an instrumented project AT FULL LEVEL (per the capture-level note above: `capture.cfg` = `capture_level=full` plus `FBK_CAPTURE_LEVEL=full` on the subprocess env) with (a) a `Makefile` whose `test:` target exits 1, (b) `git init` run, (c) the task file under `ai-docs/<feature>/<feature>-tasks/task-NN.md` declaring a narrow file scope, and (d) a file modified OUTSIDE that declared scope; feed the payload referencing the task path; assert the hook exits 2 (unchanged) AND a `VERIFICATION_RESULT` event is in `<project>/.fbk-capture/events.jsonl` carrying a failing-test count `>= 1`, a lint-error count field, and the out-of-scope file list including the touched-but-undeclared file (the path list is present because the project runs at full). Assert the event's data fields by key and value (failing count and the file in the list), pairing presence with the value.
4. `test_verification_event_records_zero_failures_on_pass`: build an instrumented project AT FULL LEVEL whose `Makefile` `test:` target exits 0 and whose touched files are all in declared scope; assert the hook exits 0 (unchanged) AND a `VERIFICATION_RESULT` event records a failing-test count of exactly `0` and an empty out-of-scope list (present-and-empty, not absent).
5. `test_verification_write_failure_is_silent`: instrumented project with an unwritable events path; feed the payload; assert the hook's exit code matches the no-capture run (same pass/fail) AND no traceback appears in stderr — the write failure is swallowed.

# Files to create/modify

- `tests/test_hooks_task_completed.py` (add `TestVerificationResultEvent`)

# Test requirements

- `test_verification_event_written_on_failure` (integration): failing tests + out-of-scope file → VERIFICATION_RESULT with exact failing count, lint-error count, and the out-of-scope file in the list; hook still exits 2.
- `test_verification_event_records_zero_failures_on_pass` (integration): passing run → VERIFICATION_RESULT with failing count `0` and empty (present) out-of-scope list; hook exits 0.
- `test_verification_write_failure_is_silent` (integration): unwritable events path → hook exit code unchanged, no traceback.

# Acceptance criteria

AC-04 (verification persistence with counts and out-of-scope list, exit codes unchanged), AC-11 (fail-silent write). Gate: tests compile and fail before implementation. Existing detection-helper assertions unaffected.

# Model

Sonnet — subprocess hook with a fixture that forces a failing verification run.

# Wave

4
