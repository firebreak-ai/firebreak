## Objective

Modify the existing `/spec-review` skill to add test strategy review via the test reviewer agent and create the brownfield spec-stage instruction doc.

## Context

The `/spec-review` skill at `home/.claude/skills/spec-review/SKILL.md` currently runs a council review, synthesizes findings, determines threat model need, runs the gate, and transitions. This task adds a test strategy review step between finding synthesis (after council review) and gate invocation. The test reviewer agent (checkpoint 1) validates the spec's testing strategy via an Agent Teams teammate invocation for context isolation.

The brownfield doc at `home/.claude/docs/brownfield-spec.md` provides 5 instructions for the `/spec` skill to load when writing technical approaches in existing codebases. These instructions ensure specs account for existing code patterns and avoid duplication or partial replacement.

All existing skill behavior must be preserved — council invocation, classification, finding synthesis, threat model determination, gate invocation, and transition logic remain unchanged. The test strategy review is inserted as a new step.

## Instructions

1. Read `home/.claude/skills/spec-review/SKILL.md` to understand the current structure and section ordering.

2. Add a new section between "Finding synthesis" and "Threat model determination" with the heading `## Test strategy review`. Add the following content:

3. In the new section, write these instructions (direct-address imperatives):
   - Invoke the test reviewer agent (`test-reviewer`) as an Agent Teams teammate with checkpoint 1 context. Pass the spec file and the spec schema as the artifact set.
   - The test reviewer evaluates independently — it has no memory of the council review discussion and no access to council findings.
   - If the test reviewer returns FAIL: add its findings to the review document under a "Test Strategy Review" heading within the findings. Set the overall review result to fail. Include each defect the test reviewer identified, tagged with the AC it affects.
   - If the test reviewer returns PASS: add "Test strategy review: pass" to the review document as an informational note.

4. Verify the section ordering in the modified file is: (1) Argument, (2) Load spec, (3) Prior stage gate, (4) Re-run check, (5) Classification, (6) Council invocation, (7) Finding synthesis, (8) Test strategy review [NEW], (9) Threat model determination, (10) Gate invocation, (11) Transition.

5. Verify no existing sections were removed or reordered. The council invocation, finding synthesis, threat model determination, gate invocation, and transition sections must remain verbatim except for any minimal adjustments needed to reference the test strategy review result in the overall pass/fail determination.

6. Create `home/.claude/docs/brownfield-spec.md` with the following content (direct-address imperatives, no preamble, no introduction):

   Line 1: `Search the codebase for existing code that overlaps with the proposed feature before writing the technical approach.`

   Line 2: `Identify established patterns, abstractions, and conventions that the feature must follow. Reference specific files or modules.`

   Line 3: `In the technical approach, distinguish what is new from what extends or modifies existing code.`

   Line 4: `If the feature replaces existing functionality, include removal or migration of the old path in scope. Partial replacement — new code on the new pattern, old code left on the old pattern — is a defect, not a follow-up.`

   Line 5: `If the feature duplicates functionality that already exists, stop and reconsider the approach. Prefer extending existing abstractions over introducing parallel ones.`

   Each instruction is a separate paragraph (blank line between them). No heading, no preamble, no closing text.

7. Verify the brownfield doc:
   - Starts with the first instruction (no heading or preamble)
   - Contains exactly 5 instruction paragraphs
   - Each instruction uses direct-address imperative voice
   - No passive voice, no third-person framing

## Files to create/modify

- `home/.claude/skills/spec-review/SKILL.md` (modify)
- `home/.claude/docs/brownfield-spec.md` (create)

## Test requirements

Tests from task-17 must pass. Run `bash tests/sdl-workflow/test-review-integration.sh` from project root and verify all tests pass.

## Acceptance criteria

AC-05: Review integration invokes council review via `/spec-review` and parses output for pass/fail. Failing reviews set state to PARKED with feedback attached.

Primary AC: all tests from task-17 pass.

## Model

Sonnet

## Wave

3
