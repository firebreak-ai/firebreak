---
description: >-
  Review a compiled breakdown (task set) for semantic quality at the
  breakdown gate. Use when validating that the tasks produced by breakdown
  are complete, consistent with the spec, and actionable by an implementing
  agent without further design decisions.
argument-hint: "[feature-name]"
---

This preset runs the shared review-loop spine from `assets/fbk-docs/fbk-review-lenses/review-loop.md` with `task-lens.md` as the loaded lens. It spawns one `review-researcher` and one `review-challenger` (1/1 cardinality), with a round cap of 5, and writes a verdict artifact at `ai-docs/<feature>/task-review.md`.

Invoke as `/fbk-task-review <feature-name>`.

## Argument

If `$ARGUMENTS` is empty, ask: "Which feature's task set would you like to review?" Use the provided name as `<feature-name>`.

## Artifact under review

The artifact under review is the compiled task set: all task files under `ai-docs/<feature-name>/tasks/` (or the breakdown's declared task output directory). Locate all task files before spawning the researcher.

## Lens

Load `assets/fbk-docs/fbk-review-lenses/task-lens.md` as the active lens for this run. Inject it into every agent spawn. The lens defines finding types (`under-specified`, `coverage-gap`, `sizing-violation`, `spec-conflict`), severities (`critical`, `major`, `minor`), the type-severity validity matrix, and the verdict-contract section for `task-review.md`.

## Review loop

Follow the shared review-loop spine in `review-loop.md` exactly. Configured for this preset:

- **Researcher:** `review-researcher` — reads the task files cold with `task-lens.md` and the feature spec as source of truth. Produces candidate findings in the finding schema.
- **Challenger:** `review-challenger` — reads the task files cold, then receives the normalized candidate findings and `task-lens.md`. Verifies or rejects each candidate.
- **Cardinality:** 1 researcher, 1 challenger.
- **Round cap:** 5.
- **Minimum severity threshold:** `minor` (all three severity levels surface).

Between rounds, validate candidate findings against the `lens-matrix` block in `task-lens.md` (types, severities, required fields). Reject malformed candidates before passing to the challenger.

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

If the verdict is `needs-revision`: surface the confirmed findings, allow the author to address them in the task files, then re-run this preset. The gate blocks until the artifact records `accepted`.

## Isolation

Apply the isolation invariant from `review-loop.md`: every researcher reads the artifact cold (no prior-round output, no framing beyond the task files, the lens, and the spec). Every challenger reads the artifact cold before receiving candidate findings. Candidate findings passed to the challenger contain no researcher framing — only mechanism, consequence, evidence location, type, severity, and source-of-truth reference.
