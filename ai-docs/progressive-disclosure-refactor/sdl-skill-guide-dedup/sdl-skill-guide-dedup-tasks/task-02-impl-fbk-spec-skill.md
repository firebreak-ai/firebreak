---
id: task-02
type: implementation
wave: 1
covers: [AC-01, AC-04, AC-05, AC-06]
files_to_modify:
  - assets/skills/fbk-spec/SKILL.md
test_tasks: [task-01]
completion_gate: "task-01 assertions T1, T1b, T2, T11a, T12, T13, T14, T15 pass"
---

## Objective

Refactor `assets/skills/fbk-spec/SKILL.md` to remove duplicated workflow prose (authoring-loop instructions, gate-decision narrative, transition narrative) while preserving all operational glue (frontmatter, `$ARGUMENTS` resolution, gate-script invocation, retrospective write directive, exit prompt, chained `/spec-review` invocation).

## Context

The `fbk-spec` skill loads `feature-spec-guide.md` unconditionally on its first instruction (line 10). Workflow protocol restated in the skill body is therefore duplicated on the same load path. Spec §4.3 enumerates three duplicated sections to remove from this file; spec §4.2 enumerates the operational-glue sections that must remain.

**Must be retained verbatim per spec §4.2:**

- YAML frontmatter (lines 1-8): `description:` and `argument-hint:` fields.
- `## Entry` section (lines 16-24): `$ARGUMENTS` resolution, scope determination, file-existence handling.
- The read-the-guide pointers (lines 10, 12, 14): `feature-spec-guide.md`, `corrective-workflow.md`, `fbk-brownfield-spec.md`.
- `## Gate` heading and the literal gate-script invocation block (lines 32-38): the `python3 "$HOME"/.claude/fbk-scripts/fbk.py spec-gate <spec-path>` command in its fenced code block.
- `## Retrospective` section (lines 44-46): the Stage 1 retrospective write directive plus the read-then-write file-handling rule.
- The literal `/spec-review $ARGUMENTS` chained invocation line (line 52).
- The exit-prompt sentence `Would you like to move to spec review?` — currently at line 42 inside the `## Gate` decision narrative; must survive in some form (skill keeps the prompt as the user-facing exit hand-off).

**Must be removed per spec §4.3:**

- The `## Authoring Loop` section body (lines 28, 30): "Co-author the spec iteratively..." and "Refuse to write code...".
- The `## Gate` decision narrative (lines 40-42): the three bullet-points describing what to do when the gate fails / passes / user is satisfied.
- The `## Transition` section body (lines 50-52): the "Before invoking the next stage..." summarize-and-compact directive (consolidated to `feature-spec-guide.md` per task-05). The `/spec-review $ARGUMENTS` chained invocation line is retained.

**Operational decision for the exit prompt:** Spec §4.3 removes the gate-decision narrative including the line `If the user is satisfied: ask "Would you like to move to spec review?"`. T15 of the test asserts the skill `does` contain `Would you like to move to spec review?`. The skill must therefore retain this prompt sentence as a single operational instruction outside the removed decision narrative — for example, by keeping it as a one-line directive within or after the `## Gate` section that says "On gate pass and user satisfaction, ask: 'Would you like to move to spec review?'", or by moving the prompt sentence to the `## Transition` section as the final operational step before the chained invocation. Choose the second option (place the prompt in the `## Transition` section immediately before the `/spec-review $ARGUMENTS` line) — this keeps the exit prompt co-located with the chained invocation it gates and matches the existing structure of `fbk-spec-review/SKILL.md` which keeps "Would you like to proceed to task breakdown?" near its chained `/breakdown` invocation.

## Instructions

Read the current file (`assets/skills/fbk-spec/SKILL.md`) before editing. The line ranges below match the current state of the file as of compilation time.

1. **Site 1 — Remove the `## Authoring Loop` body (lines 28-30 content, keep heading optional).**

   Locate the section starting at line 26 (`## Authoring Loop`). Remove the heading and all its body content (lines 26-30 inclusive). The section currently reads:

   ```
   ## Authoring Loop

   Co-author the spec iteratively with the user. Follow the doc for required sections, content requirements, and which clarifying questions to ask.

   Refuse to write code. If the user asks for implementation, explain that Stage 1 produces specification artifacts only and implementation begins in Stage 3.
   ```

   Remove the heading line and both body paragraphs in their entirety. Do not leave the heading orphaned without content.

   **Completion check:** `grep -qvF 'Refuse to write code' assets/skills/fbk-spec/SKILL.md` succeeds (no match). `grep -qvF 'Co-author the spec iteratively' assets/skills/fbk-spec/SKILL.md` succeeds.

2. **Site 2 — Remove the `## Gate` decision narrative (current lines 40-42).**

   Locate the three-bullet block immediately after the gate-script fenced code block (currently at lines 40-42):

   ```
   - If the gate fails: report which checks failed and what is missing.
   - If the gate passes: present the semantic criteria from the doc for the user to assess. Verify that the testing strategy enumerates all callers of any symbol being removed or renamed, not only the definition site.
   - If the user is satisfied: ask "Would you like to move to spec review?"
   ```

   Remove all three bullet lines. The fenced code block (lines 36-38) and the `## Gate` heading (line 32) and the `When the user signals the spec is complete, run:` line (line 34) all remain.

   **Completion checks:**
   - `grep -qvF 'If the gate fails:' assets/skills/fbk-spec/SKILL.md` succeeds.
   - `grep -qvF 'Verify that the testing strategy enumerates all callers' assets/skills/fbk-spec/SKILL.md` succeeds.
   - `grep -qF 'spec-gate' assets/skills/fbk-spec/SKILL.md` succeeds (gate-script invocation retained).

3. **Site 3 — Refactor the `## Transition` section (current lines 48-52).**

   The section currently reads:

   ```
   ## Transition

   Before invoking the next stage: confirm all artifacts are written to disk, then summarize the completed spec (feature name, artifact path, key decisions made during authoring). Compact context before invoking the next skill.

   If the user agrees to proceed, invoke `/spec-review $ARGUMENTS`.
   ```

   Replace the entire body with:

   ```
   ## Transition

   On gate pass and user satisfaction, ask: "Would you like to move to spec review?"

   If the user agrees to proceed, invoke `/spec-review $ARGUMENTS`.
   ```

   The "Before invoking the next stage..." summarize-and-compact directive is removed (it is consolidated into `feature-spec-guide.md` §"Transition" by task-05). The `Would you like to move to spec review?` exit prompt is relocated here from the removed `## Gate` decision narrative (Site 2) so the prompt remains in the skill (T15 requires it). The `/spec-review $ARGUMENTS` chained invocation line is preserved verbatim.

   **Completion checks:**
   - `grep -qvF 'Before invoking the next stage' assets/skills/fbk-spec/SKILL.md` succeeds.
   - `grep -qvF 'Compact context before invoking the next skill' assets/skills/fbk-spec/SKILL.md` succeeds.
   - `grep -qF 'Would you like to move to spec review?' assets/skills/fbk-spec/SKILL.md` succeeds.
   - `grep -qF '/spec-review $ARGUMENTS' assets/skills/fbk-spec/SKILL.md` succeeds.

4. **Must-NOT-be-removed sections** (verify these survive untouched after the edits above):

   - YAML frontmatter (lines 1-8) — `description:` and `argument-hint:` fields verbatim. First line of the file is `---`.
   - `## Entry` section — `$ARGUMENTS` resolution, scope determination, file-existence handling.
   - Read-the-guide pointers — three `Read \`.claude/fbk-docs/...\`` lines.
   - `## Gate` heading + `When the user signals the spec is complete, run:` line + the fenced gate-script code block containing `python3 "$HOME"/.claude/fbk-scripts/fbk.py spec-gate <spec-path>`.
   - `## Retrospective` section — the Stage 1 retrospective write directive and the read-then-write rule.

   **Completion checks for retentions:**
   - `head -n 1 assets/skills/fbk-spec/SKILL.md` returns exactly `---`.
   - `grep -qF 'description:' assets/skills/fbk-spec/SKILL.md` succeeds.
   - `grep -qF '$ARGUMENTS' assets/skills/fbk-spec/SKILL.md` succeeds.
   - `grep -qF 'spec-gate' assets/skills/fbk-spec/SKILL.md` succeeds.
   - `grep -qF '## Retrospective' assets/skills/fbk-spec/SKILL.md` succeeds.

5. **Run task-01's test to verify post-refactor state:**

   ```
   bash tests/sdl-workflow/test-skill-guide-dedup.sh
   ```

   The assertions covering this file (T1, T1b, T2, T12, T13, T14, T15) must all report `ok`. T11a's guide-side assertion is covered by task-05; do not be alarmed if it still reports `not ok` until task-05 lands. T1, T1b, T2 specifically must flip from `not ok` (pre-refactor) to `ok` (post-refactor) as a direct result of this task's edits.

## Files to create/modify

- `assets/skills/fbk-spec/SKILL.md` (modify)

Do not modify any other file. Do not edit `feature-spec-guide.md` (that is task-05's scope).

## Test requirements

This task makes the following task-01 assertions flip from `not ok` to `ok`:

- T1 (AC-01) — `If the gate fails:` absent from `fbk-spec/SKILL.md`.
- T1b (AC-01) — `Verify that the testing strategy enumerates all callers` absent from `fbk-spec/SKILL.md`.
- T2 (AC-01) — `Refuse to write code` absent from `fbk-spec/SKILL.md`.

This task must keep the following task-01 assertions reporting `ok` (they should be `ok` before this task too — but the edits must not break them):

- T10 (AC-04) — `spec-gate` present in `fbk-spec/SKILL.md`.
- T12 (AC-04) — first line `---` and `description:` present in `fbk-spec/SKILL.md`.
- T13 (AC-04) — `$ARGUMENTS` present in `fbk-spec/SKILL.md`.
- T14 (AC-04) — `/spec-review $ARGUMENTS` present in `fbk-spec/SKILL.md`.
- T15 (AC-04) — `Would you like to move to spec review?` present in `fbk-spec/SKILL.md`.

## Acceptance criteria

- AC-01: `fbk-spec/SKILL.md` no longer contains the duplicated authoring-loop prose, gate decision narrative, or transition narrative.
- AC-04: Operational glue is preserved — frontmatter, `$ARGUMENTS` resolution, gate-script invocation, chained `/spec-review` invocation, exit prompt.
- task-01 assertions T1, T1b, T2 flip to `ok`. T10, T12, T13, T14, T15 remain `ok`.

## Model

Haiku

## Wave

Wave 1
