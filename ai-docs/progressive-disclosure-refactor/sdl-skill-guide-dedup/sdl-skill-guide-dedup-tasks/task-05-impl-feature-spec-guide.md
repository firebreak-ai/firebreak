---
id: task-05
type: implementation
wave: 1
covers: [AC-01, AC-06]
files_to_modify:
  - assets/fbk-docs/fbk-sdl-workflow/feature-spec-guide.md
test_tasks: [task-01]
completion_gate: "task-01 assertion T11a (specifically the `Before invoking \\`/spec-review\\`` substring) passes"
---

## Objective

Add one summarize-and-compact transition step to the `## Transition` section of `assets/fbk-docs/fbk-sdl-workflow/feature-spec-guide.md`, consolidating the directive that currently lives in `fbk-spec/SKILL.md` (removed by task-02) into single-source ownership in the guide.

## Context

Per spec §4.3a, the summarize-and-compact directive currently duplicated in `fbk-spec/SKILL.md` §"Transition" is consolidated into `feature-spec-guide.md` §"Transition" as one additive step. Task-02 removes the directive from the skill; this task adds it to the guide.

The existing `## Transition` section in `feature-spec-guide.md` contains a 5-step numbered list (lines 147-153). The new step is inserted as a new numbered item BEFORE the existing "If agreed: invoke `/spec-review <feature-name>`" line (currently step 5 at line 153). After insertion, the list expands from 5 steps to 6 steps; the previous step 5 becomes step 6 (or the steps remain numbered as-is and the new step becomes step 5; choose to renumber so the chained-invocation step remains the final step).

**Verbatim insertion text per spec §4.3a:**

> Before invoking `/spec-review`: confirm all artifacts are written to disk; summarize the completed spec (feature name, artifact path, key decisions); compact context.

The text contains literal backticks around `/spec-review` — preserve them exactly. Task-01's T11a assertion uses `grep -qF` against the substring `` Before invoking `/spec-review` `` (with backticks) to verify this insertion.

No other guide content changes. No existing prose is reworded.

## Instructions

Read the current file (`assets/fbk-docs/fbk-sdl-workflow/feature-spec-guide.md`) before editing. The line ranges below match the current state of the file as of compilation time.

1. **Site 1 — Insert one new step in `## Transition` section (current lines 145-155).**

   The current `## Transition` section reads:

   ```
   ## Transition

   When the user signals the spec is complete:

   1. Run structural prerequisites by calling the gate script.
   2. If the gate fails: report which checks failed and what is missing.
   3. If the gate passes: confirm structural completeness and present the semantic criteria for the user to assess.
   4. If the user is satisfied: ask "Would you like to move to spec review?"
   5. If agreed: invoke `/spec-review <feature-name>`.

   For project-level: after the user agrees on the overview and feature decomposition, ask which feature to spec first. Do not invoke `/spec-review` until a complete feature-level spec passes the gate.
   ```

   Insert one new numbered step between current step 4 ("If the user is satisfied...") and current step 5 ("If agreed: invoke...") so the section becomes:

   ```
   ## Transition

   When the user signals the spec is complete:

   1. Run structural prerequisites by calling the gate script.
   2. If the gate fails: report which checks failed and what is missing.
   3. If the gate passes: confirm structural completeness and present the semantic criteria for the user to assess.
   4. If the user is satisfied: ask "Would you like to move to spec review?"
   5. Before invoking `/spec-review`: confirm all artifacts are written to disk; summarize the completed spec (feature name, artifact path, key decisions); compact context.
   6. If agreed: invoke `/spec-review <feature-name>`.

   For project-level: after the user agrees on the overview and feature decomposition, ask which feature to spec first. Do not invoke `/spec-review` until a complete feature-level spec passes the gate.
   ```

   The previous step 5 (`If agreed: invoke...`) is renumbered to step 6. The new step 5 contains the verbatim sentence from spec §4.3a. The preceding paragraph (`When the user signals the spec is complete:`) and the trailing project-level paragraph remain unchanged.

   **Completion checks:**
   - `grep -qF 'Before invoking \`/spec-review\`' assets/fbk-docs/fbk-sdl-workflow/feature-spec-guide.md` succeeds.
   - `grep -qF 'confirm all artifacts are written to disk' assets/fbk-docs/fbk-sdl-workflow/feature-spec-guide.md` succeeds.
   - `grep -qF 'compact context' assets/fbk-docs/fbk-sdl-workflow/feature-spec-guide.md` succeeds.
   - `grep -qF 'If agreed: invoke \`/spec-review <feature-name>\`' assets/fbk-docs/fbk-sdl-workflow/feature-spec-guide.md` succeeds (preserved chained invocation).

2. **Verify other guide content is unchanged.** No section other than `## Transition` is edited. No existing prose is reworded.

   **Completion checks for unchanged content:**
   - `grep -qF 'If the gate fails:' assets/fbk-docs/fbk-sdl-workflow/feature-spec-guide.md` succeeds (existing content T11a verifies preserved).
   - `grep -qF 'Refuse to write code' assets/fbk-docs/fbk-sdl-workflow/feature-spec-guide.md` succeeds (existing content T11a verifies preserved).

3. **Run task-01's test to verify post-edit state:**

   ```
   bash tests/sdl-workflow/test-skill-guide-dedup.sh
   ```

   T11a (`feature-spec-guide.md` contains `If the gate fails:`, `Refuse to write code`, AND `` Before invoking `/spec-review` ``) must report `ok`. The first two substrings already exist in the guide pre-edit; only the third (added by this task) flips from `not ok` to `ok`.

## Files to create/modify

- `assets/fbk-docs/fbk-sdl-workflow/feature-spec-guide.md` (modify)

Do not modify any other file. Do not edit `fbk-spec/SKILL.md` (that is task-02's scope).

## Test requirements

This task makes the following task-01 assertion flip from partial-fail to fully `ok`:

- T11a (AC-01) — `feature-spec-guide.md` contains `If the gate fails:` AND `Refuse to write code` AND `` Before invoking `/spec-review` ``. The first two are pre-existing; only the third is added by this task. Until this task lands, T11a fails on the third substring.

## Acceptance criteria

- AC-01: The summarize-and-compact transition directive is present in `feature-spec-guide.md` §"Transition" as a numbered step before the chained-invocation step. The verbatim sentence from spec §4.3a is inserted with backticks around `/spec-review` preserved.
- task-01 assertion T11a flips to fully `ok`.

## Model

Haiku

## Wave

Wave 1
