---
description: >-
  SDL entry point: starting the SDL, opening an intent interview, or
  co-authoring a PRD for a new feature. Produces the intent artifacts
  (PRD, behavior inventory, grilling log) and runs the intent gate.
argument-hint: "<feature-name> <terse description>"
---

Read `.claude/fbk-docs/fbk-sdl-workflow/intent-guide.md` for the detailed phase instructions — the required PRD sections, the behavior inventory format, the architecture-overview read-first behavior, and the gate criteria.

## Entry

If `$ARGUMENTS` is set, parse the first token as the feature name and the remainder as the terse description. Otherwise, ask the user for a feature name and a one-sentence description before proceeding.

Before beginning the interview, read `docs/architecture-overview.md` to inherit existing project intent and direction. For an established project, ask only about the delta — what is new or different about this feature relative to what the overview already describes.

Open an interview to draw out what the work is and why. Probe for: the user problem being solved, behavioral scope boundaries, success criteria, and user-flow edge cases.

## Techniques

When product-level ambiguity surfaces that cannot be closed by inference — behavior-inventory completeness, user-flow edge cases, acceptance-criteria boundaries — invoke `fbk-grilling` to run structured grilling questions. Record each decision in `grilling-log-intent.md` with a `Confirmed:` reflect-back line per decision.

At gate closure, invoke `fbk-fresh-eyes` on the PRD and behavior inventory. Frame the spawn so the reviewer treats items already pinned elsewhere (seam-doc deferrals, pre-staged design-phase work) as scoping decisions for a later phase, not open intent questions. Before passing the report to the gate, compare the fresh-eyes raw report against the grilling log and remove observations that map to already-resolved grilling-log decisions. Pass only the reduced report to the gate.

## PRD drafting

Delegate PRD drafting to the `fbk-product-author` agent (context-isolated so the draft is produced cold). The agent returns PRD prose; this skill owns the file write — the agent has no Write tool. PRD content is behavioral only: no implementation details, no file targets, no code paths.

## Artifacts

Produce the following in `ai-docs/<feature>/`:

- `prd.md` — behavioral PRD content only
- `behavior-inventory.yaml` — structured behavior list with IDs
- `grilling-log-intent.md` — grilling decision log with `Confirmed:` lines

## Architecture overview

This skill reads `docs/architecture-overview.md` before drafting to inherit project intent. When the feature shifts project intent — a new convention, architectural direction, or standing constraint — update `docs/architecture-overview.md` in the feature branch so the change merges with the code.

## Gate

When the PRD and behavior inventory are complete and the fresh-eyes report has been reduced against the grilling log, run:

```
python3 "$HOME"/.claude/fbk-scripts/fbk.py intent-gate <feature-dir>
```

## Retrospective and transition

After the gate passes:

1. Write artifacts to `ai-docs/<feature>/` (if not already written).
2. Update `docs/architecture-overview.md` if project intent shifted.
3. Append the intent stage section to `ai-docs/<feature>/<feature>-retrospective.md` following `.claude/fbk-docs/fbk-sdl-workflow/retrospective-guide.md`. Create the file with the feature header if it does not exist; read before writing to preserve existing content.
4. Summarize the intent phase outcomes for the operator.
5. Compact.
6. With operator approval, invoke `/fbk-design <feature-name>`.
