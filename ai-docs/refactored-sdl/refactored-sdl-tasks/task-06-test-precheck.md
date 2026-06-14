---
id: task-06
type: test
wave: 1
covers: [AC-12]
files_to_create:
  - assets/fbk-scripts/tests/test_precheck.py
completion_gate: "tests compile and fail before implementation"
---

## 1. Objective

Creates `assets/fbk-scripts/tests/test_precheck.py`, a pytest unit test verifying that a capability-entry prerequisite probe returns a structured result naming the missing artifact and the upstream phase for each of the four upstream-missing cases, without hard-failing.

## 2. Context

AC-12 requires that when a phase is invoked without its upstream artifacts, the system names the specific missing artifact and the upstream phase to run, and does not hard-block. The spec notes this as a compilation decision: the behavior lives in a new `fbk/precheck.py` module with a function:

```python
def check_prerequisites(phase: str, feature_dir: str) -> dict
```

The function is non-blocking (never calls `sys.exit`). It returns a dict of this shape:
```python
{
  "phase": "<requested-phase>",
  "ready": True | False,
  "missing": [  # empty if ready
    {"artifact": "<artifact-name>", "upstream_phase": "<phase-name>"}
  ]
}
```

The four upstream-missing cases the test must cover (per the spec's §Testing strategy). `feature_dir` is the actual feature directory (not a project root); artifacts are placed directly under it:
1. **intent-missing-at-design**: caller requests `design` phase, `<feature_dir>/prd.md` is absent → returns missing artifact `prd.md`, upstream phase `intent`
2. **design-missing-at-spec**: caller requests `spec` phase, `<feature_dir>/design-manifest.md` is absent → returns missing artifact `design-manifest.md`, upstream phase `design`
3. **spec-missing-at-breakdown**: caller requests `breakdown` phase, `<feature_dir>/<feature>-spec.md` is absent → returns missing artifact `<feature>-spec.md`, upstream phase `spec`
4. **impl-missing-at-code-review**: caller requests `code-review` phase, `<feature_dir>/implementation/` directory is absent → returns missing artifact `implementation/`, upstream phase `implement`

When all prerequisites are present, `ready` is `True` and `missing` is empty.

`fbk/precheck.py` does not yet exist. The import will fail (ImportError) before implementation, giving the correct red state.

No mocks. Use `tmp_path` pytest fixture to create real temp directories representing feature directories.

## 3. Instructions

1. Create `assets/fbk-scripts/tests/test_precheck.py`.

2. Add this import at the top:
   ```python
   import pytest
   from pathlib import Path
   from fbk.precheck import check_prerequisites
   ```
   This import raises `ImportError` before the module exists — correct red state.

3. Add a fixture `feature_dir(tmp_path)` that creates an explicit feature subdirectory (e.g. `tmp_path / "sample"`) and returns that path (the actual feature directory) along with the feature name `"sample"` as a tuple:
   ```python
   @pytest.fixture
   def feature_dir(tmp_path):
       feature = tmp_path / "sample"
       feature.mkdir()
       return feature, "sample"
   ```
   Note: `feature_dir[0]` is the actual feature directory and is what gets passed as the second argument to `check_prerequisites`. Upstream artifacts are placed directly under `feature_dir[0]`, not under `tmp_path / "ai-docs" / "sample"`.

4. Write a class `TestPrerequisiteCheckNonBlocking` with one test:
   - `test_check_never_calls_sys_exit(feature_dir, monkeypatch)`: monkeypatch `sys.exit` to raise `AssertionError`. Call `check_prerequisites("design", str(feature_dir[0]))` with an empty feature dir. Assert no `AssertionError` is raised (i.e., the function never called `sys.exit`). Assert the return value is a dict.

5. Write a class `TestIntentMissingAtDesign` with these tests (all use `feature_dir` fixture, feature name `"sample"`):
   - `test_design_fails_when_prd_missing(feature_dir)`: feature dir has no `prd.md`. Call `check_prerequisites("design", str(feature_dir[0]))`. Assert `result["ready"] is False`. Assert any item in `result["missing"]` has `"artifact"` matching `"prd.md"` and `"upstream_phase"` matching `"intent"`.
   - `test_design_passes_when_prd_present(feature_dir)`: write `feature_dir[0] / "prd.md"` with content `"# PRD"`. Call `check_prerequisites("design", str(feature_dir[0]))`. Assert `result["ready"] is True` and `result["missing"] == []`.

6. Write a class `TestDesignMissingAtSpec`:
   - `test_spec_fails_when_design_manifest_missing(feature_dir)`: no `design-manifest.md` under `feature_dir[0]`. Assert `result["ready"] is False`. Assert missing artifact `"design-manifest.md"`, upstream phase `"design"`.
   - `test_spec_passes_when_design_manifest_present(feature_dir)`: write `feature_dir[0] / "design-manifest.md"`. Assert `result["ready"] is True`.

7. Write a class `TestSpecMissingAtBreakdown`:
   - `test_breakdown_fails_when_spec_missing(feature_dir)`: no `sample-spec.md` under `feature_dir[0]`. Assert `result["ready"] is False`. Assert missing artifact name ends with `-spec.md`, upstream phase `"spec"`.
   - `test_breakdown_passes_when_spec_present(feature_dir)`: write `feature_dir[0] / "sample-spec.md"`. Assert `result["ready"] is True`.

8. Write a class `TestImplMissingAtCodeReview`:
   - `test_code_review_fails_when_impl_absent(feature_dir)`: no `implementation/` directory under `feature_dir[0]`. Call `check_prerequisites("code-review", str(feature_dir[0]))`. Assert `result["ready"] is False`. Assert missing artifact `"implementation/"`, upstream phase `"implement"`.
   - `test_code_review_passes_when_impl_present(feature_dir)`: create `feature_dir[0] / "implementation"` directory. Assert `result["ready"] is True`.

9. Write a class `TestReturnStructure`:
   - `test_return_dict_has_required_keys(feature_dir)`: call with an incomplete feature dir. Assert the returned dict has keys `"phase"`, `"ready"`, `"missing"`. Assert `result["missing"]` is a list. Assert each item in `result["missing"]` has keys `"artifact"` and `"upstream_phase"`.

## 4. Files to create/modify

- `assets/fbk-scripts/tests/test_precheck.py` (create)

## 5. Test requirements

All pytest unit tests. No mocks except the `sys.exit` monkeypatch for the non-blocking assertion. Real temp directories via `tmp_path`.

10 test methods across 5 classes covering the 4 upstream-missing cases plus the return structure and non-blocking invariant.

## 6. Acceptance criteria

Covers AC-12: for each of the four upstream-missing cases, the probe returns a structured dict naming the missing artifact and the upstream phase, without calling `sys.exit`.

## 7. Model

Sonnet

## 8. Wave

Wave 1
