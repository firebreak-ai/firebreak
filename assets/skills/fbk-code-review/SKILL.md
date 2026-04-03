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

- **Detector** (`code-review-detector`): Reads code, produces sightings with type and severity classification. Tools: Read, Grep, Glob.
- **Challenger** (`code-review-challenger`): Verifies or rejects sightings. Tools: Read, Grep, Glob.

Inject the behavioral comparison methodology from `code-review-guide.md` and the relevant source of truth into each agent's spawn prompt. Agents do not inherit skills.

## Pre-Spawn Linter Execution

Before spawning Detectors, discover and run project-native linters and static analysis tools. Search for lint configurations (`.eslintrc`, `eslint.config.*`, `.pylintrc`, `pyproject.toml`, `golangci-lint` configs) and run available tools. Capture raw text output, truncated to the first 100 findings if output is large. Include the linter output as supplementary context in each Detector's spawn prompt. Linter output is context, not pre-formed sightings — the Detector reads it to understand what mechanical issues the linter already caught and focuses on issues linters miss. Tag any sightings derived from linter output with detection source `linter`.

## Detection-Verification Loop

Run the iterative detection and verification loop:

1. Spawn Detector with target code scope + source of truth + behavioral comparison instructions + structural detection targets from `fbk-docs/fbk-design-guidelines/quality-detection.md` + linter output (if available). Remind the Detector to tag each sighting with its detection source (`spec-ac`, `checklist`, `structural-target`, or `linter`).
2. Collect sightings
3. Spawn Challenger with sightings + code + 'verify or reject each sighting with evidence'
4. Collect verified findings and rejections
5. When applying fixes for a verified finding, grep the same file and package for all instances of the identified pattern. Apply the fix to every instance.
6. Run additional rounds for weakened but unrejected sightings
7. Terminate when a round produces no new sightings above `info` severity (or no sightings), or after a maximum of 5 rounds

Only verified findings surface to the user. Rejected sightings are excluded.

## Post-Fix Verification

After all fixes from a review session are applied, run the full test suite and confirm zero failures before closing the review.

## Broad-Scope Reviews

When the user requests a full codebase review rather than specific modules:

1. Survey the project structure and identify reviewable units
2. Propose a review order to the user
3. Spawn fresh Detector/Challenger pairs per unit. For broad-scope reviews with multiple independent units, spawn parallel Detector agents as a team — each Detector reviews its assigned unit independently with its own context. Detectors do not share state.
4. Accumulate verified findings across units, watching for cross-module patterns
5. After all units complete, perform cross-unit pattern deduplication: identify findings from different units that describe the same underlying pattern, assign a shared pattern name (e.g., "string-error-dispatch", "dead-handler-registration"), and group them in the retrospective. Deduplicated findings retain their individual IDs but share the pattern label.
6. Checkpoint with the user after each unit

## Stuck-Agent Recovery

When a Detector or Challenger agent becomes unresponsive (no output within the expected time frame), relaunch it once with the same spawn prompt and context. If the relaunched agent is also unresponsive, escalate to the user with a summary of what the agent was assigned and where it stalled. Never perform the stuck agent's work directly — the orchestrator coordinates, it does not substitute for agents.

## Spec Conflict Detection

When multiple specs exist for the reviewed code, compare them for consistency. Surface conflicts between specs, or between specs and code, for user discussion during the conversational review.

## Retrospective

After the review completes, produce a retrospective following the fields defined in `code-review-guide.md`.

After the retrospective is written to disk, invoke `/fbk-improve <feature-name>` to analyze the retrospective for pipeline improvement opportunities.
