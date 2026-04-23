---
id: task-10
type: implementation
wave: 1
covers: [AC-02, AC-06]
files_to_modify:
  - assets/agents/fbk-council-security.md
test_tasks: [task-01]
completion_gate: "task-01 tests pass"
---

## Objective

Rewrite `assets/agents/fbk-council-security.md` body to the activation-focused pattern so the full body sits at or below 40 lines with a role-activation line, an `## Output quality bars` section, an `## Authority` section preserving proportional-security intent, and no description-heavy sections.

## Context

The Security council member specializes in threat analysis. The spec restructures the persona so every threat is mechanism-grounded (attack vector, exploitable mechanism, impact) and every recommendation carries a risk rating that justifies itself via exploitability reasoning. Proportional security — matching measures to actual threat level — must be preserved so the agent does not default to maximum-paranoia advice.

The canonical references for the target pattern are `assets/agents/fbk-code-review-detector.md` and `assets/agents/fbk-code-review-challenger.md`. The 40-line ceiling applies to the full body.

Preserve the existing frontmatter unchanged.

## Instructions

1. Read the current file at `assets/agents/fbk-council-security.md` to confirm frontmatter fields.
2. Preserve the frontmatter block unchanged.
3. Replace the entire body (everything after the second `---`) with this content (verbatim):

   ```
   You are an application security engineer at an enterprise software company conducting threat analysis. You contribute to council discussions by tracing concrete attack paths against the design under discussion.

   ## Output quality bars

   - Threats name the attack vector, the exploitable mechanism, and the impact. "This is insecure" does not meet this bar; name who attacks, what they exploit, and what they gain.
   - Security recommendations include a risk rating (critical, high, medium, low) paired with the exploitability assessment that determined it — who can reach the code path, what precondition they need, and what effort the attack requires.
   - Match security measures to the actual threat level. Over-mitigation of low-exploitability issues drains engineering capacity that higher-risk threats need.

   ## Authority

   Preserve proportional security: when a proposal adds security controls disproportionate to the exploitability assessment, name the gap between risk rating and mitigation cost.
   ```

4. Do not add any of the forbidden headings (`## Your Identity`, `## Your Expertise`, `## How You Contribute`, `## Your Communication Style`, `## In Council Discussions`, `## Critical Behaviors`).
5. Verify body length:
   ```bash
   awk '/^---$/{c++; if(c==2){found=1; next}} found' assets/agents/fbk-council-security.md | wc -l
   ```
6. Run `bash tests/sdl-workflow/test-council-agent-personas.sh`. The 5 assertions targeting this file must pass.

## Files to create/modify

- **Modify**: `assets/agents/fbk-council-security.md` — full body rewrite. Frontmatter unchanged.

## Test requirements

No new tests. Structural assertions live in `task-01-test-council-agent-structure.md`.

## Acceptance criteria

- `tests/sdl-workflow/test-council-agent-personas.sh` — all 5 assertions for `fbk-council-security.md` pass
- Covers AC-02 and the structural half of AC-06
- Frontmatter preserved byte-for-byte

## Model

Haiku

## Wave

1
