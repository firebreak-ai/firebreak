---
description: >-
  Code review and remediation. Use when reviewing existing code, auditing
  for AI failure modes, performing post-implementation review, or
  co-authoring remediation specs from code review findings.
argument-hint: "[target-path or feature-name]"
allowed-tools: Read, Grep, Glob, Write, Edit, Bash, Agent
---

Read `.claude/fbk-docs/fbk-sdl-workflow/code-review-guide.md` for the behavioral comparison methodology, finding format, sighting format, orchestration protocol, and retrospective fields. Read `.claude/fbk-docs/fbk-sdl-workflow/ai-failure-modes.md` for the AI failure mode checklist used when no specs are available. Read `.claude/fbk-docs/fbk-design-guidelines/quality-detection.md` for structural detection targets applicable to all code reviews.

## Entry and Path Routing

Determine the invocation context:

- **Post-implementation review**: If invoked after `/implement` completion (the user accepted the stage-transition prompt), follow the post-implementation path in `references/post-impl-review.md`.
- **Standalone review**: For all other invocations, follow the conversational review path in `references/existing-code-review.md`.

## Source of Truth Handling

Check for existing specs — provided by the user or discovered in `ai-docs/`. If specs exist, use their ACs and UV steps as the primary comparison target. Run Intent Extraction for standalone and broad-scope reviews — documentation outside the spec often contains behavioral claims not covered by ACs. When no specs are available, the intent register and the AI failure mode checklist together form the comparison target. If no documentation and no existing code context is provided, ask the user what to review.

## Agent Team

Spawn agents as a team with fresh context per invocation. Use two agents:

- **Detector** (`code-review-detector`): Reads code, produces sightings with type and severity classification. Tools: Read, Grep, Glob.
- **Challenger** (`code-review-challenger`): Verifies or rejects sightings using JSON verdict format. Tools: Read, Grep, Glob.

Inject the behavioral comparison methodology from `code-review-guide.md` and the relevant source of truth into each agent's spawn prompt. Agents do not inherit skills.

## Review Report

Create a review report file at the start of every review: `fbk-code-review-<YYYY-MM-DD>-<HHMM>.md` in the project's working directory. Write the intent register, verified findings, and retrospective to this file as the review progresses. The user opens this file to see rendered diagrams and review results.

## Pre-Spawn Linter Execution

Before spawning Detectors, discover and run project-native linters and static analysis tools. Search for lint configurations (`.eslintrc`, `eslint.config.*`, `.pylintrc`, `pyproject.toml`, `golangci-lint` configs) and run available tools. Capture raw text output, truncated to the first 100 findings if output is large. Include the linter output as supplementary context in each Detector's spawn prompt. Linter output is context, not pre-formed sightings — the Detector reads it to understand what mechanical issues the linter already caught and focuses on issues linters miss. Tag any sightings derived from linter output with detection source `linter`.

## Intent Extraction

Complete these steps before spawning Detectors.

### Discover documentation

Search for intent-bearing documents in priority order:
1. Feature specs in `ai-docs/` (acceptance criteria and UV steps)
2. README, CLAUDE.md, CONTRIBUTING.md, architecture docs
3. Inline module-level documentation (JSDoc, docstrings, module headers)
4. CI/CD configuration, deployment docs, API documentation

### Build the intent register

From discovered documentation, produce a structured intent register with two parts:

**Intent claims**: A list of up to 30 behavioral claims the project makes about itself. Each claim is one sentence describing what the project or a specific module is supposed to do. Prefer claims that are specific and verifiable.

**Intent diagram**: Generate a Mermaid diagram capturing module relationships, data flow, and key behavioral contracts. Optimize for the VSCode markdown preview renderer:
- Use `graph TD` or `graph LR` for data flow and module relationships
- Keep node labels under 30 characters
- Use subgraphs to group related modules
- Label edges with the behavioral contract (e.g., "filters by interest", "scores via AI")
- Avoid `classDef`, `click`, `callback`, and other advanced features that may not render

Write the intent register (claims + diagram) to the review report file.

### User checkpoint

Tell the user the review report file is ready for review. Ask specific questions to close ambiguity — areas where documentation is silent, contradictory, or where multiple interpretations exist. Proceed after the user confirms, corrects, or instructs the agent to continue as-is.

### Supplement from code

Where the intent register has gaps (modules with no documentation coverage), derive intent from code structure: function names, type signatures, module organization, and cross-module call patterns. Update the diagram and claims in the review report file.

## Detection-Verification Loop

Resolve the active preset and severity threshold at the start of the review. Defaults: preset=`behavioral-only`, severity=`minor`. Both are overridable by user instruction.

Run the iterative detection and verification loop:

1. Spawn Detector with: target code file contents first, then linter output (if available), then intent register (from Intent Extraction), then source of truth + behavioral comparison instructions from `code-review-guide.md` + structural detection targets from `fbk-docs/fbk-design-guidelines/quality-detection.md` + the JSON sighting schema and type/severity definitions last. Instruct the Detector to tag each sighting with its detection source (`spec-ac`, `checklist`, `structural-target`, `intent`, or `linter`) and to output sightings as a JSON array.
2. Collect sightings as JSON.
3. Run `uv run assets/scripts/pipeline.py run --preset <preset> --min-severity <threshold>` to validate, domain-filter, and severity-filter the sightings in a single invocation. If >30% of sightings are rejected during validation, log a warning about prompt compliance.
4. Spawn Challenger with: target code file contents first, then the filtered JSON sightings to verify, then verification instructions + type/severity definitions + the type-severity validity matrix last. The Challenger receives and produces JSON — no format translation between agents.
5. Validate Challenger output: status and evidence fields present, matrix validation on any reclassified type-severity combinations.
6. Filter to `status: verified` or `verified-pending-execution`. Assign sequential finding IDs (F-01, F-02...).
7. Run `uv run assets/scripts/pipeline.py to-markdown` to convert verified findings to markdown once for the review report. Adjacent observations from the Challenger are rendered at the end of each finding and accumulated into the retrospective.
7a. After each verification round, append verified findings to the review report file.
8. When applying fixes for a verified finding, grep the same file and package for all instances of the identified pattern. Apply the fix to every instance.
9. Run additional rounds for weakened but unrejected sightings.
10. Terminate when a round produces no new sightings above `info` severity (or no sightings), or after a maximum of 5 rounds.

Only verified findings surface to the user. Rejected sightings are excluded. JSON is the working format throughout the pipeline. Markdown conversion happens once for the human-facing review report.

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

After the review completes, append the retrospective to the review report file, following the fields defined in `code-review-guide.md`.

After the retrospective is written to disk, invoke `/fbk-improve <feature-name>` to analyze the retrospective for pipeline improvement opportunities.
