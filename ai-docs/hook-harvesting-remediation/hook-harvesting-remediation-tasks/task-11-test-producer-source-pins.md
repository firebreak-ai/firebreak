---
id: task-11
type: test
wave: 1
covers: [AC-13]
files_to_modify:
  - assets/fbk-scripts/tests/test_capture_hook_router.py
  - assets/fbk-scripts/tests/test_hooks_task_completed.py
completion_gate: "Both source-literal pin assertions collect cleanly and pass at the current tree (they pin already-correct literals — the runtime warn-but-write check cannot catch a wrong-but-registered label; these pins are the only check that can); noted as green-at-pre-fix in the source-attribution completion notes."
---

## Objective

Pin each hook producer's exact `source` string literal in its own test file — the only check that catches a wrong-but-registered label.

## Context

Slice: source-attribution-and-validation. The spec resolves source validation as warn-but-write: the runtime check only flags UNREGISTERED labels, so the mislabel class the review actually found (a producer stamping a different registered name — the gates stamped `"chokepoint"`) can only be caught by per-producer tests pinning the exact literal. No test in the suite currently asserts any producer's `source` value (verified by grep). The four producers and their literals: hook_router → `"hook_router"` (fbk/capture/hook_router.py:175), chokepoint → `"chokepoint"` (pinned in task-17), task_completed → `"task_completed"` (fbk/hooks/task_completed.py:230), code_review → `"code_review"` (pinned in task-08).

Two-files note: one pin per producer file; these are the two producer files no other wave-1 task touches.

These pins are expected GREEN at the pre-fix commit (the two producers already stamp the right literal); their value is regression-locking. AC-13 is not in AC-21's red-run list.

## Instructions

1. In `tests/test_capture_hook_router.py`, add `test_event_source_is_exact_hook_router_literal(tmp_path)` using the file's existing `run_router` and `_read_events` helpers and the `make_project(..., instrumented=True, marked=True, capture_cfg="standard")` pattern: feed a `PostToolUse` payload (`tool_name="Read"`), assert exit 0, exactly 1 event, and `events[0]["source"] == "hook_router"` (exact equality against the literal — not a substring or membership check). Docstring: the envelope `source` is the writer's provenance name; after the subagent fix nothing computes metrics from it, so this pin is the regression lock against a relabel. Done when the exact-equality assertion is present.
2. In `tests/test_hooks_task_completed.py`, locate `test_verification_event_records_zero_failures_on_pass` (line ~393) and add, where that test reads back the written envelope, the assertion that the envelope's `source` equals exactly `"task_completed"` (adapt to the test's local variable name for the parsed event; add a one-line comment naming this as the producer's source-literal pin). Done when the assertion is present and the test still passes.
3. Run both files; confirm green. Record in the slice's completion notes that these pins are green at the pre-fix commit by design (regression locks, not defect demonstrations).

## Files to create/modify

- `assets/fbk-scripts/tests/test_capture_hook_router.py` (modify)
- `assets/fbk-scripts/tests/test_hooks_task_completed.py` (modify)

## Test requirements

- Integration (router subprocess) — written event's `source == "hook_router"` exactly.
- Integration (task-completed hook) — written verification envelope's `source == "task_completed"` exactly.

## Acceptance criteria

- AC-13 (pinning half): every producer's tests pin its exact `source` string literal (router and task-completed here; chokepoint in task-17; code-review gate in task-08).

## Model

Sonnet

## Wave

Wave 1
