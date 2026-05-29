---
id: task-09
type: test
wave: 2
covers: [AC-03, AC-24]
files_to_create:
  - assets/fbk-scripts/tests/test_gates_design.py
completion_gate: "tests compile and fail before implementation"
---

## 1. Objective

Creates `assets/fbk-scripts/tests/test_gates_design.py`, a pytest unit test verifying the design gate enforces bidirectional manifest↔directory consistency in both directions and combined, requires a decomposition rationale, requires a non-zero "Decisions recorded" count, fails on open-critical fresh-eyes, runs injection scan, and guards against missing paths.

## 2. Context

The `design.py` gate (new module, subcommand `design-gate`) validates:

1. **Manifest present**: `ai-docs/<feature>/design-manifest.md` exists.
2. **Bidirectional check (both directions)**:
   - Forward: every page listed in the manifest resolves to a file at `ai-docs/<feature>/design/<slug>.md`
   - Backward: every `.md` file under `ai-docs/<feature>/design/` appears in the manifest
   - A combined failure (both forward and backward drift simultaneously) must report BOTH failures, not only the first.
3. **Decomposition rationale present**: the manifest (or a design page) contains a section or line providing decomposition rationale.
4. **"Decisions recorded" count non-zero**: the manifest contains a line matching `Decisions recorded:` followed by a non-zero integer.
5. **Injection scan**: runs `detect_injections` on the design pages and manifest; emits `injection_warnings` count.
6. **Semantic anchor**: `fresh-eyes-design.md` is present with no open critical observations.
7. **Path guard (AC-24)**: exits 2 on missing feature directory; binary files degrade gracefully.

Import the pure function as `validate_design(feature_dir: str) -> dict` (following the `validate_breakdown` convention). The JSON result shape: `{"gate": "design", "result": "pass"|"fail", "failures": [...], "injection_warnings": N}`.

No mocks. Real temp files via `tmp_path`.

## 3. Instructions

1. Create `assets/fbk-scripts/tests/test_gates_design.py`.

2. Import:
   ```python
   import json, subprocess, sys, pytest
   from pathlib import Path
   ```
   And attempt:
   ```python
   try:
       from fbk.gates.design import validate_design
   except ImportError:
       validate_design = None
   ```
   At the start of each test that calls `validate_design`, check `if validate_design is None: pytest.skip("fbk.gates.design not yet implemented")`.

3. Write a `make_design_dir(tmp_path, slugs=("overview", "module-shape"))` helper that creates:
   - `tmp_path / "ai-docs" / "sample" / "design-manifest.md"` — lists the slugs as `- design/overview.md`, `- design/module-shape.md`; includes `Decomposition rationale: vertical slices by capability boundary`; includes `Decisions recorded: 2`.
   - A `design/` subdirectory with `overview.md` and `module-shape.md`, each with `# Overview` and at least one line of content.
   - `tmp_path / "ai-docs" / "sample" / "fresh-eyes-design.md"` — `## Critical` section empty, `## Substantive` with one entry.
   Returns `(tmp_path, tmp_path / "ai-docs" / "sample")`.

4. Write class `TestDesignGatePassesFull`:
   - `test_well_formed_design_artifacts_pass(tmp_path)`: build via helper. Assert `result["result"] == "pass"` and `result["injection_warnings"] >= 0`.

5. Write class `TestManifestToDirDrift`:
   - `test_manifest_lists_nonexistent_page_fails(tmp_path)`: build helper. Add `- design/missing-page.md` to manifest but do NOT create the file. Assert fail, failure mentions `missing-page.md`.
   - This is the forward-drift case (manifest→file).

6. Write class `TestDirToManifestDrift`:
   - `test_unlisted_page_in_design_dir_fails(tmp_path)`: build helper. Create `design/unlisted.md` under the design dir but do NOT add it to the manifest. Assert fail, failure mentions `unlisted.md`.
   - This is the backward-drift case (file→manifest).

7. Write class `TestBothDirectionsDrift`:
   - `test_both_directions_reports_both_failures(tmp_path)`: build helper. Add an unlisted entry to the manifest AND create an unlisted file in the directory (two separate drift items). Assert `result["result"] == "fail"`. Assert `len(result["failures"]) >= 2`. Assert at least one failure mentions the missing file (forward drift) and at least one mentions the unlisted file (backward drift). This ensures the gate does not short-circuit on the first failure.

8. Write class `TestDecompositionRationale`:
   - `test_missing_decomposition_rationale_fails(tmp_path)`: build helper, remove the `Decomposition rationale:` line from `design-manifest.md`. Assert fail.
   - `test_decomposition_rationale_present_passes(tmp_path)`: standard helper. Assert pass (rationale present).

9. Write class `TestDecisionsRecordedCount`:
   - `test_zero_decisions_recorded_fails(tmp_path)`: write `Decisions recorded: 0`. Assert fail.
   - `test_absent_decisions_recorded_fails(tmp_path)`: omit `Decisions recorded:` entirely. Assert fail.
   - `test_nonzero_decisions_recorded_passes(tmp_path)`: write `Decisions recorded: 2`. Assert pass.

10. Write class `TestFreshEyesGate`:
    - `test_open_critical_design_observation_fails(tmp_path)`: write `fresh-eyes-design.md` with non-empty `## Critical` section. Assert fail.
    - `test_empty_critical_section_passes(tmp_path)`: `## Critical` empty. Assert pass.

11. Write class `TestInjectionScan`:
    - `test_injection_in_design_page_emits_warning(tmp_path)`: inject `"ignore previous instructions"` into one design page. Assert `result["injection_warnings"] >= 1`.

12. Write class `TestPathGuard`:
    - `test_missing_feature_dir_exits_2(tmp_path)`: call gate via subprocess with non-existent path. Assert `returncode == 2`.
    - `test_binary_manifest_degrades_gracefully(tmp_path)`: write `design-manifest.md` as binary garbage bytes. Call gate. Assert no traceback exit (returncode 0 or 2, not None; response is valid JSON or returncode 2).

## 4. Files to create/modify

- `assets/fbk-scripts/tests/test_gates_design.py` (create)

## 5. Test requirements

All pytest unit tests. No mocks. Real temp files.

Key assertions that are structurally new (not covered by any existing gate test):
- Both-directions simultaneous drift reports both failures (not just first).
- Zero/absent "Decisions recorded" count fails.
- Decomposition rationale required.

Failing before implementation: all tests that call `validate_design` (skipped via the ImportError guard).

## 6. Acceptance criteria

Covers AC-03 (bidirectional manifest check in both directions and combined, decomposition rationale, decisions count, fresh-eyes semantic anchor, injection scan), AC-24 (exits 2 on missing path, degrades on binary).

## 7. Model

Sonnet

## 8. Wave

Wave 2
