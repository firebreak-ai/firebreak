---
description: >-
  Design a feature's module shape and contracts after intent, or co-author a
  design. Use when moving from a confirmed PRD to an architecture — module list,
  dependency graph, schemas, interface contracts, and decomposition rationale.
argument-hint: "<feature-name>"
---

Read `.claude/fbk-docs/fbk-sdl-workflow/design-guide.md` for the detailed phase instructions: artifact structure, decomposition rationale format, design-manifest shape, and decision-record conventions.

## Entry

If `$ARGUMENTS` is set, use it as the feature name and derive `<feature-dir>` as `ai-docs/$ARGUMENTS`. Otherwise ask the user for the feature name before proceeding.

## Prerequisite probe (mid-pipeline entry)

Before any design authoring, call `fbk.precheck.check_prerequisites("design", <feature_dir>)`.

If `prd.md` is missing the probe returns it as the missing artifact with `intent` as the upstream phase. In that case:

- Name the missing artifact (`prd.md`) and explain that the design phase needs a completed intent phase first.
- Offer to run `/fbk-intent $ARGUMENTS` to produce it.
- Do not hard-block: if the operator has the PRD content at hand and wants to proceed, allow it.

An operator with a clear enough idea may also skip design entirely and start at spec — design is a capability, not a forced step.

## Design authoring

Delegate drafting to the `fbk-architect` agent in authoring mode. The agent is context-isolated and has no Write tool — the skill owns all file writes. The architect produces module lists, dependency graphs, schemas, interface contracts, and decomposition rationale.

When a design choice has multiple reasonable options, invoke `fbk-grilling` to surface each choice with recommendation and tradeoff before the operator decides.

## Artifacts

Write the following to `ai-docs/<feature>/`:

- `design/` — one page per capability, each with shape, contracts, and decomposition rationale
- `design-manifest.md` — index of all design pages, including a non-zero "Decisions recorded" count line that points to `docs/decisions-log.md`

Append enduring decisions (status-bearing entries) to `docs/decisions-log.md` — the project-relative durable decisions log. The manifest points to this log and never duplicates it.

## Gate

When the operator signals design is complete, invoke `fbk-fresh-eyes` on the design pages and manifest before running the gate.

For a foundational module — one most other capabilities will import — also run a cross-model second-opinion review (`/fbk-cross-model-review`) of the design pages in parallel with fresh-eyes, before running the gate. The skill no-ops for projects that have not opted in. Adjudicate every candidate finding against the design and shipped code before applying it.

Then run:

```
python3 "$HOME"/.claude/fbk-scripts/fbk.py design-gate <feature-dir>
```

The gate checks the manifest↔directory consistency, decomposition rationale presence, non-zero "Decisions recorded" count, injection scan, and no open critical fresh-eyes findings.

## Retrospective and transition

After the gate passes:

1. Append the design stage section to `ai-docs/<feature>/<feature>-retrospective.md` following `.claude/fbk-docs/fbk-sdl-workflow/retrospective-guide.md`. Read the file first to preserve prior stage content.
2. Summarize and compact.
3. With operator approval, invoke `/fbk-spec $ARGUMENTS`.
