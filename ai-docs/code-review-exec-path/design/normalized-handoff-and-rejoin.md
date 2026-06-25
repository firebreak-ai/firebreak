# The neutral handoff and the re-join — the second defect

## The problem in one line

The challenger is meant to judge each candidate cold, but code review hands it the full findings — titles, detection-source tags, suggested fixes, confidence — so its "independent" verdict is biased.

## What independence requires

The handoff from researcher to challenger must pass through a normalization step that strips a finding down to exactly six neutral fields: `mechanism`, `consequence`, `evidence`, `type`, `severity`, and `source_of_truth_ref`. The location is folded into the evidence string; no `id`, no `title`, no detection-source tag, no remediation hint survives. The challenger's own contract already says it receives only those six fields. The code-review skill contradicts this — it spawns the challenger with the full findings and an explicit "no format translation between agents" instruction.

## Make the strip a tool, not a prose promise

Add a `normalize` subcommand to the pipeline. It reads a list of findings and emits the six-field records, one per input finding, in the same order.

```
pipeline normalize        # reads findings on stdin, emits six-field records on stdout
```

The subcommand takes no arguments. The six neutral fields are the same for every finding-mode review type — they are the independence boundary itself, not a per-lens choice. If that boundary ever needed to change, that is a design-level revision, not a command-line flag, so there is no `--lens` on `normalize`. This replaces the prose instruction in every finding-mode skill with a call that provably produces exactly six fields.

## The end-to-end data flow

The wrinkle: the normalized record carries no stable identifier, yet the orchestrator must (a) map each challenger verdict back to the full finding it kept, to build the report, and (b) re-validate after the challenge, against a required set that demands `title` and `location` — which normalized records lack. The resolution is the same for all four finding-mode review types.

**Stage 1 — detect.** The researcher emits full findings (no `id`).

**Stage 2 — validate and filter, with the lens.** The orchestrator runs the findings through validation (lens supplied), which assigns `S-NN` ids, and through the severity filter. It keeps this full, id-bearing list as its own record store.

**Stage 3 — normalize for the handoff.** The orchestrator pipes the kept list through `pipeline normalize` and hands the challenger only the resulting six-field records. The ids and titles stay on the orchestrator's side; they never reach the challenger.

**Stage 4 — challenge.** The challenger returns one verdict record per input record, in the same order — its contract already guarantees "the same array you received, with verdict fields added."

**Stage 5 — re-join by position.** The orchestrator overlays each verdict onto the full finding it kept at the same position. The overlay is deliberately narrow: it takes from the challenger only the **verdict fields** (`status`, `verification_evidence`, `rejection_reason`, `adjacent_observations`) and any **reclassified `type`/`severity`** the challenger changed. It does **not** copy back the six neutral fields the challenger received — those are unchanged copies of what the orchestrator already holds, and copying them back would re-apply the location into the evidence string a second time (the normalize step folds location into evidence). So the merged record is the kept full finding (`id`, `title`, `location`, original `evidence`, …) with the verdict fields added and type/severity updated if reclassified.

**The correlation key is position**, with a known limitation worth stating plainly. Position is the only stable handle once `id` and `title` are deliberately withheld, and it is implied by the challenger's same-array-same-order contract. A content hash was considered and rejected (it needs stable serialization and breaks on trivial field variation). The orchestrator checks that the verdict count equals the kept-finding count, which catches a dropped or inserted record. **What a count check does not catch is a same-length reordering** — if the challenger returned its records shuffled, every position would mis-join silently. The challenger reads cold and has no instruction or incentive to reorder, and the contract says same-order, so the residual risk is low — but it is real, and position-only cannot detect it. **Decision (locked 2026-06-24): position-only, no hardening this iteration.** An opaque echoed index token was considered and declined: it would add a carried field to the six-field handoff the parent feature just locked as its isolation invariant, a heavier change to a freshly-settled contract than a low-probability silent mis-join warrants. The limitation is accepted and documented, not hidden behind the count check. The token remains a clean future follow-on only if a real reorder is ever observed in practice — it is not a spec-phase open item.

**Stage 6 — re-validate, with the lens.** The merged records (which carry `title` and `location` again) are run back through the validator with the lens supplied — the same `cmd_validate` that Contract 1 teaches to read a lens. Be precise about what this command does: it is not a pure check. `cmd_validate` **drops** any record it rejects and **renumbers** the survivors' `S-NN` ids. So a reclassification that lands on an invalid type-severity combination is removed here, and the surviving ids are reassigned. That is acceptable and matches how code review already treats challenger output today: the re-join (stage 5) has already happened, so dropping a record at stage 6 cannot corrupt the correlation; and the human-facing finding identifiers (`F-NN`) are assigned afterward, so the `S-NN` renumber is invisible downstream. The lens is required here, not just at stage 2: without it, the re-validation would check reclassified combinations against code review's built-in matrix, which does not know the other review types' finding types and would wrongly reject them as unknown types.

**Stage 7 — report.** Only code review renders a human-facing findings report from the surviving merged records; that step is unchanged and reads only fields the merged record carries. The other three review types write their verdict artifact from the orchestrator's own reasoning, so for them the re-join exists only to satisfy stage-6 re-validation, not to feed a formatter.

## Which exact call X-1 breaks

The "validator rejects every finding" defect is specific to the **detection-round validation** — the `run`/`validate` call at stage 2, before any id exists. The post-challenge validation at stage 6 works on records that already have ids, so it was never the broken call. This page's stage-6 change is made for a different reason: to validate the other review types' reclassifications against their own lens, which the built-in matrix cannot do. Keeping the two reasons separate avoids the impression that one fix addresses both calls.

## Realizes

The normalization-callable and isolation-invariant contracts, made executable rather than prose-trusted, and the routing half of the normalize-in-the-path requirement. See `contracts.md`.
