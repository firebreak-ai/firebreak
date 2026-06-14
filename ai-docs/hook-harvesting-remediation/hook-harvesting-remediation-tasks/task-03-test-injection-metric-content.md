---
id: task-03
type: test
wave: 1
covers: [AC-04]
files_to_modify:
  - assets/fbk-scripts/tests/test_capture_retro_injector.py
  - assets/fbk-scripts/tests/test_capture_e2e_seam.py
completion_gate: "Strengthened injector and e2e-seam tests collect cleanly at the current tree and FAIL against the stage_summary stub from a second git worktree at the pre-fix commit (40ec021 at spec time) with both files copied in; failing output captured in the injection-render slice's completion notes."
---

## Objective

Extend the heading-only injection test and the existing two-source seam test to assert exact metric values, and re-choreograph the seam test so the router event fires while the stage is actively running.

## Context

Slice: injection-render (contract-evolving; these are the slice's two retired-and-rebuilt tests). `report.stage_summary` (fbk/report.py:209-227) is a stub: it emits only the provenance marker plus `stage:`/`spec:` label lines. The fix makes it load the events file and the state and render the stage's real gate-rate, parks, and rework values. Both existing tests pass against the stub because they assert only the heading and marker prefix.

**Declared block contract (the implementation task copies this verbatim).** `stage_summary(spec, stage)` returns these lines in order, after the existing marker / `stage:` / `spec:` lines:

```
first-try rate: <f"{rate:.2f}">
after-rework rate: <f"{rate:.2f}">
parks: <int>
rework: <int>
```

where first-try / after-rework rates come from `classify_gate_attempts` + `first_try_pass_rate` over the stage's events (loaded the same way the report command loads them: events from `<cwd>/.fbk-capture/events.jsonl`, state via `fbk.report._load_state(spec)`), `parks` is `len(derive_parks(st, stage))`, and `rework` is `derive_rework(st, stage)`.

Two-files note: the two rebuilds are the same retired-guard correction named by one slice; splitting them would split a single behavior's red run across tasks.

## Instructions

1. In `tests/test_capture_retro_injector.py`, extend `_setup_project` so the fixture computes non-trivial metrics:
   - Add `monkeypatch.delenv("STATE_DIR", raising=False)` so `_load_state` resolves the default `.claude/automation/state` path under the chdir'd tmp project.
   - Replace the single LIFECYCLE event with three `VERIFICATION_RESULT` events, `source="task_completed"`, spec/stage as given, production payload shape `{"failing_test_count": <n>, "lint_error_count": 0, "out_of_scope_files": [], "tests_passed": <bool>}`:
     fail at `2026-01-01T00:01:00+00:00`, pass at `2026-01-01T00:01:30+00:00`, pass at `2026-01-01T00:03:00+00:00`.
   - Build the state with `stage_timestamps={stage: "2026-01-01T00:00:00+00:00", "PARKED": "2026-01-01T00:02:00+00:00", "READY": "2026-01-01T00:02:30+00:00"}`, `current_state=stage`, and `error_history=[{"stage": stage, "error": "gate failed", "timestamp": "2026-01-01T00:02:00+00:00"}]`.
   Hand-derived expectations: first-try attempts = fail + pass (both before the 00:02 park) → rate exactly 1/2; after-rework attempts = the 00:03 pass → rate exactly 1.0; parks = 1; rework = 1. Done when the fixture writes exactly these events and state.
2. Extend `test_injects_block_under_metrics_heading`: keep the heading and structural-marker assertions, then assert each of these exact lines is present in the file's lines: `first-try rate: 0.50`, `after-rework rate: 1.00`, `parks: 1`, `rework: 1`. The stub emits none of them, so the test fails against it by construction. Done when all four exact-line assertions are present.
3. Confirm the other three tests in the file (prose preservation, two marked blocks, swallowed exception) still pass with the richer fixture — they assert structure only; do not weaken them.
4. In `tests/test_capture_e2e_seam.py::test_two_source_cycle_joins_in_one_report`, re-choreograph: move Step 4 (the router `PostToolUse` payload) to run BEFORE the `VALIDATING -> VALIDATED` transition, so the router event fires while the stage is actively `VALIDATING`. After the corrected resolver lands, an event fired post-transition would carry no stage and exit the asserted table for a reason unrelated to the stub. Add the assertion `tool_use_sample["stage"] == "VALIDATING"`. Done when the router step precedes the VALIDATED transition and the stage assertion is present.
5. In the same test, strengthen Step 8: after the existing heading and marker-prefix assertions, assert these exact lines are present in the retrospective: `first-try rate: 0.00`, `parks: 0`, `rework: 0`. Comment the intentional zero-values: this cycle drives no gate dispatch and no park, so the fixture computes to zeros — the guard's teeth are that the stub renders no metric lines at all. Done when the three exact-line assertions and the comment are present.
6. Red run: from the pre-fix worktree with both files copied in, run the two strengthened tests; capture the failing output in the slice's completion notes.

## Files to create/modify

- `assets/fbk-scripts/tests/test_capture_retro_injector.py` (modify)
- `assets/fbk-scripts/tests/test_capture_e2e_seam.py` (modify)

## Test requirements

- Integration (injector over fixture events/state) — injected block contains exact lines `first-try rate: 0.50`, `after-rework rate: 1.00`, `parks: 1`, `rework: 1` beneath a structurally valid marker.
- E2E (subprocess fbk.py + router) — two-source cycle: router event carries `stage == "VALIDATING"`; retrospective block contains exact lines `first-try rate: 0.00`, `parks: 0`, `rework: 0` (intentional zeros, commented).

## Acceptance criteria

- AC-04: the per-stage block produced by `stage_summary` and injected into the retrospective contains the stage's real gate-rate, parks, and rework values.

## Model

Sonnet

## Wave

Wave 1
