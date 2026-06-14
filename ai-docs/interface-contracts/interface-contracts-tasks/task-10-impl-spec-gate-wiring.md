---
id: task-10
type: implementation
wave: 2
covers: [AC-13, AC-17]
files_to_modify:
  - assets/fbk-scripts/fbk/gates/spec.py
test_tasks: [task-09]
completion_gate: "task-09 tests pass"
dependencies: [task-02]
---

# task-10 — Wire the four contract checks into the spec gate

## 1. Objective

Produces an edit to `assets/fbk-scripts/fbk/gates/spec.py` that imports the four check functions from `fbk.gates.contracts` at module top level and calls all four inside the `if scope == "feature":` branch, after the existing `check_slices` call, accumulating their failures into the shared `fails` list without short-circuiting — preserving the gate's existing exit-code and JSON-result contract.

## 2. Context

Implementation task for the `spec-gate-wiring` slice (contract-evolving discipline). This is an **orchestrator task**: `spec.py` is the file that wires the gate's checks together and produces the gate's CLI / exit-code / JSON-result contract. It is higher-risk than a leaf module change, so it carries a dedicated wiring checklist (§5 below) and routes to Sonnet.

This task is Wave 2 because it depends on task-02 (Wave 1), which creates `fbk/gates/contracts.py` and the four functions. Without that module the import fails at startup. Task-09 (the paired test, also Wave 2) migrates the `test_gates_spec.py` fixtures and adds wiring-proof tests; this task makes those wiring tests pass.

**Activation is unconditional.** The four checks run on every feature spec — there is no backward-compat hinge. The structural check treats a missing `## Interface contracts` section as a failure, and the design-anchor check treats a missing `design/contracts.md` as a failure. Task-09 owns the fixture migration that keeps the existing pass-expecting tests green under this new activation; this task touches ONLY `spec.py` — do not edit any test file here.

**The pre-existing contract to protect (IF-S-01).** `spec.py` exposes a CLI/result contract: `python3 fbk.py spec-gate <spec-path>` exits `0` on pass and `2` on fail, and prints `{"gate": "spec", "result": "pass"|"fail", ...}` JSON to stdout. This feature adds four checks to the feature-scope branch but must NOT change the exit-code behavior, the JSON shape, or the dispatcher contract. The four checks accumulate into the same `fails` list the existing checks use, so they flow through the existing failure-printing and exit path unchanged. Do not add a new exit path, a new result key, or a short-circuit.

**What already exists in `spec.py` (read it to confirm).** The feature-scope branch (`if scope == "feature":`) runs the section checks, `check_open_questions`, `_check_ac_format`, `_check_testing_strategy_traceability`, then computes `feature_dir = pathlib.Path(spec_path).parent`, loads the behavior inventory, and calls `fails.extend(check_slices(spec_text, inventory_behaviors))`. The variable `feature_dir` (a `pathlib.Path`) is already in scope at that point and `spec_text` is already read. The existing top-level imports (`from fbk.injection import detect_injections`, `from fbk.slices import TEST_DISCIPLINES`) are the precedent for the new top-level import.

## 3. Instructions

1. Add the top-level import block (after the existing `from fbk.slices import TEST_DISCIPLINES` line), using the exact integration snippet from the design's gate-checks page:
   ```python
   from fbk.gates.contracts import (
       check_interface_contracts_structure,
       check_design_anchor,
       check_ac_coverage,
       check_seam_coverage,
   )
   ```
   Completion: the import appears at module top level; `python3 -c "import fbk.gates.spec"` succeeds (contracts.py exists from task-02).

2. In the `if scope == "feature":` branch, immediately AFTER the existing `fails.extend(check_slices(spec_text, inventory_behaviors))` line, add the four calls in this exact order, accumulating into the same `fails` list with no short-circuit:
   ```python
   fails.extend(check_interface_contracts_structure(spec_text))
   fails.extend(check_design_anchor(spec_text, str(feature_dir)))
   fails.extend(check_ac_coverage(spec_text))
   fails.extend(check_seam_coverage(spec_text))
   ```
   Note: `check_design_anchor` receives `str(feature_dir)` (the `feature_dir` `Path` is already computed earlier in the branch — convert to `str`). The other three receive `spec_text` only. Completion: the four `fails.extend(...)` calls appear in order after the `check_slices` call, inside the feature-scope branch.

3. Do not change anything else: the failure-printing loop, the `sys.exit(2)` path, the `result` dict shape, the `print(json.dumps(result))` line, the audit logging, and the project-scope branch all stay exactly as they are. Completion: a `git diff` of `spec.py` shows only the import block and the four added call lines — no other hunks.

4. Run `python3 -m pytest tests/test_gates_spec.py` from `assets/fbk-scripts/` and confirm the full suite passes green — both the migrated existing tests (task-09's fixtures now provide the no-contracts section and a `design/contracts.md`) and the new wiring-proof tests.

## 4. Files to create/modify

- Modify: `assets/fbk-scripts/fbk/gates/spec.py`

Do not touch `fbk/gates/contracts.py` (task-02), any test file (task-09), or any other file.

## 5. Wiring checklist (orchestrator task)

This is the dedicated wiring checklist required for an orchestrator-file change. Verify each item:

- **Import**: exactly the four names `check_interface_contracts_structure`, `check_design_anchor`, `check_ac_coverage`, `check_seam_coverage` from `fbk.gates.contracts`, at module top level, in one import block. Nothing else imported from that module.
- **Call site**: all four calls inside `if scope == "feature":`, AFTER `fails.extend(check_slices(...))`, in the order structural → design-anchor → AC-coverage → seam-coverage.
- **Argument wiring**: `check_design_anchor` gets `(spec_text, str(feature_dir))`; the other three get `(spec_text)`. `feature_dir` is the already-computed `pathlib.Path(spec_path).parent`.
- **Accumulation**: every call is `fails.extend(...)` into the existing `fails` list — no separate list, no short-circuit, no early return.
- **No contract change**: exit codes (0 pass / 2 fail), the `result` JSON shape `{"gate": "spec", "result": ..., ...}`, stdout/stderr routing, and audit logging are untouched (regression-protects IF-S-01).
- **No test-file edits**: this task modifies only `spec.py`; the fixture migration is task-09's.
- **No project-scope change**: the `else` (project-scope) branch is not touched.

## 6. Acceptance criteria

- Primary: task-09's tests pass (green phase) — both migrated existing tests and the new wiring-proof tests.
- Covers AC-13. Also contributes the implementation for AC-17: wiring the four checks into the gate is what makes the assembled gate produce the end-to-end behavior the dogfood slice verifies (task-11). AC-17's implementation is distributed across the gate module (task-02) and this wiring; this task is the terminal integration point, so AC-17 is attributed here for coverage. The end-to-end verification itself lives in task-11.
- The four functions are imported at module top level and called in the feature-scope branch after `check_slices`, accumulating into `fails` without short-circuit.
- The gate's exit-code and JSON-result contract is unchanged (IF-S-01 preserved).
- The diff touches only the import block and the four call lines.

## 7. Model

Sonnet

Rationale: orchestrator-file change — `spec.py` wires the gate together and owns the externally-relied-on CLI/exit/JSON contract. The task-compilation rule routes orchestrator tasks to Sonnet minimum regardless of size. The risk is in preserving the existing contract while adding the calls in the right place with the right arguments. Sonnet.

## 8. Wave

Wave 2

Depends on task-02 (creates `fbk/gates/contracts.py` and the four functions). Build-order edge: this task imports that module, so it must run after task-02 completes.
