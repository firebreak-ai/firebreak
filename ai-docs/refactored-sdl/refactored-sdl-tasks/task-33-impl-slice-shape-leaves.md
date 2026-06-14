---
id: task-33
type: implementation
wave: 2
covers: [AC-05]
files_to_create:
  - assets/fbk-docs/fbk-sdl-workflow/slice-shapes.md
  - assets/fbk-docs/fbk-sdl-workflow/slice-shapes/new-contract.md
  - assets/fbk-docs/fbk-sdl-workflow/slice-shapes/contract-preserving.md
  - assets/fbk-docs/fbk-sdl-workflow/slice-shapes/contract-evolving.md
  - assets/fbk-docs/fbk-sdl-workflow/slice-shapes/cross-cutting.md
test_tasks: [task-11]
dependencies: []
completion_gate: "the referenced test tasks pass"
---

## 1. Objective

Produces the slice-shapes index leaf (`slice-shapes.md`) and the four shape leaves (`new-contract.md`, `contract-preserving.md`, `contract-evolving.md`, `cross-cutting.md`) under `assets/fbk-docs/fbk-sdl-workflow/slice-shapes/`, so breakdown loads one shape at a time by progressive disclosure.

## 2. Context

Breakdown routes to these leaves: once a slice's `test-discipline` is read, the agent loads only that one shape leaf (the progressive-disclosure contract). The index (`slice-shapes.md`) is a stage-local routing table; each leaf describes exactly one shape and the work-unit structure it implies.

The four shapes and their work-unit structure (canonical definitions are in `GLOSSARY.md` — match them; do not contradict the glossary):
- **new-contract**: behavior that does not exist yet. The test-task agent writes new tests against the slice's contract; they must fail against an empty implementation (red). Hash-locking applies to the new tests. The impl-task agent turns the tests green without modifying them. Classic red→green. Produces a test task AND an impl task.
- **contract-preserving**: implementation changes while an existing contract is preserved. Existing tests cover the contract and must keep passing; NO new tests for the contract. Hash-locking applies to the existing (locked) tests. No red phase. Produces an impl task over locked existing tests, NO new test task.
- **contract-evolving**: both implementation and contract change. Some existing tests are retired (the slice declaration must list which and why); new tests are written for the new behaviors. Produces a retired-tests list (with rationale per entry), new test tasks, and an impl task.
- **cross-cutting**: behavior spanning multiple existing modules/seams. Tests live at the seams (integration / contract / e2e). Test-only: produces seam tests but NO paired implementation (the implementation already exists across the other slices).

These four shapes are the same values as the shared `TEST_DISCIPLINES` constant and the spec/breakdown/test-hash gate taxonomy. The breakdown gate's cheap invariants (task-30) enforce cross-cutting ⇒ no impl task and contract-evolving ⇒ retired-tests list — the leaves' guidance must be consistent with those invariants.

Asset-type rules: referenced leaves (loaded only on routing). The index gives each shape a one-line `When the slice's test-discipline is <shape>, read slice-shapes/<shape>.md` row. Each leaf has a one-line load condition and one shape's guidance. Use installed path forms (AC-22) — no `assets/` prefix in any leaf body.

The paired task-11 test is the breakdown-gate unit test (it does not read these leaves). These leaves are validated by the wave-4 installer e2e (T installs the slice-shapes docs are reachable) and the reference-integrity adversarial grep (no `assets/` prefix). The breakdown skill (task-32) routes to them.

## 3. Instructions

1. Create the directory `assets/fbk-docs/fbk-sdl-workflow/slice-shapes/`.

2. Create `assets/fbk-docs/fbk-sdl-workflow/slice-shapes.md` as the index leaf: a one-line load condition (`Load condition: routed by the breakdown skill once a slice's test-discipline is known.`), then a routing table with four rows, one per shape, each routing to `slice-shapes/<shape>.md`. Completion: `[ -s assets/fbk-docs/fbk-sdl-workflow/slice-shapes.md ]` and the file references all four leaf filenames.

3. Create `assets/fbk-docs/fbk-sdl-workflow/slice-shapes/new-contract.md`: one-line load condition + new-contract work-unit guidance (red→green; new tests locked; test task + impl task). Completion: `[ -s ...new-contract.md ]` and `grep -c '\bassets/' ...new-contract.md` returns 0.

4. Create `assets/fbk-docs/fbk-sdl-workflow/slice-shapes/contract-preserving.md`: load condition + guidance (existing tests locked, no new test task, impl task only). Completion: file non-empty, no `assets/` prefix.

5. Create `assets/fbk-docs/fbk-sdl-workflow/slice-shapes/contract-evolving.md`: load condition + guidance (retired-tests list with rationale required; new tests for new behaviors; impl task). Completion: file non-empty, mentions "retired", no `assets/` prefix.

6. Create `assets/fbk-docs/fbk-sdl-workflow/slice-shapes/cross-cutting.md`: load condition + guidance (test-only at seams; no paired impl task). Completion: file non-empty, no `assets/` prefix.

7. Confirm no leaf body contains an `assets/` path prefix: `grep -rc '\bassets/' assets/fbk-docs/fbk-sdl-workflow/slice-shapes.md assets/fbk-docs/fbk-sdl-workflow/slice-shapes/ | grep -v ':0$'` prints nothing.

8. Run the paired unit test (regression): from `assets/fbk-scripts`, `python3 -m pytest tests/test_gates_breakdown.py -q` (these leaves don't affect it, but confirm no breakage from the slice's other tasks).

## 4. Files to create/modify

- `assets/fbk-docs/fbk-sdl-workflow/slice-shapes.md` (create)
- `assets/fbk-docs/fbk-sdl-workflow/slice-shapes/new-contract.md` (create)
- `assets/fbk-docs/fbk-sdl-workflow/slice-shapes/contract-preserving.md` (create)
- `assets/fbk-docs/fbk-sdl-workflow/slice-shapes/contract-evolving.md` (create)
- `assets/fbk-docs/fbk-sdl-workflow/slice-shapes/cross-cutting.md` (create)

File-scope justification: five files for one cohesive doc-set (an index plus its four leaves) implementing progressive disclosure for the four slice shapes. The index has no value without its leaves, and each leaf must exist for the breakdown routing to resolve; the set is a single conceptual unit (the slice-shapes routing tree). Splitting would create artificial boundaries between an index and the leaves it routes to.

## 5. Test requirements

- New tests: none authored here. The paired task-11 test (breakdown-gate) is satisfied by task-30. These leaves are validated by the wave-4 installer e2e and the reference-integrity adversarial `assets/`-prefix grep (task-13).

## 6. Acceptance criteria

- AC-05: the four slice-shape leaves and their index exist, each describing one shape's work-unit structure consistent with the breakdown gate's cheap invariants and the glossary definitions; breakdown loads one shape leaf at a time.
- Structural criterion: no leaf body contains an `assets/` path prefix (installed-path compliance).
- Primary criterion: the breakdown-gate unit test (task-11) stays green and the leaves install (wave-4 e2e).

## 7. Model

Sonnet

## 8. Wave

Wave 2
