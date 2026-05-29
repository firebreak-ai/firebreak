---
id: task-10
type: test
wave: 2
covers: [AC-04, AC-21]
files_to_modify:
  - assets/fbk-scripts/tests/test_gates_spec.py
completion_gate: "tests compile and fail before implementation"
---

## 1. Objective

Modifies `assets/fbk-scripts/tests/test_gates_spec.py` to add tests asserting the spec gate's slice-awareness behavior: backward-compatible no-slices pass, adversarial-prose non-triggering, per-slice `test-discipline` enforcement, inventory-coverage enforcement, and retention of the existing testing-strategy AC-traceability check for slices-bearing specs.

## 2. Context

The spec gate gains new behavior activated **only** when the spec declares a `## Slices` block. The gate must:
1. Pass a spec with no `## Slices` block identically to today (backward compat — AC-21)
2. NOT activate slice checking when the token `test-discipline` appears only in prose or a code fence, not in a `## Slices` block (the adversarial-prose case — AC-21)
3. Fail a slice that is missing its `test-discipline` field (AC-04)
4. Fail a slice whose `test-discipline` is not in the four-value taxonomy `{new-contract, contract-preserving, contract-evolving, cross-cutting}` (AC-04)
5. Fail when a behavior in the linked inventory is covered by no slice (AC-04)
6. Still require `AC-NN` references in the testing-strategy section of slices-bearing specs (the existing `_check_testing_strategy_traceability` check is retained — AC-04/AC-21)

The gate detects the `## Slices` block as a distinct YAML block, NOT by searching for the bare token `test-discipline` in prose. This hinge must be tested explicitly.

The slice-check tests exercise the gate's **observable output via subprocess** — they run the gate against a temp spec file and assert on its exit code (0 pass / 2 fail) and stderr/stdout. They do NOT import an internal `check_slices` function. The spec does not pin `check_slices` (or any slice-check helper) as public; importing it would couple the test to an implementation detail and break the test on a rename even when behavior is unchanged. Drive the gate the same way `main()` is invoked in production: `python3 .../fbk.py spec-gate <temp-spec-file>` (or `python3 -m fbk spec-gate <temp-spec-file>`), or call `fbk.gates.spec.main` on a temp file path. Follow the existing subprocess/main-on-temp-file pattern in `assets/fbk-scripts/tests/test_gates_spec_injection.py`.

Note: `spec.main()` infers scope from the filename — write temp spec files as `*-spec.md` so the gate treats them as feature specs (a file not ending in `-spec.md`/`-overview.md` exits 2 with a scope error, which would mask the slice behavior under test).

The existing tests in `test_gates_spec.py` import `check_section` and `check_open_questions` from `fbk.gates.spec` — leave those imports and tests unchanged. Do NOT add a `check_slices` import. Before implementation the gate has no slice behavior, so a slices-bearing spec that should fail still exits 0 — that is the correct red state for the new cases.

No mocks. Real temp spec files. Follow the existing class structure in the file.

## 3. Instructions

1. Open `assets/fbk-scripts/tests/test_gates_spec.py`.

2. Ensure the module imports `subprocess` and `sys` (the existing import line for `check_section, check_open_questions` from `fbk.gates.spec` stays as-is). Do NOT import `check_slices` — the slice tests drive the gate through its observable CLI output, not an internal function.

3. Add a `run_spec_gate(tmp_path, spec_text, name="sample-spec.md")` helper local to the test module that writes `spec_text` to `tmp_path / name` (the name must end in `-spec.md` so the gate treats it as a feature spec) and runs the gate via subprocess, returning the `CompletedProcess`:
   ```python
   def run_spec_gate(tmp_path, spec_text, name="sample-spec.md"):
       spec_file = tmp_path / name
       spec_file.write_text(spec_text)
       return subprocess.run(
           [sys.executable, "-m", "fbk", "spec-gate", str(spec_file)],
           capture_output=True, text=True,
       )
   ```
   (If `-m fbk` is not runnable in the test environment, fall back to the dispatcher path: `[sys.executable, str(FBK_PY), "spec-gate", str(spec_file)]`, locating `fbk.py` the same way `test_gates_spec_injection.py` / `test_dispatcher.py` do.) Exit code `0` = pass, `2` = fail; assert on `result.returncode` and on `result.stdout + result.stderr` for substring checks.

   Also introduce a `make_spec_with_slices(discipline="new-contract", covers="B-001", include_slices=True)` helper that builds a minimal valid 8-section feature spec; when `include_slices` is true it embeds a `## Slices` block with one slice entry carrying the given `test-discipline` and `covers` fields, and a `## Testing strategy` section that references `AC-01`. Variants below override individual pieces.

4. Add a class `TestSliceBlockDetection` that tests the hinge logic (which determines whether slice checking activates), via the gate's observable output:

   - `test_no_slices_block_passes_identically()` (regression — AC-21): run the gate on an otherwise-valid spec with NO `## Slices` block. Assert `returncode == 0` (passes identically to today; the slice check is inactive).

   - `test_test_discipline_in_prose_does_not_activate_check()` (adversarial — AC-21): run the gate on an otherwise-valid spec where the bare token `test-discipline` appears ONLY inside prose (`"The test-discipline concept is described here."`) and inside a code fence (`"```yaml\ntest-discipline: new-contract\n```"`), with NO `## Slices` block. Assert `returncode == 0` — the prose/code-fence token does not fire the slice check.

   - `test_slices_block_with_valid_slice_passes()`: run the gate on a spec with a valid `## Slices` block containing one complete well-formed slice. Assert `returncode == 0`.

5. Add a class `TestSliceDisciplineValidation` (AC-04), all via subprocess:

   - `test_slice_missing_test_discipline_fails()`: spec with a `## Slices` block whose one slice omits the `test-discipline:` field. Assert `returncode == 2` and the combined output mentions the slice name and "test-discipline".

   - `test_slice_invalid_test_discipline_fails()`: spec with a slice carrying `test-discipline: unknown-value` (out of taxonomy). Assert `returncode == 2` and output mentions the invalid value or the valid taxonomy values.

   - `test_valid_new_contract_discipline_passes()`: slice with `test-discipline: new-contract`. Assert `returncode == 0`.
   - `test_valid_contract_preserving_discipline_passes()`: slice with `test-discipline: contract-preserving`. Assert `returncode == 0`.
   - `test_valid_contract_evolving_discipline_passes()`: slice with `test-discipline: contract-evolving`. Assert `returncode == 0`.
   - `test_valid_cross_cutting_discipline_passes()`: slice with `test-discipline: cross-cutting`. Assert `returncode == 0`.

6. Add a class `TestInventoryCoverage` (AC-04), via subprocess:

   - `test_behavior_not_covered_by_any_slice_fails()`: build a spec whose linked inventory declares `B-001` but no slice's `covers` field includes it (the spec references `B-001` in the inventory/PRD link but the lone slice covers a different behavior). Assert `returncode == 2` and output mentions `B-001` or "not covered".

   - `test_all_behaviors_covered_passes()`: inventory behavior `B-001` is covered by one slice's `covers` field. Assert `returncode == 0`.

   - `test_empty_inventory_passes()`: a slices-bearing spec with no inventory behaviors to cover. Assert `returncode == 0`.

7. Add a class `TestTestingStrategyRetainedForSliceSpecs` (AC-04/AC-21):

   This verifies the existing testing-strategy AC-traceability check still runs for slices-bearing specs.

   - `test_slices_spec_without_ac_in_testing_strategy_fails(tmp_path)`: build a spec with a valid `## Slices` block AND a `## Testing strategy` section that contains only prose with NO `AC-NN` references. Run the gate via `run_spec_gate`. Assert `returncode == 2` and the combined output mentions "Testing strategy".
   ```python
   def test_slices_spec_without_ac_in_testing_strategy_fails(tmp_path):
       result = run_spec_gate(tmp_path, SLICES_SPEC_WITHOUT_TS_AC)
       assert result.returncode == 2
       assert "Testing strategy" in (result.stdout + result.stderr)
   ```
   Define `SLICES_SPEC_WITHOUT_TS_AC` as a module-level constant: a minimal 8-section feature spec that has a `## Slices` block with one complete valid slice but whose `## Testing strategy` section contains only prose with no `AC-NN` references.

## 4. Files to create/modify

- `assets/fbk-scripts/tests/test_gates_spec.py` (modify)

## 5. Test requirements

14 new test methods across 4 new classes, added to the existing file, all driving the gate via subprocess on temp `*-spec.md` files. Existing tests (`TestCheckSection`, `TestCheckOpenQuestions`) and their imports are unchanged. No `check_slices` import is added.

Failing before implementation: the slice-failure cases (missing/invalid `test-discipline`, uncovered behavior, slices-spec missing testing-strategy AC references) expect `returncode == 2`, but the un-extended gate has no slice behavior and exits 0 — that mismatch is the correct red state. The pass-case and adversarial-prose/no-slices regression cases already exit 0 and stay green (they assert backward-compatible behavior).

## 6. Acceptance criteria

Covers AC-04 (slice `test-discipline` enforcement, taxonomy validation, inventory coverage) and AC-21 (no-slices backward compat, adversarial-prose non-trigger, existing testing-strategy check retained for slices specs).

## 7. Model

Sonnet

## 8. Wave

Wave 2
