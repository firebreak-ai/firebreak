# Task 13: Create /breakdown Skill

## Objective

Create the user-invocable skill that serves as the Stage 3 entry point for compiling specs into executable task specifications.

## Context

The `/breakdown` skill compiles a reviewed spec into individual task files that implementation agents can execute independently. It is the most transformative stage — turning a human-readable spec into machine-executable instructions.

### Skill behavior

1. **Argument handling**: Expects `/breakdown <feature-name>`. If omitted, ask.

2. **Read inputs**: Load the spec and review outputs from `ai-docs/<feature-name>/`.

3. **Fail fast**: Check Stage 2 gate before proceeding. Call: `"$HOME"/.claude/hooks/sdl-workflow/review-gate.sh <review-path> <perspectives> [threat-model-path]`. If fail, report what's missing and offer to run `/spec-review`.

4. **Load guidance**: Read `home/.claude/docs/sdl-workflow/task-compilation.md` for compilation rules, sizing constraints, and task structure.

5. **Compile tasks**: Transform the spec into task files following the doc's guidance:
   - Separate test tasks from implementation tasks.
   - Size tasks within constraints (1-2 files, <55 lines).
   - Assign to waves based on dependency analysis.
   - Assign model routing (Haiku vs. Sonnet) per task complexity.
   - Build the coverage map: every spec AC → test task + impl task.
   - Write context sections from comprehension, not copy-paste.

6. **Ambiguity detection**: If unable to write unambiguous instructions for a task, stop and report — the spec is underspecified. Offer to return to `/spec` or `/spec-review`.

7. **Output**: Write task files to `ai-docs/<feature-name>/<feature-name>-tasks/`. Produce `task-overview.md` + individual `task-NN-<description>.md` files.

8. **Optional council validation**: If the breakdown is complex (many dependencies, aggressive sizing), classify whether council input would help (Builder for sizing, Analyst for measurability). Present recommendation; user can adjust or skip.

9. **Gate invocation**: Call: `"$HOME"/.claude/hooks/sdl-workflow/breakdown-gate.sh <spec-path> <tasks-dir>`.

10. **Transition**: Present task overview summary. Offer: review individual tasks, invoke council, or proceed. If agreed: invoke `/implement <feature-name>`.

### Frontmatter

```yaml
---
description: >-
  Task breakdown for implementation. Use when breaking down, decomposing,
  or planning implementation of a reviewed feature specification. Compiles
  specs into sized, wave-assigned task files.
argument-hint: "[feature-name]"
---
```

## Instructions

1. Create directory `home/.claude/skills/breakdown/` if it doesn't exist.
2. Create `home/.claude/skills/breakdown/SKILL.md`.
3. Read the created docs at:
   - `home/.claude/docs/sdl-workflow/task-compilation.md` (primary doc)
   - `home/.claude/docs/context-assets/skills.md` (skill authoring principles)
4. Write the skill with:

   **Frontmatter**: As specified above.

   **Body**:

   - **First line**: Route to the compilation doc.
   - **Input loading**: Read spec + review from expected paths. Verify they exist.
   - **Prior stage gate**: Run review gate script. If fail, report and offer to run `/spec-review`.
   - **Compilation**: Instruct the agent to compile per the doc's rules. Emphasize: tasks are executable specifications, not summaries. Ambiguity = compilation error.
   - **Output paths**: Write to `ai-docs/<feature-name>/<feature-name>-tasks/`.
   - **Optional council**: Brief instruction to classify if validation would help.
   - **Gate invocation**: Run breakdown gate script.
   - **Transition**: Summary, options (review/council/proceed), then `/implement`.
   - **Compaction note**: Summarize before invoking next stage.

5. Keep under 80 lines. The compilation doc carries the detail.
6. Do NOT use `allowed-tools`.

## Files to Create/Modify

- **Create**: `home/.claude/skills/breakdown/SKILL.md`

## Acceptance Criteria

- AC-09: Skill loads doc, compiles tasks, runs structural gate, offers transition
- AC-15: Follows skill authoring principles

## Model

Sonnet

## Wave

2
