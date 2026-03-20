---
id: T-05
type: implementation
wave: 2
covers: ["AC-04"]
files_to_modify: ["../../home/dot-claude/docs/sdl-workflow/review-perspectives.md"]
test_tasks: ["T-02"]
completion_gate: "review-perspectives.md contains pattern consistency criterion with three verification points"
---

## Objective

Adds a pattern consistency criterion to the council review perspectives for brownfield and integration work.

## Context

The current review perspectives at `home/dot-claude/docs/sdl-workflow/review-perspectives.md` defines SDL concerns and review prompt framings but has no criterion for checking whether proposed approaches follow existing codebase patterns. The rendering path split that caused 2 of 5 greenfield bugs was a design-level issue the council review could have caught.

## Instructions

1. In the SDL concerns table, expand the "Architectural soundness" row's review prompt framing to include pattern consistency. Add to the existing prompt framing text:

   "When the spec's technical approach describes integrating with or extending existing modules, also verify: (1) Pattern consistency — does the proposed approach follow the existing pattern or introduce a parallel path? (2) Integration point existence — do the integration points referenced actually exist in the code? (3) Convention visibility — are there conventions in existing code that the spec doesn't mention but tasks will need? Flag these for breakdown discovery."

3. Follow the existing document's format and style. The document uses tables and concise descriptions.

## Files to create/modify

Modify:
- `home/dot-claude/docs/sdl-workflow/review-perspectives.md`

## Test requirements

Semi-manual: Confirm the criterion appears in the review perspectives. During brownfield testing, confirm the council review references pattern consistency when reviewing specs that extend existing modules.

## Acceptance criteria

AC-04: Pattern consistency criterion present with three verification points (pattern consistency, integration point existence, convention visibility).

## Model

Haiku

## Wave

Wave 2
