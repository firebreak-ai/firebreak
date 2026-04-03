---
id: T-06
type: implementation
wave: 3
covers: [AC-01, AC-06]
depends_on: [T-04]
files_to_modify: [assets/skills/fbk-code-review/SKILL.md, assets/fbk-docs/fbk-sdl-workflow.md]
test_tasks: [T-05]
completion_gate: "T-05 tests pass"
---

## Objective

Updates the code review skill to transition into `/fbk-improve` after retrospective finalization, and adds self-improvement to the SDL workflow pipeline doc.

## Context

The code review skill currently ends after producing the retrospective. This task adds a transition instruction so the pipeline flows seamlessly into self-improvement analysis. The SDL workflow doc lists all pipeline stages and needs an entry for the new stage.

## Instructions

### Code review skill update

1. Read `assets/skills/fbk-code-review/SKILL.md`.
2. In the `## Retrospective` section, after the existing instruction "After the review completes, produce a retrospective following the fields defined in `code-review-guide.md`.", add:

   ```
   After the retrospective is written to disk, invoke `/fbk-improve <feature-name>` to analyze the retrospective for pipeline improvement opportunities.
   ```

3. Do not modify any other section of the code review skill.

### SDL workflow doc update

1. Read `assets/fbk-docs/fbk-sdl-workflow.md`.
2. In the `## Stage Guides` section, after the code review entry ("When reviewing code or running post-implementation review → `/code-review` skill loads `fbk-sdl-workflow/code-review-guide.md`"), add:

   ```
   When analyzing retrospectives for pipeline improvement → `/fbk-improve` skill spawns the improvement analyst agent
   ```

3. Do not modify any other section of the SDL workflow doc.

## Files to create/modify

- Modify: `assets/skills/fbk-code-review/SKILL.md`
- Modify: `assets/fbk-docs/fbk-sdl-workflow.md`

## Test requirements

T-05 tests validate:
- Code review skill contains `/fbk-improve` invocation in Retrospective section
- SDL workflow doc references the self-improvement stage after code review

## Acceptance criteria

- AC-01: Code review skill transitions to `/fbk-improve` after retrospective, establishing the automatic invocation seam.
- AC-06: No change needed here — the improve skill already has Edit in its allowed-tools (established in T-04).

## Model

Sonnet

## Wave

Wave 3
