---
id: task-30
type: implementation
wave: 2
covers: [AC-05, AC-06]
files_to_modify:
  - assets/fbk-scripts/fbk/gates/breakdown.py
test_tasks: [task-11]
dependencies: [task-16]
completion_gate: "the referenced test tasks pass"
---

## 1. Objective

Extends `assets/fbk-scripts/fbk/gates/breakdown.py` so checks #1 and #8 become slice-shape-aware behind a slice-metadata hinge, adds the two cheap shape invariants (cross-cutting ⇒ no impl task; contract-evolving ⇒ retired-tests list), and adds a bounce-back marker check — all while leaving legacy (no-slice-metadata) breakdowns unchanged.

## 2. Context

The breakdown gate gains slice-shape-awareness activated **only when tasks carry slice metadata** — the same backward-compat hinge style the spec gate uses. The hinge is a `"slice_shape"` field on a task entry in `task.json` (the test adds `"slice_shape": "<mode>"` to task dicts). A breakdown with no `slice_shape` on any task runs the existing checks unchanged.

Read the current `assets/fbk-scripts/fbk/gates/breakdown.py` — `validate_breakdown(spec_text, manifest, task_files)` and its eight numbered checks. The signature does NOT change (the test imports `validate_breakdown` unchanged); new behavior is triggered by slice metadata inside the manifest/task content.

Import the shared constant: `from fbk.slices import TEST_DISCIPLINES` — use it for shape validation; do not hard-code the four strings. (Per the spec, the breakdown gate reads the test-lock manifest by its pinned schema and does NOT import `test_hash`. The pre-lock test-review verdict is verified by **manifest presence**: when slice metadata is present, the gate confirms a test-lock manifest (`test-hashes.json`) exists in the feature directory by its pinned path/schema. This is a plain file-presence check — the breakdown skill only populates the manifest on an `accepted` pre-lock verdict, so the manifest's presence is the proxy for "pre-lock verdict accepted." Do NOT add a `test_hash` import to perform this; it is a filesystem existence check by the pinned path. The remaining test cases here are shape invariants, bounce-back, and legacy regression.)

The modifications (read the task-11 test for exact manifest/task-file fixtures and failure substrings):

- **Check #1 (AC coverage requires an impl task)** becomes slice-shape-aware: for an AC covered by a task whose `slice_shape == "cross-cutting"`, an impl task is NOT required (a test-only task suffices). So the existing `if category != "corrective" and not has_impl` failure must be suppressed when the AC's covering tasks are cross-cutting. The test `test_cross_cutting_test_only_slice_passes` must pass.
- **Check #8 (every code-modifying impl task has a corresponding test task)** becomes slice-shape-aware: for an impl task whose `slice_shape == "contract-preserving"`, a NEW test task is NOT required (it locks existing tests). So the "code-modifying task has no corresponding test task" failure must be suppressed for contract-preserving impl tasks. The test `test_contract_preserving_impl_without_new_test_passes` must pass.
- **New cheap invariant — cross-cutting ⇒ no impl task**: if any task with `slice_shape == "cross-cutting"` is of type `implementation`, OR an impl task covers the same AC as a cross-cutting slice, fail. Read the test `test_cross_cutting_with_impl_task_fails` for the exact shape (a cross-cutting manifest that also includes an impl task for the same AC → fail). Implement: when a slice/AC is cross-cutting, the presence of an `implementation`-type task covering that AC is a failure.
- **New cheap invariant — contract-evolving ⇒ retired-tests list present**: a task with `slice_shape == "contract-evolving"` must carry a non-empty `"retired_tests"` field (the test uses `"retired_tests": [{"file": ..., "rationale": ...}]`). Absent or empty → failure mentioning "retired" or "contract-evolving".
- **New invariant — pre-lock test-review verdict accepted (verified by manifest presence)**: when slice metadata is present, the breakdown must have a test-lock manifest (`test-hashes.json`) for the feature. The breakdown skill only writes this manifest on an `accepted` pre-lock test-review verdict, so the manifest's presence is the proxy for "pre-lock verdict accepted." The gate confirms the manifest is present by its pinned name/schema — a presence check, NOT a `test_hash` import and NOT a hash recomputation. The signature does not change, so the manifest's presence is signaled through the data the function already receives: surface the `test-hashes.json` manifest as a key in the `task_files` dict (the same dict `main()` builds from the feature/tasks directory; `main()` includes `test-hashes.json` when present). When slice metadata is present and no `test-hashes.json` entry is present, append a failure mentioning "test-lock manifest" / "pre-lock" / "test-hashes.json". When no slice metadata is present, this check does not fire (legacy breakdowns are unaffected). Read the task-11 test for the exact key/fixture and the failure substring it asserts.
- **Bounce-back marker check**: scan each task file body for an unresolved bounce-back marker — the literal `BOUNCE-BACK:` (it may appear as `<!-- BOUNCE-BACK: ... -->`). Any task file containing it → failure mentioning "bounce" or "BOUNCE-BACK". This check is unconditional (not behind the slice-metadata hinge) per the test, but in practice only fires when a marker is present.

Backward compatibility: when no task carries `slice_shape`, checks #1 and #8 behave exactly as today. The test `test_legacy_no_slice_metadata_passes_same_as_before` (the existing valid breakdown) must still pass, and `test_legacy_uncovered_ac_still_fails` (the existing uncovered-AC case) must still fail. Existing DAG/wave/schema/file-scope checks are preserved unchanged.

## 3. Instructions

1. Read the current `assets/fbk-scripts/fbk/gates/breakdown.py` and the task-11 test (the `make_cross_cutting_manifest`, `make_contract_preserving_manifest` helpers, the `slice_shape`/`retired_tests` fields, and the bounce-back fixture).

2. Add `from fbk.slices import TEST_DISCIPLINES` to the imports.

3. Build a per-task and per-AC view of slice shapes: for each task, read `t.get("slice_shape")`. Compute, per AC, the set of slice shapes of its covering tasks. Determine `slice_metadata_present = any(t.get("slice_shape") for t in tasks)` as the hinge.

4. Modify check #1: in the AC-coverage loop, when computing `has_impl` requirement, skip the no-impl failure for an AC whose covering tasks are cross-cutting. Concretely, if any covering task for the AC has `slice_shape == "cross-cutting"`, do not append the "no implementation task" failure for that AC.

5. Modify check #8: in the code-modifying-impl-needs-test loop, skip the failure for an impl task whose `slice_shape == "contract-preserving"`.

6. Add the cross-cutting ⇒ no-impl invariant: for each AC whose covering tasks include a cross-cutting shape, if any covering task is type `implementation`, append a failure (e.g. `f"Slice shape: cross-cutting AC {ac} must not have an impl task"`).

7. Add the contract-evolving ⇒ retired-tests invariant: for each task with `slice_shape == "contract-evolving"`, if `not t.get("retired_tests")`, append a failure mentioning "retired" and "contract-evolving".

8. Add the pre-lock-verdict-accepted invariant (verified by manifest presence): when `slice_metadata_present`, check whether a test-lock manifest is present. Treat presence of the key `test-hashes.json` in `task_files` as the manifest-present signal (this is the in-memory analog of the file existing in the feature directory; `main()` already loads the feature directory's files into `task_files`, so include `test-hashes.json` there when it exists — extend the `main()` glob to also pick up `test-hashes.json` alongside the `task-*.md` files). If `slice_metadata_present` and there is no `test-hashes.json` key, append a failure mentioning "test-lock manifest" / "pre-lock" / "test-hashes.json". Do NOT import `test_hash`, do NOT read or hash the manifest's contents — presence by the pinned name is sufficient (the manifest is only written on an accepted pre-lock verdict). Legacy (no-slice-metadata) breakdowns skip this check.

9. Add the bounce-back marker check: for each task-file body in `task_files`, if `"BOUNCE-BACK:"` appears, append a failure mentioning "bounce" / "BOUNCE-BACK". (Note: do not treat the `test-hashes.json` manifest entry as a task-file body for the bounce-back scan — scan only actual task-*.md bodies.)

10. Keep all other checks (schema, DAG, wave ordering, test-before-impl, file reference, file count, file-scope conflict) unchanged. The result dict shape is unchanged. Ensure the `test-hashes.json` entry in `task_files` is excluded from checks that iterate task bodies expecting task-*.md content (file-reference, file-list parsing, bounce-back) so it is used only as the manifest-presence signal.

11. Run the paired test: from `assets/fbk-scripts`, `python3 -m pytest tests/test_gates_breakdown.py -q`. The new classes (`TestSliceShapeAwareness`, `TestBounceBackMarkerDetection`, `TestLegacyBreakdownUnchanged`) and the existing `TestBreakdownGateValidation` must all pass.

## 4. Files to create/modify

- `assets/fbk-scripts/fbk/gates/breakdown.py` (modify)

## 5. Test requirements

- New tests: none authored here. Make the new task-11 classes pass while keeping `TestBreakdownGateValidation` green.
- Existing tests impacted: the existing breakdown fixtures keep passing because they carry no slice metadata (the hinge). No test files retired.

## 6. Acceptance criteria

- AC-05: with slice metadata, the gate enforces cross-cutting ⇒ no impl task and contract-evolving ⇒ retired-tests list; its AC-coverage check is slice-shape-aware so a cross-cutting test-only slice and a contract-preserving impl-without-new-test slice both pass.
- AC-05 (pre-lock verdict): with slice metadata, the gate verifies the pre-lock test-review verdict was accepted by confirming the test-lock manifest (`test-hashes.json`) is present in the feature directory — a file-presence proxy, not a `test_hash` import or hash recomputation. A slices-bearing breakdown missing its manifest fails; one with it passes.
- AC-06: the gate fails on an unresolved bounce-back marker.
- Backward compat: no-slice-metadata breakdowns behave unchanged.
- Primary criterion: the task-11 tests pass.

## 7. Model

Sonnet

## 8. Wave

Wave 2
