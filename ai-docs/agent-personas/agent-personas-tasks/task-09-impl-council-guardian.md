---
id: task-09
type: implementation
wave: 1
covers: [AC-02, AC-06]
files_to_modify:
  - assets/agents/fbk-council-guardian.md
test_tasks: [task-01]
completion_gate: "task-01 tests pass"
---

## Objective

Rewrite `assets/agents/fbk-council-guardian.md` body to the activation-focused pattern so the full body sits at or below 40 lines with a role-activation line, an `## Output quality bars` section, and no description-heavy sections.

## Context

The Guardian is one of 6 council agents, specialized in testing strategy and edge-case analysis. The spec restructures the persona so every quality-assurance recommendation is concrete: specific triggering inputs, named test types, named failure modes, and risk-grounded must/nice distinctions.

The canonical references for the target pattern are `assets/agents/fbk-code-review-detector.md` and `assets/agents/fbk-code-review-challenger.md`. The 40-line ceiling applies to the full body.

Preserve the existing frontmatter unchanged.

## Instructions

1. Read the current file at `assets/agents/fbk-council-guardian.md` to confirm frontmatter fields.
2. Preserve the frontmatter block unchanged.
3. Replace the entire body (everything after the second `---`) with this content (verbatim):

   ```
   You are a QA architect at an enterprise software company who designs testing strategies for production services. You contribute to council discussions by naming the specific failure modes a design must survive and the tests that prove it.

   ## Output quality bars

   - Edge cases include the specific input or state that triggers them. "Handle null input" is table stakes; name the call path and the upstream producer that makes null reachable.
   - Testing recommendations name the test type (unit, integration, contract, property-based, end-to-end), the behavior covered, and the failure mode caught. "Add a test" does not meet this bar.
   - Distinguish "must handle" from "nice to handle" with the risk assessment that determines which. Name the user impact and the likelihood of occurrence, not a generic "edge case" label.
   ```

4. Do not add any of the forbidden headings (`## Your Identity`, `## Your Expertise`, `## How You Contribute`, `## Your Communication Style`, `## In Council Discussions`, `## Critical Behaviors`).
5. Verify body length:
   ```bash
   awk '/^---$/{c++; if(c==2){found=1; next}} found' assets/agents/fbk-council-guardian.md | wc -l
   ```
6. Run `bash tests/sdl-workflow/test-council-agent-personas.sh`. The 5 assertions targeting this file must pass.

## Files to create/modify

- **Modify**: `assets/agents/fbk-council-guardian.md` — full body rewrite. Frontmatter unchanged.

## Test requirements

No new tests. Structural assertions live in `task-01-test-council-agent-structure.md`.

## Acceptance criteria

- `tests/sdl-workflow/test-council-agent-personas.sh` — all 5 assertions for `fbk-council-guardian.md` pass
- Covers AC-02 and the structural half of AC-06
- Frontmatter preserved byte-for-byte

## Model

Haiku

## Wave

1
