---
description: >-
  Code review and remediation. Use when reviewing existing code, auditing
  for AI failure modes, performing post-implementation review, or
  co-authoring remediation specs from code review findings.
argument-hint: "[target-path or feature-name]"
allowed-tools: Read, Grep, Glob, Write, Edit, Bash, Agent
---

Read `.claude/fbk-docs/fbk-sdl-workflow/code-review-guide.md` for the behavioral comparison methodology, finding format, sighting format, orchestration protocol, and retrospective fields. Read `.claude/fbk-docs/fbk-sdl-workflow/ai-failure-modes.md` for the AI failure mode checklist used when no specs are available.

## Entry and Path Routing

Determine the invocation context:

- **Post-implementation review**: If invoked after `/implement` completion (the user accepted the stage-transition prompt), follow the post-implementation path in `references/post-impl-review.md`.
- **Standalone review**: For all other invocations, follow the conversational review path in `references/existing-code-review.md`.

## Source of Truth Handling

Check for existing specs — provided by the user or discovered in `ai-docs/`. If specs exist, use their ACs and UV steps as the comparison target. If no specs are available, use the AI failure mode checklist for structural issue detection. If no spec and no existing code context is provided, ask the user what to review.

## Agent Team

Spawn agents as a team with fresh context per invocation. Use two agents:

- **Detector** (`code-review-detector`): Reads code, produces sightings. Tools: Read, Grep, Glob, Bash.
- **Challenger** (`code-review-challenger`): Verifies or rejects sightings. Tools: Read, Grep, Glob.

Inject the behavioral comparison methodology from `code-review-guide.md` and the relevant source of truth into each agent's spawn prompt. Agents do not inherit skills.

## Detection-Verification Loop

Run the iterative detection and verification loop:

1. Spawn Detector with target code scope + source of truth + behavioral comparison instructions
2. Collect sightings
3. Spawn Challenger with sightings + code + 'verify or reject each sighting with evidence'
4. Collect verified findings and rejections
5. Run additional rounds for weakened but unrejected sightings
6. Terminate when a round produces only `nit`-category sightings (or no sightings), or after a maximum of 5 rounds

Only verified findings surface to the user. Rejected sightings are excluded.

## Broad-Scope Reviews

When the user requests a full codebase review rather than specific modules:

1. Survey the project structure and identify reviewable units
2. Propose a review order to the user
3. Spawn fresh Detector/Challenger pairs per unit
4. Accumulate verified findings across units, watching for cross-module patterns
5. Checkpoint with the user after each unit

## Spec Conflict Detection

When multiple specs exist for the reviewed code, compare them for consistency. Surface conflicts between specs, or between specs and code, for user discussion during the conversational review.

## Retrospective

After the review completes, produce a retrospective following the fields defined in `code-review-guide.md`.

After the retrospective is written to disk, invoke `/fbk-improve <feature-name>` to analyze the retrospective for pipeline improvement opportunities.
