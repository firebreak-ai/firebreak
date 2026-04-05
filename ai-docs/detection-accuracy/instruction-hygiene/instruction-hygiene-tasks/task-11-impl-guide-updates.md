---
id: task-11
type: implementation
wave: 2
covers: [AC-06, AC-13]
files_to_modify:
  - assets/fbk-docs/fbk-sdl-workflow/code-review-guide.md
test_tasks: [task-02, task-05, task-06, task-07]
completion_gate: "task-02, task-05, task-06, task-07 tests pass"
---

## Objective

Modifies `code-review-guide.md` to remove the dead infrastructure subsection, add pattern-label fields to format templates, align the Orchestration Protocol with content-first ordering, and remove hierarchy language from Source of Truth Handling.

## Context

`code-review-guide.md` has four changes:
1. The "Dead and disconnected infrastructure" subsection (lines 15-17) is a detection target that belongs in detection target documents, not the behavioral comparison methodology. It must be removed.
2. The Sighting Format and Finding Format templates lack a `Pattern label:` field. The Detector assigns pattern labels but they have no structural slot in the output schema.
3. The Orchestration Protocol step 1 (line 94) must reflect content-first/instructions-last ordering consistent with the SKILL.md rewrite.
4. The Source of Truth Handling "No spec available" paragraph (line 112) uses "Supplement with" hierarchy language that implies quality-detection.md is secondary, contradicting the unconditional injection model.

## Instructions

1. Remove the `### Dead and disconnected infrastructure` subsection (lines 15-17): the heading and the two-line paragraph body. Remove lines 15 through 17 inclusive (the heading, the paragraph, and any trailing blank line before the next section). The `## Sighting Format` heading should follow directly after `### AC verification precision` content.

   Completion: `! grep -q 'Dead and disconnected infrastructure' code-review-guide.md` succeeds.

2. In the Sighting Format template (the code block starting at line ~23), add a `Pattern label:` field after the `Source of truth:` line. Insert:

   ```
   Pattern label: cross-cutting pattern name (if applicable)
   ```

   Completion: Extract the Sighting Format section and verify it contains "Pattern label": `sed -n '/## Sighting Format/,/^## /p' code-review-guide.md | grep -q 'Pattern label'` succeeds.

3. In the Finding Format template (the code block starting at line ~50), add a `Pattern label:` field after the `Evidence:` line. Insert:

   ```
   Pattern label: cross-cutting pattern name (if applicable)
   ```

   Completion: Extract the Finding Format section and verify it contains "Pattern label": `sed -n '/## Finding Format/,/^## /p' code-review-guide.md | grep -q 'Pattern label'` succeeds.

4. In the Orchestration Protocol section, replace step 1 (line ~94, currently reads "The orchestrator spawns the Detector with target code, source of truth, this guide's behavioral comparison instructions, and the structural detection targets from...") with:

   ```
   1. The orchestrator spawns the Detector with target code file contents first, then linter output (if available), then source of truth + this guide's behavioral comparison instructions + structural detection targets from `fbk-docs/fbk-design-guidelines/quality-detection.md` last
   ```

   Completion: `sed -n '/## Orchestration Protocol/,/^## /p' code-review-guide.md | grep -qiE 'contents? first|code.*first|file contents first'` succeeds.

5. In the Source of Truth Handling section, replace the "No spec available" paragraph (line ~112, currently reads "**No spec available**: Use the AI failure mode checklist... Supplement with the structural detection targets from `fbk-docs/fbk-design-guidelines/quality-detection.md` for framework-aware pattern detection.") with:

   ```
   **No spec available**: Use both the AI failure mode checklist (`fbk-docs/fbk-sdl-workflow/ai-failure-modes.md`) and the structural detection targets from `fbk-docs/fbk-design-guidelines/quality-detection.md` for structural issue detection.
   ```

   Completion: `! grep -qi 'supplement with' code-review-guide.md` succeeds AND `grep -q 'Use both' code-review-guide.md` succeeds.

## Files to create/modify

- `assets/fbk-docs/fbk-sdl-workflow/code-review-guide.md` (modify)

## Test requirements

Tests from task-02 (dead infrastructure assertion redirected), task-05 (AC-06: Pattern label fields in Sighting Format and Finding Format), task-06 (AC-13: Orchestration Protocol content-first ordering, Source of Truth no hierarchy language), and task-07 (coverage: no targets lost) must pass after this task.

## Acceptance criteria

- AC-06: Sighting Format and Finding Format templates both contain a `Pattern label:` field
- AC-13: Orchestration Protocol step 1 reflects content-first ordering; Source of Truth Handling uses "both" without primary/supplementary hierarchy

## Model

Haiku

## Wave

Wave 2
