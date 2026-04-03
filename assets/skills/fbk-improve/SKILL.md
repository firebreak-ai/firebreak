---
description: >-
  Pipeline self-improvement from retrospective observations. Use when analyzing
  a retrospective to propose targeted improvements to Firebreak context assets,
  or after code review retrospective finalization.
argument-hint: "<feature-name>"
allowed-tools: Read, Grep, Glob, Edit, Agent
---

## Entry

If the argument is provided, use it as `<feature-name>`. Otherwise, ask the user for the feature name before proceeding.

## Retrospective Location

Use Glob to search `ai-docs/<feature-name>/` for files matching `*-retrospective.md`.

If no retrospective is found, report: "No retrospective found at `ai-docs/<feature-name>/`. Run `/fbk-code-review` to generate one." Exit.

If one retrospective is found, offer: "Found retrospective at `<path>`. Proceed with improvement analysis, or skip?" If multiple are found, list all paths and offer: "Found N retrospectives. Proceed with improvement analysis using all files, or skip?" Collect all found paths as the retrospective set. If the user skips, exit.

## Asset Discovery

Use Glob to search for `fbk-*/SKILL.md` in both `<cwd>/.claude/skills/` (project) and `~/.claude/skills/` (global).

If both locations return results, prefer project-level and use it as the installation root. If neither returns results, report: "No Firebreak installation found." Exit.

From the resolved installation root, enumerate all `fbk-*` prefixed files under `skills/`, `agents/`, and `fbk-docs/`. Collect these paths as the asset list.

## Improvement Analysis

Create an agent team. For each asset path in the discovered list, spawn an `fbk-improvement-analyst` teammate. Each teammate's spawn prompt contains:

- Paths to all retrospective files in the retrospective set
- Path to the authoring rules index (resolve `fbk-context-assets.md` relative to the installation root's `fbk-docs/` directory)
- The single asset path assigned to this teammate
- The proposal output format contract: each proposal must include target (asset file and instruction), change type (add/edit/remove with diff), observation (the retrospective observation that motivates the proposal), and necessity (why removing this instruction increases the probability of an agent mistake)

Pass paths only. Do not inject file contents into spawn prompts.

Do not pass spec, implementation, or review content to the teammates.

Collect proposals from all teammates. Proposals may target any Firebreak asset regardless of which phase originally authored it — there is no restriction on cross-phase proposals.

After all teammates return, shut down the team.

## Routing Chain Analysis

After per-asset analysis, identify routing chains in the asset list: skills with `references/` directories and index docs with execution-handoff routing tables. For each chain, spawn one additional analyst with all files in the chain as its assigned paths. Collect proposals from chain analysts alongside per-asset proposals.

## Proposal Presentation

Present the collected proposals as a numbered list. Each proposal displays:

- **Target**: asset file and specific instruction location
- **Change**: add/edit/remove with diff
- **Observation**: the retrospective observation that motivates this proposal
- **Necessity**: why reverting this change increases the probability of an agent mistake

Instruct the user: respond with which proposals to apply (e.g., "apply 1, 3"), discuss ("discuss 2"), or skip ("skip 4").

## Selective Application

For accepted proposals: apply the diff to the target file using Edit.

For "discuss": present the agent's detailed reasoning for that proposal. Enter a conversational loop until the user accepts, modifies, or rejects.

For "skip": no action.

After processing all decisions, present a summary of changes made.

## Edge Cases

**No actionable observations**: if no teammates return proposals, report: "No improvement proposals — retrospective contains no observations that map to specific asset changes." Exit.

**Discussion items exceeding single-instruction scope**: present them separately as: "Discussion item: [observation]. This may require a structural change to [asset] that exceeds single-instruction scope. Consider addressing in a future spec."
