---
id: task-17
type: test
wave: 3
covers: [AC-12, AC-13]
files_to_modify:
  - assets/fbk-scripts/tests/test_capture_chokepoint_integration.py
  - assets/fbk-scripts/tests/test_capture_event_writer.py
completion_gate: "Single-dispatch and warn-but-write tests collect cleanly at the current tree; the single-dispatch test FAILS (two PIPELINE_COMMAND events per spec-gate dispatch) from a second git worktree at the pre-fix commit (40ec021 at spec time) with the file copied in; failing output captured in the source-attribution slice's completion notes."
---

## Objective

Author the positive single-writer guard (one real gate dispatch yields exactly one `PIPELINE_COMMAND`, source `"chokepoint"`) and the writer's warn-but-write source-validation guard.

## Context

Slice: source-attribution-and-validation (contract-evolving; the negative gate-side half is task-10). Pre-fix, one `fbk.py spec-gate` dispatch writes TWO `PIPELINE_COMMAND` events: the chokepoint's (with `outcome`) and the gate's own duplicate (mislabeled `source="chokepoint"`, carrying `result` but no `outcome`) — double-counting attempts and poisoning the rate arithmetic.

**Declared writer contract (the implementation task copies this verbatim).** In `fbk/capture/event_writer.py`, after the event-type vocabulary guard and before the envelope is built: when `source not in schema.SOURCES`, emit to stderr exactly

```python
print(f"event_writer: unregistered source {source!r} — writing anyway", file=sys.stderr)
```

and continue — the event is written unchanged (warn-but-write; mirrors the event-type warning path but never discards data, preserving the fail-silent guarantee that no event is dropped over a label).

Two-files note: the dispatch-side and writer-side checks are the two halves of one slice contract; wave 3 because `tests/test_capture_event_writer.py` is owned by task-09 (wave 1) and task-16 (wave 2).

Chokepoint facts (verified): `fbk.py` routes every command through `chokepoint.record_dispatch`, which resolves spec/stage via the shared resolver and writes `data` with `command_name`, `args`, `outcome`, `exit_code`, `duration`, `output`. The integration file's `_run_fbk`/`_read_event_lines` helpers drive real subprocess dispatches.

## Instructions

1. In `tests/test_capture_chokepoint_integration.py`, add `test_one_gate_dispatch_yields_exactly_one_pipeline_command(tmp_path)`:
   - Instrumented marked project (`capture_fixtures.make_project`); state dir at `<project>/.claude/automation/state` holding a state for spec `"demo-spec"` with `current_state="VALIDATING"` (`stage_timestamps={"QUEUED": ..., "VALIDATING": ...}`) so the dispatch resolves to an active working stage.
   - Write `<project>/sample-spec.md` containing a gate-passing spec: copy the exact markdown produced by `_make_minimal_spec()` in `tests/test_gates_spec.py` into a local constant, with a comment crediting that file as the source of truth.
   - Run `_run_fbk(["spec-gate", "sample-spec.md"], project, state_dir)`; assert rc 0.
   - Read the events; let `gate_events = [e for e in events if e["event_type"] == "PIPELINE_COMMAND" and e["data"].get("command_name") == "spec-gate"]`; assert `len(gate_events) == 1` exactly (the gates' duplicate writes are gone; the chokepoint's event is the single record per dispatch).
   - On that one event assert: `source == "chokepoint"` exactly (the producer's source-literal pin), `data["outcome"] == "pass"`, `data["exit_code"] == 0`, `spec == "demo-spec"`, `stage == "VALIDATING"`.
   Done when the exactly-one and per-field assertions are present.
2. In the same file, add `test_failing_gate_dispatch_also_yields_exactly_one_event(tmp_path)`: same setup with `<project>/broken-spec.md` containing `"# Feature Specification\n\n## Problem\nOnly one section present.\n"`; dispatch returns rc 2; assert exactly one spec-gate `PIPELINE_COMMAND` with `data["outcome"] == "fail"` and `data["exit_code"] == 2`, `source == "chokepoint"`. Done when both outcome paths are pinned.
3. In `tests/test_capture_event_writer.py`, add `test_unregistered_source_is_written_with_stderr_warning(tmp_path, capsys)`:
   - `event_writer.write("TOOL_USE", "rogue_producer", {"count": 1}, "s", "IMPLEMENTING", "standard", path)`.
   - Assert exactly 1 line written; `record["source"] == "rogue_producer"` (written unchanged — never dropped over a label) and `record["data"]["count"] == 1`.
   - Assert stderr contains both `"unregistered source"` and `"rogue_producer"`; assert stdout is empty.
   Done when the written-unchanged and warning assertions are present.
4. In the same file, add `test_registered_source_writes_without_warning(tmp_path, capsys)`: write with source `"hook_router"`; assert 1 line written and `capsys.readouterr().err == ""`. Done when present.
5. Verification step (no modification): run `tests/test_capture_chokepoint.py` and the rest of `tests/test_capture_chokepoint_integration.py`; confirm green, updating nothing.
6. Red run: from the pre-fix worktree with the chokepoint-integration file copied in, run the single-dispatch tests; capture the failing output (two events) in the slice's completion notes. The warn-but-write tests' pre-fix outcome (no warning emitted) is captured alongside.

## Files to create/modify

- `assets/fbk-scripts/tests/test_capture_chokepoint_integration.py` (modify)
- `assets/fbk-scripts/tests/test_capture_event_writer.py` (modify)

## Test requirements

- Integration (real fbk.py dispatch) — passing spec-gate: exactly 1 `PIPELINE_COMMAND` with `command_name == "spec-gate"`, `source == "chokepoint"`, `outcome == "pass"`, `exit_code == 0`, `spec == "demo-spec"`, `stage == "VALIDATING"`.
- Integration — failing spec-gate dispatch: exactly 1 event, `outcome == "fail"`, `exit_code == 2`, `source == "chokepoint"`.
- Unit (production write path) — unregistered source: event written unchanged with the source preserved, stderr warning naming it, empty stdout; registered source: no warning.

## Acceptance criteria

- AC-12: one real dispatch through the chokepoint yields exactly one `PIPELINE_COMMAND` event for that command.
- AC-13: `event_writer` checks `source` against `schema.SOURCES` and warn-but-writes — an unregistered source is written unchanged with a stderr warning.

## Model

Sonnet

## Wave

Wave 3
