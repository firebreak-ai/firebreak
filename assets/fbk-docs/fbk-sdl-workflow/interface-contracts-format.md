# Interface Contracts Format — Spec Side

This leaf describes the three section shapes a spec author fills when the feature has interface contracts to record, exclude, or has acceptance criteria that no contract covers. Read this leaf when you are enumerating contracts, excluding a design contract, or noting an uncovered acceptance criterion. The minimal case (no contracts in this feature) does not require this leaf — see the one-sentence form described in `feature-spec-guide.md`.

---

## Section ordering

The spec sections that carry contract information appear in this fixed order:

1. `## Acceptance criteria` (existing required section)
2. `## Interface contracts` (required — present in every feature spec)
3. `## Excluded contracts` (conditional — present only when one or more design contracts are excluded)
4. `## Uncovered acceptance criteria` (conditional — present only when one or more ACs have no covering contract)
5. `## Open questions` (existing required section)
6. `## Dependencies` (existing required section)

---

## Interface contracts

The `## Interface contracts` section is required in every feature spec. Its body is one of two forms:

**No-contracts form.** When the feature introduces no new or changed contracts, write this single sentence as the entire body:

```
No new or changed contracts in this feature.
```

**Contract-entry form.** When the feature has contracts to record, write each contract as a YAML-block list item. Do not use a sub-heading per entry — a heading per entry causes the section parser to terminate at the first entry. The section body is a flat YAML list.

Each entry carries these fields:

- `id`: the contract identifier. Two valid forms:
  - `IF-D-NN` — a contract carried verbatim from the design contracts page (`design/contracts.md`), where `NN` is the zero-padded two-digit number assigned there (e.g., `IF-D-01`, `IF-D-12`).
  - `IF-S-NN` — a contract minted by the spec author, either because the contract was discovered during spec work with no design antecedent, or because it is a pre-existing contract on a module the feature touches (a blast-radius entry). `NN` is zero-padded, minimum two digits, assigned sequentially within this spec.
- `name`: a short descriptive name for the contract (plain prose, no identifier).
- `signature`: the callable form — function signature, HTTP route, message schema, or equivalent. Use the exact runtime representation.
- `invariants`: a list of at least one normal-path condition and at least one error condition. Write each as a plain sentence.
- `covers`: a non-empty YAML inline list of acceptance criterion identifiers (e.g., `[AC-03, AC-07]`). Every value must match an entry in `## Acceptance criteria`. A contract with no covering AC is a signal that the AC is missing.
- `design-ref`: one of three valid forms (described below).

Example entry:

```yaml
- id: IF-D-03
  name: Token validation endpoint
  signature: "POST /auth/validate → {valid: bool, claims: object | null}"
  invariants:
    - Returns valid=true and a populated claims object when the token signature and expiry check pass.
    - Returns valid=false and claims=null when the token is expired, malformed, or has an invalid signature.
  covers: [AC-04, AC-06]
  design-ref: design/contracts.md#if-d-03
```

---

## The three design-ref forms

Every contract entry carries a `design-ref` that records where the contract originated:

1. **Path/anchor into the design contracts page** — used for `IF-D-NN` entries carried from the design phase. The value is a relative path and anchor, for example `design/contracts.md#if-d-03`. The spec reviewer uses this to verify the spec entry matches the design entry (the design-anchor check).

2. **`pre-existing`** — used for `IF-S-NN` entries that represent pre-existing contracts on modules the feature touches (blast-radius entries). The value is the literal string `pre-existing`. Always paired with an `IF-S-NN` id.

3. **`none`** — used for `IF-S-NN` entries discovered during spec work that have no design reference. The value is the literal string `none`. Always paired with an `IF-S-NN` id.

---

## Blast-radius derivation

Before closing the `## Interface contracts` section, derive the blast radius: the dependent set of every module the spec declares changed.

1. Identify the modules listed in the spec's `## Technical approach` module touch policy as *extend* or *refactor-then-extend* (any module whose code changes).
2. Run the project's reference tooling against those modules to find all callers and consumers. From the repo root: `python3 "$HOME"/.claude/fbk-scripts/fbk.py deps --module <module-path>` (or the equivalent reference command for this project).
3. For each pre-existing contract found on a touched module or its dependents, add an entry with a new `IF-S-NN` id, `design-ref: pre-existing`, and fill the remaining fields from the existing contract definition.
4. If the blast radius is empty (no pre-existing contracts on any touched module or dependent), no entries are added and no note is required.

---

## Excluded contracts

The `## Excluded contracts` section is conditional — include it only when one or more contracts from the design contracts page are intentionally excluded from this feature's spec.

Each entry carries:

- `id`: the `IF-D-NN` identifier from the design contracts page.
- `rationale`: a non-empty explanation of why this contract is excluded (e.g., deferred to a later feature, out of scope per the non-goals, handled by a different spec).

Example:

```yaml
## Excluded contracts

- id: IF-D-05
  rationale: Deferred to the rate-limiting feature; not in scope per non-goals.
```

When no contracts are excluded, omit this section entirely.

---

## Uncovered acceptance criteria

The `## Uncovered acceptance criteria` section is conditional — include it only when one or more acceptance criteria in `## Acceptance criteria` are not covered by any contract entry in `## Interface contracts`.

Each entry carries:

- `id`: the `AC-NN` identifier from the acceptance criteria section.
- `rationale`: a non-empty explanation of why this AC has no covering contract (e.g., purely behavioral with no interface boundary, covered by a test strategy entry instead, implementation detail with no observable contract).

Example:

```yaml
## Uncovered acceptance criteria

- id: AC-09
  rationale: Performance requirement — verified by load test in testing strategy, not by a contract boundary.
```

When all acceptance criteria are covered by at least one contract, omit this section entirely.
