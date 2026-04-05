---
id: task-13
type: implementation
wave: 2
covers: [AC-05, AC-06]
files_to_modify:
  - assets/agents/fbk-code-review-detector.md
  - assets/agents/fbk-code-review-challenger.md
test_tasks: [task-05, task-07]
completion_gate: "task-05, task-07 tests pass"
---

## Objective

Adds a nit suppression instruction to the Detector agent definition and two pattern-label handling instructions to the Challenger agent definition.

## Context

The Detector currently generates nit-level sightings that waste Challenger verification cycles (the Challenger already rejects them per code-review-guide.md). Adding a nit suppression instruction to the Detector's "Scope discipline" section stops them at the source. The Challenger currently has no instruction to preserve or correct the Detector's cross-cutting pattern labels — labels silently vanish during verification. Two instructions must be added to the Challenger's "Verified finding" section.

## Instructions

1. In `fbk-code-review-detector.md`, add the following line at the end of the `## Scope discipline` section (after "Do not write files — you are read-only." on line 17):

   ```
   Exclude nits (naming, formatting, style with no behavioral or maintainability impact) from sightings.
   ```

   Completion: `grep -q 'Exclude nits' fbk-code-review-detector.md` succeeds AND `sed -n '/## Scope discipline/,/^## /p' fbk-code-review-detector.md | grep -q 'nit'` succeeds.

2. In `fbk-code-review-challenger.md`, locate the `**Verified finding:**` paragraph within the `## Verification protocol` section (line 14). Add the following two sentences at the end of this paragraph, after "...confirms the issue.":

   ```
   Preserve the Detector's cross-cutting pattern label in each verified finding. When verification reveals that sightings sharing a pattern label are independent issues, note the label correction.
   ```

   Completion: `grep -q 'pattern label' fbk-code-review-challenger.md` succeeds AND `grep -qiE 'label correction|independent issues' fbk-code-review-challenger.md` succeeds.

## Files to create/modify

- `assets/agents/fbk-code-review-detector.md` (modify)
- `assets/agents/fbk-code-review-challenger.md` (modify)

## Test requirements

Tests from task-05 (AC-05: nit suppression in Detector scope discipline; AC-06: pattern-label preservation and correction in Challenger, pattern-label fields tested in task-11's guide changes) and task-07 (coverage: no targets lost) must pass after this task.

## Acceptance criteria

- AC-05: `fbk-code-review-detector.md` contains "Exclude nits" instruction in the Scope discipline section
- AC-06: `fbk-code-review-challenger.md` contains two pattern-label instructions: one for preservation ("Preserve the Detector's cross-cutting pattern label") and one for correction ("label correction")

## Model

Haiku

## Wave

Wave 2
