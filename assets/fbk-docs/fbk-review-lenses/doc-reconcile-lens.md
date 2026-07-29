# Doc Reconcile Lens

## 1. Lens identity

This lens reconciles the shipped module's code against the project's durable docs, surfacing every place where a doc claims something the code no longer supports (drift) or where the match is ambiguous and worth a closer look (note).

```
output_mode: scan
output_contract: observation-format
```

This is a scan-mode lens. It bypasses `validate_sighting()`. Observations are validated only against the structural output schema declared in the observation-format section below. No `lens-matrix` block is present.

---

## 2. Finding types

Not applicable. This lens is `output_mode: scan`. It does not produce finding-shaped records and does not route through the finding validator. The output schema is the two-class (`drift` / `note`) taxonomy declared in the observation-format section.

---

## 3. Severity levels

Not applicable. This lens is `output_mode: scan`. The output schema uses `class` (`drift` / `note`) rather than a severity axis. No severity field appears in the output records.

---

## 4. Type-severity validity matrix

Not applicable. This lens is `output_mode: scan` and carries no `lens-matrix` block. The researcher's output is validated only against the structural schema in the observation-format section.

---

## 5. What to look for (researcher instructions)

The researcher receives a set of `(kind, path)` pairs — the durable docs in scope — and the shipped-module file paths. For each doc in scope, compare the doc's claims against the code and emit a record for every mismatch or ambiguous signal.

Apply the per-doc comparison guidance for each doc kind:

- **Decisions ledger** — code that contradicts a recorded decision is drift; a decision whose mechanism the code has refactored but still honors is a note.
- **Contracts file** — signature or shape mismatch is drift; renamed-but-equivalent surfaces are a note.
- **Package layout** — files in a package the layout doesn't describe, imports against the layout's stated direction, or an architecture diagram whose depicted components or connections no longer match the shipped code, are drift.
- **Changelog** — unrecorded user-facing changes are drift; recorded entries whose described change doesn't match the diff are also drift.
- **Spec** — unmet claims the spec implies are now true are drift; claims whose phrasing has gone stale but whose intent is met are notes.

When a doc carries a claim whose shape doesn't fit its doc kind (e.g., a spec containing a contracts-shaped claim about a function signature), apply the per-doc guidance that most closely matches the claim's shape rather than the guidance keyed to the doc kind.

Apply the classification rules:

- **drift** — concrete divergence. The doc names something (a function, a file, a contract field, a stated decision) the code doesn't contain or contradicts. Clear mismatch.
- **note** — ambiguous signal. The doc references something at a name the code might still implement under a different name, or describes a behavior that's been refactored such that direct comparison is hard. Worth a look but might be benign.

Emit one record per observation, carrying all five required fields: `class`, `doc`, `doc_says`, `code_shows`, `rationale`. Do not propose fixes. Do not modify any file. This is an advisory-only, read-only pass.

---

## 6. Source-of-truth handling

The researcher compares the artifact (the shipped module's code and file paths) against each durable doc in the in-scope `(kind, path)` pair list. The durable docs are the source of truth for the claims being checked against the code.

When no durable docs are found, or none reference the shipped module by name, file path, or feature scope, the researcher returns an empty result and the skill writes `no durable docs to reconcile`.

No spec or external contract is used as a source of truth for the reconciler's own output shape; the output shape is declared in the observation-format section below.

---

## 7. Challenger instructions

This lens runs at zero-challenger cardinality (degenerate scan-only preset). The challenge stage does not run. This section is present for format completeness; no challenger disciplines apply.

---

## 10. Observation format (`output_contract: observation-format`)

Doc-reconcile output is a JSON array of records. Each record carries exactly these five fields:

| Field | Type | Description |
|---|---|---|
| `class` | string | `"drift"` or `"note"` — no other values are valid |
| `doc` | string | Which durable doc and where in it the claim appears |
| `doc_says` | string | The doc's claim, quoted or summarized |
| `code_shows` | string | The contradicting or diverging code observation |
| `rationale` | string | One sentence justifying the classification |

**Ordering**: all `drift` records must appear before all `note` records in the array.

**Advisory only**: this output does not gate code-review pass/fail. The operator reviews each item and decides whether to update the doc, accept the asymmetry as intentional, or mark it as historical.

**Structural schema for the conformance check**: the output is a JSON array (`[]`) of objects. Each object must have all five keys listed above. `class` must be one of `drift` or `note`. No additional fields are required; extra fields do not fail the conformance check but are not expected.

The artifact is written to `ai-docs/<feature>/doc-reconcile.md`. When the researcher returns no records, the skill writes `no drift found` instead.
