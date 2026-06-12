---
id: task-29
type: implementation
wave: 4
covers: [AC-12, AC-13]
files_to_modify:
  - assets/fbk-scripts/fbk/gates/spec.py
  - assets/fbk-scripts/fbk/gates/task_reviewer.py
  - assets/fbk-scripts/fbk/capture/event_writer.py
test_tasks: [task-10, task-11, task-17]
dependencies: [task-10, task-11, task-17]
completion_gate: "task-10's four rebuilt gate tests pass (zero gate-written envelopes on both outcome paths of both gates); task-17's tests pass (exactly one PIPELINE_COMMAND per real spec-gate dispatch with source 'chokepoint'; warn-but-write for an unregistered source; no warning for a registered one); task-11's source pins stay green"
---

## Objective

Make the chokepoint the single writer of gate-outcome events by removing the spec and task-reviewer gates' own duplicate `PIPELINE_COMMAND` writes, and add warn-but-write source validation to the event writer so an unregistered source is surfaced but never dropped.

## Context

Slice: source-attribution-and-validation. Two halves of one single-writer contract (IF-S-11):

- Pre-fix, one `fbk.py spec-gate` dispatch writes TWO `PIPELINE_COMMAND` events: the chokepoint's (with `data["outcome"]`, the resolved stage, and the gate's JSON stdout in `output`) plus the gate's own duplicate — mislabeled `source="chokepoint"`, carrying `result` but no `outcome` and no stage. The duplicates double-count gate attempts and poison the exact-fraction rate arithmetic the gate-rate slice (task-23, wave 5) depends on — which is why this task must land first. The council-resolved fix removes the gates' writes entirely; the gates' richer payload survives unparsed inside the chokepoint event's `output` field.
- `event_writer.write` accepts any `source` string silently. The fix checks it against `schema.SOURCES` (`("hook_router", "chokepoint", "task_completed", "code_review")`, schema.py:23) and warn-but-writes: an unregistered source gets a stderr warning and is written UNCHANGED — dropping a real event over a label would recreate the silent-data-loss class this remediation exists to kill. The wrong-but-registered mislabel (the class the review actually found) is caught by the per-producer literal pins (tasks 08, 11, 17), not by any runtime check.

**Writer contract (copied verbatim from task-17 — do not paraphrase).** In `fbk/capture/event_writer.py`, after the event-type vocabulary guard and before the envelope is built: when `source not in schema.SOURCES`, emit to stderr exactly

```python
print(f"event_writer: unregistered source {source!r} — writing anyway", file=sys.stderr)
```

and continue — the event is written unchanged (warn-but-write; mirrors the event-type warning path but never discards data, preserving the fail-silent guarantee that no event is dropped over a label).

Invariants to preserve: gate pass/fail logic, exit codes, and stdout JSON are untouched (only the event side effects go); the writer stays fail-silent (the new warning goes to stderr only, before the swallow-everything try block, mirroring the event-type guard at lines 57-62); no event is ever discarded over a source label.

Three-files justification: the two duplicate-write removals and the writer's validation are the two sides of the single-writer contract asserted by one integration test (task-17's single-dispatch guard) — landing them apart leaves that guard red across waves.

Constraints: do NOT modify any test file; file scope is exactly the three files listed. Paths relative to `/home/rahvin/context-assets/assets/fbk-scripts/`.

## Instructions

1. In `fbk/gates/spec.py`, delete BOTH event-write blocks entirely:
   - the fail-path block (lines 310-324): the whole `try: from fbk.capture import event_writer, gate_check ... except Exception: pass` construct between the stderr loop and `sys.exit(2)` — keep the loop and the `sys.exit(2)`;
   - the pass-path block (lines 338-352): the whole trailing `try/except` after `print(json.dumps(result))` — the function then ends at the print.
   The capture imports are local to those blocks, so nothing else needs cleanup. Done when `grep -n "event_writer" fbk/gates/spec.py` returns nothing.
2. In `fbk/gates/task_reviewer.py`, delete the event-write block (lines 340-361): the comment ("Record the gate outcome on both pass and fail...") and the whole `try/except` construct between `print(json.dumps(result))` and `sys.exit(0 if ...)`. Done when `grep -n "event_writer" fbk/gates/task_reviewer.py` returns nothing.
3. In `fbk/capture/event_writer.py`, insert the source check immediately after the event-type vocabulary guard (after line 62's `return None`) and before the `try:` at line 64:
   ```python
   # Source check — warn-but-write. Unlike the event-type guard above, an
   # unregistered source is surfaced on stderr but the event is still written
   # unchanged: source is provenance, not load-bearing, and dropping a real
   # event over a label would be silent data loss. Wrong-but-registered
   # labels are caught by the per-producer literal pins in the tests, not here.
   if source not in schema.SOURCES:
       print(
           f"event_writer: unregistered source {source!r} — writing anyway",
           file=sys.stderr,
       )
   ```
   The print call must match the contract string byte-for-byte (task-17 asserts substrings `"unregistered source"` and the quoted source name). Done when an unregistered source produces one stderr line and one written envelope, and a registered source produces no stderr.
4. Update the writer's module docstring line listing producers (lines 3-5): the producers are the hook router, the chokepoint, the verification hook, and the code-review gate — the spec/task-reviewer gates no longer write events of their own (the chokepoint's dispatch event is the single record). Update the `source` arg docstring to mention the warn-but-write check against `schema.SOURCES`. Done when no doc text claims the gates write events.
5. Run the gating tests. Expected: each gate `main()` invoked directly leaves the events file empty on both pass and fail paths; one real `fbk.py spec-gate` dispatch yields exactly one `PIPELINE_COMMAND` with `source == "chokepoint"`, `data["outcome"]`/`data["exit_code"]` correct on both outcome paths; `rogue_producer` is written unchanged with the stderr warning; `hook_router` writes with empty stderr.

## Files to create/modify

- `assets/fbk-scripts/fbk/gates/spec.py` (modify)
- `assets/fbk-scripts/fbk/gates/task_reviewer.py` (modify)
- `assets/fbk-scripts/fbk/capture/event_writer.py` (modify)

## Test requirements

- Gating: task-10's `tests/test_gates_spec.py::TestSpecGateWritesNoEnvelope` (both tests) and `tests/test_gates_task_reviewer.py::TestTaskReviewerGateWritesNoEnvelope` (both tests); task-17's `tests/test_capture_chokepoint_integration.py::test_one_gate_dispatch_yields_exactly_one_pipeline_command`, `::test_failing_gate_dispatch_also_yields_exactly_one_event`, and `tests/test_capture_event_writer.py::test_unregistered_source_is_written_with_stderr_warning`, `::test_registered_source_writes_without_warning`.
- Must stay green: task-11's source pins (`tests/test_capture_hook_router.py`, `tests/test_hooks_task_completed.py`); the structural gate-validation tests in both gate test files; `tests/test_capture_chokepoint.py` and the rest of `tests/test_capture_chokepoint_integration.py`; the rest of `tests/test_capture_event_writer.py`.

## Acceptance criteria

- AC-12: the spec and task-reviewer gates write no `PIPELINE_COMMAND` of their own — one real dispatch through the chokepoint yields exactly one `PIPELINE_COMMAND` event for that command.
- AC-13: `event_writer` checks `source` against `schema.SOURCES` and warn-but-writes — an unregistered source is written unchanged with a stderr warning; no event is ever dropped over a label.

## Model

Sonnet

## Wave

Wave 4
