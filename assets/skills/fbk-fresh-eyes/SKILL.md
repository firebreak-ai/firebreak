---
description: >-
  Adversarial review of a document or artifact. Spawns an isolated reviewer
  that treats the author as unreliable and returns severity-categorized
  observations of what the author missed. Invocable standalone, outside of
  ceremony.
argument-hint: "[artifact-path or feature-name]"
---

Adversarial review: a reviewer reads the artifact without authoring context, treats the author as unreliable, and surfaces what the author missed, classified by severity. The reviewer has no fix authority — observations only. Fixes return to the authoring agent.

## Reviewer execution

Resolve the installed directory from `${CLAUDE_PROJECT_DIR:-$PWD}/.claude` when
it contains `fbk-scripts/fbk.py`, otherwise `$HOME/.claude`. Read
`fbk-docs/workflow/reviewer-execution.md` there and launch each reviewer as it
describes. Publish the requested report after the round completes. A missing
check is a limitation, never an invented result.

## Argument

If `$ARGUMENTS` is empty, ask: "Which artifact or feature would you like a fresh-eyes review of?" Use the provided value as `<artifact>`. If `$ARGUMENTS` is a feature name (no file extension), resolve the artifact to `.fbk/<artifact>/spec.md` unless the user specifies otherwise.

## Run the reviewer round

Write the reviewer's instruction file under `.fbk/runtime/` (for example `.fbk/runtime/fresh-eyes-instructions.txt`). It contains, in this order: `fbk-docs/review/researcher-role.md` in full; `fbk-docs/fbk-review-lenses/fresh-eyes-lens.md`; the cardinality statement (0 challengers, round cap 1) per the shared review-loop spine's degenerate-cardinality rule; the artifact under review, plus any cross-cutting convention files the artifact consumes — an authoritative conventions document, a shared config or interface definition, a naming or event registry the artifact builds on — so the researcher can check the artifact against the convention it should follow rather than re-deriving it; applicable requirements and source-attributed authorization for proposed contract changes or phase scope as original comparison sources; and the output instructions: return the observations grouped under `## Critical`, `## Substantive`, and `## Minor` as prose in `result: {report: "..."}`. Include no authoring history, no prior conversation context, no review of how the artifact came to be. The researcher reads cold, and the convention files are reference material to compare against, not a record of the author's reasoning.

Then launch the round, with `firebreak_dir` resolved as the reviewer-execution section describes and `--required` naming the artifact and each convention or requirement file the instructions cite:

```bash
python3 "$firebreak_dir/fbk-scripts/fbk.py" review-round begin --root "$PWD" \
  --instructions .fbk/runtime/fresh-eyes-instructions.txt \
  --contributors reviewer --required <artifact> <convention-and-requirement-files>
python3 "$firebreak_dir/fbk-scripts/fbk.py" review-round run --round ID --contributors reviewer
python3 "$firebreak_dir/fbk-scripts/fbk.py" review-round require-complete --round ID
```

Use the returned round ID. Read the reviewer's result path that `run` returns; the observations are the prose under `result.report`.

## Collect observations

The reviewer returns observations grouped under `## Critical`, `## Substantive`, and `## Minor` inside `result.report`. Collect these without modification once `require-complete` has passed.

## Write the report

Write the observations to `reviews/fresh-eyes-<artifact-name>.md` using exactly the three section headings the reviewer produced:

```
## Critical
## Substantive
## Minor
```

Add a one-line header identifying the artifact reviewed and the date. Do not add editorial commentary or summaries.

## No-fix rule

This skill observes; it does not fix. If the reviewer surfaces problems, relay them to the user and let them decide whether to invoke the authoring agent to address them before proceeding.
