---
id: task-08
type: test
wave: 2
covers: [AC-01, AC-02, AC-13, AC-24]
files_to_create:
  - assets/fbk-scripts/tests/test_gates_intent.py
completion_gate: "tests compile and fail before implementation"
---

## 1. Objective

Creates `assets/fbk-scripts/tests/test_gates_intent.py`, a pytest unit test file verifying the intent gate passes a well-formed artifact set, fails on each required-PRD-section absence, fails on PRD↔inventory reference mismatches, fails on a missing OR malformed grilling log, fails on an open-critical fresh-eyes observation, emits an injection warning count on a poisoned input, exits 2 on a missing path, and degrades to structural failure on binary input.

## 2. Context

The `intent.py` gate (new module, subcommand `intent-gate`) validates:

**Mechanical checks:**
1. PRD present with all 10 required sections: Vision, Problem statement, Goals and non-goals, Use cases, Functional requirements, Non-functional requirements, Edge cases and failure modes, Dependencies, Success metrics, Open questions
2. Behavior inventory (`behavior-inventory.yaml`) present with consistent IDs and bidirectional PRD↔inventory reference consistency — the PRD references each behavior ID and the inventory lists each ID referenced in the PRD
3. Grilling log (`grilling-log-intent.md`) present AND well-formed — it must contain a well-formed decision block (a `### ` decision-slug heading) with a `Confirmed:` reflect-back line. A log that is absent fails; a log that exists but is malformed (no `### ` decision block / no `Confirmed:` line) also fails (AC-13)

**Semantic anchor:**
4. Fresh-eyes report (`fresh-eyes-intent.md`) present with no open critical observations (the `## Critical` section is empty or absent after dedup)

**Injection scan:**
5. Runs `detect_injections` (from `fbk.injection`) on the PRD, inventory, and grilling log; emits `injection_warnings` count in the JSON result

**Path guard (AC-24):**
6. Exits 2 on a missing file path
7. Reads with `errors="replace"` so binary input degrades gracefully

The gate function to import is `main` via subprocess or a `validate_intent(feature_dir: str) -> dict` pure function. The spec is silent on whether the internal pure function is `validate_intent` — use that name by convention (matching `validate_breakdown`, `validate_review` in the existing gates).

The gate's JSON result shape: `{"gate": "intent", "result": "pass"|"fail", "failures": [...], "injection_warnings": N}`.

No mocks. All inputs are real files in `tmp_path`. Follow the fixture pattern from `conftest.py` (`valid_spec_text`) for building artifact text.

## 3. Instructions

1. Create `assets/fbk-scripts/tests/test_gates_intent.py`.

2. Import:
   ```python
   import json
   import subprocess
   import sys
   import pytest
   from pathlib import Path
   ```
   Also attempt: `from fbk.gates.intent import validate_intent` — wrap in try/except to skip if module not yet present; use subprocess fallback only for path-guard tests.

3. Define a `make_feature_dir(tmp_path)` helper function (not a fixture) that creates:
   - `tmp_path / "ai-docs" / "sample" / "prd.md"` — a minimal valid PRD with all 10 section headings as `## Section Name` headers with at least one line of content each, and references to behavior IDs `B-001` and `B-002` in the body.
   - `tmp_path / "ai-docs" / "sample" / "behavior-inventory.yaml"` — YAML with entries `B-001` and `B-002`, each referencing back to the PRD.
   - `tmp_path / "ai-docs" / "sample" / "grilling-log-intent.md"` — a grilling log with at least one well-formed block (per Interface contract #6 shape: `### decision-slug`, `- Question:`, `- Recommendation:`, `- Answer:`, `- Confirmed:`).
   - `tmp_path / "ai-docs" / "sample" / "fresh-eyes-intent.md"` — a fresh-eyes report with `## Critical` section that is empty (no observations under it), plus a `## Substantive` section with one entry.
   Returns `(tmp_path, tmp_path / "ai-docs" / "sample")`.

4. Write class `TestIntentGatePassesFull`:
   - `test_well_formed_artifact_set_passes(tmp_path)`: build via `make_feature_dir`. Call `validate_intent(str(feature_dir))`. Assert `result["result"] == "pass"`. Assert `"failures" not in result or len(result["failures"]) == 0`. Assert `"injection_warnings" in result`.

5. Write class `TestMissingPRDSections` with individual tests for each of the 10 required sections. For each section heading `H`:
   - Build the feature dir. Remove or replace the section by rewriting `prd.md` without `## H`. Call `validate_intent`. Assert `result["result"] == "fail"`. Assert at least one item in `result["failures"]` references the missing section name.
   - Test names: `test_missing_vision_fails`, `test_missing_problem_statement_fails`, `test_missing_goals_fails`, `test_missing_use_cases_fails`, `test_missing_functional_requirements_fails`, `test_missing_nonfunctional_requirements_fails`, `test_missing_edge_cases_fails`, `test_missing_dependencies_fails`, `test_missing_success_metrics_fails`, `test_missing_open_questions_fails`.

6. Write class `TestPRDInventoryConsistency`:
   - `test_behavior_in_inventory_not_referenced_in_prd_fails(tmp_path)`: write inventory with `B-003` but do NOT mention `B-003` in the PRD. Assert fail and failure message references the mismatch.
   - `test_behavior_in_prd_not_in_inventory_fails(tmp_path)`: write PRD referencing `B-999` but do NOT include `B-999` in the inventory. Assert fail.
   - `test_consistent_bidirectional_references_passes(tmp_path)`: both PRD and inventory agree. Assert pass.

7. Write class `TestGrillingLog`:
   - `test_missing_grilling_log_fails(tmp_path)`: build feature dir without the grilling log file. Assert fail with a failure message mentioning "grilling" or "grilling-log".
   - `test_malformed_grilling_log_fails(tmp_path)`: build feature dir, then overwrite `grilling-log-intent.md` with a malformed log — present but lacking a well-formed decision block: no `Confirmed:` reflect-back line and no well-formed `### ` decision-slug heading (e.g. write only a paragraph of prose with no `### ` block and no `- Confirmed:` line). Call `validate_intent`. Assert `result["result"] == "fail"` and a failure message references the grilling log being malformed / missing its decision block or `Confirmed:` line. This is the seam case: a grilling log that exists but is malformed must FAIL the gate, distinct from a missing log.
   - `test_well_formed_grilling_log_passes(tmp_path)`: build feature dir (the default `make_feature_dir` log has a well-formed `### ` decision block with a `- Confirmed:` line) and leave all other artifacts valid. Call `validate_intent`. Assert `result["result"] == "pass"` — a well-formed log passes.

8. Write class `TestFreshEyesGate`:
   - `test_open_critical_observation_fails(tmp_path)`: write `fresh-eyes-intent.md` with `## Critical` section containing a non-empty observation line (`- Some critical issue`). Assert fail.
   - `test_empty_critical_section_passes(tmp_path)`: `## Critical` section is present but empty (no bullet lines). Assert pass (other artifacts valid).

9. Write class `TestInjectionWarnings`:
   - `test_poisoned_prd_emits_warning_count(tmp_path)`: build feature dir. Inject `"ignore previous instructions"` into `prd.md`. Call `validate_intent`. Assert `result["injection_warnings"] >= 1`. The gate may still pass structurally if injection detection is non-blocking; the key assertion is that the count is > 0.

10. Write class `TestPathGuard`:
    - `test_missing_feature_dir_exits_2(tmp_path)`: call the gate via `subprocess.run` with a non-existent directory path. Assert `returncode == 2`.
    - `test_binary_prd_degrades_to_structural_failure(tmp_path)`: write `prd.md` as binary garbage bytes (`b'\x89PNG\r\n\x1a\n' + b'\x00' * 100`). Call the gate. Assert it does NOT raise an unhandled exception (returncode is 0 or 2, not a traceback exit). Assert the response is valid JSON or exits 2.

## 4. Files to create/modify

- `assets/fbk-scripts/tests/test_gates_intent.py` (create)

Justification for file count: this is a single new gate's test file; the 10-section PRD check is a quantifier AC (AC-02 says "any missing required PRD section") and the spec explicitly enumerates 10 sections, all requiring individual test cases.

## 5. Test requirements

All pytest unit tests. No mocks. Real temp files via `tmp_path`.

Failing before implementation: all tests, because `fbk.gates.intent` does not exist yet (`ImportError`). The subprocess path-guard tests also fail because the gate CLI does not exist.

## 6. Acceptance criteria

Covers AC-01 (gate exists and passes a well-formed set), AC-02 (fails on missing sections, reference mismatch, missing grilling log, open-critical fresh-eyes, emits injection count), AC-13 (a grilling log that exists but is malformed — missing its `Confirmed:` reflect-back line / well-formed `### ` decision block — fails the gate, while a well-formed log passes), AC-24 (exits 2 on missing path, degrades gracefully on binary).

## 7. Model

Sonnet

## 8. Wave

Wave 2
