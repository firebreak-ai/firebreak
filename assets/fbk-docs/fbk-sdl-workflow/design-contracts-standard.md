## Design Contracts Standard — Entry Schema

This leaf applies when the feature introduces or changes one or more contracts. It defines the document forms, identifier scheme, and entry schema for `design/contracts.md`.

---

## Document Forms

A feature's `design/contracts.md` takes one of two forms:

**No-contracts form.** When the feature changes no existing contracts and introduces none, the file contains exactly one sentence:

> No new or changed contracts in this feature.

**Entry form.** When the feature introduces or changes contracts, the file contains one entry per contract, each starting with a level-two heading:

```
## IF-D-NN — <name>
```

Entries appear in identifier order.

---

## Identifier Scheme

Two namespaces apply:

- `IF-D-NN` — design-originated contracts. Minted at design time and live in `design/contracts.md`. `NN` is zero-padded, minimum two digits (for example, `IF-D-01`, `IF-D-12`). Use exactly the literal prefix `IF-D` — never substitute a capability- or feature-specific prefix (for example `IF-A` for an "affect" capability). The design-anchor check verifies only `IF-D` ids: a non-IF-D contract heading on the design page fails the gate loudly, and a non-IF-D id anywhere else (a spec's carried-contract entry) is invisible to carry verification — either way, only the literal `IF-D` scheme gets verified.
- `IF-S-NN` — spec-originated contracts. Minted at spec time for blast-radius discoveries and spec-phase additions. Same zero-padding rule.

**Carry rule.** When the spec carries a design contract forward into `spec/contracts.md`, it copies the `IF-D-NN` identifier verbatim — the identifier does not change namespace when it crosses phase boundaries.

---

## Entry Schema

Each entry uses the heading form `## IF-D-NN — <name>` followed by four fields, each on its own line:

```
## IF-D-NN — <name>

signature: <implementable type signature>
invariants: <pre/post-conditions and error conditions>
consumed-by: <one or more consumers>
produced-by: <exactly one producer>
```

**Field rules:**

**signature** — Write a signature that two independent implementers could use without coordinating. It must be precise enough that both would produce compatible implementations.

**invariants** — Name at least one pre-condition or post-condition and at least one error condition. "None" is not a valid value — if you have nothing to write, the entry does not belong in the schema. When an entry carries more than one invariant clause, check them against a partial-failure or edge case together — two clauses that each read correctly alone can still contradict each other in a case neither one names explicitly; state the edge-case resolution as its own clause when they would otherwise conflict.

**consumed-by** — Name at least one consumer. Include the candidates that the spec gate's seam heuristic will match; omitting known consumers causes the gate to flag a seam violation.

**produced-by** — Name exactly one producer. A contract with multiple producers is a design defect — resolve it before recording the entry.

---

## Design-Page Parse Rule

The design-anchor walk identifies contract entries using this pattern applied under `re.MULTILINE`:

```
^## (IF-D-[0-9]{2,})
```

This matches a line-start, level-two heading, `IF-D-` prefix, and two or more digits. Prose mentions of identifiers do not match because `^##` anchors to line start.
