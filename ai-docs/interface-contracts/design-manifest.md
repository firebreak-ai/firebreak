# Design Manifest: interface-contracts

Index of the design pages for this feature. Read by the design gate for the bidirectional check: every page listed under "Design pages" exists under `design/`, and every page under `design/` is listed here. The design pages are ephemeral scaffolding deleted at squash-merge; enduring decisions persist in the durable decisions log at `docs/decisions-log.md`.

## For an agent reading this package cold

This package carries everything needed to author the spec: the PRD and the design pages here, plus the durable decisions log. The decisions log lives at `docs/decisions-log.md` rather than inside this folder by design — it outlives the feature, while these design pages are deleted at squash-merge.

- Start with `design/overview.md` for the module shape, the data-flow picture, and the bootstrap exemption.
- `design/contracts-standard.md` is the normative schema for the design contracts page every feature produces; `design/contracts.md` is this feature's own worked instance of that schema.
- This feature is exempt from its own new gate checks (the checks ship as part of its implementation). Its `contracts.md` is the first hand-authored example future authors will read as the reference.

## Design pages

- design/overview.md — module shape, data flow, where the code lands, the two identifier namespaces, and the bootstrap exemption.
- design/contracts-standard.md — the normative schema for `design/contracts.md`: document forms, the `IF-D-NN`/`IF-S-NN` identifier scheme, the entry schema, and the parse rule for gate tooling.
- design/contracts.md — this feature's own interface contracts (the four gate-check functions plus the module interface), and the first worked instance of the standard.
- design/spec-sections.md — the author-facing shape of the three new spec sections: `## Interface contracts`, `## Excluded contracts`, `## Uncovered acceptance criteria`.
- design/gate-checks.md — the four new spec-gate check algorithms (structural, design-anchor, AC-coverage, seam-coverage), with parse rules, set logic, error messages, and the `spec.py` integration.
- design/skill-and-review-changes.md — the three targeted edits to existing assets: the design guide's `contracts.md` requirement, the blast-radius derivation instruction, and the architecture reviewer's contract-drift check.

Decomposition rationale: vertical slices by ownership boundary — the standard (contracts-standard), the worked instance (contracts), what the author writes (spec-sections), what the gate reads (gate-checks), and what changes in neighboring assets (skill-and-review-changes) — so a change to the spec format does not force an edit to the gate algorithm page and vice versa.

Decisions recorded: 6

The six enduring decisions are appended to `docs/decisions-log.md` (all dated 2026-06-09): blast-radius derivation via reference tooling; separate `IF-D`/`IF-S` identifier namespaces; the seam-coverage substring heuristic; the new `contracts.py` gate module; the heading-based parse of the design contracts page; and contract-drift elevation through the architecture reviewer's brief. The decision-by-decision grilling record is in `grilling-log-design.md`.
