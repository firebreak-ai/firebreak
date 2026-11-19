# Review lens format

Use when creating or changing a standalone review lens. Keep domain-specific detection criteria in the lens and generic researcher/challenger behavior in `review-loop.md`.

Lenses live under `fbk-docs/fbk-review-lenses/`. Current lenses are code, test, fresh-eyes, quality, and doc-reconcile.

## Identity and output

Declare what the lens examines and its output mode:

- `output_mode: finding` for code and test review: candidate findings pass through the executable pipeline and an independent challenger.
- `output_mode: scan` for fresh-eyes, quality, and doc-reconcile: observations use the lens's own report format and remain unverified by a challenger.

Use `output_contract: findings-artifact` for finding reports and `output_contract: observation-format` for scan reports. These labels guide the orchestrator; the Python pipeline does not validate the full prose structure of a lens. Reports do not provide managed phase acceptance.

## Detection and source authority

Define finding types and severities with concrete boundaries. Name the artifact and governing sources to read, the defect each pass detects, and the evidence needed to support it. A pass must produce a checkable observation rather than a preference disguised as a requirement.

Reference `shared-detection.md` for passes used by multiple lenses. Keep passes with one consumer in that lens or its referenced domain guide.

Describe domain-specific challenger criteria: source comparisons, reachable type/severity reclassifications, and evidence needed to resolve an apparent dead path or contract mismatch. The challenger reads original sources before ruling.

## Machine-readable finding matrix

Finding-mode lenses include a fenced `lens-matrix` block. The pipeline reads the exact type vocabulary, severity vocabulary, valid combinations, and required fields from this block. For example:

```lens-matrix
types: [behavioral]
severities: [critical, major]
matrix:
  behavioral: [critical, major]
required: [title, location, type, severity, mechanism, consequence, evidence]
```

Keep the block consistent with the explanatory tables. The researcher emits no identifier; validation assigns one. Scan-mode observations follow their stated report schema instead of the finding matrix.

## Report contract

Specify the report's fields, ordering, and interpretation of an empty result. Finding reports distinguish confirmed findings from unresolved evidence. Scan reports clearly identify their observations as advisory. Use the project's review directory, default `reviews/`, or an explicit caller-supplied path.
