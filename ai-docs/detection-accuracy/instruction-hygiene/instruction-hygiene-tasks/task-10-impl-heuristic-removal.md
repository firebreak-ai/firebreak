---
id: task-10
type: implementation
wave: 2
covers: [AC-04, AC-08, AC-10]
files_to_modify:
  - assets/skills/fbk-code-review/references/existing-code-review.md
test_tasks: [task-01, task-04, task-07]
completion_gate: "task-01, task-04, task-07 tests pass"
---

## Objective

Removes all six detection heuristic sections from `existing-code-review.md`, leaving the conversational flow guidance, user interaction model, spec co-authoring, finding presentation, and retrospective sections intact.

## Context

`existing-code-review.md` currently contains six detection heuristic sections that have been promoted to `quality-detection.md` or are duplicates of items in `ai-failure-modes.md`. These sections must be removed entirely (heading and body). The file retains all non-heuristic sections: Conversational Review Flow, User Interaction Model, Spec Co-Authoring, Spec Output, Scope Recognition, When Only Structural Issues Surface, Finding presentation, and Retrospective.

## Instructions

1. Remove the `## Dual-path verification` section (currently lines 35-37: heading and the paragraph body). Remove the heading and the following paragraph, up to but not including the next `## ` heading.

   Completion: `! grep -q '## Dual-path verification' existing-code-review.md` succeeds.

2. Remove the `## Sentinel value confusion` section (currently lines 39-41: heading and paragraph). Remove the heading and the following paragraph, up to but not including the next `## ` heading.

   Completion: `! grep -q '## Sentinel value confusion' existing-code-review.md` succeeds.

3. Remove the `## Test-production string alignment` section (currently lines 43-45: heading and paragraph). Remove the heading and the following paragraph, up to but not including the next `## ` heading.

   Completion: `! grep -q '## Test-production string alignment' existing-code-review.md` succeeds.

4. Remove the `## String-based error classification` section (currently lines 47-49: heading and paragraph). Remove the heading and the following paragraph, up to but not including the next `## ` heading.

   Completion: `! grep -q '## String-based error classification' existing-code-review.md` succeeds.

5. Remove the `## Dead infrastructure detection` section (currently lines 51-53: heading and paragraph). Remove the heading and the following paragraph, up to but not including the next `## ` heading.

   Completion: `! grep -q '## Dead infrastructure detection' existing-code-review.md` succeeds.

6. Remove the `## Dead code after field or function removal` section (currently lines 55-57: heading and paragraph). Remove the heading and the following paragraph, up to but not including the next `## ` heading.

   Completion: `! grep -q '## Dead code after field' existing-code-review.md` succeeds.

7. Verify the file still contains the retained sections: `grep -q '## Finding presentation' existing-code-review.md` AND `grep -q '## Retrospective' existing-code-review.md` AND `grep -q '## Conversational Review Flow' existing-code-review.md` all succeed.

## Files to create/modify

- `assets/skills/fbk-code-review/references/existing-code-review.md` (modify)

## Test requirements

Tests from task-01 (redirected assertions no longer assert on existing-code-review.md for promoted targets), task-04 (AC-04 removal: all 6 section headings absent from existing-code-review.md), and task-07 (coverage: targets still exist in other agent-facing docs) must pass after this task.

## Acceptance criteria

- AC-04: `existing-code-review.md` no longer contains any of the six detection heuristic sections (Dual-path verification, Sentinel value confusion, Test-production string alignment, String-based error classification, Dead infrastructure detection, Dead code after field or function removal)

## Model

Haiku

## Wave

Wave 2
