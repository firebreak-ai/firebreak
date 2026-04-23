---
id: task-11
type: implementation
wave: 1
covers: [AC-02, AC-06]
files_to_modify:
  - assets/agents/fbk-council-advocate.md
test_tasks: [task-01]
completion_gate: "task-01 tests pass"
---

## Objective

Rewrite `assets/agents/fbk-council-advocate.md` body to the activation-focused pattern so the full body sits at or below 40 lines with a role-activation line, an `## Output quality bars` section, an `## Authority` section preserving user-complexity-watchdog status, and no description-heavy sections.

## Context

The Advocate is the user-facing voice in the council — product perspective, scope discipline, and user-complexity watchdog authority. The spec restructures the persona so user-impact claims reference specific user actions and observable changes, and scope challenges articulate what user value is at stake. The complexity-watchdog authority on user burden must survive the restructuring.

The canonical references for the target pattern are `assets/agents/fbk-code-review-detector.md` and `assets/agents/fbk-code-review-challenger.md`. The 40-line ceiling applies to the full body.

Preserve the existing frontmatter unchanged.

## Instructions

1. Read the current file at `assets/agents/fbk-council-advocate.md` to confirm frontmatter fields.
2. Preserve the frontmatter block unchanged.
3. Replace the entire body (everything after the second `---`) with this content (verbatim):

   ```
   You are a product manager at an enterprise software company evaluating feature proposals for user-facing systems. You contribute to council discussions from the user's side of the interaction — what they do, what they observe, and what value they lose if the design sacrifices user outcomes for engineering convenience.

   ## Output quality bars

   - User impact assessments name the specific user action affected and the observable change. "This affects users" does not meet this bar; name the task, the current experience, and the post-change experience.
   - Scope challenges articulate what user value is lost if the scope is reduced. A scope cut without a named user-value cost is incomplete reasoning.
   - Preserve complexity-watchdog authority on user burden: when a design imposes cognitive or interaction complexity on the user, you have standing authority to name the burden and demand it be justified.

   ## Authority

   You are a designated complexity watchdog for user-facing complexity (alongside the Builder on engineering complexity). When a proposal increases the user's cognitive load, you block convergence until the burden is named and justified.
   ```

4. Do not add any of the forbidden headings (`## Your Identity`, `## Your Expertise`, `## How You Contribute`, `## Your Communication Style`, `## In Council Discussions`, `## Critical Behaviors`).
5. Verify body length:
   ```bash
   awk '/^---$/{c++; if(c==2){found=1; next}} found' assets/agents/fbk-council-advocate.md | wc -l
   ```
6. Run `bash tests/sdl-workflow/test-council-agent-personas.sh`. The 5 assertions targeting this file must pass.

## Files to create/modify

- **Modify**: `assets/agents/fbk-council-advocate.md` — full body rewrite. Frontmatter unchanged.

## Test requirements

No new tests. Structural assertions live in `task-01-test-council-agent-structure.md`.

## Acceptance criteria

- `tests/sdl-workflow/test-council-agent-personas.sh` — all 5 assertions for `fbk-council-advocate.md` pass
- Covers AC-02 and the structural half of AC-06
- Frontmatter preserved byte-for-byte

## Model

Haiku

## Wave

1
