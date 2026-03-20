---
id: T-10
type: implementation
wave: 2
covers: ["AC-12"]
files_to_create: ["phase-1.5-core-enhancement/permissions-audit.md"]
test_tasks: ["T-02"]
completion_gate: "permissions-audit.md contains predicted prompt map (stage, tool, path, reason) and PreToolUse hook design specification"
---

## Objective

Produces the permissions friction audit: a predicted prompt map from static analysis of allowlist rules, and a PreToolUse logging hook design for empirical validation.

## Context

The greenfield test revealed significant permissions friction during pipeline operation. The agent cannot observe when the user receives prompts (auto-approved and user-approved tool calls are indistinguishable). The audit uses static analysis of allowlist rules against known pipeline tool call patterns to predict which calls trigger prompts.

## Instructions

1. Read `home/dot-claude/settings.json` and `home/dot-claude/settings.local.json` (if it exists) to identify current allowlist rules.

2. For each pipeline stage, identify tool call patterns from the skill and agent definitions. Read these specific files:

   **Skills** (in `home/dot-claude/skills/`):
   - `spec/SKILL.md` — `/spec` skill
   - `spec-review/SKILL.md` — `/spec-review` skill
   - `breakdown/SKILL.md` — `/breakdown` skill
   - `implement/SKILL.md` — `/implement` skill (if exists)
   - `council/SKILL.md` — `/council` skill

   **Agents** (in `home/dot-claude/agents/`):
   - `test-reviewer.md` — test reviewer agent (invoked during review and breakdown)

   **Hooks** (in `home/dot-claude/hooks/sdl-workflow/`):
   - `spec-gate.sh`, `review-gate.sh`, `breakdown-gate.sh`, `task-reviewer-gate.sh` — gate scripts invoked by skills

   For each file, identify Bash commands, file reads/writes, and other tool calls. Map each tool call pattern against the allowlist rules from step 1.

3. Produce `ai-docs/dispatch/phase-1.5-core-enhancement/permissions-audit.md` containing:
   - **Predicted prompt map**: A table with columns: pipeline stage, tool, command/path, covered by allowlist rule (yes/no), if no — why not (path not matched, command not matched, etc.)
   - **Highest-frequency prompt sources**: The tool call patterns that fire most often per pipeline run, prioritized for mitigation
   - **Candidates for helper-script encapsulation**: Tool calls where the agent currently uses raw bash but could invoke a sanitized script (e.g., council session management)
   - **PreToolUse hook design**: A specification for a lightweight hook that logs tool name, parameters, and target path to a file during pipeline runs. Include the hook configuration for `settings.json` and the log format.

4. Do not implement the hook or modify allowlists — this is audit and design only.

## Files to create/modify

Create:
- `ai-docs/dispatch/phase-1.5-core-enhancement/permissions-audit.md`

## Test requirements

Artifact review: the predicted prompt map is reviewed for completeness and accuracy by the human.

## Acceptance criteria

AC-12: Predicted prompt map produced, highest-frequency sources identified, hook design specified. Mitigations deferred.

## Model

Sonnet

## Wave

Wave 2
