---
id: T-03
type: test
wave: 2
covers: [AC-01, AC-02, AC-03, AC-04, AC-05, AC-06, AC-07, AC-08]
depends_on: [T-02]
files_to_create: [tests/sdl-workflow/test-improvement-skill.sh]
completion_gate: "Test script runs and all assertions fail (skill does not exist yet)"
---

## Objective

Creates the structural validation test for the `fbk-improve` skill definition.

## Context

The improvement skill is the orchestrator — it locates the retrospective, discovers installed assets via Glob, spawns the improvement analyst agent, presents proposals, and applies accepted changes. The test validates that the skill file contains the instructions needed to drive all spec behaviors.

Follow the TAP test pattern from `tests/sdl-workflow/test-code-review-integration.sh`.

## Instructions

1. Create `tests/sdl-workflow/test-improvement-skill.sh` following the TAP test pattern.
2. Set `SKILL_FILE="$PROJECT_ROOT/assets/skills/fbk-improve/SKILL.md"` as the test target.
3. Add these assertions:

   **File structure:**
   - Skill file exists at expected path
   - Frontmatter contains `description:` field
   - Frontmatter contains `allowed-tools:` including Read, Grep, Glob, Write, Edit, Agent

   **Retrospective location (AC-01):**
   - Body contains instruction to search `ai-docs/<feature-name>/` for `*-retrospective.md`
   - Body contains instruction to report when no retrospective is found

   **Asset discovery (AC-01, AC-02):**
   - Body contains Glob-based discovery instruction referencing both `.claude/skills/` and `~/.claude/skills/`
   - Body contains instruction to prefer project-level when both locations have results
   - Body contains instruction to enumerate `fbk-*` prefixed files

   **Agent isolation (AC-02):**
   - Body references spawning `fbk-improvement-analyst` agent
   - Body specifies passing paths (not file contents) to the agent
   - Body specifies the agent does NOT receive spec, implementation, or review content

   **Proposal format (AC-03, AC-04):**
   - Body contains proposal format with target, change, observation, necessity fields

   **User interaction (AC-06):**
   - Body contains accept/discuss/skip flow instructions
   - Body contains opt-out prompt ("skip" or "proceed")

   **Empty result (AC-07):**
   - Body contains instruction for no-actionable-observations exit message

   **Cross-cutting (AC-08):**
   - Body does NOT restrict proposals to same-phase assets (or explicitly permits cross-phase)

4. Add TAP summary and exit with non-zero if any test fails.

## Files to create/modify

- Create: `tests/sdl-workflow/test-improvement-skill.sh`

## Test requirements

This IS the test task. Assertions validate all 8 ACs through structural presence checks on the skill file.

## Acceptance criteria

- AC-01 through AC-08: Each AC has at least one structural assertion checking the corresponding instruction exists in the skill file.

## Model

Haiku

## Wave

Wave 2
