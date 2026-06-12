---
id: task-10
type: test
wave: 1
covers: [AC-12]
files_to_modify:
  - assets/fbk-scripts/tests/test_gates_spec.py
  - assets/fbk-scripts/tests/test_gates_task_reviewer.py
completion_gate: "Rebuilt gate tests collect cleanly at the current tree and FAIL (gates still write their own envelopes) from a second git worktree at the pre-fix commit (40ec021 at spec time) with both files copied in; failing output captured in the source-attribution slice's completion notes."
---

## Objective

Rebuild the spec-gate and task-reviewer-gate envelope tests to assert the gates write NO `PIPELINE_COMMAND` of their own — the chokepoint's event is the single record per dispatch.

## Context

Slice: source-attribution-and-validation (contract-evolving; these are the slice's retired tests, named at `tests/test_gates_spec.py` 352-405 and `tests/test_gates_task_reviewer.py` 393-496). Today both gate `main()` functions write their own `PIPELINE_COMMAND` events (fbk/gates/spec.py:314-323 and 342-351; fbk/gates/task_reviewer.py:347-360) — and they even stamp `source="chokepoint"`, the wrong-but-registered mislabel the review found. One real dispatch through fbk.py therefore yields two `PIPELINE_COMMAND` events, double-counting gate attempts and breaking the exact-fraction rate arithmetic. The council-resolved fix removes the gates' writes entirely; the chokepoint event (which already carries `data["outcome"]`, the resolved stage, and the gate's full JSON stdout in `output`) is the single record. The positive single-event assertion through the chokepoint is task-17; this task pins the negative half at each gate's own entry point.

Two-files note: the two rebuilds are the same retired-guard correction (the spec folds both into one slice line); each file keeps its own fixtures.

## Instructions

1. In `tests/test_gates_spec.py`, replace the `TestSpecGateWritesEnvelope` class with `TestSpecGateWritesNoEnvelope`, reusing its `_events_path`/`_read_envelopes` helpers and its existing fixtures (instrumented marked project, `_make_minimal_spec()`, monkeypatched argv + chdir):
   - `test_spec_gate_pass_writes_no_envelope`: run `_spec_gate_mod.main()` on the valid spec (pass path returns normally); assert `self._read_envelopes(project_root) == []` — invoked directly (not through fbk.py), the gate is the only possible writer, so the events file must hold zero envelopes.
   - `test_spec_gate_fail_writes_no_envelope`: run `main()` on the one-section broken spec inside `pytest.raises(SystemExit)`; assert the exit code is 2 AND `_read_envelopes(project_root) == []`.
   - Delete `test_spec_gate_write_failure_is_silent` and any remaining tests of that class that assert the gate's own write behavior — their premise (the gate writes) is the defect being removed. Keep the class docstring explicit: one dispatch yields exactly one `PIPELINE_COMMAND`, written by the chokepoint; the chokepoint-side positive assertion lives in `tests/test_capture_chokepoint_integration.py`.
   Done when no assertion in the file expects a gate-written envelope.
2. In `tests/test_gates_task_reviewer.py`, replace `TestTaskReviewerGateWritesEnvelope` with `TestTaskReviewerGateWritesNoEnvelope`, reusing the existing `_make_task_reviewer_fixture` choreography (instrumented project, copied spec + task files):
   - `test_task_reviewer_gate_pass_writes_no_envelope`: the pass choreography (placeholder source file present), `pytest.raises(SystemExit)` with code 0; assert zero envelopes.
   - `test_task_reviewer_gate_fail_writes_no_envelope`: the fail choreography (placeholder deliberately omitted), exit code 2; assert zero envelopes.
   Done when no assertion in the file expects a gate-written envelope.
3. Confirm the rest of both files (structural gate validation tests) still pass unmodified.
4. Red run: from the pre-fix worktree with both files copied in, run the four rebuilt tests; capture the failing output (envelopes present) in the slice's completion notes.

## Files to create/modify

- `assets/fbk-scripts/tests/test_gates_spec.py` (modify)
- `assets/fbk-scripts/tests/test_gates_task_reviewer.py` (modify)

## Test requirements

- Integration (gate `main()` in-process, instrumented project) — spec gate pass path: zero envelopes in the events file; spec gate fail path (exit 2): zero envelopes; task-reviewer pass path (exit 0): zero envelopes; task-reviewer fail path (exit 2): zero envelopes.

## Acceptance criteria

- AC-12 (gate half): the spec and task-reviewer gates write no `PIPELINE_COMMAND` of their own.

## Model

Sonnet

## Wave

Wave 1
