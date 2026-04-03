---
id: task-20
type: implementation
wave: 4
covers: [AC-60, AC-16, AC-17, AC-18, AC-21, AC-22]
files_to_modify:
  - assets/skills/fbk-code-review/SKILL.md
test_tasks: [task-05]
completion_gate: "task-05 tests pass"
---

## Objective

Adds 6 orchestration instructions to the code review SKILL.md: pre-spawn linter execution, parallel Detector spawning, stuck-agent recovery, cross-unit pattern deduplication, quality-detection.md reference in Detector spawn, and detection source tagging.

## Context

The SKILL.md file orchestrates the code review skill. Current structure:
- Lines 1-8: Frontmatter + intro
- Lines 10-11: `## Entry and Path Routing`
- Lines 19-21: `## Source of Truth Handling`
- Lines 23-30: `## Agent Team` (mentions `Bash` in Detector tools on line 27)
- Lines 32-43: `## Detection-Verification Loop`
- Lines 45-54: `## Broad-Scope Reviews`
- Lines 56-57: `## Spec Conflict Detection`
- Lines 59-63: `## Retrospective`

AC-09 (Bash removal from Detector) means the SKILL.md Agent Team section must also update the Detector tools line from `Tools: Read, Grep, Glob, Bash` to `Tools: Read, Grep, Glob`.

AC-60 relocates linter discovery/execution from the Detector to the orchestrator. The orchestrator runs linters before spawning Detectors and includes results as supplementary context.

AC-16, AC-17, AC-18 add operational instructions. AC-21, AC-22 modify Detector spawn instructions.

## Instructions

1. In the `## Agent Team` section, change the Detector tools line from:
   ```
   - **Detector** (`code-review-detector`): Reads code, produces sightings. Tools: Read, Grep, Glob, Bash.
   ```
   to:
   ```
   - **Detector** (`code-review-detector`): Reads code, produces sightings with type and severity classification. Tools: Read, Grep, Glob.
   ```

2. After the `## Agent Team` section and before `## Detection-Verification Loop`, insert a new section:

```
## Pre-Spawn Linter Execution

Before spawning Detectors, discover and run project-native linters and static analysis tools. Search for lint configurations (`.eslintrc`, `eslint.config.*`, `.pylintrc`, `pyproject.toml`, `golangci-lint` configs) and run available tools. Capture raw text output, truncated to the first 100 findings if output is large. Include the linter output as supplementary context in each Detector's spawn prompt. Linter output is context, not pre-formed sightings — the Detector reads it to understand what mechanical issues the linter already caught and focuses on issues linters miss. Tag any sightings derived from linter output with detection source `linter`.
```

3. In the `## Detection-Verification Loop` section, update step 1 from:
   ```
   1. Spawn Detector with target code scope + source of truth + behavioral comparison instructions
   ```
   to:
   ```
   1. Spawn Detector with target code scope + source of truth + behavioral comparison instructions + structural detection targets from `fbk-docs/fbk-design-guidelines/quality-detection.md` + linter output (if available). Remind the Detector to tag each sighting with its detection source (`spec-ac`, `checklist`, `structural-target`, or `linter`).
   ```

4. In the `## Broad-Scope Reviews` section, replace step 3:
   ```
   3. Spawn fresh Detector/Challenger pairs per unit
   ```
   with:
   ```
   3. Spawn fresh Detector/Challenger pairs per unit. For broad-scope reviews with multiple independent units, spawn parallel Detector agents as a team — each Detector reviews its assigned unit independently with its own context. Detectors do not share state.
   ```

5. After step 4 in `## Broad-Scope Reviews` ("Accumulate verified findings across units, watching for cross-module patterns"), add a new step:

   ```
   5. After all units complete, perform cross-unit pattern deduplication: identify findings from different units that describe the same underlying pattern, assign a shared pattern name (e.g., "string-error-dispatch", "dead-handler-registration"), and group them in the retrospective. Deduplicated findings retain their individual IDs but share the pattern label.
   ```

6. Renumber the current step 5 ("Checkpoint with the user after each unit") to step 6.

7. After the `## Broad-Scope Reviews` section and before `## Spec Conflict Detection`, insert:

```
## Stuck-Agent Recovery

When a Detector or Challenger agent becomes unresponsive (no output within the expected time frame), relaunch it once with the same spawn prompt and context. If the relaunched agent is also unresponsive, escalate to the user with a summary of what the agent was assigned and where it stalled. Never perform the stuck agent's work directly — the orchestrator coordinates, it does not substitute for agents.
```

## Files to create/modify

- `assets/skills/fbk-code-review/SKILL.md` (modify)

## Test requirements

Tests from task-05: Test 1 (linter keyword in SKILL.md), Test 2 (truncation keyword), Test 3 (supplementary context keyword), Test 4 (parallel keyword), Test 5 (stuck-agent/relaunch keyword), Test 6 (never perform directly/escalate to user), Test 7 (deduplication/cross-unit pattern keyword), Test 8 (quality-detection reference), Test 9 (detection source keyword).

## Acceptance criteria

- AC-60: Linter pre-spawn instruction with raw text format, truncation to 100 findings, and supplementary context framing.
- AC-16: Parallel Detector agent team spawning instruction present.
- AC-17: Stuck-agent recovery instruction present (relaunch once, then escalate, never perform directly).
- AC-18: Cross-unit pattern deduplication and naming instruction present.
- AC-21: Detector spawn instructions reference `quality-detection.md`.
- AC-22: Detector spawn instructions include detection source tagging reminder.

## Model

Sonnet

## Wave

Wave 4
