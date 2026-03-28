---
id: T-05
type: test
wave: 3
covers: [AC-01, AC-06]
depends_on: [T-04]
files_to_create: [tests/sdl-workflow/test-improvement-integration.sh]
completion_gate: "Test script runs and integration assertions fail (pipeline changes not yet applied)"
---

## Objective

Creates the integration test validating that the code review skill transitions to `/fbk-improve`, the SDL workflow doc includes the self-improvement stage, and all cross-asset references resolve.

## Context

This test validates the pipeline integration: the code review skill must invoke `/fbk-improve` after retrospective finalization, and the SDL workflow doc must list self-improvement as a pipeline stage. It also validates cross-references between the new skill, new agent, and existing pipeline assets.

Follow the TAP test pattern from `tests/sdl-workflow/test-code-review-integration.sh`.

## Instructions

1. Create `tests/sdl-workflow/test-improvement-integration.sh` following the TAP test pattern.
2. Set paths for all relevant files:
   - `CODE_REVIEW_SKILL="$PROJECT_ROOT/assets/skills/fbk-code-review/SKILL.md"`
   - `SDL_WORKFLOW="$PROJECT_ROOT/assets/fbk-docs/fbk-sdl-workflow.md"`
   - `IMPROVE_SKILL="$PROJECT_ROOT/assets/skills/fbk-improve/SKILL.md"`
   - `IMPROVE_AGENT="$PROJECT_ROOT/assets/agents/fbk-improvement-analyst.md"`

3. Add these assertions:

   **Code review transition (AC-01 seam):**
   - Code review skill's Retrospective section contains instruction to invoke `/fbk-improve`
   - The invocation passes `<feature-name>` as argument

   **SDL workflow doc:**
   - SDL workflow doc references `/fbk-improve` or `fbk-improve` or `self-improvement`
   - The reference appears after the code review stage reference

   **Cross-asset references:**
   - Improve skill file exists
   - Improve agent file exists
   - Improve skill references agent name `fbk-improvement-analyst`
   - Improve agent references authoring rules path `fbk-context-assets`
   - Improve skill references Glob-based asset discovery
   - Code review skill references `/fbk-improve`

   **Selective application (AC-06):**
   - Improve skill contains `Edit` in its allowed-tools (needed to apply diffs)

4. Add TAP summary and exit with non-zero if any test fails.

## Files to create/modify

- Create: `tests/sdl-workflow/test-improvement-integration.sh`

## Test requirements

This IS the test task. Assertions validate:
- AC-01: Code review → improve transition seam
- AC-06: Edit tool available for applying diffs

## Acceptance criteria

- AC-01: Code review skill contains transition instruction
- AC-06: Skill has Edit in allowed-tools for applying proposals

## Model

Haiku

## Wave

Wave 3
