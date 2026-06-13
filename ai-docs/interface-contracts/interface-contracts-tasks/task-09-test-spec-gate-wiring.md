---
id: task-09
type: test
wave: 2
covers: [AC-13]
files_to_modify:
  - assets/fbk-scripts/tests/test_gates_spec.py
completion_gate: "tests compile and fail before implementation (red phase before spec.py imports and calls the four checks); migrated fixtures keep the existing pass-expecting tests green only after task-10 wires the gate"
---

# task-09 — Migrate spec-gate fixtures and add wiring-proof tests

## 1. Objective

Modifies `assets/fbk-scripts/tests/test_gates_spec.py` to (a) migrate the existing pass-expecting fixtures so they survive unconditional contract-check activation, and (b) add new tests proving `spec.py` wires the four contract checks in after `check_slices`.

## 2. Context

Test task for the `spec-gate-wiring` slice — the **contract-evolving** slice. The paired implementation task (task-10) edits `fbk/gates/spec.py` to import the four functions from `fbk.gates.contracts` and call them unconditionally in the feature-scope branch after `check_slices`. This test task DEPENDS on `fbk/gates/contracts.py` existing (created by task-02 in Wave 1) because it imports the no-contracts sentence constant from it — hence Wave 2.

**Why the fixture migration is needed (contract-evolving rationale).** Activation is unconditional: once task-10 lands, the structural check treats a missing `## Interface contracts` section as a failure, and the design-anchor check treats a missing `design/contracts.md` as a failure. Every spec the suite currently feeds to `main()` lacks both. Without migration, roughly 14 pass-expecting executions across 11 test methods (one parametrized ×4) would start failing for the *wrong* reason — and worse, the failure-path / sentinel tests (which assert exit code 2 for a *different* reason) would exit 2 because of the missing page while their pass/fail assertion stays green, silently corrupting test intent. The migration makes every spec the helpers produce contract-clean, so each test continues to prove what it claims.

**Retired tests (UPDATE, not delete) — explicit list with per-entry rationale:**

1. `_MINIMAL_VALID_SECTIONS` (module-level constant) — gains a `## Interface contracts` section whose body is the exact no-contracts sentence. Rationale: it is the base every `_make_minimal_spec()` / `make_spec_with_slices()` call builds on; without the section, every pass-expecting test through `run_spec_gate` fails the new structural check. UPDATE the constant in place; do not delete it.
2. `run_spec_gate` helper — writes a no-contracts `design/contracts.md` into its `tmp_path` UNCONDITIONALLY. Rationale: it is the actual file-writer for every gate run; the design-anchor check needs the page on disk for the spec to pass. It does NOT create a `design/` directory today — add `(<feature_dir>/design)` creation. Migrating here (not at each call site) covers all ~14 pass-expecting executions through one edit. UPDATE the helper; do not delete it.
3. `SLICES_SPEC_WITHOUT_TS_AC` (module-level inline constant) — gains the same no-contracts `## Interface contracts` section. Rationale: this constant builds a spec string inline (it does not go through `_MINIMAL_VALID_SECTIONS`), and it is fed to `run_spec_gate` by the testing-strategy-traceability sentinel, which expects exit 2 for a *missing-AC* reason; without the section it would exit 2 for a missing-contracts reason and the sentinel would pass for the wrong reason. UPDATE the constant in place.

The no-contracts sentence must be IMPORTED from `fbk.gates.contracts` as a module constant (e.g. `NO_CONTRACTS_SENTENCE`) — do NOT retype the literal `No new or changed contracts in this feature.` This keeps the check that recognizes the sentence and the fixtures that produce it from drifting by a character. Confirm the constant name matches task-01/task-02.

The existing helpers and their shapes (read the current file): `_MINIMAL_VALID_SECTIONS` (lines ~17-44), `run_spec_gate(tmp_path, spec_text, name=..., inventory_ids=...)` (lines ~67-77, writes the spec file and optional inventory under `tmp_path`), `SLICES_SPEC_WITHOUT_TS_AC` (lines ~81-96). The gate derives `feature_dir` as the spec file's parent (`pathlib.Path(spec_path).parent`), so the `design/contracts.md` must be written under the same `tmp_path` directory the spec file is written into.

## 3. Instructions

1. At the top of `assets/fbk-scripts/tests/test_gates_spec.py`, add `from fbk.gates.contracts import NO_CONTRACTS_SENTENCE` (alongside the existing `from fbk.gates.spec import ...`). State for the agent: this import will fail at red-phase run time if `contracts.py` does not yet exist — that is an acceptable red-phase failure since task-02 (Wave 1) delivers the module before this Wave-2 task runs.
2. **Site A — `_MINIMAL_VALID_SECTIONS`:** append a `## Interface contracts` section whose body is the no-contracts sentence. Because the constant is a plain triple-quoted string and the sentence comes from an import, convert the constant to an f-string or concatenate the imported `NO_CONTRACTS_SENTENCE` so the body reads exactly the sentence. Completion: `_MINIMAL_VALID_SECTIONS` contains the substring `## Interface contracts` and the no-contracts sentence.
3. **Site B — `run_spec_gate`:** after writing `spec_file` (and before invoking the gate), create the `design/` directory under `tmp_path` and write a no-contracts `design/contracts.md` containing the no-contracts sentence — unconditionally, on every call. Completion: every `run_spec_gate` call produces `tmp_path/design/contracts.md` whose content is the no-contracts sentence.
4. **Site C — `SLICES_SPEC_WITHOUT_TS_AC`:** insert a `## Interface contracts` section (no-contracts sentence body) into the inline spec string, before the `## Slices` block. Use the imported sentence (concatenate; do not retype). Completion: the constant contains `## Interface contracts` and the no-contracts sentence.
5. **New wiring-proof tests** (add a new test class, e.g. `TestContractCheckWiring`):
   - a feature spec carrying the no-contracts section plus a matching no-contracts `design/contracts.md` PASSES (exit 0). The migrated `make_spec_with_slices()` + `run_spec_gate` already produce both — assert `result.returncode == 0`.
   - a feature spec with the `## Interface contracts` section ABSENT fails on the structural check (exit 2, stderr names the missing section). Build a spec that strips the section (do not use the migrated helper for this case — construct a spec without the section) and assert exit 2 and that the structural "section missing" string appears in stderr.
   - new-check failures appear ALONGSIDE (not instead of) the existing slice/AC failures: feed a spec that fails BOTH an existing check (e.g. an out-of-taxonomy `test-discipline`, which the slice check rejects) AND a new contract check (the missing `## Interface contracts` section), and assert stderr contains BOTH the slice-failure signal AND the contracts structural-failure string. This proves accumulation without short-circuit.
6. Run `python3 -m pytest tests/test_gates_spec.py` from `assets/fbk-scripts/`. Before task-10 wires the gate: the new wiring-proof tests that expect contract failures will FAIL (the gate does not run the checks yet) — red phase. State this expectation in a comment on the new class.

## 4. Files to create/modify

- Modify: `assets/fbk-scripts/tests/test_gates_spec.py`

Do not modify `fbk/gates/spec.py` (that is task-10) or any other file. This task modifies only the test file.

## 5. Test requirements

- All existing pass-expecting tests in `test_gates_spec.py` continue to assert what they assert today (exit 0 for the pass cases, exit 2 for the sentinel/failure cases) — the migration changes the fixtures, not the assertions. After task-10 wires the gate, the full `test_gates_spec.py` suite must pass green.
- New wiring-proof tests (level: integration — they invoke the gate via `run_spec_gate`/subprocess):
  - no-contracts section + matching page → exit 0.
  - section absent → exit 2; stderr contains `"Interface contracts section missing — add ## Interface contracts to the spec. Carry at least one entry or the no-contracts sentence from design/contracts.md."`
  - combined failure → stderr contains BOTH a slice-check failure signal (the slice name or an out-of-taxonomy discipline value) AND the contracts structural-failure string above. Assert both substrings present in the same run's stderr.
- The no-contracts sentence is imported from `fbk.gates.contracts`, never retyped.

## 6. Acceptance criteria

- Covers AC-13 (the gate runs the four checks after `check_slices`, accumulating without short-circuit, preserving exit-code/JSON contract — proven by the wiring tests).
- The three migration sites (Sites A, B, C) are each updated in place (not deleted), each with its own completion condition met.
- New wiring tests FAIL before task-10 wires the gate (red phase); the migrated existing tests pass after wiring.

## 7. Model

Sonnet

## 8. Wave

Wave 2
