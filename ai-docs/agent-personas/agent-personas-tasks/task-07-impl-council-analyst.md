---
id: task-07
type: implementation
wave: 1
covers: [AC-02, AC-06]
files_to_modify:
  - assets/agents/fbk-council-analyst.md
test_tasks: [task-01]
completion_gate: "task-01 tests pass"
---

## Objective

Rewrite `assets/agents/fbk-council-analyst.md` body to the activation-focused pattern so the full body sits at or below 40 lines with a role-activation line, an `## Output quality bars` section, and no description-heavy sections.

## Context

The Analyst is one of 6 council agents currently using a ~75-line description-heavy template. The spec replaces the template with an activation-focused pattern. The Analyst's domain is observability and measurement — every claim should be paired with how to measure it, and belief should be distinguished from knowledge.

The canonical references for the target pattern are `assets/agents/fbk-code-review-detector.md` and `assets/agents/fbk-code-review-challenger.md`. The 40-line ceiling applies to the full body (council agents are persona-only).

Preserve the existing frontmatter unchanged.

## Instructions

1. Read the current file at `assets/agents/fbk-council-analyst.md` to confirm frontmatter fields.
2. Preserve the frontmatter block unchanged.
3. Replace the entire body (everything after the second `---`) with this content (verbatim):

   ```
   You are an observability engineer at an enterprise software company who designs measurement systems for production services. You contribute to council discussions by grounding claims in measurable evidence.

   ## Output quality bars

   - Every claim includes how to measure it. "This will be faster" without a metric and a collection mechanism is not an Analyst contribution.
   - Distinguish "we believe" from "we know" with the specific evidence that would convert belief to knowledge. Name the experiment, log, or instrumentation that would resolve the uncertainty.
   - Name the specific metric and its collection mechanism (counter, histogram, distributed trace, log query). Vague references to "telemetry" or "monitoring" do not meet this bar.
   ```

4. Do not add any of the forbidden headings (`## Your Identity`, `## Your Expertise`, `## How You Contribute`, `## Your Communication Style`, `## In Council Discussions`, `## Critical Behaviors`).
5. Verify body length:
   ```bash
   awk '/^---$/{c++; if(c==2){found=1; next}} found' assets/agents/fbk-council-analyst.md | wc -l
   ```
6. Run `bash tests/sdl-workflow/test-council-agent-personas.sh`. The 5 assertions targeting this file must pass.

## Files to create/modify

- **Modify**: `assets/agents/fbk-council-analyst.md` — full body rewrite. Frontmatter unchanged.

## Test requirements

No new tests written by this task. The paired test task `task-01-test-council-agent-structure.md` covers structural assertions for this file.

## Acceptance criteria

- `tests/sdl-workflow/test-council-agent-personas.sh` — all 5 assertions for `fbk-council-analyst.md` pass
- Covers AC-02 and the structural half of AC-06
- Frontmatter preserved byte-for-byte

## Model

Haiku

## Wave

1
