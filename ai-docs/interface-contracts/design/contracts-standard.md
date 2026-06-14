# Standard — the design contracts page

Defines the standardized document schema every feature's `design/contracts.md` must follow. This is the normative reference — not a worked example. For a worked example, see this feature's own `contracts.md`.

## Document-level shape

A `design/contracts.md` file has two possible forms.

**No-contracts form** (feature changes no contracts):
A single sentence: `No new or changed contracts in this feature.`
Nothing else is required. The design gate and the design-anchor walk in the spec gate both pass vacuously.

**Entry form** (feature introduces or modifies at least one contract):
A sequence of contract entries, one per `## IF-D-NN` heading, followed by an optional `## Rationale` section when the overall contracts need contextual explanation.

## Identifier scheme

The `IF` identifier space is split into two namespaces that are structurally separate, so collisions are impossible.

**`IF-D-NN`** — Design-originated contracts. Minted by the design phase for contracts the design introduces or modifies. These identifiers live in `design/contracts.md`. `NN` is a zero-padded decimal integer, minimum two digits, starting from `IF-D-01` per feature.

**`IF-S-NN`** — Spec-originated contracts. Minted by the spec phase for two kinds of entries: pre-existing blast-radius contracts (touched modules whose interfaces were not enumerated at design), and spec-discovered new contracts (interfaces the spec author identifies that design did not enumerate). `NN` is a zero-padded decimal integer, minimum two digits, starting from `IF-S-01` per feature.

**Carry rule**: When the spec carries a design-originated contract forward, the spec entry keeps the `IF-D-NN` identifier verbatim. The spec author does not re-mint the identifier; inheritance means copying the id as-is. Collision between the two namespaces is structurally impossible because the prefixes differ.

The sequence within each namespace is per-feature. Two different features may both have `IF-D-01` without any global conflict, because the identifier is always qualified by its feature directory when read by tooling.

**Supersedes the PRD's illustrative scheme.** The intent-phase PRD sketches a single flat `IF-NN` identifier form and a no-contracts sentence written as "No new or changed contracts." Those were placeholders from before the design phase resolved the identifier-collision question. This design supersedes them: identifiers use the two-namespace `IF-D-NN` / `IF-S-NN` form, and the exact no-contracts sentence is `No new or changed contracts in this feature.` The spec phase reconciles the PRD prose and the behavior inventory to match this design; a spec author should follow the forms defined here, not the PRD's sketch.

## Entry schema for `design/contracts.md`

Each contract entry is a level-two heading followed by four named fields, each on its own line.

```
## IF-D-NN — <name>

- signature: <function shape, schema shape, or interface shape>
- invariants: <pre-conditions; post-conditions; error conditions>
- consumed-by: <comma-separated list of components or phases that call or read this interface>
- produced-by: <component or module that implements this interface>
```

Field rules:

- `## IF-D-NN — <name>`: The heading carries the identifier and a short descriptive name. The identifier is the carry key — the spec and exclusion entries reference it verbatim. The name may change across phases; the identifier must not change once minted.
- `signature`: May carry code-shaped text. Must be specific enough that two independent implementers would produce compatible implementations.
- `invariants`: Must name at least one pre-condition or post-condition, and at least one error condition. "None" is not an acceptable value.
- `consumed-by`: Must name at least one consumer. Components named here are the candidates the seam-coverage heuristic in the spec gate matches against integration-seam declarations.
- `produced-by`: Must name exactly one producer module or component.

## Parse rule for gate tooling

The design-anchor walk in the spec gate identifies contract entries in `design/contracts.md` by scanning for lines matching `^## (IF-D-[0-9]{2,})` with `re.MULTILINE` set (line-start, level-two heading, `IF-D-` prefix, two or more digits). The `re.MULTILINE` flag is required so `^` anchors to the start of every line, not just the start of the document. Each match yields one `IF-D-NN` identifier. The text after `— ` in the heading is the entry name, used only in teaching error messages.

Identifier mentions in prose (for example, "see IF-D-01 above") do not match, because the regex requires the `##` at line start. Only true heading-level entries are counted as contract entries.
