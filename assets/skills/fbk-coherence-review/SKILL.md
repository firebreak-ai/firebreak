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

1. The spec's interface-contracts section carries only the no-contracts sentence ("No new or changed contracts in this feature.") **and** the design contracts page has no contract entries. Both sides must hold: if the spec declares any interface contract, this condition fails even when `design/contracts.md` is absent. An absent `design/contracts.md` counts only as "no design contract entries" (the design side of this condition) — it does not by itself satisfy condition 1, and it is never a missing-source loud failure.
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

## Review loop

The steps below apply when the trivial-accept condition does not hold. The trivial-accept branch above short-circuits before reaching this section.

**No preset entry:** coherence review does not add any entry to `fbk-presets.json`. The coherence lens (`coherence-lens.md`) is the single type-filter authority — its type matrix rejects out-of-type findings at the validate step, making a separate domain-filter step and a preset entry unnecessary.

**Severity threshold:** use `minor` as the `--min-severity` default (coherence review has no prior numeric prose default; all three severity levels surface). Operators may override this threshold by explicit instruction.

### Stage 1 — spawn researcher (cold)

Spawn `review-researcher` cold with the full task set, the design contracts document (`design/contracts.md`), and the spec's integration-seams section as the artifact and source of truth, plus `"$HOME"/.claude/fbk-docs/fbk-review-lenses/coherence-lens.md` as the loaded lens. Collect candidate findings as a JSON array.

### Stage 2 — validate and filter (composable pipe)

Run `pipeline validate --lens coherence-lens.md` followed by `pipeline severity-filter --min-severity minor` as a composable pipe:

```
python3 "$HOME"/.claude/fbk-scripts/fbk.py pipeline validate --lens "$HOME"/.claude/fbk-docs/fbk-review-lenses/coherence-lens.md | python3 "$HOME"/.claude/fbk-scripts/fbk.py pipeline severity-filter --min-severity minor
```

The lens's type matrix does the type-filtering: findings with a type not listed in the coherence lens matrix are rejected and logged as `REJECTED: invalid type …`. There is no separate domain-filter step and no preset entry. Retain the surviving, id-bearing list as the orchestrator's record store (the kept list).

### Stage 3 — normalize

Pipe the kept list through:

```
python3 "$HOME"/.claude/fbk-scripts/fbk.py pipeline normalize
```

This produces the normalized findings the challenger will receive.

### Stage 4 — collect cited sources

Collect the documents named in each kept finding's `source_of_truth_ref` field. Inject these cited-source documents into the challenger spawn after the normalized findings and before the verification instructions.

### Stage 5 — spawn challenger (cold)

Spawn `review-challenger` cold with inputs in this order:

1. The artifact under review (task set, design contracts, spec seams section)
2. The loaded lens (`coherence-lens.md`)
3. The normalized findings (from stage 3)
4. The cited-source documents collected from `source_of_truth_ref` (from stage 4)
5. The verification instructions

Collect the verdict array as JSON and write it to a temp file.

### Stage 6 — validate verdicts

Pipe the verdicts temp file through:

```
python3 "$HOME"/.claude/fbk-scripts/fbk.py pipeline validate-verdicts
```

This enforces the required verdict fields and enum values on the challenger's output.

### Stage 7 — rejoin by position

Pipe the kept list on stdin through:

```
python3 "$HOME"/.claude/fbk-scripts/fbk.py pipeline rejoin --verdicts <verdicts-file>
```

The count guard fires here: if the number of verdicts does not match the number of kept findings, the rejoin step raises an error before merging. This step produces the merged record set.

### Stage 8 — re-validate and author the verdict

Pipe the merged records through `pipeline validate --lens coherence-lens.md`:

```
python3 "$HOME"/.claude/fbk-scripts/fbk.py pipeline validate --lens "$HOME"/.claude/fbk-docs/fbk-review-lenses/coherence-lens.md
```

This is a filter-and-renumber, not a pure check: `validate --lens` drops any merged record that fails re-validation (for example, a reclassification that is invalid under the coherence lens matrix) and renumbers the survivors.

Retain this command's stdout — the re-validated survivor list — as the confirmed finding set. Author the `Verdict:` artifact by reasoning only over the survivor list (per the passing and failing conditions below), never over the pre-validation merged set.

Coherence review writes its verdict from its own reasoning (no separate findings report). The rejoin exists to enforce the count guard and produce the survivor set that this re-validation confirms.

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
