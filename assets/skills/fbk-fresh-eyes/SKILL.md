---
description: >-
  Cold comprehension review of a document or artifact. Spawns an isolated
  reviewer with no authoring context and returns severity-categorized
  observations. Invocable standalone, outside of ceremony.
argument-hint: "[artifact-path or feature-name]"
---

Cold comprehension check: a reviewer reads the artifact without authoring context and surfaces what does not make sense, classified by severity. The reviewer has no fix authority — observations only. Fixes return to the authoring agent.

## Argument

If `$ARGUMENTS` is empty, ask: "Which artifact or feature would you like a fresh-eyes review of?" Use the provided value as `<artifact>`. If `$ARGUMENTS` is a feature name (no file extension), resolve the artifact to `ai-docs/<artifact>/<artifact>-spec.md` unless the user specifies otherwise.

## Spawn the reviewer

Invoke the `fbk-fresh-eyes-reviewer` agent in an isolated context. Pass it only the artifact under review — no other files, no authoring history, no prior conversation context. The reviewer reads cold.

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
