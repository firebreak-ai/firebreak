---
description: >-
  Review a compiled breakdown (task set) for semantic quality at the
  breakdown gate. Use when validating that the tasks produced by breakdown
  are complete, consistent with the spec, and actionable by an implementing
  agent without further design decisions.
argument-hint: "[feature-name]"
---

This skill runs the task-review pipeline with `task-lens.md` as the loaded lens. It spawns one `review-researcher` and one `review-challenger` (cardinality 1/1). Maximum 5 rounds. Write the verdict artifact to `ai-docs/<feature>/task-review.md`.

Invoke as `/fbk-task-review <feature-name>`.

---

## Argument

If `$ARGUMENTS` is empty, ask: "Which feature's task set would you like to review?" Use the provided name as `<feature-name>`.

## Artifact under review

The artifact under review is the compiled task set: all task files under `ai-docs/<feature-name>/tasks/` (or the breakdown's declared task output directory). Locate all task files before spawning the researcher.

## Lens

Load `"$HOME"/.claude/fbk-docs/fbk-review-lenses/task-lens.md` as the active lens for this run. Inject it into every agent spawn. The lens defines finding types (`under-specified`, `coverage-gap`, `sizing-violation`, `spec-conflict`), severities (`critical`, `major`, `minor`), the type-severity validity matrix, and the verdict-contract section for `task-review.md`.

---

## Review loop

The steps below wire the executable pipeline for this skill. This loop follows the shared spine defined in `"$HOME"/.claude/fbk-docs/fbk-review-lenses/review-loop.md`, loaded with `task-lens.md`.

**No preset entry:** task review does not add any entry to `fbk-presets.json`. The task lens (`task-lens.md`) is the single type-filter authority — its type matrix rejects out-of-type findings at the validate step, making a separate domain-filter step and a preset entry unnecessary.

**Severity threshold:** use `minor` as the `--min-severity` value. This matches the skill's prior prose default and surfaces all three severity levels (`critical`, `major`, `minor`).

### Stage 1 — spawn researcher (cold)

Spawn `review-researcher` cold with the full task set, the feature spec as the source of truth, and `"$HOME"/.claude/fbk-docs/fbk-review-lenses/task-lens.md` as the loaded lens. The researcher reads the artifact cold — no prior-round output, no framing beyond the task files, the lens, and the spec. Collect candidate findings as a JSON array.

### Stage 2 — validate and filter (composable pipe)

Run `pipeline validate --lens task-lens.md` followed by `pipeline severity-filter --min-severity minor` as a composable pipe:

```
python3 "$HOME"/.claude/fbk-scripts/fbk.py pipeline validate --lens "$HOME"/.claude/fbk-docs/fbk-review-lenses/task-lens.md | python3 "$HOME"/.claude/fbk-scripts/fbk.py pipeline severity-filter --min-severity minor
```

The lens's type matrix does the type-filtering: findings with a type not listed in the task lens matrix are rejected and logged as `REJECTED: invalid type …`. There is no separate domain-filter step and no preset entry. Retain the surviving, id-bearing list as the orchestrator's record store (the kept list).

### Stage 3 — normalize

Pipe the kept list through:

```
python3 "$HOME"/.claude/fbk-scripts/fbk.py pipeline normalize
```

This produces exactly the six neutral fields the isolation invariant requires the challenger to receive: mechanism, consequence, evidence location, type, severity, and source-of-truth reference.

### Stage 4 — collect cited sources

Collect the documents named in each kept finding's `source_of_truth_ref` field. Inject these cited-source documents into the challenger spawn after the normalized findings and before the verification instructions.

### Stage 5 — spawn challenger (cold)

Spawn `review-challenger` cold with inputs in this order:

1. The artifact under review (task files)
2. The loaded lens (`task-lens.md`)
3. The normalized findings (from stage 3)
4. The cited-source documents collected from `source_of_truth_ref` (from stage 4)
5. The verification instructions

Collect the verdict array as JSON and write it to a temp file.

### Stage 6 — validate verdicts

Pipe the verdicts temp file on stdin:

```
python3 "$HOME"/.claude/fbk-scripts/fbk.py pipeline validate-verdicts < <verdicts-file>
```

This enforces the required verdict fields and enum values on the challenger's output.

### Stage 7 — rejoin by position

Pipe the kept list on stdin through:

```
python3 "$HOME"/.claude/fbk-scripts/fbk.py pipeline rejoin --verdicts <verdicts-file>
```

The count guard fires here: if the number of verdicts does not match the number of kept findings, the rejoin step raises an error before merging. This step produces the merged record set.

### Stage 8 — keep only confirmed findings

Pipe the merged records through `pipeline keep-confirmed`:

```
python3 "$HOME"/.claude/fbk-scripts/fbk.py pipeline keep-confirmed
```

This drops every record the challenger marked `rejected` or `rejected-as-nit`, and surfaces any `unresolvable` record to stderr (unadjudicated — the cited source could not be located) so it is not silently lost. Only `verified` and `verified-pending-execution` records pass to stdout. Without this stage a rejected finding that still carries a valid type and severity would survive the next re-validation and wrongly enter the confirmed set.

### Stage 9 — re-validate and author the verdict

Pipe the confirmed records through `pipeline validate --lens task-lens.md`:

```
python3 "$HOME"/.claude/fbk-scripts/fbk.py pipeline validate --lens "$HOME"/.claude/fbk-docs/fbk-review-lenses/task-lens.md
```

This is a filter-and-renumber, not a pure check: `validate --lens` drops any merged record that fails re-validation (for example, a reclassification that is invalid under the task lens matrix) and renumbers the survivors.

Retain this command's stdout — the re-validated survivor list — as the confirmed finding set. Author the `task-review.md` artifact and its `Verdict:` line by reasoning only over the survivor list (per the verdict logic below), never over the pre-validation merged set.

Task review writes its verdict from its own reasoning (no separate findings report). The rejoin exists to enforce the count guard and produce the survivor set that this re-validation confirms.

---

## Output artifact

Write `ai-docs/<feature-name>/task-review.md` when the loop terminates. The artifact must contain:

- A heading identifying the feature and the review date.
- A summary section describing what the researcher examined.
- A findings section listing confirmed findings with type, severity, location, mechanism, consequence, and evidence.
- Exactly one verdict line as the final meaningful line of the file:

```
Verdict: accepted
```

or

```
Verdict: needs-revision
```

The `Verdict:` line must match `^Verdict: (accepted|needs-revision)$` exactly. No trailing content, no alternative capitalization, no additional verdict lines.

## Verdict logic

Emit `Verdict: needs-revision` when any of the following are true:

- One or more confirmed findings of type `coverage-gap` at any severity.
- One or more confirmed findings of type `spec-conflict` at any severity.
- One or more confirmed findings of type `under-specified` at `critical` severity.
- One or more confirmed findings of type `sizing-violation` at `major` severity.

Emit `Verdict: accepted` when none of the above conditions are met (zero confirmed findings, or only `minor` `under-specified` or `minor` `sizing-violation` findings).

## Blocking behavior

A `needs-revision` verdict blocks the breakdown gate. The breakdown gate reads `task-review.md`; the conversation output is not authoritative. Do not proceed to the breakdown gate until `task-review.md` exists and records a verdict.

If the verdict is `needs-revision`: surface the confirmed findings, allow the author to address them in the task files, then re-run this skill. The gate blocks until the artifact records `accepted`.

## Isolation

Apply the isolation invariant: every researcher reads the artifact cold (no prior-round output, no framing beyond the task files, the lens, and the spec). Every challenger reads the artifact cold before receiving candidate findings. Candidate findings passed to the challenger contain no researcher framing — only mechanism, consequence, evidence location, type, severity, and source-of-truth reference. The `normalize` step (stage 3) is what produces this six-field neutral output, enforcing the isolation invariant at the pipeline level.
