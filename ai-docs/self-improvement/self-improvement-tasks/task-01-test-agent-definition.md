---
id: T-01
type: test
wave: 1
covers: [AC-02, AC-03, AC-04, AC-05, AC-08]
files_to_create: [tests/sdl-workflow/test-improvement-agent.sh]
completion_gate: "Test script runs and all assertions fail (asset does not exist yet)"
---

## Objective

Creates the structural validation test for the `fbk-improvement-analyst` agent definition.

## Context

The improvement analyst agent is a new agent that analyzes retrospectives and proposes changes to Firebreak context assets. It must have specific tool restrictions (read-only analysis), reference the authoring rules, and specify the sub-agent team pattern for context-independent asset analysis. The test validates these structural properties exist in the agent definition before the agent is created.

Existing agent structural tests follow the TAP format pattern established in `tests/sdl-workflow/test-code-review-integration.sh` — define `ok()`/`not_ok()` helpers, use `grep -q` against asset files, report TAP output.

## Instructions

1. Create `tests/sdl-workflow/test-improvement-agent.sh` following the TAP test pattern from existing tests.
2. Set up `SCRIPT_DIR`, `PROJECT_ROOT`, TAP header, and `ok()`/`not_ok()` helpers matching the pattern in `tests/sdl-workflow/test-code-review-integration.sh`.
3. Set `AGENT_FILE="$PROJECT_ROOT/assets/agents/fbk-improvement-analyst.md"` as the test target.
4. Add these assertions:
   - Agent file exists at expected path
   - Frontmatter contains `name: improvement-analyst` or `fbk-improvement-analyst`
   - Frontmatter contains a `description:` field
   - Frontmatter contains `tools:` field listing only read-only tools (Read, Grep, Glob — no Write, Edit, Bash)
   - Body contains instruction referencing authoring rules (`fbk-context-assets`)
   - Body contains instruction about sub-agent spawning for per-asset analysis
   - Body contains scope discipline section restricting the agent to read-only analysis and proposal output
   - Body contains proposal output format specification (target, change type, diff, observation, necessity)
   - Body contains instruction about cross-cutting proposals (proposals can target any Firebreak asset regardless of which phase the observation originated from)
   - Body does NOT contain references to receiving spec, implementation, or review conversation content
5. Add TAP summary and exit with non-zero if any test fails.

## Files to create/modify

- Create: `tests/sdl-workflow/test-improvement-agent.sh`

## Test requirements

This IS the test task. Assertions validate:
- AC-02: Agent tools are read-only; no spec/impl/review content referenced
- AC-03: Proposal output format specified in agent body
- AC-04: Anchoring instruction present
- AC-05: Authoring rules reference present
- AC-08: Cross-cutting proposal instruction present

## Acceptance criteria

- AC-02: Agent definition restricts tools to read-only set
- AC-03: Agent body specifies proposal format fields
- AC-05: Agent body references authoring rules
- AC-08: Agent body permits cross-cutting proposals

## Model

Haiku

## Wave

Wave 1
