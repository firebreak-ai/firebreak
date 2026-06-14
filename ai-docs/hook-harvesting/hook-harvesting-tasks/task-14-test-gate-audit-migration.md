---
id: task-14
type: test
wave: 4
covers: [AC-03, AC-11]
files_to_modify:
  - assets/fbk-scripts/tests/test_gates_spec.py
  - assets/fbk-scripts/tests/test_gates_task_reviewer.py
completion_gate: "tests compile and fail before implementation"
---

# Objective

Add new envelope-write assertions to the spec-gate and task-reviewer-gate test files proving each gate, on the paths that previously called the old audit log, now writes a correctly-stamped event envelope through the shared event writer — and does so fail-silently.

# Context

The spec and task-reviewer gates carry `audit.log_event` calls that record a gate result. Those calls move onto the new shared event writer, which appends one JSON envelope line to `.fbk-capture/events.jsonl`. The migration is a call-site swap; the gates' pass/fail output is unchanged. No existing test asserts the old audit call (verified: neither file references `audit` or `log_event`, and the call sites sit in bare `try/except`), so the swap would otherwise ship with zero coverage. These tests gain NEW assertions that each gate, when run in an instrumented project, writes a correctly-stamped envelope.

The spec gate has TWO live audit sites — a fail path (around line 312) and a pass path (around line 330) of `fbk/gates/spec.py`'s `main()` — and BOTH migrate. The task-reviewer gate has one (around line 344 of `fbk/gates/task_reviewer.py`'s `main()`, on the pass path). All three live inside `main()`.

Drive the gates in-process via their `main()` and argv — a new in-process approach (note the existing `test_gates_spec.py` invokes the gate by subprocess), required here because `monkeypatch.chdir` only redirects `os.getcwd()` in-process and the writer resolves its events path from `os.getcwd()`. No subprocess. `main()` calls `sys.exit(...)`, so wrap each call in `pytest.raises(SystemExit)` and read `exc.value.code` for the exit code. Set the spec/task path argument by patching `sys.argv` (e.g. `monkeypatch.setattr(sys, "argv", ["spec-gate", str(spec_file)])`). To make the envelope write land in a fixture location, `monkeypatch.chdir(<instrumented tmp project>)` so `os.getcwd()` resolves there and the writer creates `<project>/.fbk-capture/events.jsonl`. Build the instrumented project with `capture_fixtures.make_project` (marked Firebreak project). The event for these gates is a `PIPELINE_COMMAND` envelope (the gate result), carrying the gate name and result.

# Instructions

1. In `tests/test_gates_spec.py`, add a new test class `TestSpecGateWritesEnvelope` guarded so it skips if the event writer module is absent (`from fbk.capture import event_writer` inside `try/except ImportError`, skipif). Reuse the file's existing spec-building helpers. Import `fbk.gates.spec` to call its `main()`.
2. `test_spec_gate_pass_writes_envelope`: build a valid spec; `monkeypatch.chdir(<instrumented project>)`, set argv to the spec path, call `spec.main()` inside `pytest.raises(SystemExit)` (or capture a normal return — the pass path may not raise; handle both); assert the pass outcome AND `<project>/.fbk-capture/events.jsonl` contains a `PIPELINE_COMMAND` envelope whose recorded gate result is `pass` and whose `spec`/`stage` fields are present (structure check, not a timestamp value). Match by structure (envelope keys + gate-name/result fields), not body vocabulary.
3. `test_spec_gate_fail_writes_envelope`: build a spec that fails structural validation; chdir to the instrumented project, set argv, call `main()` inside `pytest.raises(SystemExit)`; assert `exc.value.code == 2` (fail path) AND an envelope was written recording the `fail` result. This covers the second audit site (the fail path).
4. `test_spec_gate_write_failure_is_silent`: chdir to an instrumented project where the events path is unwritable (e.g. `.fbk-capture/` is a read-only dir or a file where the dir should be); run `main()` on a valid and an invalid spec; assert the gate's exit code/pass-fail behavior is unchanged versus the writable run and nothing raised beyond the gate's own `SystemExit` — the envelope-write failure never affects the gate.
5. In `tests/test_gates_task_reviewer.py`, add a new test class `TestTaskReviewerGateWritesEnvelope` similarly guarded. Follow the file's passing-fixture pattern: the existing `validate_tasks(...)` tests show the valid spec-AC + task-set shape the gate accepts. Drive `fbk.gates.task_reviewer.main()` in-process by patching `sys.argv` to the arguments its argparse expects (inspect `main()` for the exact arguments — spec path, task files, `--project-root`, `--tasks-dir`). Build a minimal passing fixture: a valid spec file plus a minimal task set the gate passes (reuse the shapes the file's passing `validate_tasks` tests already construct).
6. `test_task_reviewer_gate_pass_writes_envelope`: build the minimal passing fixture; `monkeypatch.chdir(<instrumented project>)`, set argv, call `task_reviewer.main()` inside `pytest.raises(SystemExit)`; assert `exc.value.code == 0` AND a `PIPELINE_COMMAND` envelope recording the `pass` result was written to the project events file, with envelope fields present (structural match).
7. `test_task_reviewer_gate_write_failure_is_silent`: same pass scenario with an unwritable events path; assert the gate's exit code is unchanged and nothing raised beyond the gate's own `SystemExit` — fail-silent.

# Files to create/modify

- `tests/test_gates_spec.py` (add `TestSpecGateWritesEnvelope`)
- `tests/test_gates_task_reviewer.py` (add `TestTaskReviewerGateWritesEnvelope`)

# Test requirements

- `test_spec_gate_pass_writes_envelope` (integration): spec-gate pass → PIPELINE_COMMAND envelope with `pass` result and present spec/stage fields.
- `test_spec_gate_fail_writes_envelope` (integration): spec-gate fail → envelope recording `fail` (second audit site).
- `test_spec_gate_write_failure_is_silent` (integration): unwritable events path → gate behavior unchanged, no traceback.
- `test_task_reviewer_gate_pass_writes_envelope` (integration): task-reviewer-gate pass → PIPELINE_COMMAND envelope recording `pass`.
- `test_task_reviewer_gate_write_failure_is_silent` (integration): unwritable events path → gate behavior unchanged, no traceback.

# Acceptance criteria

AC-03 (the migrated gate command events carry the result envelope), AC-11 (the migrated write is fail-silent). Gate: tests compile and fail before implementation. Existing pass/fail assertions in both files are unaffected.

# Model

Sonnet — two existing files, in-process `main()` invocation (argv-patched, SystemExit-caught) with chdir-pinned writes and fail-silent cases.

# Wave

4
