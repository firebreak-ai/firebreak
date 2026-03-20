# Task 12: Create /spec-review Skill

## Objective

Create the user-invocable skill that serves as the Stage 2 entry point for SDL spec review with council agents.

## Context

The `/spec-review` skill orchestrates the review of a completed spec through SDL lenses using council agents. It handles classification, invocation, finding synthesis, threat model determination, and transition.

### Skill behavior

1. **Argument handling**: Expects `/spec-review <feature-name>`. If omitted, ask for the feature name.

2. **Read spec**: Load the spec from `ai-docs/<feature-name>/<feature-name>-spec.md`.

3. **Fail fast**: Check Stage 1 gate before proceeding. Call: `"$HOME"/.claude/hooks/sdl-workflow/spec-gate.sh <spec-path>`. If the gate fails, report what's missing and offer to run `/spec <feature-name>` to fix it. Do not proceed to review with a structurally incomplete spec.

4. **Load guidance**: Read `home/dot-claude/docs/sdl-workflow/review-perspectives.md` for detailed review instructions.

5. **Council classification**: Analyze the spec and project context. Select which council agents to invoke and in what mode (solo/discussion/full). Present the classification with rationale. Proceed unless the user intervenes to adjust.

6. **Invoke council**: Use the existing `/council` skill with the classified agents. Frame each agent's review with the SDL-specific prompts from the review perspectives doc.

7. **Synthesize findings**: Consolidate council feedback into `ai-docs/<feature-name>/<feature-name>-review.md`. Organize by SDL concern, not by agent. Tag each finding with severity (blocking/important/informational).

8. **Threat model determination**: Present security summary. Ask the user: "Does this feature need a threat model?" Record decision in review doc.
   - If yes: read `home/dot-claude/docs/sdl-workflow/threat-modeling.md` and guide threat model creation. Output: `ai-docs/<feature-name>/<feature-name>-threat-model.md`.
   - If no: record skip with rationale in review doc.

9. **Gate invocation**: Call: `"$HOME"/.claude/hooks/sdl-workflow/review-gate.sh <review-path> <perspectives> [threat-model-path]`.

10. **Transition**: Handle blocking findings (revise spec or accept with rationale). If resolved and user approves, invoke `/breakdown <feature-name>`.

### On re-run

If the review document already exists (user revised spec and re-ran), replace it entirely. Do not append to stale findings.

### Frontmatter

```yaml
---
description: >-
  SDL spec review using council agents. Use when reviewing, validating,
  or checking a completed feature specification. Invokes security,
  architecture, and quality review perspectives.
argument-hint: "[feature-name]"
---
```

## Instructions

1. Create directory `home/dot-claude/skills/spec-review/` if it doesn't exist.
2. Create `home/dot-claude/skills/spec-review/SKILL.md`.
3. Read the created docs at:
   - `home/dot-claude/docs/sdl-workflow/review-perspectives.md` (primary doc)
   - `home/dot-claude/docs/sdl-workflow/threat-modeling.md` (conditional doc)
   - `home/dot-claude/docs/context-assets/skills.md` (skill authoring principles)
4. Write the skill with:

   **Frontmatter**: As specified above.

   **Body**:

   - **First line**: Route to the perspectives doc.
   - **Spec loading**: Read spec from expected path. Check it exists.
   - **Prior stage gate**: Run spec gate script. If fail, report and offer to run `/spec`.
   - **Classification**: Instruct the agent to classify per the doc's guidance, present to user, proceed.
   - **Council invocation**: Instruct the agent to invoke `/council` with selected agents and SDL-framed prompts.
   - **Finding synthesis**: Write review document. Organization and severity tagging per the doc.
   - **Threat model determination**: The active decision flow. If yes, load threat-modeling.md.
   - **On re-run**: If review doc exists, warn user it will be replaced and proceed.
   - **Gate invocation**: Run review gate script with appropriate arguments.
   - **Transition**: Blocking finding resolution, then offer `/breakdown`.
   - **Compaction note**: Summarize before invoking next stage.

5. Keep under 100 lines. This skill has more steps than `/spec` but the doc carries the detail.
6. Do NOT use `allowed-tools` — needs full access for codebase analysis, council invocation, file writing.

## Files to Create/Modify

- **Create**: `home/dot-claude/skills/spec-review/SKILL.md`

## Acceptance Criteria

- AC-08: Skill loads doc, classifies council, invokes review, handles threat model, runs gate, transitions
- AC-15: Follows skill authoring principles

## Model

Sonnet

## Wave

2
