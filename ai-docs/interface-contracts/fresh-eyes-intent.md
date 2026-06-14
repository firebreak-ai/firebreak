# Fresh-eyes review — interface-contracts intent artifacts (2026-06-09)

Reviewer: `fbk-fresh-eyes-reviewer` (cold read; no authoring context). Artifacts reviewed: `prd.md`, `behavior-inventory.yaml`. Four rounds of cold review ran; the PRD was revised between rounds to address criticals each round surfaced. A final tightening pass compressed the dense paragraphs section 5 had accumulated.

This is the **reduced** report. Each round-4 critical was either fixed in the PRD or deferred to design phase with explicit acknowledgement. The Reduction record section below documents the disposition of every round-4 critical for audit.

## Critical

None.

## Substantive

- `design-ref: none` semantics described differently in the Use cases section than in the Functional requirements section. Both wordings are correct but the tonal mismatch could confuse a spec author. Design phase to tighten.
- Bootstrap exemption (this feature is exempt from its own gate checks) and "every feature with a design phase produces the page" coexist for this feature. The PRD asserts the exemption but does not name what this feature's own spec's `## Interface contracts` section looks like in practice. Design phase will produce a worked example.
- `covers:` non-empty rule may misfit pre-existing blast-radius contracts whose own ACs are out-of-scope for this feature. Design phase to resolve: weaken the rule for `design-ref: pre-existing` entries, add a third escape hatch, or allow empty `covers:` when `design-ref: pre-existing`.
- AC scope for the coverage check is undefined. Whether functional-only or all ACs count for the coverage check is not specified. A noisy `## Uncovered acceptance criteria` section may result. Design phase to specify scope or accept the noise.
- "Empty rationale" rule for escape-hatch sections needs a literal-rule definition. Whitespace-only? Single char? Reserved strings? Design phase to fix.
- Hollow-carry risk (gate ignores signature/invariant drift) depends on spec review running, but the dependency is not signposted as load-bearing in the most prominent place. Optional clarity improvement.
- "Carrying" defined as identifier match but the Use cases prose says the author "takes each entry's identifier and name." Whether the spec entry's `name` must match the design entry's `name` is implicit. Optional clarity improvement.
- Success metric "silent contract drops stop happening" is circular — it measures whether the gate is running, not whether the underlying goal is met. A second-order metric would better capture the goal. Optional metrics improvement.
- Identifier-collision policy when design is re-edited is acknowledged as open but not bounded with a fallback. Design phase to land a concrete policy.
- Seam-coverage failure-path recommendation (add a placeholder entry) conflicts with field-completeness rule. Design phase to resolve: add a third escape hatch (`## Uncovered seams`) or allow placeholder markers.

## Minor

- Path shorthand (`design/contracts.md` vs `ai-docs/<feature>/design/contracts.md`) used interchangeably without flagging they're the same.
- Behavior inventory descriptions are paraphrases of PRD bullets, not canonical wording. Minor drift risk; harmless at intent altitude.
- External sibling features (`wave-commit-model`, the slice-block hygiene PR) referenced without reachable links. The brainstorm work-order is the canonical reference, available in the wiki.
- "Plain language" NFR carve-out for `signature` doesn't address `invariants` (which can also be code-like).
- Success-metric placeholder for operator-help-requested events explicitly admits it's not measurable until baseline emerges. Acknowledged in the PRD.
- `IF-NN` form description permits ambiguous variants (`IF-001`, `IF-100`). Design-phase regex will pin this.
- Gate failure batching behavior not specified (fails-fast vs. batch-all). Implementation detail.

## Reduction record

Round-4 critical observations from the raw fresh-eyes pass and how each was dispositioned:

Gate path resolution under-specified. Fixed in PRD: B-006 now states the spec gate receives the feature directory as an argument per the existing fbk-scripts gate-invocation convention. Gate-invocation pattern is not a novel decision; the PRD cites the existing convention.

Design-anchor check's input format undefined. Reduced as intent-altitude deferral made explicit: the PRD acknowledges that the parse rule for extracting `IF-NN` identifiers from the design page is determined by the standardized shape this feature's design phase defines (B-009), and the gate cannot be implemented before that shape is decided. The shape and the parse rule are a single design-phase deliverable.

Seam-coverage check unbuildable as written. Reduced as deferred to design with explicit acknowledgement in PRD: B-008 names the check at intent altitude; the precise mechanical rule (fields scanned, pair recognition, casing/qualification) is in Open questions as design-phase work. The intent-altitude requirement is "this check exists."

Blast-radius completeness not gate-checkable. Fixed in PRD: B-002 explicitly states that blast-radius completeness is not mechanically verifiable by the spec gate (no upstream enumeration to anchor against). Completeness is spec-author judgment, supported by spec review's brownfield-modifies-existing-contract detection. This converts a previously implicit silent failure mode into a documented design choice with a named mitigating layer.
