---
description: >-
  Review a compiled breakdown's cross-task contract consistency. Use
  post-breakdown, pre-implementation to verify that every producer-declared
  contract matches what each consumer task expects, and to write a verdict
  artifact that the implementation-phase gate reads.
argument-hint: "[feature-name]"
---

Route the review through the shared review-loop spine at `fbk-docs/fbk-review-lenses/review-loop.md`, loaded with `fbk-docs/fbk-review-lenses/coherence-lens.md`.

Spawn one `review-researcher` and one `review-challenger` (cardinality 1/1). Maximum 5 rounds. Write the verdict artifact to `ai-docs/<feature>/coherence-review.md`.

---

## Trivial-accept routing

Before spawning the review loop, check whether the feature has any contracts or seams to review.

**Condition:** the feature declares no contracts and no seams — both of the following hold:

1. The spec's interface-contracts section carries only the no-contracts sentence ("No new or changed contracts in this feature.") **or** `design/contracts.md` is absent entirely. An absent `design/contracts.md` is treated as "no design contract entries" and routes to trivial-accept — not to a missing-source loud failure.
2. The spec's technical approach declares no integration seams (the producer→consumer seam checklist is empty).

**When both hold:** skip the review loop. Write a one-line trivial-accept note plus `Verdict: accepted` to `ai-docs/<feature>/coherence-review.md`:

```
No contracts or seams declared — trivial-accept applies.
Verdict: accepted
```

**When either condition does not hold:** run the full review loop. The detection passes in the coherence lens cover whichever dimension is present (contracts, seams, or both).

This is distinct from the missing-lens loud failure (IF-S-01): an absent lens file is a loud failure.
An absent `design/contracts.md` routes to trivial-accept (assuming no seams are present) — these are separate cases and must not be conflated.

---

## What the agents review

The `review-researcher` reads the full task set, the design contracts document, and the spec's integration seams section to inventory producer declarations and consumer expectations. It runs the four detection passes defined in `coherence-lens.md` (contract inventory, seam matching, design contracts alignment, spec seam cross-check) and emits candidate findings with detection source tags.

The `review-challenger` verifies each candidate finding against the coherence lens's reclassification guidance: traces provenance for orphan-declaration candidates, checks whether gaps are in explicitly declared seams, and confirms that contract-ambiguity findings are not reclassified to critical. The challenger applies the lens's type-severity validity matrix and rejects findings that fall outside valid combinations.

---

## Verdict artifact

The artifact at `ai-docs/<feature>/coherence-review.md` carries a verdict line as its final line:

```
Verdict: accepted
```

or

```
Verdict: needs-revision
```

The gate locates the verdict by its `Verdict:` prefix. The artifact must not end with trailing content after the verdict line that would make the prefix unlocatable.

**Passing condition:** no confirmed contract mismatches, contract gaps, or contract ambiguities. Orphan declarations at minor severity do not block.

**Failing condition:** any confirmed `contract-mismatch` or `contract-gap` at any severity; any confirmed `contract-ambiguity` at major severity.
