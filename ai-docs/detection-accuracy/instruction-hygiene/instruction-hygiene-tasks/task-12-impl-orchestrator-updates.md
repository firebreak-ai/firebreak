---
id: task-12
type: implementation
wave: 2
covers: [AC-07, AC-12]
files_to_modify:
  - assets/skills/fbk-code-review/SKILL.md
test_tasks: [task-06]
completion_gate: "task-06 tests pass"
---

## Objective

Rewrites SKILL.md steps 1 and 3 in the Detection-Verification Loop to specify content-first/instructions-last prompt ordering, and adds `quality-detection.md` to the initial read instructions.

## Context

SKILL.md is the orchestrator's instruction file. Its Detection-Verification Loop step 1 (line 40) currently constructs the Detector spawn prompt as "target code scope + source of truth + behavioral comparison instructions + structural detection targets + linter output" — placing instructions in the middle. Anthropic research measures 30% improvement from data-first/instructions-last ordering. Step 3 (line 42) similarly needs reordering. Additionally, the initial read instructions (line 10) reference `ai-failure-modes.md` but not `quality-detection.md`, meaning the conversational review flow may never load the structural detection targets.

## Instructions

1. In the initial read instructions (line 10, currently reads "Read `.claude/fbk-docs/fbk-sdl-workflow/code-review-guide.md` for the behavioral comparison methodology... Read `.claude/fbk-docs/fbk-sdl-workflow/ai-failure-modes.md` for the AI failure mode checklist used when no specs are available."), append a new sentence at the end:

   ```
   Read `.claude/fbk-docs/fbk-design-guidelines/quality-detection.md` for structural detection targets applicable to all code reviews.
   ```

   Completion: `head -20 SKILL.md | grep -q 'quality-detection'` succeeds.

2. Replace step 1 in the Detection-Verification Loop (line 40, currently reads "Spawn Detector with target code scope + source of truth + behavioral comparison instructions + structural detection targets from `fbk-docs/fbk-design-guidelines/quality-detection.md` + linter output (if available). Remind the Detector to tag each sighting with its detection source (`spec-ac`, `checklist`, `structural-target`, or `linter`).") with:

   ```
   1. Spawn Detector with: target code file contents first, then linter output (if available), then source of truth + behavioral comparison instructions + structural detection targets from `fbk-docs/fbk-design-guidelines/quality-detection.md` last. Instruct the Detector to tag each sighting with its detection source (`spec-ac`, `checklist`, `structural-target`, or `linter`).
   ```

   Completion: `grep -qiE 'file contents first' SKILL.md` succeeds.

3. Replace step 3 in the Detection-Verification Loop (line 42, currently reads "Spawn Challenger with sightings + code + 'verify or reject each sighting with evidence'") with:

   ```
   3. Spawn Challenger with: target code file contents first, then sightings to verify, then verification instructions last.
   ```

   Completion: `grep -A3 'Spawn Challenger' SKILL.md | grep -qiE 'contents? first|file contents first'` succeeds.

## Files to create/modify

- `assets/skills/fbk-code-review/SKILL.md` (modify)

## Test requirements

Tests from task-06 (AC-07: steps 1 and 3 content-first ordering; AC-12: initial reads reference both ai-failure-modes and quality-detection) must pass after this task.

## Acceptance criteria

- AC-07: SKILL.md steps 1 and 3 specify prompt component ordering with code content first and instructions last
- AC-12: SKILL.md initial read instructions include both `ai-failure-modes.md` and `quality-detection.md`

## Model

Haiku

## Wave

Wave 2
