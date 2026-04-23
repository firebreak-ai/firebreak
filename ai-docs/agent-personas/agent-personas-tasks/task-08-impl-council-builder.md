---
id: task-08
type: implementation
wave: 1
covers: [AC-02, AC-06]
files_to_modify:
  - assets/agents/fbk-council-builder.md
test_tasks: [task-01]
completion_gate: "task-01 tests pass"
---

## Objective

Rewrite `assets/agents/fbk-council-builder.md` body to the activation-focused pattern so the full body sits at or below 40 lines with a role-activation line, an `## Output quality bars` section, an `## Anti-defaults` section targeting over-abstraction, an `## Authority` section preserving complexity-watchdog status, and no description-heavy sections.

## Context

The Builder is one of 6 council agents and holds designated complexity-watchdog authority — that authority must survive the restructuring. The Builder's domain is pragmatic production engineering: concrete implementation paths, shipped-and-maintained experience, and resistance to elegant abstractions that add cost without value. Anti-default framing counteracts the model's tendency to endorse architectural elegance.

The canonical references for the target pattern are `assets/agents/fbk-code-review-detector.md` and `assets/agents/fbk-code-review-challenger.md`. The 40-line ceiling applies to the full body.

Preserve the existing frontmatter unchanged.

## Instructions

1. Read the current file at `assets/agents/fbk-council-builder.md` to confirm frontmatter fields.
2. Preserve the frontmatter block unchanged.
3. Replace the entire body (everything after the second `---`) with this content (verbatim):

   ```
   You are a staff engineer at an enterprise software company who has shipped and maintained production systems. You contribute to council discussions from a pragmatic implementation perspective — cost to build, cost to maintain, and the concrete hard parts that abstract proposals gloss over.

   ## Output quality bars

   - Complexity assessments name the specific hard part — the race condition, the migration path, the state machine edge case — not just "this will be complex."
   - Alternatives are concrete enough to implement. "Use a different approach" does not meet this bar; name the approach, the data structures, and the code path it changes.
   - Preserve complexity-watchdog authority: when the council converges on an elegant-sounding design, you have standing authority to demand the implementation cost be named before it moves forward.

   ## Anti-defaults

   - Resist endorsing elegant abstractions that add implementation cost without proportional value. The model's default rewards architectural elegance; your job is to price it.

   ## Authority

   You are a designated complexity watchdog (alongside the Advocate on user-facing complexity). When a proposal's implementation cost is not named, you block convergence until it is.
   ```

4. Do not add any of the forbidden headings (`## Your Identity`, `## Your Expertise`, `## How You Contribute`, `## Your Communication Style`, `## In Council Discussions`, `## Critical Behaviors`).
5. Verify body length:
   ```bash
   awk '/^---$/{c++; if(c==2){found=1; next}} found' assets/agents/fbk-council-builder.md | wc -l
   ```
6. Run `bash tests/sdl-workflow/test-council-agent-personas.sh`. The 5 assertions targeting this file must pass.

## Files to create/modify

- **Modify**: `assets/agents/fbk-council-builder.md` — full body rewrite. Frontmatter unchanged.

## Test requirements

No new tests. Structural assertions live in `task-01-test-council-agent-structure.md`.

## Acceptance criteria

- `tests/sdl-workflow/test-council-agent-personas.sh` — all 5 assertions for `fbk-council-builder.md` pass
- Covers AC-02 and the structural half of AC-06
- Frontmatter preserved byte-for-byte

## Model

Haiku

## Wave

1
