# Interface contracts — Product Requirements Document

## Vision

Make the list of interfaces a feature touches into a structured, carried artifact that survives the trip from design through spec into implementation, so contracts can no longer be silently dropped between the layer that planned them and the layer that builds them.

## Problem statement

Today, the design phase produces a contracts page, but nothing in the spec phase carries that list forward. The spec author re-derives contracts from the prose of the intent, and the breakdown step re-derives signatures again from the spec's prose. Each re-derivation is a compression, and at each compression a contract can disappear with no signal. The spec gate does not check the spec's contracts against the design's contracts, and spec review does not check it either. A feature can ship with an interface that was specified at design, forgotten at spec, never tested, and never built — and nothing in the pipeline will notice. The carrying mechanism is missing, the anchor that would make a completeness check possible is missing, and the gate that would run that check is missing.

## Goals and non-goals

**Goals**

- Give the spec a dedicated, structured section that enumerates every interface contract the feature affects, including pre-existing contracts on touched modules (full blast radius).
- Standardize the design's contracts page — document shape and identifier scheme — so a mechanical check can confirm every design-listed contract is accounted for in the spec.
- Run a deterministic spec-gate check that anchors the spec's contracts against the design's contracts and against the feature's acceptance criteria, so silent drops surface as gate failures with a named missing item.
- Provide spec-side escape hatches for intentional scope shifts — one for contracts the spec is dropping, one for acceptance criteria the spec is leaving uncovered — both requiring a free-text rationale the gate enforces as non-empty.
- Have spec review reliably elevate contract drift it detects and leave the response to the operator.

**Non-goals**

- This work does not change the wave or commit model for implementation. That overhaul is the sibling `wave-commit-model` feature.
- This work does not split the implementation-task status taxonomy (`parked` / `accepted-incomplete`). That belongs to the sibling feature.
- This work does not snapshot or hash the design page so the spec gate can detect changes after it has passed. If the design is edited after the spec gate has passed, the operator handles it; spec review will elevate the drift the next time it runs.
- This work does not mechanically judge whether the *right* contract is covering the *right* acceptance criterion. That judgment stays with spec review.

## Use cases

**A spec author carries the design's contracts into the spec (B-001, B-002).**
The author opens the design's contracts page and writes a matching entry in the spec's `## Interface contracts` section for each design entry. The author also adds blast-radius entries — pre-existing contracts on touched modules — using `design-ref: pre-existing` so downstream agents can distinguish "regression-protect this" from "build this."

**A spec author deliberately drops a contract the design enumerated (B-003).**
Scope changed after design. The author writes an entry under `## Excluded contracts` naming the contract and the reason. The gate sees the design identifier as accounted for and passes. The design page is not back-updated — design pages are ephemeral scaffolding deleted at squash-merge.

**A spec author has an acceptance criterion no contract serves (B-004).**
The criterion is covered by something other than a named interface contract — a configuration default, a documentation change, a behavior emerging from existing code without modification. The author records it under `## Uncovered acceptance criteria` with a rationale. The gate passes.

**The spec gate surfaces a missing contract or an uncovered criterion (B-005, B-006, B-007).**
The gate names the specific item, points at where it appears (the design page; the acceptance criteria section), and states the two paths to resolve — carry it, or excuse it under the matching escape-hatch section with a rationale.

**The spec gate surfaces an interface seam with no contract entry (B-008).**
The integration-seam declaration names two interacting components. The gate checks that at least one contract entry names that pair. If none does, the gate fails. This is a mechanical approximation, not authoritative coverage; the operator is the final judge of whether the check misfired.

**A design author writes the standardized design contracts page (B-009).**
Every feature with a design phase produces `design/contracts.md` in the standardized shape this feature defines. When the feature changes no contracts, a single-sentence file suffices.

**Spec review elevates contract drift (B-010).**
Review reports any drift it sees — spec adds a contract not in design, identifier preserved but name/signature changed, design has moved on mid-stream. Review does not adjudicate; the operator decides the response.

## Functional requirements

### Design assumptions and accepted tradeoffs

These shape the requirements below. Each is a deliberate choice; the tradeoff is named with each.

- **Bootstrap exemption.** This feature's own design and spec are exempt from the new gate checks. The standardized shape of `design/contracts.md` is itself this feature's design deliverable; this feature's own design page is hand-authored as the first instance. The gate checks ship as part of this feature's implementation. Enforcement begins on the next feature. *Tradeoff:* the standard's first worked example is this feature itself; future readers will look at it for what a well-shaped contracts page is.

- **Identifier-only carry; signature drift is a review concern.** "Carrying" a contract means the spec entry's `id` matches a design entry's identifier. The deterministic gate does not compare `signature` or `invariants` between same-identifier entries; semantic comparison is spec review's job. *Tradeoff:* when spec review is skipped or lacks the design page, a hollow carry (same id, contradictory content) goes undetected. Spec review running is a load-bearing assumption.

- **Spec mints identifiers for non-design entries.** Blast-radius pre-existing entries and spec-discovered new contracts get identifiers minted by the spec author from the same per-feature `IF-NN` sequence. Collision policy (when design is later re-edited and design's next identifier collides with a spec-minted one) is deferred to design phase; see Open questions.

- **Blast-radius completeness is not gate-checkable.** Touched-but-unchanged contracts have no upstream enumeration to anchor against, so the gate cannot verify the author listed them all. Completeness is spec-author judgment, supported by spec review's brownfield-modifies-existing-contract check.

- **Design-phase deferrals.** Three precise rules live at design altitude, not intent: bound of "touched module" for blast radius; parse rule for `IF-NN` identifiers in the design page; mechanical rule for seam-coverage matching. See Open questions.

### Behavioral requirements

**`## Interface contracts` section with six required fields per entry (B-001).**
Every entry has:
- `id` — `IF-NN` form (zero-padded, at least two digits; gate regex pinned at implementation). Per-feature scope. Inherited verbatim from design when the contract was design-enumerated; minted by the spec from the same sequence otherwise.
- `name` — short descriptive name.
- `signature` — function shape, schema, or interface shape.
- `invariants` — pre/post-conditions and error conditions.
- `covers` — non-empty list of `AC-NN` identifiers this contract serves.
- `design-ref` — a path/anchor into `<feature-dir>/design/contracts.md` (design-enumerated), `pre-existing` (blast-radius), or `none` (spec-discovered).

When the feature changes no contracts, a single-sentence rationale ("No new or changed contracts.") satisfies the presence check; field-completeness applies only to actual entries.

**Blast-radius enumeration (B-002).**
The section lists every affected contract on touched modules, not only contracts this feature introduces. Pre-existing entries use `design-ref: pre-existing`.

**`## Excluded contracts` section (B-003).**
For design-enumerated contracts the spec deliberately does not carry. Each entry has a free-text rationale; the gate rejects empty rationales.

**`## Uncovered acceptance criteria` section (B-004).**
For ACs intentionally not served by any contract. Each entry has a free-text rationale; the gate rejects empty rationales, symmetric with `## Excluded contracts`.

**Spec-gate structural checks on `## Interface contracts` (B-005).**
1. Section present and non-empty.
2. Every contract entry has all six required fields filled.
3. Every entry's `id` matches the `IF-NN` form.
4. Every entry's `covers:` list is non-empty.
5. Every `AC-NN` in any `covers:` list exists in the spec's `## Acceptance criteria` section.

**Spec-gate design-anchor check (B-006).**
The gate reads `<feature-dir>/design/contracts.md` and verifies every `IF-NN` identifier there is either carried into `## Interface contracts` or accounted for in `## Excluded contracts`. The check is one-directional (design → spec); the reverse direction is review's job. On failure: name the missing identifier, point at its design anchor, state the two resolution paths.

**Spec-gate AC-coverage check (B-007).**
Every `AC-NN` in the spec's `## Acceptance criteria` is either covered by some contract's `covers:` list or accounted for in `## Uncovered acceptance criteria`. On failure: name the uncovered criterion, state the two resolution paths.

**Spec-gate light seam-coverage check (B-008).**
The gate reads the existing integration-seam declaration and checks every named component pair is referenced by at least one contract entry. Mechanical approximation only.

**Standardized `design/contracts.md` produced by every feature (B-009).**
This feature's design phase defines the shape and updates the design skill/guide to make it required output. When no contracts change, a single-sentence file suffices.

**Spec review elevates contract drift (B-010).**
Review names spec-added contracts absent from design, identifier-preserving renames, and design changes the spec hasn't picked up. Review does not adjudicate. This feature's design phase decides whether spec review gets a new explicit checklist entry or whether existing review perspectives are extended.

## Non-functional requirements

- **Deterministic gate.** All gate checks are mechanical text operations; same inputs always produce the same pass/fail.
- **Teaching error messages.** Every gate failure names the specific item, points at the artifact that defines it, and states the resolution paths. The gate teaches the convention through its failures.
- **Plain-language artifacts.** The contracts section, escape-hatch sections, and design contracts page are readable by a smart technical lead who is not a coder. `signature` and `invariants` may carry code-shaped text.
- **No new top-level directories.** New content lives inside artifacts the SDL already produces.
- **Operator-overridable through escape hatches.** Every author-intent gate failure has a documented "this is intentional" path in the spec. The gate never blocks an intentional decision the operator has recorded.

## Edge cases and failure modes

- **Design page missing entirely.** Design-anchor check fails with "design page not found" diagnostic; operator runs (or reruns) the design phase.
- **Design page exists with no `IF-NN` entries.** Legitimate no-contracts case. The design-anchor walk passes vacuously; the spec's `## Interface contracts` section still must satisfy the presence check.
- **Author mislabels a new contract as `pre-existing` to bypass the design anchor.** The deterministic gate cannot detect this; spec review compares against the design entry and elevates the mislabel.
- **Design edited after spec gate has passed.** Not detected automatically (named in Non-goals). Spec review elevates drift the next time it runs; operator decides the response.
- **Seam-coverage check fires but the operator believes the seam is genuinely contract-free.** Operator either revisits the integration-seam declaration or adds a contract entry; the check is a heuristic.
- **Single AC covered by multiple contracts.** Allowed and expected. Whether the assignments are correct is spec review's call.

## Dependencies

- **Slice-block hygiene fix lands first.** A separate out-of-ceremony PR aligns the spec guide and spec gate on slice-block vocabulary and field names. The canonical shape (`new-contract | contract-preserving | contract-evolving | cross-cutting` + `covers:`) is assumed to be the surviving shape.
- **Existing `AC-NN` convention.** B-007 reads acceptance-criterion identifiers from the spec's existing `## Acceptance criteria` using the convention the spec gate already enforces.
- **Existing integration-seam declaration.** B-008 reads the existing required spec block.
- **Spec review runs.** Several checks this feature pushes to spec review (mapping correctness, signature correctness, missed-contract detection, brownfield-modifies detection, mislabel detection) depend on spec review actually running. The hollow-carry tradeoff named under Design assumptions and accepted tradeoffs flags this as load-bearing.

## Success metrics

- **Silent contract drops stop happening.** Features reaching implementation with at least one design-enumerated contract neither carried nor excluded in the spec. Target: zero, once enforcing.
- **Uncovered acceptance criteria stop reaching implementation undetected.** Features reaching implementation with at least one AC neither covered nor documented as intentionally uncovered. Target: zero.
- **Escape hatches are used and carry rationales.** On features where scope shifted after design or ACs are intentionally uncovered, the relevant escape-hatch section is non-empty with non-empty rationales. Target: every applicable feature.
- **Spec review elevates drift when it exists.** Sampled across feature runs where drift is known to have happened: review's report names the drift. Target: every sampled case.
- **Operators do not need help interpreting gate failures.** Sampled across spec-author sessions where the gate fails: count of operator-help-requested events. Target placeholder: zero help-requested in the typical case; the metric becomes load-bearing once baseline emerges from real use.

## Open questions

- **Bound of "touched module" for blast-radius enumeration (B-002).** Whether "touched" means files implementation will edit, files a test will import, files reached by transitive import, or author judgment. Deferred to design.
- **Mechanical rule for seam-coverage matching (B-008).** Which fields the gate scans for component names, how a "component pair" is recognized inside an entry, casing/qualification handling. Deferred to design.
- **Identifier-collision policy (B-001).** When design is re-edited after the spec has minted entries and the natural next identifier collides with a spec-minted one. Possible shapes: separate namespaces, design-checks-spec-on-rerun, operator-resolves. Deferred to design.
