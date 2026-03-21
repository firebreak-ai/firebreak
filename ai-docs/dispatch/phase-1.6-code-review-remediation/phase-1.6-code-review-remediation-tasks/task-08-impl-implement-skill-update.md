---
id: T-08
type: implementation
wave: 4
covers: ["AC-07"]
files_to_create: []
files_to_modify: ["../../home/dot-claude/skills/implement/SKILL.md"]
test_tasks: ["T-02"]
completion_gate: "T-02 tests 17-18 pass (implement skill contains post-implementation review prompt with stage-transition pattern)"
---

## Objective

Adds a one-line stage-transition prompt to `home/dot-claude/skills/implement/SKILL.md` that asks the user if they want a code review after implementation completes.

## Context

The existing `/implement` skill follows a stage-transition pattern: at stage completion, it summarizes what was done and asks the user if they want to proceed to the next stage. Phase 1.6 adds a post-implementation code review as an optional next stage.

The prompt follows the existing pattern: the agent asks, the user decides. It does not auto-trigger the code review.

The addition goes in the "Final Verification" section or "Team Shutdown" section — after verification passes but before (or as part of) the final report to the user. The existing text in the Team Shutdown section reads: "Report: 'All tasks complete and verified...'" The new prompt goes just before this final report line.

T-02 validates with two tests:
- Test 17: The implement skill contains `review the implementation` or `code review` or `code-review` (case-insensitive)
- Test 18: The implement skill contains `would you like` or `ask` combined with `review` (case-insensitive) — the stage-transition pattern asks the user rather than auto-triggering

## Instructions

1. Read `home/dot-claude/skills/implement/SKILL.md` to find the exact insertion point.

2. In the "Team Shutdown" section, add the following line before the existing `Report:` line:

   `After final verification passes, ask the user: "Would you like to review the implementation with /code-review?" Follow the existing stage-transition pattern — summarize what was verified and offer the next stage.`

3. Do not modify any other section of the implement skill. Do not change the skill's frontmatter. This is a single-line addition.

## Files to create/modify

- `home/dot-claude/skills/implement/SKILL.md` (modify — add one line)

## Test requirements

This is an implementation task. The corresponding test task T-02 validates:
- Test 17: File contains post-implementation review prompt text
- Test 18: Prompt follows the stage-transition pattern (asks the user, does not auto-trigger)

## Acceptance criteria

- AC-07 (partial): The `/implement` skill contains the post-implementation code review stage-transition prompt

## Model

Haiku

## Wave

Wave 4
