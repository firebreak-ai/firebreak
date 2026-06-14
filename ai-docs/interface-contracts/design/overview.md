# Overview — interface-contracts module shape

## What this feature builds

A carrying mechanism for interface contracts that survives the trip from design through spec into implementation, plus the gate checks that make a silent drop impossible to miss. Four moving parts:

1. **A standardized design contracts page** (`design/contracts.md`) every feature produces, with a fixed shape and identifier scheme so a mechanical check can read it. Defined in `contracts-standard.md`.
2. **Three spec-side sections** the author writes — the contracts list itself, plus two escape hatches for intentional scope shifts. Defined in `spec-sections.md`.
3. **Four new spec-gate checks** that anchor the spec's contracts against the design's contracts and against the feature's acceptance criteria. Defined in `gate-checks.md`; this feature's own contracts page (`contracts.md`) is the first worked instance of the standard.
4. **Two small asset edits** — the spec-authoring guidance gains a blast-radius derivation step, and the architecture reviewer's brief gains a contract-drift check. Defined in `skill-and-review-changes.md`.

## Where the code lands

The four gate checks live in a new module, `fbk/gates/contracts.py`. The existing spec gate, `fbk/gates/spec.py`, imports the four functions and calls them inside its feature-scope branch, after the existing slice check. Data crossing that boundary: the spec text and the feature directory go in; a list of failure strings comes back. This mirrors how the spec gate already delegates to `fbk.injection` and `fbk.slices`.

## How the pieces connect

```
design phase  →  design/contracts.md   (IF-D-NN entries)
                        │
                        │  design-anchor walk reads it
                        ▼
spec phase    →  ## Interface contracts        (carries IF-D-NN; mints IF-S-NN)
                 ## Excluded contracts          (design contracts deliberately dropped)
                 ## Uncovered acceptance criteria (ACs intentionally without a contract)
                        │
                        │  four gate checks read these
                        ▼
spec gate     →  structural + design-anchor + AC-coverage + seam-coverage
                        │
                        ▼
spec review   →  architecture reviewer elevates contract drift (judgment, not gate)
```

## Two identifier namespaces

Contracts carry one of two identifier forms so the two phases can never collide on a number:

- **`IF-D-NN`** — minted by the design phase, lives in `design/contracts.md`. Carried into the spec verbatim.
- **`IF-S-NN`** — minted by the spec phase for blast-radius (pre-existing, touched) contracts and for contracts the spec discovers that design never enumerated.

## The bootstrap exemption

This feature's own design and spec are exempt from the new gate checks — the checks ship as part of this feature's implementation, so enforcement begins on the next feature. This feature's own `contracts.md` is therefore hand-authored as the first worked example of the standard it defines; future authors will read it as the reference for what a well-shaped contracts page looks like.

## What the gate does not do

The gate verifies the **shape** of the contracts list, not the **completeness** of the blast radius. The spec-authoring agent derives the blast-radius set deterministically using the project's own reference tooling; the gate checks each entry is present and well-formed but does not recompute the caller set. Completeness verification across languages is a deferred follow-on, because the gate is language-blind and runs inside arbitrary target projects.
