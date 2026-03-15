# Task 11: Create /spec Skill

## Objective

Create the user-invocable skill that serves as the Stage 1 entry point for iterative spec authoring.

## Context

The `/spec` skill is invoked by the user (or recognized from natural language) to begin designing a specification. It loads the detailed guidance from the leaf doc and orchestrates the spec authoring process.

### Skill behavior

1. **Argument handling**: User invokes `/spec <name>` or `/spec` without a name.
   - If name provided: create artifact directory `ai-docs/<name>/` and start the spec file.
   - If omitted: ask the user for a name and brief description.

2. **Load guidance**: Read `home/.claude/docs/sdl-workflow/feature-spec-guide.md` for detailed stage instructions. This doc tells the agent how to co-author the spec.

3. **Scope recognition**: Determine project-level vs. feature-level from the user's description. Project-level: produce overview + feature decomposition. Feature-level: produce feature spec.

4. **Iterative co-authoring**: Work with the user to build the spec. Draft sections, ask clarifying questions on meaningful design decisions, incorporate feedback, surface open questions.

5. **Refuse code**: This stage produces specification artifacts only. If the user asks to implement, redirect to completing the spec first.

6. **Verification gate**: When the user signals the spec is complete, call the gate script: `"$HOME"/.claude/hooks/sdl-workflow/spec-gate.sh <path-to-spec>`. Report results.

7. **Transition**: If gate passes and user approves, invoke `/spec-review <feature-name>`.

### Mid-pipeline entry

If the user invokes `/spec <name>` and the spec already exists, continue iterating on the existing spec rather than starting fresh.

### What the skill body should contain vs. what goes in the doc

The skill body (SKILL.md) should contain:
- Frontmatter configuration
- The high-level orchestration flow (steps 1-7 above)
- The routing instruction to read the leaf doc
- The gate script invocation command

The leaf doc (feature-spec-guide.md) contains the detailed guidance: section structures, testing strategy requirements, scope recognition patterns, etc. The skill body should NOT duplicate this — it routes to the doc.

### Frontmatter fields

```yaml
---
description: >-
  Spec-driven feature or project specification. Use when designing a new
  feature, planning a project, or co-authoring a specification document.
  Guides iterative spec creation through structured sections.
argument-hint: "[feature-name]"
---
```

`user-invocable: true` is the default and can be omitted. The description must be specific enough for natural-language matching (when the user describes wanting to design or plan something) but not so broad that it fires on general coding tasks.

## Instructions

1. Create directory `home/.claude/skills/spec/` if it doesn't exist.
2. Create `home/.claude/skills/spec/SKILL.md`.
3. Read the created docs at:
   - `home/.claude/docs/sdl-workflow/feature-spec-guide.md` (the doc this skill routes to)
   - `home/.claude/docs/context-assets/skills.md` (skill authoring principles)
4. Write the skill with:

   **Frontmatter**: As specified above. Confirm against skill authoring principles.

   **Body** (the instructions the agent follows when the skill activates):

   - **First line**: Route to the leaf doc — "Read `~/.claude/docs/sdl-workflow/feature-spec-guide.md` for detailed guidance."
   - **Entry flow**: Check if name is provided via `$ARGUMENTS`. If yes, create `ai-docs/$ARGUMENTS/$ARGUMENTS-spec.md` (or `$ARGUMENTS-overview.md` for project-level). If no, ask the user.
   - **Existing spec**: If the spec file already exists at the expected path, continue iterating — do not overwrite.
   - **Scope recognition**: Brief instruction to determine project vs. feature from user description and the doc's guidance.
   - **Authoring loop**: Co-author iteratively. Reference the doc for section structure and content requirements.
   - **Gate invocation**: When user signals completion, run: `"$HOME"/.claude/hooks/sdl-workflow/spec-gate.sh <spec-path>`. Present results per the doc's transition protocol.
   - **Transition**: If gate passes and user approves, invoke `/spec-review $ARGUMENTS`.
   - **Compaction note**: Before invoking the next stage, summarize the completed spec (feature name, artifact path, key decisions) to carry context through compaction.

5. Keep the skill body under 80 lines. The detailed guidance is in the doc — the skill orchestrates.
6. Do NOT use `allowed-tools` — spec authoring needs full tool access (reading codebase, writing files, running gate script).

## Files to Create/Modify

- **Create**: `home/.claude/skills/spec/SKILL.md`

## Acceptance Criteria

- AC-07: Skill loads doc, handles both scopes, runs structural gate, offers transition
- AC-15: Follows skill authoring principles — clear description, concise body, routes to doc

## Model

Sonnet

## Wave

2
