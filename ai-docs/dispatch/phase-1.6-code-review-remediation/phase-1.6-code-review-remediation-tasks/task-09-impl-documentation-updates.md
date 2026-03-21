---
id: T-09
type: implementation
wave: 6
covers: []
files_to_create: []
files_to_modify: ["../../README.md", "../../home/dot-claude/docs/sdl-workflow.md", "dispatch-overview.md"]
test_tasks: ["T-03"]
completion_gate: "README.md contains /code-review in the commands table, sdl-workflow.md references code review as a stage, dispatch-overview.md references Phase 1.6"
---

## Objective

Updates three documentation files to reference the new `/code-review` skill: README.md (commands table and pipeline diagram), sdl-workflow.md (stage listing), and dispatch-overview.md (phase listing).

## Context

These are small documentation updates — adding a table row, a stage entry, and a phase reference. No structural changes. The updates reference the skill and docs created in prior waves, so this task runs last.

This task modifies 3 files, exceeding the 1-2 file target. Justification: each modification is a single-line or few-line addition to an existing section. The changes are trivial insertions into established structures (a table row, a list item, a paragraph). Splitting into 3 tasks would add overhead without reducing risk.

No test task covers these documentation changes. The completion gate is a manual verification that the additions are present.

## Instructions

1. Read `README.md` and locate the slash commands table in the "SDL Workflow" section. The table currently has 4 rows: `/spec`, `/spec-review`, `/breakdown`, `/implement`.

2. Add a new row to the commands table after the `/implement` row:

   ```
   | `/code-review` | Review existing code or post-implementation output using adversarial Detector/Challenger agents | Verified findings and optional remediation spec |
   ```

3. In the same README.md, locate the pipeline diagram (the ASCII art showing `Spec ─► Review ─► Breakdown ─► ...`). Add `Code Review` after `Verification` in the pipeline:

   Update the pipeline to:
   ```
   Spec ─► Review ─► Breakdown ─► Test Creation ─► Test Review ─► Implementation ─► Verification ─► Code Review ─► PR
   ```

   Add a notation below the diagram for the Code Review stage:
   ```
        adversarial
        Detector/Challenger
        verification loop
   ```

4. In the README.md "How It Works" section, in the "SDL Workflow" subsection (the paragraph starting "A 4-stage interactive pipeline"), add a sentence noting that code review is available as both a standalone skill and a post-implementation pipeline stage. Change "4-stage" to "5-stage" and add `/code-review` to the list: "**Spec → Review → Breakdown → Implement → Code Review**".

5. Read `home/dot-claude/docs/sdl-workflow.md` and locate the "Stage Guides" section.

6. Add a new entry after the "When implementing tasks from a breakdown" line:

   ```
   When reviewing code or running post-implementation review → `/code-review` skill loads `sdl-workflow/code-review-guide.md`
   ```

7. Read `ai-docs/dispatch/dispatch-overview.md` and locate the feature map or phase listing. Find where Phase 1.5 is mentioned.

8. Add a reference to Phase 1.6 after the Phase 1.5 reference. If the phases are listed in the testing philosophy or elsewhere, add: "Phase 1.6 (code review and remediation) adds `/code-review` — adversarial code review with Detector/Challenger agents producing verified findings and optional remediation specs."

## Files to create/modify

- `README.md` (modify — add table row, update diagram, update stage count)
- `home/dot-claude/docs/sdl-workflow.md` (modify — add one stage guide entry)
- `ai-docs/dispatch/dispatch-overview.md` (modify — add Phase 1.6 reference)

## Test requirements

This is an implementation task. No test task explicitly covers these documentation changes. Visual verification:
- README.md commands table includes `/code-review` row
- README.md pipeline diagram includes Code Review stage
- sdl-workflow.md Stage Guides section includes code review entry
- dispatch-overview.md references Phase 1.6

## Acceptance criteria

- README.md documents `/code-review` in the commands table and pipeline diagram
- sdl-workflow.md lists code review as a workflow stage
- dispatch-overview.md references Phase 1.6

## Model

Haiku

## Wave

Wave 6
