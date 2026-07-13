---
description: >-
  Review a test set for integrity at a pipeline checkpoint or standalone.
  Use when validating that AI-written tests actually catch the behavior they
  claim to cover, at either the pre-lock gate (before hash-locking) or the
  final gate (after implementation, invoked by code-review).
argument-hint: "[feature-name or test-path]"
---

Route through the shared review-loop spine (`fbk-docs/fbk-review-lenses/review-loop.md`) with `test-lens.md` loaded. Spawn one `review-researcher` to surface candidate test-integrity findings and one `review-challenger` to verify them (cardinality 1 researcher / 1 challenger, round cap 5). The caller or operator selects the mode — **spec**, **pre-lock**, or **final** — based on where in the pipeline the review occurs.

## Mode routing

**Spec checkpoint** — invoked during spec review, after the council is clean and the review document is stable. Reviews the spec's planned testing strategy against its own requirements, criteria, and integration seams: for each requirement, does the planned test actually prove the behavior? Only an `accepted` spec verdict lets the spec gate pass.

**Pre-lock mode** — invoked by the breakdown agent before applying hash locks to test files. Reviews test tasks and test implementations to verify they are ready to lock. Only an `accepted` pre-lock verdict triggers lock application downstream.

**Final mode** — invoked by the code-review gate after implementation is complete. Reviews the full set of tests covering the changed module, including pre-existing locked tests that the contract-preserving slice keeps. Only an `accepted` final verdict allows the code-review gate to close.

When invoked standalone (outside the pipeline), the caller specifies the mode explicitly. If mode is not specified, ask before proceeding.

## What the agent reviews

**Spec checkpoint:** the stabilized spec — its requirements, acceptance criteria, and declared integration seams. The agent walks each requirement and asks whether its planned test would actually prove the behavior, and whether each declared seam has end-to-end coverage planned. It works from the spec alone, with no council memory or findings.

**Pre-lock:** test task files and test implementations for the current slice. Checks that implementations faithfully translate tasks, trace to ACs, pass Tier 1 mechanical checks, and are structured to fail before implementation (red before implementation).

**Final:** the full set of tests covering the changed module — both tests written in this slice and pre-existing tests the manifest locks. Checks for weakened assertions, trivially-passing tests, unauthorized test modification, drift from the locked manifest, and (for contract-evolving slices) that the retired-tests list is justified and the surviving tests protect the surviving contract.

## Artifact

Every mode writes an artifact to `ai-docs/<feature>/test-review-<checkpoint>.md`.

- The spec checkpoint writes `ai-docs/<feature>/test-review-spec.md` — the canonical spec-checkpoint artifact name the spec/review gate reads.
- The pre-lock pass writes `ai-docs/<feature>/test-review-pre-lock.md` (or the checkpoint label the breakdown supplies).
- The final pass writes `ai-docs/<feature>/test-review-final.md` — the canonical final-checkpoint artifact name the code-review gate reads.

The artifact carries a verdict line, exactly one of:

```
Verdict: accepted
Verdict: needs-revision
```

A `needs-revision` verdict at any checkpoint blocks the downstream gate. The verdict is load-bearing — downstream gates read the artifact file, not the agent's conversation output. Both the spec gate and the code-review gate locate the artifact in the feature folder and read its `Verdict:` line, so the verdict must be emitted as a `Verdict:` line for the gate to find it.

A confirmed finding's `remediation` field is an advisory fix direction, not a verified patch. Before applying a suggested fix, re-derive it against the artifact and cited source directly — a plausible-sounding remediation can itself be wrong, and applying one unverified can break a correct implementation.

## Review loop

This loop follows the shared spine, with `"$HOME"/.claude/fbk-docs/fbk-review-lenses/test-lens.md` as the loaded lens. Because there is no preset entry for test review (see the no-preset rule below), type-filtering is done by the lens's type matrix inside `validate --lens`, not by a domain-filter step.

Executable commands use the full installed lens path. The short label `test-lens.md` appears in prose step introductions as a readable reference only — it is not passed to the pipeline directly.

Severity default: `minor` (no explicit prose default existed in this skill before; `minor` is the conservative floor for test-integrity concerns and is overridable by operator instruction).

1. **Stage 1 — spawn researcher (cold).** Spawn `review-researcher` with the artifact under review, `"$HOME"/.claude/fbk-docs/fbk-review-lenses/test-lens.md`, and the source of truth. Instruct the researcher to output candidate findings as a JSON array. Completion: a cold researcher spawn produces the JSON candidate array.

2. **Stage 2 — validate and filter (composable pipe).** Run `pipeline validate --lens test-lens.md` followed by `pipeline severity-filter --min-severity minor` as a composable pipe:

   ```
   python3 "$HOME"/.claude/fbk-scripts/fbk.py pipeline validate --lens "$HOME"/.claude/fbk-docs/fbk-review-lenses/test-lens.md | python3 "$HOME"/.claude/fbk-scripts/fbk.py pipeline severity-filter --min-severity minor
   ```

   The lens's type matrix does the type-filtering — a finding whose type is outside the lens's allowed types is rejected and logged as `REJECTED: invalid type …`. There is no separate domain-filter step and no preset entry. Retain the kept, id-bearing list as the orchestrator's record store.

3. **Stage 3 — normalize.** Pipe the kept list through:

   ```
   python3 "$HOME"/.claude/fbk-scripts/fbk.py pipeline normalize
   ```

   This produces the six neutral fields handed to the challenger.

4. **Stage 4 — collect cited sources.** For each kept finding in the normalized list, collect the documents named in that finding's `source_of_truth_ref` field. Inject those documents into the challenger spawn as additional context, positioned after the normalized findings and before the verification instructions.

5. **Stage 5 — spawn challenger (cold).** Spawn `review-challenger` with inputs in this order: (a) artifact under review, (b) `"$HOME"/.claude/fbk-docs/fbk-review-lenses/test-lens.md`, (c) normalized findings JSON, (d) cited-source documents collected in stage 4, (e) verification instructions. Collect the verdict array as JSON and write it to a temp file.

6. **Stage 6 — validate-verdicts.** Pipe the verdicts temp file on stdin:

   ```
   python3 "$HOME"/.claude/fbk-scripts/fbk.py pipeline validate-verdicts < <verdicts-file>
   ```

   This fails the handoff if any verdict has an invalid status or is missing the evidence its status requires. This replaces any prose verdict-field check.

7. **Stage 7 — rejoin by position.** Pipe the retained kept list on stdin through:

   ```
   python3 "$HOME"/.claude/fbk-scripts/fbk.py pipeline rejoin --verdicts <verdicts-file>
   ```

   This produces the merged records. The count guard fires here — a mismatch between the number of kept findings and the number of verdicts is a hard failure.

8. **Stage 8 — keep only confirmed findings.** Pipe the merged records through `pipeline keep-confirmed`:

   ```
   python3 "$HOME"/.claude/fbk-scripts/fbk.py pipeline keep-confirmed
   ```

   This drops every record the challenger marked `rejected` or `rejected-as-nit`, and surfaces any `unresolvable` record to stderr (unadjudicated — the cited source could not be located) so it is not silently lost. Only `verified` and `verified-pending-execution` records pass to stdout. Without this stage a rejected finding that still carries a valid type and severity would survive the next re-validation and wrongly enter the confirmed set.

9. **Stage 9 — re-validate and author the verdict.** Pipe the confirmed records through `pipeline validate --lens test-lens.md`:

   ```
   python3 "$HOME"/.claude/fbk-scripts/fbk.py pipeline validate --lens "$HOME"/.claude/fbk-docs/fbk-review-lenses/test-lens.md
   ```

   This is a filter-and-renumber, not a pure check: `validate --lens` drops any merged record that fails re-validation (for example a reclassification whose new type or severity is invalid under the lens matrix) and renumbers the survivors' `S-NN` ids. Retain this command's stdout — the re-validated survivor list — as the confirmed finding set.

   Test review writes its verdict from the orchestrator's own reasoning, not from a formatted findings report. The rejoin in stage 7 exists to enforce the count guard and to produce the survivor set that this re-validation confirms. Reason only over the confirmed survivor list when authoring the `Verdict:` artifact line — never over the pre-validation merged set.

## No-preset rule

No entry is added to `fbk-presets.json` for test review. The lens is the single type-filter authority — a preset entry would duplicate the lens's type list and invite drift.
