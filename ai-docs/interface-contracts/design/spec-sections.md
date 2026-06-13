# Spec-side sections — what the author writes

The exact markdown shape a spec author writes for the three new sections. This is the author-facing format specification; `gate-checks.md` describes how the gate reads these shapes.

## `## Interface contracts` section

Every feature-level spec must contain this section. It belongs after `## Acceptance criteria` and before `## Open questions` in the spec's section ordering.

**No-contracts form** (feature changes no contracts):

```
## Interface contracts

No new or changed contracts in this feature.
```

The gate accepts this as satisfying the presence check. The body must contain that exact sentence.

**Entry form**:

```
## Interface contracts

- id: IF-D-01
  name: <short descriptive name>
  signature: <function shape, schema shape, or interface shape>
  invariants: <pre-conditions; post-conditions; error conditions>
  covers: [AC-01, AC-02]
  design-ref: design/contracts.md#if-d-01

- id: IF-S-01
  name: <short descriptive name>
  signature: <function shape, schema shape, or interface shape>
  invariants: <pre-conditions; post-conditions; error conditions>
  covers: [AC-03]
  design-ref: pre-existing
```

Field rules:

- `id`: Accepts two forms. `IF-D-NN` — a design-originated contract carried from `design/contracts.md`; the identifier is copied verbatim from the design entry and must not be changed. `IF-S-NN` — a spec-originated contract minted by the spec author for a pre-existing blast-radius entry or a spec-discovered new contract. `NN` is zero-padded, minimum two digits. Any other form is a structural gate failure.
- `name`: Short descriptive name, plain prose.
- `signature`: May carry code-shaped text. Must be specific enough to implement from.
- `invariants`: Must name at least one condition and at least one error condition.
- `covers`: YAML inline list, non-empty. Every value must match an `AC-NN` identifier present in `## Acceptance criteria`.
- `design-ref`: Three valid shapes — a path or anchor into `design/contracts.md` (used for carried `IF-D-NN` entries; e.g., `design/contracts.md#if-d-01`), the literal `pre-existing` (used for blast-radius entries — pre-existing contracts on touched modules; always paired with an `IF-S-NN` id), or the literal `none` (used for spec-discovered new contracts that have no design reference and none is expected; always paired with an `IF-S-NN` id). Any other value is a structural failure.

Multiple entries follow consecutively, each starting with `- id:`. There is no sub-heading per entry in the spec — entries are YAML-block list items inside the single `## Interface contracts` section body. This lets the existing section-parsing pattern handle all entries as one section; a `## IF-D-NN` heading per entry would cause the parser to terminate the section at the first entry heading.

## `## Excluded contracts` section

Present only when the spec deliberately does not carry one or more design-originated contracts. Comes after `## Interface contracts`.

```
## Excluded contracts

- id: IF-D-NN
  rationale: <non-empty free text explaining why this contract is not carried>
```

The `id` field here always carries an `IF-D-NN` identifier — excluded entries are always design-originated, because a spec author cannot exclude a contract they minted themselves. An entry with an empty `rationale` field is a structural gate failure, identical to a missing entry.

## `## Uncovered acceptance criteria` section

Present only when one or more acceptance criteria in `## Acceptance criteria` are intentionally not served by any contract entry.

```
## Uncovered acceptance criteria

- id: AC-NN
  rationale: <non-empty free text explaining why no contract covers this criterion>
```

Empty `rationale` is a structural failure, symmetric with `## Excluded contracts`.

## Section ordering in a feature spec

```
## Acceptance criteria           (existing)
## Interface contracts           (new — required)
## Excluded contracts            (new — conditional; omit when not needed)
## Uncovered acceptance criteria (new — conditional; omit when not needed)
## Open questions                (existing)
## Dependencies                  (existing)
```
