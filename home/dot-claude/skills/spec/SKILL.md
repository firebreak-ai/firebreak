---
description: >-
  Spec-driven feature or project specification. Use when designing a new
  feature, planning a project, fixing a bug, investigating an issue,
  planning a fix, or co-authoring a specification document. Guides
  iterative spec creation through structured sections.
argument-hint: "[feature-name]"
---

Read `home/dot-claude/docs/sdl-workflow/feature-spec-guide.md` for detailed guidance on section structure, scope recognition, iterative authoring, and the verification gate.

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
"$HOME"/.claude/hooks/sdl-workflow/spec-gate.sh <spec-path>
```

- If the gate fails: report which checks failed and what is missing.
- If the gate passes: present the semantic criteria from the doc for the user to assess.
- If the user is satisfied: ask "Would you like to move to spec review?"

## Transition

Before invoking the next stage: confirm all artifacts are written to disk, then summarize the completed spec (feature name, artifact path, key decisions made during authoring). Compact context before invoking the next skill.

If the user agrees to proceed, invoke `/spec-review $ARGUMENTS`.
