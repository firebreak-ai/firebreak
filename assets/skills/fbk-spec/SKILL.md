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

## Entry

If `$ARGUMENTS` is set, use it as the feature name. Otherwise, ask the user for a name and brief description before proceeding.

Determine scope from the user's description using the doc's guidance:
- Feature-level: create `ai-docs/$ARGUMENTS/$ARGUMENTS-spec.md`
- Project-level: create `ai-docs/$ARGUMENTS/$ARGUMENTS-overview.md`

If the target file already exists, continue iterating on it — do not overwrite.

## Closing ambiguity

Grill the user to close any remaining ambiguity in the spec. Ask detailed questions one at a time. Ask for the user's judgment for any ambiguities that are not trivial or obvious. For each, give your recommendation and justification. When asking the user for a decision, provide the user with all of the detail that they need to decide. Use natural language instead of reference numbers or abbreviations so that the user doesn't need to look up items.

## Gate

When the user signals the spec is complete, run:

```
python3 "$HOME"/.claude/fbk-scripts/fbk.py spec-gate <spec-path>
```

## Retrospective

After the gate passes, write the Stage 1 section to `ai-docs/$ARGUMENTS/$ARGUMENTS-retrospective.md` following `.claude/fbk-docs/fbk-sdl-workflow/retrospective-guide.md`. Create the file with the feature header if it does not exist. Read the file before writing to preserve existing content from prior stages.

## Transition

If the user agrees to proceed (per the guide's transition flow), invoke `/fbk-spec-review $ARGUMENTS`.
