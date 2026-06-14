---
id: task-02
type: implementation
wave: 1
covers: [AC-01, AC-02, AC-03, AC-04, AC-05, AC-06, AC-07, AC-08, AC-09, AC-10, AC-11, AC-12]
files_to_create:
  - assets/fbk-scripts/fbk/gates/contracts.py
test_tasks: [task-01]
completion_gate: "task-01 tests pass"
---

# task-02 — Implement the four interface-contract gate checks

## 1. Objective

Produces `assets/fbk-scripts/fbk/gates/contracts.py`: a new module exposing exactly the four pure check functions `check_interface_contracts_structure`, `check_design_anchor`, `check_ac_coverage`, `check_seam_coverage` (each returning `List[str]`), the no-contracts sentence as a module constant, and every teaching-failure string as a module constant.

## 2. Context

This is the implementation task for the `contracts-gate-module` slice (new-contract discipline). The paired test task (task-01) wrote `assets/fbk-scripts/tests/test_gates_contracts.py`, which imports the four functions and the no-contracts sentence constant from `fbk.gates.contracts` and asserts each failure path returns the EXACT teaching string. Your job is to make those tests pass. The tests are the spec for behavior; the exact strings below are the spec for wording.

**Why a new module, not additions to `spec.py`.** The existing gate package already places a self-contained gate's logic in its own file — `assets/fbk-scripts/fbk/gates/code_review.py` is that precedent. These four checks are a cohesive unit with shared parse helpers and a four-function public interface that `spec.py` imports as a group; co-locating them in `contracts.py` mirrors the precedent and keeps `spec.py` from bloating. The module-interface contract (the fifth design contract this slice delivers) requires the four functions co-located in one importable module.

**Reuse the existing section helpers — do not re-implement them.** `spec.py` already defines `heading_line(spec_text, heading)` (returns the 1-based line number of the first line whose lowercased text starts with the lowercased heading, or `None`) and `section_body(spec_text, line_number)` (returns the text between that heading line and the next `## ` heading). Several of the four algorithms locate a section and read its body — use those two helpers by importing them:

```python
from fbk.gates.spec import heading_line, section_body
```

This is a cross-task interface contract: `heading_line` and `section_body` already exist in `spec.py` at compilation time (read them there to confirm the convention) and are imported, not copied. Note this creates a circular-looking pair (`spec.py` will import the four functions from `contracts.py` in task-10, and `contracts.py` imports two helpers from `spec.py`) — this is safe because the helper imports are at `contracts.py` module top and the four-function import lands at `spec.py` module top; Python resolves both at load time without a cycle error as long as neither import is executed inside the other module's top-level body in a way that re-enters. The existing `fbk.injection` / `fbk.slices` imports in `spec.py` are the precedent for top-level gate-module imports.

**Pinned wording is non-negotiable.** Every teaching string below is copied verbatim from the design's gate-checks page — the single source of truth. Define each as a module-level string constant and build the per-case message by substituting the concrete value (entry id, field name, AC id, path, component names) into the constant. Do not paraphrase, re-order clauses, or change punctuation; task-01 asserts the exact string and any drift fails the test.

**Constant-name contract for the no-contracts sentence.** Task-01 imports `NO_CONTRACTS_SENTENCE` from this module; task-09 (the wiring test, Wave 2) imports the same name. The canonical constant name is `NO_CONTRACTS_SENTENCE` and its value is exactly `No new or changed contracts in this feature.` — define it once here; both downstream tests depend on this exact name and value.

The four algorithms (parse rules, set logic) are pinned below in §3. Follow them step for step.

## 3. Instructions

1. Create `assets/fbk-scripts/fbk/gates/contracts.py`. Add the module docstring and imports:
   - `import re`
   - `import pathlib`
   - `from typing import List`
   - `from fbk.gates.spec import heading_line, section_body`

2. Define the sentence constant:
   ```python
   NO_CONTRACTS_SENTENCE = "No new or changed contracts in this feature."
   ```

3. Define every teaching string as a module-level constant. Use these EXACT literals (copy verbatim — placeholders shown as `{...}` mark where you substitute concrete values with `.format(...)` or f-strings at the call site; keep the surrounding text byte-for-byte):

   - Structural — section missing:
     `"Interface contracts section missing — add ## Interface contracts to the spec. Carry at least one entry or the no-contracts sentence from design/contracts.md."`
   - Structural — present but empty:
     `"Interface contracts section present but empty — add at least one contract entry or the no-contracts sentence (No new or changed contracts in this feature.)."`
   - Structural — missing field (substitute `{id}`, `{field}`):
     `"Interface contracts: entry {id} is missing the {field} field. Every entry needs id, name, signature, invariants, covers, and design-ref."`
   - Structural — invalid id format (substitute `{id}`):
     `"Interface contracts: entry {id} has an invalid id format. Expected IF-D-NN (design-originated, carry from design/contracts.md) or IF-S-NN (spec-originated, minted by the spec author). NN must be at least two digits."`
   - Structural — empty covers (substitute `{id}`):
     `"Interface contracts: entry {id} has an empty covers list — every contract must cover at least one acceptance criterion."`
   - Structural — covers AC absent (substitute `{id}`, `{ac}` twice):
     `"Interface contracts: entry {id} lists {ac} in covers but {ac} does not appear in ## Acceptance criteria. Check the identifier or add the missing criterion."`
   - Structural — invalid design-ref (substitute `{id}`, `{value}`):
     `"Interface contracts: entry {id} has an invalid design-ref value '{value}' — valid values are a path/anchor into design/contracts.md (e.g., design/contracts.md#if-d-01), the literal 'pre-existing', or the literal 'none'."`
   - Excluded — empty rationale (substitute `{id}`):
     `"Excluded contracts: entry {id} has an empty rationale — every excluded contract needs a non-empty rationale explaining why it is not carried."`
   - Excluded — invalid id (substitute `{id}`):
     `"Excluded contracts: entry {id} has an invalid id format — excluded entries reference a design-originated contract and must use the IF-D-NN form."`
   - Uncovered AC — empty rationale (substitute `{id}`):
     `"Uncovered acceptance criteria: entry {id} has an empty rationale — every uncovered criterion needs a non-empty rationale explaining why no contract covers it."`
   - Design-anchor — page not found (substitute `{path}`):
     `"Design contracts page not found at {path} — run /fbk-design <feature-name> to produce it before running the spec gate."`
   - Design-anchor — contract not carried (substitute `{id}`, `{name}`; keep the literal `IF-D-NN` text NOT substituted only where the verbatim string carries it — match the exact wording below, substituting the real id and name):
     `"Contract {id} ({name}) is listed in design/contracts.md but is not carried into ## Interface contracts and has no entry in ## Excluded contracts. Resolution: (1) add an {id} entry to ## Interface contracts with all required fields, or (2) add an ## Excluded contracts entry for {id} with a non-empty rationale explaining the scope change."`
     (Cross-check against task-01's TestDesignAnchor case: it substitutes the case's concrete identifier and `<name>` into the canonical string and asserts membership. Build this message by substituting the real id everywhere `IF-D-NN` appears in the canonical wording and the real name for `<name>`.)
   - AC-coverage — not covered (substitute `{ac}` everywhere the canonical string shows `AC-NN`):
     `"{ac} is not covered by any contract's covers: list and has no entry in ## Uncovered acceptance criteria. Resolution: (1) add {ac} to some contract's covers: list, or (2) add an ## Uncovered acceptance criteria entry for {ac} with a non-empty rationale."`
   - Seam-coverage — uncovered pair (substitute `{a}`, `{b}` for the two component names everywhere the canonical string shows `ComponentA` / `ComponentB`):
     `"Integration seam '{a} → {b}' is declared in ## Technical approach but no entry in ## Interface contracts appears to name both components. This is a heuristic check — if the seam genuinely needs no contract, either add a contract entry naming both components or revisit the integration-seam declaration. Resolution: (1) add or update a contract entry that names both {a} and {b}, or (2) update the integration-seam declaration if this seam is contract-free."`
     The arrow between component names is Unicode U+2192 (`→`). Keep the word `heuristic` in the message (task-01 asserts it is present).

4. Implement `check_interface_contracts_structure(spec_text: str) -> List[str]` per the pinned parse + set logic:
   - Locate `## Interface contracts` with `heading_line`. If absent: return one failure (section-missing string).
   - Extract its body with `section_body`. If `body.strip()` is empty: return one failure (present-but-empty string).
   - If the stripped body equals (or contains as its sole meaningful line) the `NO_CONTRACTS_SENTENCE`: the contracts section is valid — skip entry parsing and proceed to validate the two escape-hatch sections below.
   - Otherwise parse entries. Entry boundary regex: `^\s*-\s+id:\s+(IF-[DS]-[0-9]{2,})` (line-anchored, `re.MULTILINE`) opens a new entry; but to also catch entries whose `id` value is malformed, detect entry starts on any `^\s*-\s+id:\s+(\S+)` and validate the captured id against `^IF-[DS]-[0-9]{2,}$` (invalid-id string on mismatch). For each entry read subsequent indented field lines `^\s+<field>:\s+(.+)` for `name`, `signature`, `invariants`, `covers`, `design-ref`.
   - For each entry, verify all six fields (`id`, `name`, `signature`, `invariants`, `covers`, `design-ref`) are present and non-empty — one missing-field failure per absent field, naming the entry id and field.
   - `covers`: extract the inline YAML list with `\[([^\]]*)\]` and split on commas (strip each). Empty list → empty-covers failure. For each `AC-NN` in the list, verify it appears in the `## Acceptance criteria` body — locate that section with `heading_line`/`section_body` and collect AC ids with `re.findall(r"\bAC-[0-9]+\b", ac_body)`; any covered id absent from that set → covers-AC-absent failure (substitute the entry id and the AC id).
   - `design-ref`: a value is valid when it is the literal `pre-existing`, the literal `none`, or a path/anchor form (recognized by containing a `/` or a `#`). Any other present, non-empty value (for example, the bare token `whatever`) returns the invalid-design-ref failure. An absent/empty `design-ref` is caught by the missing-field check above, not here. Implement exactly: `valid = value in ("pre-existing", "none") or ("/" in value) or ("#" in value)`. (This rule is pinned in the design's gate-checks page, Check 1 set logic; task-01's cases confirm it — path/`pre-existing`/`none` pass, `whatever` fails.)
   - Escape-hatch `## Excluded contracts` (if present): parse entries with boundary `^\s*-\s+id:\s+(\S+)` and a `rationale:` field. Each id must match `^IF-D-[0-9]{2,}$` (else excluded-invalid-id string); each `rationale` must be non-empty (else excluded-empty-rationale string).
   - Escape-hatch `## Uncovered acceptance criteria` (if present): parse entries with boundary `^\s*-\s+id:\s+(\S+)` and a `rationale:` field; each `rationale` must be non-empty (else uncovered-empty-rationale string).
   - Accumulate all failures into one list and return it.

5. Implement `check_design_anchor(spec_text: str, feature_dir: str) -> List[str]`:
   - Compute `design_path = pathlib.Path(feature_dir) / "design" / "contracts.md"`.
   - If it does not exist: return one failure (page-not-found string, substituting `str(design_path)` for `{path}`). Do not raise.
   - Read the file. Extract design ids: `re.findall(r"^## (IF-D-[0-9]{2,})", design_text, re.MULTILINE)`. If none: return `[]` (vacuous pass).
   - For each design id, extract its name from the heading line `## IF-D-NN — <name>` (text after `— `; use `"unnamed"` if no ` — ` separator present).
   - Extract carried ids from the spec's `## Interface contracts` body: all `id:` values matching `IF-D-[0-9]{2,}`. Extract excluded ids from `## Excluded contracts`: same pattern. (`IF-S-NN` entries are ignored here.)
   - `missing = set(design_ids) - (carried | excluded)`. One contract-not-carried failure per id in `missing` (substitute the id and its name). Return the list.

6. Implement `check_ac_coverage(spec_text: str) -> List[str]`:
   - Locate `## Acceptance criteria`; if absent return `[]` (the existing `check_section` in `spec.py` already reports a missing section — do not double-report). Extract AC ids from its body: `re.findall(r"\bAC-[0-9]+\b", ac_body)`.
   - Locate `## Interface contracts`; parse entries (boundary `^\s*-\s+id:\s+IF-[DS]-[0-9]{2,}`) and read each entry's `covers:` inline list with `\[([^\]]*)\]`. The covered set is the union of ids drawn ONLY from those `covers:` lists — never a body-wide scan. (This is the trap: an AC mentioned only inside a `signature`/`invariants` field must NOT count as covered.)
   - Locate `## Uncovered acceptance criteria`; collect excused ids: `re.findall(r"^\s*-\s+id:\s+(AC-[0-9]+)", uca_body, re.MULTILINE)`.
   - `uncovered = set(ac_ids) - (covered | excused)`. One not-covered failure per id in `uncovered` (substitute the AC id). Return the list.

7. Implement `check_seam_coverage(spec_text: str) -> List[str]`:
   - Locate `## Technical approach`; extract body. Extract component pairs with `re.findall(r"^\s*-\s*\[[ x]\]\s*([^→\n]+?)\s*→\s*([^:\n]+?):", technical_body, re.MULTILINE)`. Group 1 = left name, group 2 = right name; strip both. The arrow is Unicode U+2192 (`→`). If no pairs: return `[]`.
   - Extract the `## Interface contracts` body. For each pair `(A, B)`: pass iff BOTH `A` and `B` appear (case-insensitive substring) in that body — `re.search(re.escape(name), contracts_body, re.IGNORECASE)`. If either is absent: one heuristic-string failure (substitute A and B). Return the list.

8. Confirm exactly the four functions plus `NO_CONTRACTS_SENTENCE` and the message constants are the module's public surface (no other exported callables). No `if __name__ == "__main__"` block — this module is imported, never invoked directly.

9. Run `python3 -m pytest tests/test_gates_contracts.py` from `assets/fbk-scripts/` and confirm all cases pass (green phase).

## 4. Files to create/modify

- Create: `assets/fbk-scripts/fbk/gates/contracts.py`

Do not modify `spec.py` (the import-and-call wiring is task-10) or any test file (task-01 owns the tests).

### File-scope justification (single new file above the line-count target)

This task creates one file but it will exceed the <55-line target — the four checks plus their shared parse logic and ~14 verbatim message constants run roughly 130-180 lines. The line-count exception is justified: the four functions are a single cohesive module with shared parse helpers and a mandated four-function public interface (the design's module-interface contract requires them co-located), the strings are pinned verbatim and cannot be split out without breaking the single-source-of-truth co-location, and splitting into multiple files would create artificial seams across functions that share the same helpers and constants. One new file, no edits to existing files — the lowest-risk shape for this much pinned logic.

## 5. Test requirements

This task writes no tests. It must make task-01's `tests/test_gates_contracts.py` pass — every structural, design-anchor, AC-coverage, seam-coverage, and module-interface case, each asserting the exact teaching string. Re-read task-01 §5 for the full case list. Key behaviors the implementation must satisfy:

- The present-but-empty case returns a distinct failure from the missing case, using the exact pinned literal in §3 (byte-identical to task-01's assertion).
- Each of the three `design-ref` forms passes individually; `whatever` fails.
- AC-coverage draws coverage only from `covers:` lists (the body-scan trap).
- The seam check's line-anchor guard ignores a `→` written in prose, and the message contains the word `heuristic`.
- Every returned element is a `str` (no `None`/`int` elements).

## 6. Acceptance criteria

- Primary: task-01's tests pass (`tests/test_gates_contracts.py`, green phase).
- Covers AC-01 through AC-12.
- `NO_CONTRACTS_SENTENCE` is defined with the exact name and value both downstream tests (task-01, task-09) import.
- Every teaching string is a module constant copied verbatim from the design's gate-checks page; no paraphrase.
- The module exposes exactly the four check functions, each returning `List[str]`; it imports `heading_line`/`section_body` from `spec.py` rather than re-implementing them.

## 7. Model

Sonnet

Rationale: substantial pinned logic across four algorithms, ~14 verbatim strings whose wording is load-bearing, and a cross-module import relationship with `spec.py`. This exceeds Haiku's bounded-single-file comfort zone; the cost of an under-routed failure (drifted strings failing the exact-match tests) is high. Sonnet.

## 8. Wave

Wave 1
