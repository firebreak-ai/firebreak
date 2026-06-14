# Fresh-eyes review — interface-contracts (design phase)

A cold reader with no authoring context reviewed the design package (`design-manifest.md`, the six design pages, against the PRD for grounding). Observations are grouped by severity. All critical observations were resolved before the design gate; the resolution is noted inline.

## Critical

None. All critical observations from the cold review were resolved — see "Resolved critical observations" below.

## Important

None open. The substantive important observations were resolved (see below); the remainder were judged correct-by-design.

## Minor

None open. Cosmetic and by-design observations were addressed or accepted (see below).

## Resolved critical observations

- **PRD used a flat `IF-NN` scheme; the design uses `IF-D-NN` / `IF-S-NN`.** This is an intentional override from the design-phase decision to make identifier collisions structurally impossible, but the package had no reconciliation note, so a spec author reading the PRD would be confused. Resolved by adding a "Supersedes the PRD's illustrative scheme" note to `contracts-standard.md` stating that the two-namespace form and the exact no-contracts sentence replace the PRD's sketch, and that the spec phase reconciles the PRD and behavior inventory.
- **Design-anchor regex did not state `re.MULTILINE` in `contracts-standard.md`.** Without it, `^` matches only the document start and no headings are found. Resolved by stating the `re.MULTILINE` requirement explicitly in the parse-rule section.
- **"Five other fields" phrasing read as a field-count contradiction against the six-field rule.** Resolved by replacing it with an explicit field list (`name`, `signature`, `invariants`, `covers`, `design-ref`) in `gate-checks.md`.
- **The structural check took a `feature_dir` parameter it never used.** Resolved by dropping the parameter — `check_interface_contracts_structure(spec_text)` now reads only the spec text; the integration snippet and the module-interface description were updated to match. Only the design-anchor check takes `feature_dir`.

## Resolved important observations

- **AC-coverage counted ACs mentioned anywhere in the contracts body.** A body-wide `AC-NN` scan would count an AC merely named in a `signature` or `invariants` field as covered. Resolved by changing Check 3 to read AC identifiers only from explicit `covers:` lists.
- **Empty-rationale enforcement was asserted but unimplemented.** The PRD requires the gate to reject empty rationales in `## Excluded contracts` and `## Uncovered acceptance criteria`, but no check parsed those sections for it. Resolved by extending the structural check to validate both escape-hatch sections (id form plus non-empty rationale), with matching teaching error messages.
- **Seam-extraction regex was not line-anchored.** It could match a seam-shaped string written mid-prose. Resolved by anchoring the regex to line start with `re.MULTILINE` in Check 4.
- **`design-ref` path form is not deep-validated.** The gate accepts any non-literal non-empty string as the path/anchor form. This is intentional — the gate is shape-only and does not resolve files or follow anchors. Resolved by stating this explicitly in `gate-checks.md` and noting the gate does not follow the illustrative anchor.

## Accepted by-design observations

- **The manifest points to the durable decisions log rather than inlining the six decisions.** Intentional: the decisions log outlives the feature while the design pages are deleted at squash-merge. The manifest wording was softened to say so rather than claim the package is fully self-contained.
- **The `#if-d-01` anchor in the `design-ref` example would not resolve on most markdown renderers** (heading slugs include the name). Accepted — the gate does not follow the anchor; a note was added clarifying the value is shape-checked, not resolved.
- **Wording differences for the `invariants` rule between `contracts-standard.md` and `spec-sections.md`** ("pre-condition or post-condition, and at least one error condition" vs "at least one condition and at least one error condition") are functionally equivalent. Accepted as-is.
- **The spec-file-location assumption** (`feature_dir = spec parent`) is the existing project convention the design gate already relies on. Accepted.
- **Field-level validation of the design page itself** (e.g., a design entry with an empty `invariants`) is not performed by the spec gate's design-anchor walk. Accepted for this feature: the design page is authored under the design phase's own review, and the bootstrap exemption means this feature's own page is hand-authored; deep design-page validation is a possible follow-on.
