---
id: task-11
type: test
wave: 2
covers: [AC-05, AC-06]
files_to_modify:
  - assets/fbk-scripts/tests/test_gates_breakdown.py
completion_gate: "tests compile and fail before implementation"
---

## 1. Objective

Modifies `assets/fbk-scripts/tests/test_gates_breakdown.py` to add tests verifying that: a cross-cutting test-only slice passes (previously rejected by check #1), a contract-preserving impl-without-new-test slice passes (previously rejected by check #8), a contract-evolving slice missing its retired-tests list fails, an unresolved bounce-back marker fails; and that the existing legacy-breakdown behavior (no slice metadata) is unchanged.

## 2. Context

The breakdown gate gains slice-shape-awareness activated **only when tasks carry slice metadata** (a `slice_shape` field in each task's task.json entry, or a slice declaration in the spec). Without slice metadata, the existing checks run unchanged — the "backward-compat hinge."

The two modified checks:
- **Check #1** (every code-modifying impl AC must have a test task): For a `cross-cutting` slice, an AC may be covered by test-only tasks — no impl task is required. The existing check currently fails this. After implementation it must pass.
- **Check #8** (every code-modifying impl task must have a corresponding test task): For a `contract-preserving` slice, an impl task over locked existing tests is valid without a NEW test task. The existing check currently fails this. After implementation it must pass.

Two new cheap invariants enforced only when slice metadata is present:
- `cross-cutting` ⇒ no impl task in the task list (if any impl task is present for a cross-cutting AC, the gate fails)
- `contract-evolving` ⇒ a `retired-tests` list with rationale is present in the task metadata

Bounce-back marker: an unresolved `BOUNCE-BACK:` or `<!-- BOUNCE-BACK:` marker in any task file body fails the gate.

The slice metadata format in task.json entries: add a `"slice_shape"` field to each task dict. The gate reads this to determine if the slice-shape-aware path applies. This field is now spec-pinned: per §Interface contracts #5, "each task.json entry whose work belongs to a declared slice optionally carries a `slice_shape` field with a value from `TEST_DISCIPLINES`; the breakdown-gate uses this as the slice-metadata hinge for its shape-aware checks (no `slice_shape` ⇒ legacy behavior)."

The import `from fbk.gates.breakdown import validate_breakdown` remains unchanged — the function signature does not change. The new behavior is triggered by slice metadata inside the manifest/task content.

All new tests must be added as new methods to new classes, not modifying the existing `TestBreakdownGateValidation` class whose tests must remain green.

## 3. Instructions

1. Open `assets/fbk-scripts/tests/test_gates_breakdown.py`.

2. Add a module-level helper `make_minimal_spec(acs)` that builds spec text:
   ```python
   def make_minimal_spec(acs):
       ac_lines = "\n".join(f"- {ac}: Requirement" for ac in acs)
       return f"## Acceptance criteria\n{ac_lines}\n"
   ```

3. Add a helper `make_cross_cutting_manifest(ac="AC-01")` that returns a manifest dict with one test-only task covering the AC, where the task has `"slice_shape": "cross-cutting"` and type `"test"` — no impl task:
   ```python
   def make_cross_cutting_manifest(ac="AC-01"):
       return {
           "category": "feature",
           "tasks": [{
               "id": "task-01",
               "title": "Test cross-cutting AC",
               "file": "task-01.md",
               "type": "test",
               "wave_id": 1,
               "dependencies": [],
               "covers": [ac],
               "model": "Haiku",
               "status": "not_started",
               "slice_shape": "cross-cutting"
           }]
       }
   ```

4. Add a helper `make_contract_preserving_manifest(ac="AC-01")` that returns a manifest with one impl task covering the AC, `"slice_shape": "contract-preserving"`, no new test task. The impl task has no code files in its task file body (or uses a mock with a justification note about locked existing tests):
   ```python
   def make_contract_preserving_manifest(ac="AC-01"):
       return {
           "category": "feature",
           "tasks": [{
               "id": "task-01",
               "title": "Impl contract-preserving change",
               "file": "task-01.md",
               "type": "implementation",
               "wave_id": 1,
               "dependencies": [],
               "covers": [ac],
               "model": "Haiku",
               "status": "not_started",
               "slice_shape": "contract-preserving"
           }]
       }
   ```

5. Write class `TestSliceShapeAwareness` with these tests:

   Note on the manifest-present signal: because the gate's pre-lock-verdict check fires whenever slice metadata is present, every slices-bearing breakdown that is meant to PASS must also carry the manifest-present signal — a `"test-hashes.json"` key in `task_files` (value can be a minimal manifest JSON string such as `'{"files": {}, "computed_at": "2026-01-01T00:00:00Z"}'`). Add this key to the `task_files` of every passing slice-shape fixture below. A module-level constant like `MANIFEST_ENTRY = {"test-hashes.json": '{"files": {}, "computed_at": "2026-01-01T00:00:00Z"}'}` merged into each passing fixture's `task_files` keeps these readable.

   - `test_cross_cutting_test_only_slice_passes()`: Use `make_minimal_spec(["AC-01"])`, `make_cross_cutting_manifest("AC-01")`, task files `{"task-01.md": "## Files to create\n- `test_ac01.py`", **MANIFEST_ENTRY}`. Call `validate_breakdown`. Assert `result["result"] == "pass"`. (This was previously failing because check #1 required an impl task for every AC — cross-cutting exempts it.)

   - `test_contract_preserving_impl_without_new_test_passes()`: Use `make_minimal_spec(["AC-01"])`, `make_contract_preserving_manifest("AC-01")`, task files `{"task-01.md": "## Files to create\n- `impl.py`\n\nLocks existing tests; no new test task needed (contract-preserving slice).", **MANIFEST_ENTRY}`. Assert `result["result"] == "pass"`. (Was previously failing because check #8 required a test task for every code-modifying impl.)

   - `test_contract_evolving_missing_retired_tests_list_fails()`: Build manifest with a `contract-evolving` slice task (impl type) but no `"retired_tests"` field. Assert `result["result"] == "fail"` and at least one failure mentioning "retired" or "contract-evolving". (Include `MANIFEST_ENTRY` so the only failure under test is the missing retired-tests list, not the manifest-presence check.)

   - `test_contract_evolving_with_retired_tests_passes()`: Same as above but add `"retired_tests": [{"file": "test_old.py", "rationale": "API changed"}]` to the task. Include `MANIFEST_ENTRY` in `task_files`. Assert pass (assuming AC coverage is otherwise complete — provide a matching test task in the manifest or use `category: "testing-infrastructure"` to avoid check #8).

   - `test_cross_cutting_with_impl_task_fails()`: Build a cross-cutting manifest that also includes an impl task for the same AC. Assert fail — cross-cutting ⇒ no impl task is the invariant.

   - `test_slices_breakdown_missing_test_lock_manifest_fails()`: Build a slices-bearing breakdown (any slice metadata present — reuse `make_cross_cutting_manifest("AC-01")` with task file `{"task-01.md": "## Files to create\n- `test_ac01.py`"}`) but supply NO `test-hashes.json` entry in `task_files`. Call `validate_breakdown`. Assert `result["result"] == "fail"` and at least one failure mentioning "test-lock manifest" or "test-hashes.json" or "pre-lock". (The pre-lock test-review verdict is verified by manifest presence; a slices breakdown with no manifest means the pre-lock verdict was not accepted.)

   - `test_slices_breakdown_with_test_lock_manifest_passes()`: Same slices-bearing breakdown, but add the manifest-present signal: include a `"test-hashes.json"` key in `task_files` (e.g. `{"task-01.md": "## Files to create\n- `test_ac01.py`", "test-hashes.json": '{"files": {}, "computed_at": "2026-01-01T00:00:00Z"}'}`). Call `validate_breakdown`. Assert `result["result"] == "pass"` (cross-cutting AC needs no impl task; manifest present satisfies the pre-lock-verdict check). This pairs with the missing-manifest test to prove the presence check is load-bearing.

6. Write class `TestBounceBackMarkerDetection`:

   - `test_unresolved_bounce_back_in_task_file_fails()`: Build a valid manifest with matching test+impl tasks. Include `"<!-- BOUNCE-BACK: spec section X is under-specified -->"` in one task file body. Assert `result["result"] == "fail"` and failure mentions "bounce" or "BOUNCE-BACK".

   - `test_no_bounce_back_marker_passes()`: Same setup without the marker. Assert pass.

7. Write class `TestLegacyBreakdownUnchanged`:

   - `test_legacy_no_slice_metadata_passes_same_as_before()`: Take the existing `test_valid_breakdown_passes` setup (copied verbatim, no slice metadata). Assert `result["result"] == "pass"` — backward compat is preserved.

   - `test_legacy_uncovered_ac_still_fails()`: Take the existing `test_uncovered_ac_detected` setup (copied verbatim, no slice metadata). Assert fail — the existing check still fires when slice metadata is absent.

## 4. Files to create/modify

- `assets/fbk-scripts/tests/test_gates_breakdown.py` (modify)

## 5. Test requirements

11 new test methods across 3 new classes (7 in `TestSliceShapeAwareness`, 2 in `TestBounceBackMarkerDetection`, 2 in `TestLegacyBreakdownUnchanged`). Existing class `TestBreakdownGateValidation` (6 tests) is unchanged.

Failing before implementation: cross-cutting pass test (`test_cross_cutting_test_only_slice_passes`) will fail because the current check #1 rejects the test-only case; contract-preserving pass test will fail because check #8 rejects the no-new-test case; contract-evolving retired-tests check is new code not yet present; the missing-manifest test (`test_slices_breakdown_missing_test_lock_manifest_fails`) will not yet fail-for-the-right-reason because the manifest-presence check is new code; bounce-back check is new code.

The two legacy-behavior tests pass immediately (the existing behavior is unchanged for no-slice-metadata manifests).

## 6. Acceptance criteria

Covers AC-05 (cross-cutting and contract-preserving shape cases pass; contract-evolving retired-tests enforcement; pre-lock test-review verdict verified by test-lock manifest presence — a slices breakdown missing its manifest fails, one with it passes), AC-06 (bounce-back marker detection), and verifies backward compat for no-slice-metadata manifests.

## 7. Model

Sonnet

## 8. Wave

Wave 2
