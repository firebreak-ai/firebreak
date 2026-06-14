# Grilling log — interface-contracts (design phase)

Decisions resolved during design-phase grilling. Each block records the question,
the recommendation, the operator's answer, and a reflect-back confirmation. The
enduring form of each decision is in `docs/decisions-log.md` (all dated 2026-06-09).

### blast-radius-derivation

- Question: When a spec lists the pre-existing interfaces a feature touches (the blast radius for regression risk), how is "touched module" bounded — and who does the work?
- Recommendation (architect's first draft): Author judgment, guided by "which existing interfaces does a reviewer need to verify still hold." The operator pushed back: the human must never hand-list modules, and soft agent judgment is the exact place silent drops happen.
- Answer: The spec-authoring agent computes the set deterministically using the project's own reference tooling (find all callers / find all importers), seeded from the modules the spec already declares it will change. Blast radius = the dependents (callers/importers) of changed modules. The gate verifies shape, not completeness.
- Confirmed: No human and no soft judgment. The agent derives the dependent set with real reference tooling. The gate checks blast-radius entries are present and well-formed (marked pre-existing, all fields filled) but does not recompute the caller set or check completeness. Gate-enforced completeness across languages is a deferred follow-on, because the gate is language-blind and runs inside arbitrary target projects. A small instruction is added to the spec-authoring guidance directing the agent to derive blast radius via reference tooling.

### identifier-collision-policy

- Question: Contract IDs are minted from one shared per-feature sequence by both design and, later, spec. If design is re-edited after the spec minted IDs, two entries could collide on a number. How is that handled?
- Recommendation (architect's first draft): Operator-resolves — no automatic prevention; the rare collision is noticed via spec review or the gate and renumbered by hand.
- Answer: Separate namespaces — make collision structurally impossible.
- Confirmed: Design mints `IF-D-NN`; spec mints `IF-S-NN` (for blast-radius pre-existing entries and spec-discovered new contracts). When the spec carries a design contract it keeps the `IF-D-NN` id verbatim (inheritance, not minting). Neither phase mints into the other's space, so collision cannot occur. This ripples through the schema, the parse regexes, the gate id-format check, and this feature's own contract IDs (now `IF-D-01`..`IF-D-05`).

### drift-detection-location

- Question: Detecting contract drift (spec and design quietly disagree — renamed, re-signatured, or spec adds one design never had) needs a reviewer's judgment, not a mechanical check. Where should that responsibility live?
- Recommendation: Extend the architecture reviewer's brief rather than adding a rigid gate check.
- Answer: Extend the architecture reviewer's brief.
- Confirmed: Drift detection lives in the architecture reviewer's brief in `review-perspectives.md`. No gate code change. It runs whenever that reviewer is engaged, which is effectively always for a feature with contracts. The reviewer reports drift as informational findings and leaves disposition to the operator.

### gate-module-placement

- Question: Where do the four new gate checks live — extended into `spec.py`, or a new module the spec gate calls?
- Recommendation: A new `fbk/gates/contracts.py` module, mirroring the 2026-05-29 decision that put the code-review gate in its own module rather than bloating an existing one.
- Answer: Adopted (precedent-following; operator did not pull it back when surfaced).
- Confirmed: The four checks live in `fbk/gates/contracts.py`; `spec.py` imports and calls them in its feature-scope branch, consistent with the existing `fbk.injection` / `fbk.slices` helper-module pattern.

### design-page-parse-shape

- Question: How is the design contracts page parsed so identifier extraction is robust?
- Recommendation: Level-two `## IF-D-NN — <name>` headings as entry boundaries, reusing the heading-based parsing the spec gate already does.
- Answer: Adopted (precedent-following; operator did not pull it back when surfaced).
- Confirmed: Identifiers are extracted with `^## (IF-D-[0-9]{2,})`. Prose mentions do not count; only heading-level entries do. The page stays readable in any markdown renderer.

### seam-coverage-match-rule

- Question: How does the light seam-coverage check decide a declared seam is covered by a contract?
- Recommendation: A case-insensitive substring scan of component names against the contracts section body, with no new `components:` field — the PRD already declares this check a deliberate heuristic.
- Answer: Adopted (precedent-following; operator did not pull it back when surfaced).
- Confirmed: The check matches both component names from each seam declaration as substrings in the `## Interface contracts` body, case-insensitive. The error message states the heuristic nature; the operator is the final judge. A `components:` field remains a future refinement if false passes prove common.
