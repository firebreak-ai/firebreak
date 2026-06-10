# Changes to existing assets

The targeted changes outside `spec.py` that this feature requires: the design skill's `contracts.md` requirement, the blast-radius derivation instruction for the spec-authoring agent, and the spec review addition for contract-drift detection.

## Change 1: Design skill requires `contracts.md`

The design guide at `assets/fbk-docs/fbk-sdl-workflow/design-guide.md` lists `contracts.md` as a typical design page. This feature makes it required.

The addition to the "What the Design Phase Produces" section, under the `contracts.md` bullet:

> `contracts.md` is required on every feature. When the feature changes no contracts, a single sentence ("No new or changed contracts in this feature.") satisfies the requirement. When the feature introduces or modifies contracts, each entry uses the `## IF-D-NN — <name>` heading form defined in the design contracts standard.

The design gate enforces this indirectly: `contracts.md` must be listed in the manifest, and the manifest must be consistent with what is on disk. If the architect writes the file but omits it from the manifest, the design gate catches it. If neither the file nor the manifest entry exists, the spec gate's design-anchor check catches it with the "design page not found" failure.

No change to the design skill's `SKILL.md` is needed — it delegates to the design guide, and the design guide change is the single authoritative update.

**Seam**: design guide (text read by the design skill/architect) → architect authoring behavior → `design/contracts.md` present in the manifest.

## Change 2: Spec-authoring agent derives blast radius from reference tooling

The spec-authoring agent (the skill at `assets/skills/fbk-spec`) computes the blast-radius set deterministically rather than relying on soft judgment. The instruction to add to `feature-spec-guide.md` under the `## Technical approach` section, as a new sub-item after the module-touch policy bullet:

> **Blast-radius derivation** (required when the module-touch policy declares any module as extend or refactor-then-extend): For each module declared as changed, run the project's reference-finding tooling ("find all callers" / "find all importers") against that module to identify every module that calls or imports it. That set of dependents is the blast-radius set for `## Interface contracts`. List each dependent's pre-existing interface contract as a separate entry with `design-ref: pre-existing` and an `IF-S-NN` id. The derivation is a mechanical step, not a judgment call — use the project's available tooling (IDE "find references," `grep -r`, language-specific import-graph tools, or equivalent) against the actual codebase. Note the tooling used in the spec if the method is non-obvious.
>
> The spec gate verifies only that blast-radius entries are present and well-formed (each has all six required fields, each uses `design-ref: pre-existing`, each has an `IF-S-NN` identifier). The gate does not recompute the caller set or check completeness — that check requires per-language analysis the gate does not perform. Per-language completeness verification is a deferred follow-on.

This change lives in `feature-spec-guide.md`. The spec-authoring skill reads that guide and instructs agents accordingly; no separate change to `SKILL.md` files is needed.

**Seam**: `feature-spec-guide.md` instruction → spec-authoring agent behavior → `## Interface contracts` entries with `design-ref: pre-existing`. Failure mode if the agent skips the derivation step: blast-radius entries are absent from the spec. The gate detects an absent design-enumerated contract through the design-anchor check, but it does not detect entirely absent blast-radius entries (those were never enumerated at design). Spec review's brownfield check is the detection mechanism for that gap.

## Change 3: Spec review elevates contract drift

The spec-review skill invokes council agents per the SDL concerns table in `review-perspectives.md`. The architecture reviewer's existing brief addresses integration risks and pattern consistency.

The addition to the architecture reviewer's brief in the SDL concerns table:

> When this feature has a `design/contracts.md` file, compare the spec's `## Interface contracts` section against `design/contracts.md` and report any of the following as informational-severity findings: (1) the spec carries an `IF-S-NN` contract not present in design — "spec-discovered contract not in design"; (2) a carried `IF-D-NN` entry preserves the identifier but the name or signature has materially changed — "identifier-preserving content drift"; (3) the count or names of `IF-D-NN` entries in the design page differ from what the spec carries or excludes — "possible mid-stream design change." Report all three as informational; leave disposition to the operator.

This is a text change to `review-perspectives.md` only. The spec-review `SKILL.md` does not change; it reads `review-perspectives.md` for its instructions. No gate code change is required — contract drift is a semantic concern that belongs in the agent review layer, not the deterministic gate layer.

**Seam**: `review-perspectives.md` architecture-reviewer brief → reviewer behavior during council invocation. Failure mode if the agent does not act on the brief: drift goes unreported. The PRD names spec review running as a load-bearing assumption and accepts this risk explicitly.
