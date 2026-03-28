---
id: T-04
type: implementation
wave: 2
covers: [AC-01, AC-02, AC-03, AC-04, AC-05, AC-06, AC-07, AC-08]
depends_on: [T-02]
files_to_create: [assets/skills/fbk-improve/SKILL.md]
test_tasks: [T-03]
completion_gate: "T-03 tests pass"
---

## Objective

Creates the `/fbk-improve` skill definition that orchestrates self-improvement analysis from retrospective observations.

## Context

This skill is invoked either automatically after code review retrospective finalization or manually by the user. It orchestrates: retrospective location, Firebreak installation discovery, agent spawning, proposal presentation, and selective application of accepted changes.

Follow the skill format in existing files like `assets/skills/fbk-code-review/SKILL.md`: YAML frontmatter with description, argument-hint, allowed-tools; markdown body with sections for entry, workflow steps, and edge cases.

The skill references the `fbk-improvement-analyst` agent (created in T-02) and the context asset authoring rules at `fbk-docs/fbk-context-assets.md`.

## Instructions

1. Create `assets/skills/fbk-improve/SKILL.md` with YAML frontmatter:
   - `description:` — "Pipeline self-improvement from retrospective observations. Use when analyzing a retrospective to propose targeted improvements to Firebreak context assets, or after code review retrospective finalization."
   - `argument-hint: "<feature-name>"`
   - `allowed-tools: Read, Grep, Glob, Write, Edit, Agent`

2. Write the skill body with these sections:

   **## Entry**
   - If argument is provided, use it as `<feature-name>`. Otherwise, ask the user for the feature name.

   **## Retrospective Location**
   - Search `ai-docs/<feature-name>/` for files matching `*-retrospective.md` using Glob.
   - If no retrospective found, report: "No retrospective found at `ai-docs/<feature-name>/`. Run `/fbk-code-review` to generate one." Exit.
   - If found, offer: "Found retrospective at `<path>`. Proceed with improvement analysis, or skip?"
   - If the user skips, exit.

   **## Asset Discovery**
   - Use Glob to search for `fbk-*/SKILL.md` in both `<cwd>/.claude/skills/` (project) and `~/.claude/skills/` (global).
   - If both return results, use project-level.
   - If neither returns results, report: "No Firebreak installation found." Exit.
   - From the resolved installation root, enumerate all `fbk-*` prefixed files under `skills/`, `agents/`, and `fbk-docs/`.

   **## Improvement Analysis**
   - Spawn the `fbk-improvement-analyst` agent with these inputs in the spawn prompt:
     - Path to the retrospective file
     - Path to the authoring rules index (resolve `fbk-context-assets.md` relative to the installation root's `fbk-docs/` directory)
     - List of discovered asset paths
     - The proposal output format contract (target, change type, diff, observation, necessity)
   - Do not inject file contents into the spawn prompt. Pass paths only.
   - Do not pass spec, implementation code, review document, or conversation context to the agent.

   **## Proposal Presentation**
   - Present the agent's proposals as a numbered list.
   - Each proposal displays: Target (asset file and instruction), Change (add/edit/remove with diff), Observation (retro observation), Necessity (why reverting increases mistake probability).
   - Instruct the user: respond with which proposals to apply (e.g., "apply 1, 3"), discuss ("discuss 2"), or skip ("skip 4").

   **## Selective Application**
   - For accepted proposals: apply the diff to the target file using Edit.
   - For "discuss": present the agent's detailed reasoning for that proposal. Enter a conversational loop until the user accepts, modifies, or rejects.
   - For "skip": no action.
   - After processing all decisions, present a summary of changes made.

   **## Edge Cases**
   - No actionable observations: if the agent returns no proposals, report: "No improvement proposals — retrospective contains no observations that map to specific asset changes." Exit.
   - Discussion items: if the agent surfaces items exceeding single-instruction scope, present them separately: "Discussion item: [observation]. This may require a structural change to [asset] that exceeds single-instruction scope. Consider addressing in a future spec."

3. Verify the skill follows context asset authoring conventions: direct-address imperatives, no preambles, positive framing.

## Files to create/modify

- Create: `assets/skills/fbk-improve/SKILL.md`

## Test requirements

T-03 tests validate structural properties of this file. Run T-03 after creation.

## Acceptance criteria

- AC-01: Skill searches correct path pattern for retrospective and reports when not found.
- AC-02: Spawn prompt passes paths only, excludes spec/impl/review content.
- AC-03: Proposal presentation specifies all five fields.
- AC-04: Proposals anchored to retro observations (via agent instructions).
- AC-05: Agent references authoring rules (via spawn prompt contract).
- AC-06: Accept/discuss/skip flow implemented with Edit for application.
- AC-07: No-actionable-observations exit message present.
- AC-08: No restriction on cross-phase proposals.

## Model

Sonnet

## Wave

Wave 2
