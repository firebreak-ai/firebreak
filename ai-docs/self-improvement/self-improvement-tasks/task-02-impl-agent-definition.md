---
id: T-02
type: implementation
wave: 1
covers: [AC-02, AC-03, AC-04, AC-05, AC-08]
files_to_create: [assets/agents/fbk-improvement-analyst.md]
test_tasks: [T-01]
completion_gate: "T-01 tests pass"
---

## Objective

Creates the `fbk-improvement-analyst` agent definition that analyzes retrospectives and produces improvement proposals for Firebreak context assets.

## Context

This agent is spawned by the `/fbk-improve` skill with a clean context. It receives paths (not file contents) to: the retrospective file, the authoring rules index, and installed asset files. It reads all files on demand.

The agent operates as a team lead — it spawns sub-agents to analyze individual assets independently. Each sub-agent reads one asset (tracing its reference paths), cross-references against retro observations, and returns proposals. This ensures analysis of one asset does not contaminate analysis of another.

The agent must NOT receive spec, implementation code, or review conversation content. Its tools are read-only (Read, Grep, Glob) since it produces proposals as text output, not file edits.

Follow the agent definition format in existing files like `assets/agents/fbk-code-review-detector.md`: YAML frontmatter with name, description, tools, model; markdown body with role, workflow, scope discipline.

## Instructions

1. Create `assets/agents/fbk-improvement-analyst.md` with YAML frontmatter:
   - `name: fbk-improvement-analyst`
   - `description:` — "Analyzes retrospectives against installed Firebreak context assets to produce improvement proposals. Use when translating retrospective observations into targeted asset edits."
   - `tools: Read, Grep, Glob`
   - `model: sonnet`

2. Write the agent body with these sections:

   **Role paragraph**: State that this agent analyzes a retrospective and the installed Firebreak context assets to produce improvement proposals. Each proposal is a single-instruction add, edit, or remove anchored to a specific retrospective observation.

   **Input contract**: The spawn prompt provides three paths — retrospective file, authoring rules index (`fbk-context-assets.md`), and a list of installed asset paths. Read all files on demand. No file contents are injected into the spawn prompt.

   **Workflow** (numbered steps):
   1. Read the retrospective file. Extract each distinct process observation.
   2. Read the authoring rules index (`fbk-context-assets.md`). Follow its routing table to load leaf docs as needed for quality validation.
   3. For each asset in the provided list, spawn a sub-agent to analyze it independently. The sub-agent reads the asset (tracing its reference paths to understand the full instruction set), cross-references against the retro observations, and returns proposals for that asset.
   4. Collect proposals from all sub-agents.
   5. Self-correct: revise proposals in-place if any would create redundancy with existing instructions, introduce compound instructions, or violate write-for-agents style.
   6. Quality review: re-read each affected asset with proposed changes applied. If pre-existing instructions no longer pass the necessity test (with or without the new additions), add removal proposals citing the authoring rules.
   7. Return the final proposal list.

   **Proposal output format**: Each proposal must include:
   - Target: asset file path and specific instruction(s)
   - Change: add / edit / remove with the specific diff
   - Observation: the retrospective observation that motivates this change
   - Necessity: why reverting the change would make the observed mistake more likely
   For removal proposals from the quality review (not retro-driven), the observation field states "authoring rules quality review" and the necessity argument explains why the instruction does not pass the necessity test.

   **Cross-cutting scope**: Proposals can target any installed Firebreak asset regardless of which pipeline phase the retrospective observation originated from. An implementation-phase failure may trace to a spec-phase instruction gap.

   **Scope discipline**: Do not write files — output proposals as text. Do not generate speculative improvements disconnected from retrospective observations (except quality-review removal proposals). Do not receive or request spec, implementation, or review conversation content.

3. Verify the file follows the agent authoring conventions: direct-address imperatives, no preambles, scope discipline section.

## Files to create/modify

- Create: `assets/agents/fbk-improvement-analyst.md`

## Test requirements

T-01 tests validate structural properties of this file. Run T-01 after creation.

## Acceptance criteria

- AC-02: Tools restricted to Read, Grep, Glob. No spec/impl/review content in agent instructions.
- AC-03: Proposal format specifies all five fields (target, change type, diff, observation, necessity).
- AC-04: Workflow requires anchoring proposals to retro observations.
- AC-05: Workflow references authoring rules for validation.
- AC-08: Cross-cutting scope explicitly stated.

## Model

Sonnet

## Wave

Wave 1
