---
id: task-06
type: implementation
wave: 1
covers: [AC-02, AC-06]
files_to_modify:
  - assets/agents/fbk-council-architect.md
test_tasks: [task-01]
completion_gate: "task-01 tests pass"
---

## Objective

Rewrite `assets/agents/fbk-council-architect.md` body to the activation-focused pattern so the full body sits at or below 40 lines with a role-activation line, an `## Output quality bars` section, and no description-heavy sections.

## Context

The Architect is one of 6 council agents currently using a ~75-line description-heavy template (`## Your Identity`, `## Your Expertise`, `## How You Contribute to Discussions`, `## Your Communication Style`, `## In Council Discussions`, `## Critical Behaviors`). The spec replaces this with an activation-focused pattern that constrains what the output demonstrates rather than describing who the agent is. The role, specialization (systems design, tradeoffs, architectural debt), and council-participation intent are preserved — only the framing changes.

The canonical reference for the activation-focused pattern is `assets/agents/fbk-code-review-detector.md` (47 lines — full pattern with quality bars) and `assets/agents/fbk-code-review-challenger.md` (21 lines — minimal effective persona). Follow the same shape: role-activation line as the first body paragraph, quality bars as a heading with 3-item falsifiable list, optional authority/anti-default sections.

The 40-line body ceiling is measured from the first content line after the closing `---` of the frontmatter to end-of-file. Council agents are persona-only — they contain no task logic — so the ceiling applies to the entire body.

Preserve the existing frontmatter (`name`, `description`, `tools`) unchanged.

## Instructions

1. Read the current file at `assets/agents/fbk-council-architect.md` to confirm frontmatter fields.
2. Preserve the frontmatter block unchanged (do not modify `name`, `description`, or `tools` fields).
3. Replace the entire body (everything after the second `---`) with this content (verbatim):

   ```
   You are a principal engineer reviewing system design at an enterprise software company. You bring a structural perspective to the council — long-term maintainability, service boundaries, and architectural coherence are your lens.

   ## Output quality bars

   - Every recommendation references the architectural constraint that motivates it. Name the constraint (service boundary, data ownership, coupling rule, scalability limit), not just "this is cleaner."
   - Tradeoff analysis names what is sacrificed, not only what is gained. An endorsement without a named tradeoff is incomplete.
   - When a proposal creates structural debt, name the specific future cost — the change that becomes harder, the team that inherits it, or the scaling limit it introduces.

   ## Authority

   Defer to the Builder and Advocate on complexity judgments — they are the designated complexity watchdogs. Focus your authority on structural soundness and long-term evolution.
   ```

4. Do not add `## Your Identity`, `## Your Expertise`, `## How You Contribute`, `## Your Communication Style`, `## In Council Discussions`, or `## Critical Behaviors` headings. These are forbidden by the test.
5. Verify the full body (post-frontmatter) is at or below 40 lines using:
   ```bash
   awk '/^---$/{c++; if(c==2){found=1; next}} found' assets/agents/fbk-council-architect.md | wc -l
   ```
6. Run `bash tests/sdl-workflow/test-council-agent-personas.sh`. The 5 tests targeting this file (file exists, frontmatter valid, body <= 40 lines, `## Output quality bars` present, no forbidden headings) must pass.

## Files to create/modify

- **Modify**: `assets/agents/fbk-council-architect.md` — full body rewrite. Frontmatter unchanged.

## Test requirements

No new tests written by this task. The paired test task `task-01-test-council-agent-structure.md` already contains the 5 assertions for this file in `tests/sdl-workflow/test-council-agent-personas.sh`.

## Acceptance criteria

- `tests/sdl-workflow/test-council-agent-personas.sh` — all 5 assertions for `fbk-council-architect.md` pass (existence, frontmatter, ≤40-line body, `## Output quality bars` heading, no forbidden headings)
- Covers AC-02 (activation-focused pattern for council agents) and the structural half of AC-06 (mechanical shape)
- Frontmatter preserved byte-for-byte

## Model

Haiku

## Wave

1
