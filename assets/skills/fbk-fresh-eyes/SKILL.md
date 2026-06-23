---
description: >-
  Adversarial review of a document or artifact. Spawns an isolated reviewer
  that treats the author as unreliable and returns severity-categorized
  observations of what the author missed. Invocable standalone, outside of
  ceremony.
argument-hint: "[artifact-path or feature-name]"
---

Adversarial review: a reviewer reads the artifact without authoring context, treats the author as unreliable, and surfaces what the author missed, classified by severity. The reviewer has no fix authority — observations only. Fixes return to the authoring agent.

## Argument

If `$ARGUMENTS` is empty, ask: "Which artifact or feature would you like a fresh-eyes review of?" Use the provided value as `<artifact>`. If `$ARGUMENTS` is a feature name (no file extension), resolve the artifact to `ai-docs/<artifact>/<artifact>-spec.md` unless the user specifies otherwise.

## Spawn the reviewer

Spawn the generic `review-researcher` agent as a cleared agent, loaded with `fresh-eyes-lens.md`, at degenerate cardinality (0 challengers, round cap 1) per the shared review-loop spine's degenerate-cardinality rule. Pass it the artifact under review, plus any cross-cutting convention files the artifact consumes — an authoritative conventions document, a shared config or interface definition, a naming or event registry the artifact builds on — so the researcher can check the artifact against the convention it should follow rather than re-deriving it. Pass nothing else: no authoring history, no prior conversation context, no review of how the artifact came to be. The researcher reads cold, and the convention files are reference material to compare against, not a record of the author's reasoning.

## Collect observations

The reviewer returns observations grouped under `## Critical`, `## Substantive`, and `## Minor`. Collect these without modification.

## Write the report

Write the observations to `ai-docs/<feature>/fresh-eyes-<artifact>.md` using exactly the three section headings the reviewer produced:

```
## Critical
## Substantive
## Minor
```

Add a one-line header identifying the artifact reviewed and the date. Do not add editorial commentary or summaries.

## Gate interpretation

The fresh-eyes output feeds the intent and design gates. The gate bar for the Critical section is: **no observation entries after dedup**. If `## Critical` contains entries, the gate fails. Report this to the user; do not suppress or reclassify critical observations to make the gate pass.

## No-fix rule

This skill observes; it does not fix. If the reviewer surfaces problems, relay them to the user and let them decide whether to invoke the authoring agent to address them before proceeding.
