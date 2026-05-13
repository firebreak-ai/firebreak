---
id: task-06
type: implementation
wave: 1
covers: [AC-02, AC-06]
files_to_modify:
  - assets/fbk-docs/fbk-sdl-workflow/review-perspectives.md
test_tasks: [task-01]
completion_gate: "task-01 assertion T11b (specifically the `Before invoking \\`/breakdown\\`` substring) passes"
---

## Objective

Add one summarize-and-compact transition step to the `## Transition` section of `assets/fbk-docs/fbk-sdl-workflow/review-perspectives.md`, consolidating the directive that currently lives in `fbk-spec-review/SKILL.md` (removed by task-03) into single-source ownership in the guide.

## Context

Per spec §4.3a, the summarize-and-compact directive currently duplicated in `fbk-spec-review/SKILL.md` §"Transition" is consolidated into `review-perspectives.md` §"Transition" as one additive step. Task-03 removes the directive from the skill; this task adds it to the guide.

The existing `## Transition` section in `review-perspectives.md` contains a 5-step numbered list (lines 114-121). The new step is inserted as a new numbered item BEFORE the existing "If agreed: invoke `/breakdown <feature-name>`" line (currently step 5 at line 121). After insertion, the list expands from 5 steps to 6 steps; the previous step 5 is renumbered to step 6 so the chained-invocation step remains the final step.

**Verbatim insertion text per spec §4.3a:**

> Before invoking `/breakdown`: confirm all artifacts are written to disk; summarize (feature name, number of findings by severity, threat model decision, gate result); compact context.

The text contains literal backticks around `/breakdown` — preserve them exactly. Task-01's T11b assertion uses `grep -qF` against the substring `` Before invoking `/breakdown` `` (with backticks) to verify this insertion.

No other guide content changes. No existing prose is reworded.

## Instructions

Read the current file (`assets/fbk-docs/fbk-sdl-workflow/review-perspectives.md`) before editing. The line ranges below match the current state of the file as of compilation time.

1. **Site 1 — Insert one new step in `## Transition` section (current lines 114-121).**

   The current `## Transition` section reads:

   ```
   ## Transition

   After presenting findings:
   1. Run structural prerequisites.
   2. If blocking findings exist: "There are N blocking findings. Would you like to revise the spec to address them, or accept with documented rationale?"
   3. If the user accepts blocking findings: record the rationale and risk owner in the review document before advancing.
   4. If all resolved: "The review is structurally complete. Would you like to proceed to task breakdown?"
   5. If agreed: invoke `/breakdown <feature-name>`.
   ```

   Insert one new numbered step between current step 4 ("If all resolved...") and current step 5 ("If agreed: invoke...") so the section becomes:

   ```
   ## Transition

   After presenting findings:
   1. Run structural prerequisites.
   2. If blocking findings exist: "There are N blocking findings. Would you like to revise the spec to address them, or accept with documented rationale?"
   3. If the user accepts blocking findings: record the rationale and risk owner in the review document before advancing.
   4. If all resolved: "The review is structurally complete. Would you like to proceed to task breakdown?"
   5. Before invoking `/breakdown`: confirm all artifacts are written to disk; summarize (feature name, number of findings by severity, threat model decision, gate result); compact context.
   6. If agreed: invoke `/breakdown <feature-name>`.
   ```

   The previous step 5 (`If agreed: invoke...`) is renumbered to step 6. The new step 5 contains the verbatim sentence from spec §4.3a. The preceding `After presenting findings:` line and step 1-4 content remain unchanged.

   **Completion checks:**
   - `grep -qF 'Before invoking \`/breakdown\`' assets/fbk-docs/fbk-sdl-workflow/review-perspectives.md` succeeds.
   - `grep -qF 'confirm all artifacts are written to disk' assets/fbk-docs/fbk-sdl-workflow/review-perspectives.md` succeeds.
   - `grep -qF 'number of findings by severity, threat model decision, gate result' assets/fbk-docs/fbk-sdl-workflow/review-perspectives.md` succeeds.
   - `grep -qF 'compact context' assets/fbk-docs/fbk-sdl-workflow/review-perspectives.md` succeeds.
   - `grep -qF 'If agreed: invoke \`/breakdown <feature-name>\`' assets/fbk-docs/fbk-sdl-workflow/review-perspectives.md` succeeds (preserved chained invocation).

2. **Verify other guide content is unchanged.** No section other than `## Transition` is edited. No existing prose is reworded.

   **Completion checks for unchanged content:**
   - `grep -qF 'Does this feature need a threat model?' assets/fbk-docs/fbk-sdl-workflow/review-perspectives.md` succeeds (existing content T11b verifies preserved).
   - `grep -qF 'There are N blocking findings' assets/fbk-docs/fbk-sdl-workflow/review-perspectives.md` succeeds (existing content T11b verifies preserved).
   - `grep -qF 'Present the classification with' assets/fbk-docs/fbk-sdl-workflow/review-perspectives.md` succeeds (existing content T11b verifies preserved).

3. **Run task-01's test to verify post-edit state:**

   ```
   bash tests/sdl-workflow/test-skill-guide-dedup.sh
   ```

   T11b (`review-perspectives.md` contains `Does this feature need a threat model?`, `There are N blocking findings`, `Present the classification with`, AND `` Before invoking `/breakdown` ``) must report `ok`. The first three substrings already exist in the guide pre-edit; only the fourth (added by this task) flips from `not ok` to `ok`.

## Files to create/modify

- `assets/fbk-docs/fbk-sdl-workflow/review-perspectives.md` (modify)

Do not modify any other file. Do not edit `fbk-spec-review/SKILL.md` (that is task-03's scope).

## Test requirements

This task makes the following task-01 assertion flip from partial-fail to fully `ok`:

- T11b (AC-02) — `review-perspectives.md` contains `Does this feature need a threat model?` AND `There are N blocking findings` AND `Present the classification with` AND `` Before invoking `/breakdown` ``. The first three are pre-existing; only the fourth is added by this task. Until this task lands, T11b fails on the fourth substring.

## Acceptance criteria

- AC-02: The summarize-and-compact transition directive is present in `review-perspectives.md` §"Transition" as a numbered step before the chained-invocation step. The verbatim sentence from spec §4.3a is inserted with backticks around `/breakdown` preserved.
- task-01 assertion T11b flips to fully `ok`.

## Model

Haiku

## Wave

Wave 1
