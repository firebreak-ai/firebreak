---
id: task-01
type: test
wave: 1
covers: [AC-01, AC-02, AC-03, AC-04, AC-05, AC-06, AC-07, AC-08, AC-09, AC-10, AC-11, AC-12]
files_to_create:
  - assets/fbk-scripts/tests/test_gates_contracts.py
completion_gate: "tests compile and fail before implementation (red phase against an empty/absent fbk/gates/contracts.py)"
---

# task-01 — Test the four interface-contract gate checks

## 1. Objective

Produces `assets/fbk-scripts/tests/test_gates_contracts.py`: a pytest module that drives the four pure check functions in `fbk/gates/contracts.py` directly and asserts each failure-path case against the exact teaching string the gate is required to emit.

## 2. Context

This is the test task for the `contracts-gate-module` slice (new-contract discipline). The paired implementation task (task-02) creates `fbk/gates/contracts.py` with four functions; this test task declares the signatures those functions must satisfy and the exact strings they must return. The functions do not exist yet — the tests must compile and FAIL when run against an empty or absent module (red phase).

The four functions and their signatures (declared here; task-02 copies them verbatim):

- `check_interface_contracts_structure(spec_text: str) -> List[str]` — reads only the spec text; validates the three spec-side sections.
- `check_design_anchor(spec_text: str, feature_dir: str) -> List[str]` — reads spec text plus the feature directory; a missing `design/contracts.md` returns one failure rather than raising.
- `check_ac_coverage(spec_text: str) -> List[str]` — reads only spec text.
- `check_seam_coverage(spec_text: str) -> List[str]` — reads only spec text.

Each returns a list of teaching failure strings; an empty list means pass.

Behavioral intent: these checks exist to deliver *message quality*. A test that only asserts `len(result) > 0` does not protect that quality and is not acceptable for any message-bearing case. Every failure-path case asserts the exact canonical string. The canonical strings live in the design's gate-checks page and are reproduced verbatim in §5 below — copy them exactly, do not paraphrase.

Two consequences of the design that shape the fixtures:

1. The no-contracts sentence is `No new or changed contracts in this feature.` It is defined once as a module constant in `contracts.py` (task-02 owns it). This test file MUST import that constant from `contracts.py` rather than retyping the literal, so the check that recognizes the sentence and the fixtures that produce it cannot drift by a character. Use a name such as `NO_CONTRACTS_SENTENCE` — confirm the exact constant name with the paired implementation (task-02 must export the same name). State the dependency: if the constant is absent at red-phase run time, the import fails and every test errors, which is an acceptable red-phase failure.

2. Two shared fixtures defined here are reused later by `test_gates_spec.py` (task-09): a minimal valid `## Interface contracts` entry string, and a minimal valid no-contracts `design/contracts.md` text. Define both as module-level constants or fixtures with clear names so task-09 can import or copy them.

Existing pattern to follow: `assets/fbk-scripts/tests/test_gates_spec.py` — pytest classes grouping behaviors, `tmp_path` for file I/O, module-level fixture strings (`_MINIMAL_VALID_SECTIONS`), `from fbk.gates.spec import ...` direct imports. Follow that import and class-organization style. `fbk` is importable in the test env because pytest's rootdir is `assets/fbk-scripts/` (the existing `test_gates_spec.py` imports `from fbk.gates.spec import check_section`). All file I/O uses `tmp_path` — fast and deterministic, no mocks (the checks are pure text/file operations; default-to-real-collaborator holds).

## 3. Instructions

1. Create `assets/fbk-scripts/tests/test_gates_contracts.py`.
2. Import the four functions and the no-contracts sentence constant from `fbk.gates.contracts`:
   `from fbk.gates.contracts import (check_interface_contracts_structure, check_design_anchor, check_ac_coverage, check_seam_coverage, NO_CONTRACTS_SENTENCE)`.
3. Define module-level fixture strings:
   - `MINIMAL_ENTRY` — a valid single `## Interface contracts` entry with all six fields, an `id` of `IF-D-01`, a `covers` listing one AC that also appears in an `## Acceptance criteria` section, and a path-form `design-ref`. Include the `## Acceptance criteria` section in the spec text the case feeds in. This is the UV-1 real-entry fixture, distinct from the no-contracts form.
   - `NO_CONTRACTS_SECTION` — a `## Interface contracts` section whose body is exactly the imported `NO_CONTRACTS_SENTENCE`.
   - `MINIMAL_DESIGN_CONTRACTS` — a minimal valid no-contracts `design/contracts.md` text (the single no-contracts sentence). Reuse the imported constant; do not retype the literal. (This fixture is reused by task-09.)
4. Write the case classes enumerated in §5 below. Group by check function (`TestStructural`, `TestDesignAnchor`, `TestACCoverage`, `TestSeamCoverage`, `TestModuleInterface`). Each test asserts on one behavior.
5. For every message-bearing failure case, assert the EXACT string is present in the returned list (e.g. `assert EXPECTED in result`, or build the expected string by substituting the entry id/field/AC/path and assert membership). Do NOT assert only `len(result) > 0`. Pair each failure assertion with a presence check and, where the case is a pass case, assert `result == []`.
6. For the design-anchor "page not found" case, additionally assert no Python traceback occurred (the function returned a list, did not raise) — wrap nothing in try/except; a raised exception fails the test naturally, which proves the no-raise invariant.
7. Do not implement `contracts.py`. Run `python3 -m pytest tests/test_gates_contracts.py` from `assets/fbk-scripts/` and confirm collection succeeds and tests FAIL (the module/constant do not exist) — red phase.

## 4. Files to create/modify

- Create: `assets/fbk-scripts/tests/test_gates_contracts.py`

Do not modify any other file. (`fbk/gates/contracts.py` is created by task-02; do not stub it here — red phase requires it absent.)

### File-scope justification (one cohesive test module)

This single file covers AC-01..AC-12 across four functions and ~30 cases. The slice design specifies one test module driving one gate module; splitting by check function would create artificial boundaries (the shared fixtures and the imported constant span all four). Estimated size is ~250-320 lines — above the 55-line task target, but test files are an explicit exception: the sizing target governs *implementation diff hunks*, not a cohesive new test module enumerated case-by-case. The cohesion (one module under test, one shared fixture set) justifies the single file.

## 5. Test requirements

All tests are unit level, calling the production functions directly. Canonical strings below are copied verbatim from the design's gate-checks page — the implementing agent must NOT paraphrase. Where a string contains a placeholder (`<id>`, `<field>`, `<AC-NN>`, `<value>`, `<path>`, `IF-D-NN`, `<name>`, `ComponentA`, `ComponentB`), the test substitutes the case's concrete value and asserts the resulting exact string is in the returned list.

### TestStructural — `check_interface_contracts_structure` (AC-01..AC-07)

- Missing `## Interface contracts` section returns exactly:
  `"Interface contracts section missing — add ## Interface contracts to the spec. Carry at least one entry or the no-contracts sentence from design/contracts.md."`  (AC-01)
- Present-but-empty section (heading present, blank body) returns exactly — a distinct failure from "missing":
  `"Interface contracts section present but empty — add at least one contract entry or the no-contracts sentence (No new or changed contracts in this feature.)."`  (AC-01)
- The no-contracts sentence (`NO_CONTRACTS_SECTION`) passes: `result == []`.  (AC-01)
- A real single `IF-D` entry with all six fields and a covered AC (`MINIMAL_ENTRY`) passes: `result == []`. This is the UV-1 real-entry pass, distinct from the no-contracts form.  (AC-01)
- An entry missing each of the six fields (`id`, `name`, `signature`, `invariants`, `covers`, `design-ref`) — one parametrized case per field — returns, for the missing `<field>` on entry `<id>`:
  `"Interface contracts: entry <id> is missing the <field> field. Every entry needs id, name, signature, invariants, covers, and design-ref."`  (AC-02)
- A non-`IF-[DS]` id prefix (e.g. `IF-X-01` or `XX-01`) returns:
  `"Interface contracts: entry <id> has an invalid id format. Expected IF-D-NN (design-originated, carry from design/contracts.md) or IF-S-NN (spec-originated, minted by the spec author). NN must be at least two digits."`  (AC-03)
- An empty `covers` list returns:
  `"Interface contracts: entry <id> has an empty covers list — every contract must cover at least one acceptance criterion."`  (AC-04)
- A `covers` AC absent from `## Acceptance criteria` returns:
  `"Interface contracts: entry <id> lists <AC-NN> in covers but <AC-NN> does not appear in ## Acceptance criteria. Check the identifier or add the missing criterion."`  (AC-04)
- Each of the three valid `design-ref` forms passes individually — a path/anchor (`design/contracts.md#if-d-01`), the literal `pre-existing`, the literal `none`: `result == []` for each. Parametrize.  (AC-05)
- Any other `design-ref` value (e.g. `whatever`) returns:
  `"Interface contracts: entry <id> has an invalid design-ref value '<value>' — valid values are a path/anchor into design/contracts.md (e.g., design/contracts.md#if-d-01), the literal 'pre-existing', or the literal 'none'."`  (AC-05)
- An `## Excluded contracts` entry with an empty rationale returns:
  `"Excluded contracts: entry <id> has an empty rationale — every excluded contract needs a non-empty rationale explaining why it is not carried."`  (AC-06)
- An `## Excluded contracts` entry with a non-`IF-D` id returns:
  `"Excluded contracts: entry <id> has an invalid id format — excluded entries reference a design-originated contract and must use the IF-D-NN form."`  (AC-06)
- An `## Uncovered acceptance criteria` entry with an empty rationale returns:
  `"Uncovered acceptance criteria: entry <id> has an empty rationale — every uncovered criterion needs a non-empty rationale explaining why no contract covers it."`  (AC-07)

### TestDesignAnchor — `check_design_anchor` (AC-08, AC-09)

Build the feature dir under `tmp_path`; write `design/contracts.md` into `tmp_path/design/`.

- A design page whose every `IF-D-NN` heading is carried into `## Interface contracts` passes: `result == []`.  (AC-08)
- One `IF-D-NN` neither carried nor excluded returns the exact (substituting the identifier `IF-D-NN` and its heading `<name>`):
  `"Contract IF-D-NN (<name>) is listed in design/contracts.md but is not carried into ## Interface contracts and has no entry in ## Excluded contracts. Resolution: (1) add an IF-D-NN entry to ## Interface contracts with all required fields, or (2) add an ## Excluded contracts entry for IF-D-NN with a non-empty rationale explaining the scope change."`  (AC-08)
- A design contract carried only in `## Excluded contracts` (with rationale) passes: `result == []`.  (AC-08)
- A missing `design/contracts.md` returns exactly (substituting the resolved `<path>`):
  `"Design contracts page not found at <path> — run /fbk-design <feature-name> to produce it before running the spec gate."` and does not raise.  (AC-09)
- A design page with no `IF-D` headings (no-contracts sentence only) passes vacuously: `result == []`.  (AC-08)

### TestACCoverage — `check_ac_coverage` (AC-10)

- Every AC in `## Acceptance criteria` covered by some entry's `covers:` list passes: `result == []`.  (AC-10)
- An uncovered AC returns exactly (substituting the identifier):
  `"AC-NN is not covered by any contract's covers: list and has no entry in ## Uncovered acceptance criteria. Resolution: (1) add AC-NN to some contract's covers: list, or (2) add an ## Uncovered acceptance criteria entry for AC-NN with a non-empty rationale."`  (AC-10)
- An AC excused in `## Uncovered acceptance criteria` passes: `result == []`.  (AC-10)
- The body-scan trap: an AC that appears ONLY inside a `signature` or `invariants` field text (never in any `covers:` list) is still reported uncovered — assert the uncovered string for that AC is returned. This proves coverage is drawn only from `covers:` lists, never a body-wide scan.  (AC-10)

### TestSeamCoverage — `check_seam_coverage` (AC-11)

- A seam (`- [ ] A → B: ...` in `## Technical approach`) whose two components both appear as substrings in the `## Interface contracts` body passes: `result == []`.  (AC-11)
- A seam where one component is absent from the contracts body returns the exact heuristic string (substituting `ComponentA`/`ComponentB`):
  `"Integration seam 'ComponentA → ComponentB' is declared in ## Technical approach but no entry in ## Interface contracts appears to name both components. This is a heuristic check — if the seam genuinely needs no contract, either add a contract entry naming both components or revisit the integration-seam declaration. Resolution: (1) add or update a contract entry that names both ComponentA and ComponentB, or (2) update the integration-seam declaration if this seam is contract-free."`  Additionally assert the returned string contains the word `heuristic` (proves the heuristic-labelling clause is present).  (AC-11)
- No declared seam passes: `result == []`.  (AC-11)
- The line-anchor guard: a `→` written inside a prose line under `## Technical approach` (not a `- [ ]` checklist item) produces zero seam failures: `result == []`. The seam arrow is Unicode U+2192 (`→`); use that exact character.  (AC-11)

### TestModuleInterface (AC-12)

- The four names import from `fbk.gates.contracts` (the module-level import at the top of the file proves this; add an explicit assertion that each is `callable`).  (AC-12)
- Each function, called with valid input, returns a list whose every element is a `str` — assert `isinstance(result, list) and all(isinstance(x, str) for x in result)`. This must reject `[None]` or `[1]`, not merely confirm a `list`. Use at least one input per function that produces a non-empty failure list so the element-type assertion is exercised against real content.  (AC-12)

## 6. Acceptance criteria

- Covers AC-01 through AC-12 (the structural, design-anchor, AC-coverage, seam-coverage, and module-interface cases above).
- Every message-bearing failure case asserts the exact canonical string (no `len(result) > 0`-only assertions).
- Tests compile (collection succeeds) and FAIL when run against the absent/empty `fbk/gates/contracts.py` (red phase). The `NO_CONTRACTS_SENTENCE` import failure at red phase is acceptable.
- All file I/O uses `tmp_path`; no mocks.

## 7. Model

Sonnet

## 8. Wave

Wave 1
