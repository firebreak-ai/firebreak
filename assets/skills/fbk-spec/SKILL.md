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

## Authoring Loop

Co-author the spec iteratively with the user. Follow the doc for required sections, content requirements, and which clarifying questions to ask.

Refuse to write code. If the user asks for implementation, explain that Stage 1 produces specification artifacts only and implementation begins in Stage 3.

## Gate

When the user signals the spec is complete, run:

```
python3 "$HOME"/.claude/fbk-scripts/fbk.py spec-gate <spec-path>
```

- If the gate fails: report which checks failed and what is missing.
- If the gate passes: present the semantic criteria from the doc for the user to assess. Verify that the testing strategy enumerates all callers of any symbol being removed or renamed, not only the definition site.
- If the user is satisfied: ask "Would you like to move to spec review?"

## Retrospective

After the gate passes, write the Stage 1 section to `ai-docs/$ARGUMENTS/$ARGUMENTS-retrospective.md` following `.claude/fbk-docs/fbk-sdl-workflow/retrospective-guide.md`. Create the file with the feature header if it does not exist. Read the file before writing to preserve existing content from prior stages.

## Transition

Before invoking the next stage: confirm all artifacts are written to disk, then summarize the completed spec (feature name, artifact path, key decisions made during authoring). Compact context before invoking the next skill.

If the user agrees to proceed, invoke `/spec-review $ARGUMENTS`.
