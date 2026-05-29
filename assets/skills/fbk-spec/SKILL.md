---
description: >-
  Spec-driven feature or project specification. Use when designing a new
  feature, planning a project, fixing a bug, investigating an issue,
  planning a fix, or co-authoring a specification document. Guides
  iterative spec creation through structured sections.
argument-hint: "[feature-name]"
---

Read `.claude/fbk-docs/fbk-sdl-workflow/feature-spec-guide.md` for detailed guidance on section structure, scope recognition, iterative authoring, and the verification gate.

When the user describes corrective work (bug reports, failing tests, fix intent), read `.claude/fbk-docs/fbk-sdl-workflow/corrective-workflow.md` for diagnostic and fast-track workflows.

When the feature modifies or extends existing code (brownfield work), read `.claude/fbk-docs/fbk-brownfield-spec.md` for codebase-first authoring constraints.

## Inputs

The spec phase builds on upstream artifacts. Before authoring, confirm these exist under `ai-docs/<feature>/`:

- `prd.md` — product requirements document (intent + user-facing behavior)
- `behavior-inventory.yaml` — enumerated behaviors from the PRD
- `design/` pages — design decisions, data flow, component interactions
- `design-manifest.md` — index of design pages and key decisions

Use installed paths when referencing these: `.claude/fbk-docs/...` and `$HOME/.claude/fbk-scripts/...`.

## Entry

If `$ARGUMENTS` is set, use it as the feature name. Otherwise, ask the user for a name and brief description before proceeding.

Determine scope from the user's description using the doc's guidance:
- Feature-level: create `ai-docs/$ARGUMENTS/$ARGUMENTS-spec.md`
- Project-level: create `ai-docs/$ARGUMENTS/$ARGUMENTS-overview.md`

If the target file already exists, continue iterating on it — do not overwrite.

## Prerequisite check

When invoked directly (not chained from an upstream phase), call:

```
fbk.precheck.check_prerequisites("spec", <feature_dir>)
```

If the design manifest (`design-manifest.md`) is missing, name the missing artifact and offer to run the design phase first — for example: "The design manifest is missing. Would you like to run `/fbk-design` before continuing?" This is non-blocking: if the user chooses to proceed without it, continue.

## Closing ambiguity

Compose `fbk-grilling` narrowed to "how" questions — technical choices, file organization, and integration decisions. Do not re-ask intent or behavior questions already resolved in the PRD or behavior inventory. See the guide's narrowed-grilling guidance for the question categories.

## Slices

After the technical approach section is drafted, author a `## Slices` block in the spec. Each entry declares one independently testable slice:

```yaml
slices:
  - name: <slice-name>
    description: <what this slice delivers>
    test-discipline: <unit | integration | e2e | contract>
    contract: <path to contract file, or "none">
    retired-tests: <list of test IDs retired when this slice evolves the contract, or "none">
```

The four `test-discipline` values are: `unit`, `integration`, `e2e`, `contract`. Use the value that reflects the dominant validation shape for the slice. The spec gate validates this block — every slice must have all five fields.

## Gate

When the user signals the spec is complete, run:

```
python3 "$HOME"/.claude/fbk-scripts/fbk.py spec-gate <spec-path>
```

## Retrospective

After the gate passes, write the Stage 1 section to `ai-docs/$ARGUMENTS/$ARGUMENTS-retrospective.md` following `.claude/fbk-docs/fbk-sdl-workflow/retrospective-guide.md`. Create the file with the feature header if it does not exist. Read the file before writing to preserve existing content from prior stages.

## Transition

If the user agrees to proceed (per the guide's transition flow), invoke `/fbk-spec-review $ARGUMENTS`.
