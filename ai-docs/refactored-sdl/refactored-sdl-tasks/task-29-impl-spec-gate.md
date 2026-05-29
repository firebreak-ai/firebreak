---
id: task-29
type: implementation
wave: 2
covers: [AC-04, AC-21]
files_to_modify:
  - assets/fbk-scripts/fbk/gates/spec.py
test_tasks: [task-10]
dependencies: [task-16]
completion_gate: "the referenced test tasks pass"
---

## 1. Objective

Extends `assets/fbk-scripts/fbk/gates/spec.py` with a slices-block-aware check (`check_slices`) that activates only when the spec declares a `## Slices` block, validates per-slice `test-discipline` and inventory coverage, and leaves the existing legacy behavior — including the retained testing-strategy AC-traceability check — unchanged.

## 2. Context

The spec gate gains slice-awareness behind a backward-compatible hinge: the new checks fire **only when the spec declares a `## Slices` block**. A legacy spec with no such block passes identically to today (AC-21), including the adversarial case where the bare token `test-discipline` appears only in prose or inside a code fence (the detector must NOT fire on those). The existing `_check_testing_strategy_traceability` (testing-strategy section must reference ≥1 `AC-NN`) is kept unchanged for both legacy and slices-bearing specs — slice declarations supplement AC traceability, they do not replace it.

This task assumes task-16 already moved `detect_injections` to `fbk/injection.py` and rewired `spec.py` to import it. Build on that state. Also import the shared discipline constant: `from fbk.slices import TEST_DISCIPLINES` — do NOT hard-code the four strings.

Recommended internal helper signature (the slice logic is an implementation detail — the paired task-10 test exercises the gate via subprocess on temp `*-spec.md` files and asserts on exit codes, NOT by importing this function, so the name is not contract-pinned and may be refactored):

```python
def check_slices(spec_text: str, inventory_behaviors: set = None) -> list
```

(Default `inventory_behaviors` to an empty set when `None`.)

Behavior of `check_slices` (returns a list of failure strings; empty list = no failures):
- **Hinge**: detect whether the spec declares a `## Slices` block. The detector must key off a `## Slices` heading (use the same heading-prefix approach as `heading_line`) AND the presence of slice entries — NOT the bare token `test-discipline`. If there is no `## Slices` heading, return `[]` immediately (check inactive). The adversarial test passes `test-discipline` in prose and inside a ```yaml code fence with no `## Slices` heading → must return `[]`.
- When the block is present, parse its slice entries (each entry has a `name`, a `test-discipline:` value, and optionally a `covers:` list, in the YAML-ish block format the spec uses — see §"Slice declaration format" in the spec). For each slice:
  - Missing `test-discipline` field → failure naming the slice and "test-discipline".
  - `test-discipline` value not in `TEST_DISCIPLINES` → failure naming the invalid value (or the valid taxonomy).
- **Inventory coverage**: for each behavior ID in `inventory_behaviors`, at least one slice's `covers` list must include it; an uncovered behavior → failure naming the behavior (or "not covered"). When `inventory_behaviors` is empty, no coverage requirement.

Note on parsing: the spec's slices block is fenced YAML-ish (`test-discipline:` lines, `name:` lines, `covers: [..]` lines). A robust line-oriented parse of the `## Slices` section body is sufficient — extract the section body via the existing `section_body(spec_text, heading_line(spec_text, "## slices"))`, then walk lines grouping by `name:` / `- name:` to delimit slices and reading the `test-discipline:` and `covers:` lines within each. Read the task-10 test's `make_spec_with_slices` helper and its inline slice blocks to match the exact format the test builds.

Wiring into `main()`: when scope is `feature`, after the existing checks, run the slice logic with the spec text and the inventory behaviors and `fails.extend(...)` the result so failures surface through the gate's exit code (2 = fail). The inventory behaviors come from a linked inventory if one is referenced; for the gate's main() path, derive `inventory_behaviors` from the spec text's own behavior references or pass an empty set if no inventory is linked. The task-10 test drives every slice case through `main()` via subprocess and asserts exit codes (0 pass / 2 fail) plus output substrings, so the slice failures must be reachable from `main()` and the failure strings must appear in the gate's output. Keep `_check_testing_strategy_traceability` in the `feature` path unchanged so a slices-bearing spec still fails if its testing-strategy section has no `AC-NN` (the `SLICES_SPEC_WITHOUT_TS_AC` subprocess test asserts exit 2).

## 3. Instructions

1. Read the current `assets/fbk-scripts/fbk/gates/spec.py` (post task-16 state: imports `detect_injections` from `fbk.injection`) and the task-10 test (the subprocess slice cases via `run_spec_gate`, the slice-block format in `make_spec_with_slices`, and `SLICES_SPEC_WITHOUT_TS_AC`) — match the slice block format the test builds and ensure each failure case the test expects produces exit 2 with the expected output substring.

2. Add `from fbk.slices import TEST_DISCIPLINES` to the imports.

3. Add the slice logic (an internal helper such as `def check_slices(spec_text: str, inventory_behaviors: set = None) -> list:`, defaulting `inventory_behaviors` to `set()` when `None`). Implement the hinge (no `## Slices` heading → return `[]`), per-slice `test-discipline` presence + taxonomy-membership checks against `TEST_DISCIPLINES`, and inventory-coverage checks. Return the failure list. Because the test reaches this only through `main()`, the helper need not be exported — but it must be wired into `main()` (step 4).

4. In `main()`'s `feature` branch, after `_check_testing_strategy_traceability`, run the slice logic with `spec_text` and `<inventory_behaviors>` and `fails.extend(...)` the result. Derive `inventory_behaviors` as an empty set unless a linked inventory is readily resolvable (the subprocess test does not require coverage). Leave the legacy structural checks and `_check_testing_strategy_traceability` unchanged. Completion: a no-slices spec still exits 0; a slice missing/with an invalid `test-discipline`, an uncovered inventory behavior, and the `SLICES_SPEC_WITHOUT_TS_AC` spec each exit 2 via `python3 -m fbk spec-gate <file>`, with the relevant failure substring in the output.

5. Run the paired test: from `assets/fbk-scripts`, `python3 -m pytest tests/test_gates_spec.py -q`. The new classes (`TestSliceBlockDetection`, `TestSliceDisciplineValidation`, `TestInventoryCoverage`, `TestTestingStrategyRetainedForSliceSpecs`) and the unchanged existing classes (`TestCheckSection`, `TestCheckOpenQuestions`) must all pass.

6. Run the existing injection test to confirm no regression from sharing the module: `python3 -m pytest tests/test_gates_spec_injection.py -q`.

## 4. Files to create/modify

- `assets/fbk-scripts/fbk/gates/spec.py` (modify)

## 5. Test requirements

- New tests: none authored here. Make the new classes in `assets/fbk-scripts/tests/test_gates_spec.py` (task-10) pass while keeping the existing classes green.
- Existing tests impacted: `test_gates_spec.py` existing pure-function tests are preserved (the task adds, does not remove). `test_gates_spec_injection.py` stays green (it imports `detect_injections` via the re-export established in task-16).

## 6. Acceptance criteria

- AC-04: with a `## Slices` block, the gate fails a slice missing `test-discipline`, fails an out-of-taxonomy value, fails an inventory behavior covered by no slice; a slices-bearing spec still requires an `AC-NN` reference in its testing-strategy section.
- AC-21: a no-slices spec passes identically over the full feature path, including the adversarial bare-token case which fires no slice check.
- Primary criterion: the task-10 tests pass.

## 7. Model

Sonnet

## 8. Wave

Wave 2
