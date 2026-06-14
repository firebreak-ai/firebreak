---
id: task-31
type: implementation
wave: 4
covers: [AC-03, AC-11]
files_to_modify:
  - assets/fbk-scripts/fbk/gates/spec.py
  - assets/fbk-scripts/fbk/gates/task_reviewer.py
test_tasks: [task-14]
completion_gate: "task-14 tests pass"
dependencies: [task-27]
---

# 1 Objective

Migrate the three live `audit.log_event` gate-result call sites — two in the spec gate (a fail path and a pass path) and one in the task-reviewer gate (a pass path) — onto the shared event writer, so each gate writes a correctly-stamped `PIPELINE_COMMAND` envelope to `.fbk-capture/events.jsonl` instead of (or in addition to nothing asserted on) the old audit log, fail-silently and with the gates' pass/fail output unchanged.

# 2 Context

The spec and task-reviewer gates record a gate result through bare `try/except`-wrapped `audit.log_event` calls that no existing test asserts. Those calls move onto the new event writer (task-27), which appends one JSON envelope line. The migration is a call-site swap: the gates' exit codes and printed JSON are unchanged; only the recording mechanism changes. The write must be fail-silent — an unwritable events path never affects the gate.

Verified call sites (the code is authoritative — there are THREE, not two):
- `fbk/gates/spec.py` `main()`: the FAIL path (around line 312, inside `if fails:` before `sys.exit(2)`) and the PASS path (around line 330, after printing the pass result).
- `fbk/gates/task_reviewer.py` `main()`: the PASS path (around line 344, inside `if result["result"] == "pass":` before `sys.exit(0)`).

A FOURTH `audit.log_event` caller in `fbk/hooks/dispatch_status.py` (~line 79) deliberately STAYS on the old audit path — do NOT touch it.

The event writer needs an events path under the project; the gates run with `os.getcwd()` as the project root (where fbk is invoked), so write to `os.path.join(os.getcwd(), ".fbk-capture", "events.jsonl")`. Resolve the capture level via `gate_check.resolve_capture_level(os.getcwd())`. Spec/stage stamping is best-effort: the spec name is the gate's `spec_name`; stage may be None.

# 3 Instructions

1. In `fbk/gates/spec.py`, add `from fbk.capture import event_writer, gate_check` near the gate's imports (or import lazily inside `main()` to keep import cost off other call paths — a function-level import is acceptable and matches the existing lazy `from fbk import audit` pattern).
2. **Spec gate FAIL site (around line 312):** replace the `audit.log_event(spec_name, "gate_result", json.dumps({"gate": "spec", "result": "fail"}))` call (keep or remove the surrounding bare try/except as you wire the new writer; the new writer is itself fail-silent) with a fail-silent `event_writer.write("PIPELINE_COMMAND", "code_review" if ... else "chokepoint", ...)` — use source `"chokepoint"` is wrong here; use a gate-appropriate registered source. The registered sources are `("hook_router", "chokepoint", "task_completed", "code_review")`; the gate result envelope is a `PIPELINE_COMMAND` recorded by the dispatch layer, but these gates write directly, so record it with `source="chokepoint"` (the dispatch-command producer) carrying `data={"gate": "spec", "result": "fail", "command_name": "spec-gate"}`, `spec=spec_name`, `stage=None`, `capture_level=gate_check.resolve_capture_level(os.getcwd())`, `events_path=<cwd>/.fbk-capture/events.jsonl`. Wrap so any failure is swallowed and the gate still `sys.exit(2)`. Completion: a failing spec writes a `PIPELINE_COMMAND` envelope recording `result: fail` and still exits 2.
3. **Spec gate PASS site (around line 330):** replace the `audit.log_event(spec_name, "gate_result", json.dumps(result))` call with a fail-silent `event_writer.write("PIPELINE_COMMAND", "chokepoint", {"gate": "spec", "result": "pass", "command_name": "spec-gate", **<summarized result>}, spec_name, None, level, events_path)`. Completion: a passing spec writes a `PIPELINE_COMMAND` envelope recording `result: pass` with spec/stage fields present.
4. **Task-reviewer gate PASS site (around line 344):** in `fbk/gates/task_reviewer.py`, add the same import and replace the `log_event(spec_name, "gate_result", json.dumps({"gate": "task-reviewer", "result": "pass"}))` call with a fail-silent `event_writer.write("PIPELINE_COMMAND", "chokepoint", {"gate": "task-reviewer", "result": "pass", "command_name": "task-reviewer-gate"}, spec_name, None, level, events_path)`. Keep the existing `sys.exit(0)`. Completion: a passing task-review writes a `PIPELINE_COMMAND` envelope recording `result: pass` and still exits 0.
5. Fail-silence: each write must be wrapped so an unwritable events path raises nothing and leaves the gate's exit code and printed JSON unchanged. (The writer itself is fail-silent, but keep a defensive wrap so an import or path-resolution error cannot escape.) Completion: with an unwritable events path, both gates' pass/fail behavior matches the writable run and no traceback escapes.
6. Do NOT modify `fbk/hooks/dispatch_status.py`. Completion: that file's `audit.log_event` caller is untouched.

# 4 Files to create/modify

- Modify `fbk/gates/spec.py` (two sites: fail path ~line 312, pass path ~line 330)
- Modify `fbk/gates/task_reviewer.py` (one site: pass path ~line 344)

# 5 Test requirements

Makes task-14 (new `TestSpecGateWritesEnvelope` in `tests/test_gates_spec.py` and `TestTaskReviewerGateWritesEnvelope` in `tests/test_gates_task_reviewer.py`) pass: spec-gate pass and fail each write a correctly-stamped `PIPELINE_COMMAND` envelope; task-reviewer pass writes one; an unwritable events path leaves gate behavior unchanged with no traceback. Existing pass/fail assertions in both files remain green.

# 6 Acceptance criteria

Primary: task-14's tests pass. Covers AC-03 (the migrated gate command events carry the result envelope) and AC-11 (the migrated write is fail-silent).

# 7 Model

Sonnet

# 8 Wave

4
