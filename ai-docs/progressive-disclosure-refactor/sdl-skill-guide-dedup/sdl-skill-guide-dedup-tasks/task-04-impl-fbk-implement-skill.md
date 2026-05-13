---
id: task-04
type: implementation
wave: 1
covers: [AC-03, AC-04, AC-05, AC-06]
files_to_modify:
  - assets/skills/fbk-implement/SKILL.md
test_tasks: [task-01]
completion_gate: "task-01 assertions T5, T5b, T6, T7, T8, T9b, T11c, T12, T13 pass"
---

## Objective

Refactor `assets/skills/fbk-implement/SKILL.md` to remove duplicated workflow prose (wave-loop step narratives, escalation-protocol numbered list, final-verification list, retrospective field summary, team-shutdown list) while preserving all operational glue (frontmatter, `FEATURE=$ARGUMENTS` resolution, breakdown-gate invocation, env-flag check, `Task file:` spawn-prompt template, retrospective write directive, exit prompt).

## Context

The `fbk-implement` skill loads `implementation-guide.md` unconditionally on its first instruction (line 9). Workflow protocol restated in the skill body is therefore duplicated on the same load path — and this skill exhibits the largest duplication (≈40 lines per spec §1). Spec §4.3 enumerates six duplicated sections to remove from this file; spec §4.2 enumerates the operational-glue sections that must remain. The env-flag prerequisite line at `implementation-guide.md:9` is consolidated to skill-side per §4.3a (task-07 removes it from the guide; this task retains it in the skill).

**Must be retained verbatim per spec §4.2 (do NOT remove):**

- YAML frontmatter (lines 1-7) — `description:` and `argument-hint:` fields.
- `Read \`.claude/fbk-docs/fbk-sdl-workflow/implementation-guide.md\`` pointer (line 9).
- `## Input` section (lines 11-22): `$ARGUMENTS` empty-check, `FEATURE=$ARGUMENTS` resolution, paths block, `task.json` read + JSON-validity check.
- `## Stage 3 Gate` section (lines 24-34): the `breakdown-gate` invocation block + failure handling.
- The `CLAUDE_CODE_EXPERIMENTAL_AGENT_TEAMS` env-flag check (currently at line 38 inside `## Team Setup`). This is the operational gate; only the orchestrator at the skill boundary actually performs the check. **Must NOT be removed.**
- The literal `Task file:` spawn-prompt template block (currently inside `## Wave Loop` Step 1, lines 52-57). This is concrete `Task` tool plumbing. **Must NOT be removed.**
- The exit-prompt sentence `Would you like to review the implementation with /code-review?` (currently inside `## Team Shutdown`, line 97). **Must NOT be removed** — load-bearing for `tests/sdl-workflow/test-code-review-skill.sh` Tests 15-16.

**Must be removed per spec §4.3:**

- The wave-width selection prose and team-lead role description in `## Team Setup` (currently lines 40, 42) — duplicated with guide §"Team Setup" lines 1-12. The env-flag check on line 38 is retained.
- The entire numbered narrative for Steps 1-7 inside `## Wave Loop` (currently lines 50-69), retaining only: (a) the literal `Task file:` spawn-prompt template block; (b) a one-line "for each wave, follow the protocol in the implementation guide" pointer.
- The numbered list inside `## Escalation Protocol` (currently lines 73-80), retaining only a one-line pointer to the implementation guide.
- The structural / semantic checklist inside `## Final Verification` (currently lines 84-89), retaining only a one-line pointer.
- The factual-data / upstream-traceability / failure-attribution field enumeration inside `## Retrospective` (currently in line 93 — but spec §4.3 says retain "the literal write-Stage-4-section directive plus the read-then-write file-handling rule"). The `## Retrospective` section is one paragraph; remove the field-list sentence "Include the factual data, upstream traceability, and failure attribution sections defined in the implementation guide." and retain only the Stage-4 write directive plus the read-then-write rule.
- The 3-step list inside `## Team Shutdown` (currently lines 97), retaining a one-line pointer plus the literal user-prompt sentence `Would you like to review the implementation with /code-review?`.

## Instructions

Read the current file (`assets/skills/fbk-implement/SKILL.md`) before editing. The line ranges below match the current state of the file as of compilation time.

1. **Site 1 — Trim the `## Team Setup` section (current lines 36-42).**

   The section currently reads:

   ```
   ## Team Setup

   Check that `CLAUDE_CODE_EXPERIMENTAL_AGENT_TEAMS` is set. If not, stop and inform the user — teammates cannot be spawned without this flag.

   From `task.json`, determine the maximum wave width (the largest number of tasks in any single wave). Create an agent team. Spawn teammates equal to the maximum wave width. Teammates persist for the full run — they claim new tasks as each wave opens.

   Task files specify a model (Haiku or Sonnet). Use the `model` parameter when spawning teammates to match the task assignments.
   ```

   Replace the body with:

   ```
   ## Team Setup

   Check that `CLAUDE_CODE_EXPERIMENTAL_AGENT_TEAMS` is set. If not, stop and inform the user — teammates cannot be spawned without this flag.

   Follow the team setup protocol in the implementation guide for wave-width selection, team-lead role, and model assignment.
   ```

   The env-flag check sentence is retained verbatim (T7 requires the env-flag string). The wave-width / team-lead / model-assignment paragraphs are replaced with a one-line pointer.

   **Completion checks:**
   - `grep -qF 'CLAUDE_CODE_EXPERIMENTAL_AGENT_TEAMS' assets/skills/fbk-implement/SKILL.md` succeeds.
   - `grep -qvF 'maximum wave width (the largest number' assets/skills/fbk-implement/SKILL.md` succeeds.
   - `grep -qvF 'Task files specify a model' assets/skills/fbk-implement/SKILL.md` succeeds.

2. **Site 2 — Trim the `## Wave Loop` section (current lines 44-69).**

   The current body contains six numbered "Step N — ..." paragraphs (Steps 1, 2, 3, 4, 5, 6) plus a brief lead-in. Step 1's body contains the `Task file:` spawn-prompt template fenced block (currently lines 52-57). Replace the entire `## Wave Loop` body with:

   ```
   ## Wave Loop

   For each wave, follow the protocol in the implementation guide.

   When creating native tasks for a wave's test or implementation tasks, use this spawn-prompt template:

   ```
   Task file: ai-docs/$FEATURE/$FEATURE-tasks/task-NN-name.md
   Read that file as your sole context and execute it.

   Before your turn ends, send a work summary message to the team lead describing what you created, what verification you ran, and any caveats. A turn ending without this message is incomplete work.
   ```
   ```

   The `Task file:` spawn-prompt template fenced code block must be preserved verbatim — it is concrete `Task` tool plumbing (T8 asserts the `Task file:` substring is present). All Step 1-6 narrative paragraphs are removed. The wave-loop steps now live only in guide §"Wave Execution" / §"Status Tracking" / §"Per-Wave Verification" / §"Wave Checkpoint".

   **Completion checks:**
   - `grep -qvF 'Step 1 — Test tasks' assets/skills/fbk-implement/SKILL.md` succeeds.
   - `grep -qvF 'Step 2 — Test compilation check' assets/skills/fbk-implement/SKILL.md` succeeds.
   - `grep -qvF 'Tests are expected to fail' assets/skills/fbk-implement/SKILL.md` succeeds.
   - `grep -qF 'Task file:' assets/skills/fbk-implement/SKILL.md` succeeds.
   - `grep -qF 'Read that file as your sole context' assets/skills/fbk-implement/SKILL.md` succeeds.

3. **Site 3 — Trim the `## Escalation Protocol` section (current lines 71-80).**

   The section currently contains a 6-item numbered list (lines 75-80). Replace the entire body with:

   ```
   ## Escalation Protocol

   Follow the escalation protocol in the implementation guide.
   ```

   The numbered-list narrative is removed (lives in guide §"Escalation Protocol", lines 157-170).

   **Completion checks:**
   - `grep -qvF 'Cap: 2 escalation attempts per task' assets/skills/fbk-implement/SKILL.md` succeeds.
   - `grep -qvF 'Collect a structured error report' assets/skills/fbk-implement/SKILL.md` succeeds.

4. **Site 4 — Trim the `## Final Verification` section (current lines 82-89).**

   The section currently contains a structural / semantic bulleted checklist (lines 86-87) and a closing sentence (line 89). Replace the entire body with:

   ```
   ## Final Verification

   After the final wave checkpoint, run the structural and semantic checks defined in the implementation guide. Report any gaps. Do not write the retrospective until final verification passes, or until the user explicitly accepts with known gaps documented.
   ```

   The structural/semantic checklist bullets are removed (live in guide §"Final Verification", lines 174-187). The "Report any gaps" + "Do not write the retrospective until..." sentences are operational gate logic and remain.

   **Completion checks:**
   - `grep -qvF 'No dead code (no files created but unused)' assets/skills/fbk-implement/SKILL.md` succeeds.
   - `grep -qvF 'All tasks completed and verified' assets/skills/fbk-implement/SKILL.md` succeeds.

5. **Site 5 — Trim the `## Retrospective` section (current lines 91-93).**

   The section currently reads (line 93):

   ```
   Write the Stage 4 section to `ai-docs/$FEATURE/$FEATURE-retrospective.md` following `.claude/fbk-docs/fbk-sdl-workflow/retrospective-guide.md`. Create the file with the feature header if it does not exist. Read the file before writing to preserve existing content from prior stages. Include the factual data, upstream traceability, and failure attribution sections defined in the implementation guide.
   ```

   Remove only the final sentence `Include the factual data, upstream traceability, and failure attribution sections defined in the implementation guide.` Retain the Stage-4 write directive and the read-then-write rule. The section's new body reads:

   ```
   Write the Stage 4 section to `ai-docs/$FEATURE/$FEATURE-retrospective.md` following `.claude/fbk-docs/fbk-sdl-workflow/retrospective-guide.md`. Create the file with the feature header if it does not exist. Read the file before writing to preserve existing content from prior stages.
   ```

   **Completion checks:**
   - `grep -qvF 'factual data, upstream traceability, and failure attribution' assets/skills/fbk-implement/SKILL.md` succeeds.
   - `grep -qF 'Read the file before writing to preserve existing content' assets/skills/fbk-implement/SKILL.md` succeeds.
   - `grep -qF 'Stage 4' assets/skills/fbk-implement/SKILL.md` succeeds.

6. **Site 6 — Trim the `## Team Shutdown` section (current lines 95-97).**

   The section currently reads (line 97):

   ```
   Shut down all teammates. Clean up the team. After final verification passes, ask the user: "Would you like to review the implementation with /code-review?" Follow the existing stage-transition pattern — summarize what was verified and offer the next stage. Report: "All tasks complete and verified. Retrospective captured at `ai-docs/$FEATURE/$FEATURE-retrospective.md`. Implementation is ready for your review."
   ```

   Replace the body with:

   ```
   Follow the team-shutdown protocol in the implementation guide. After final verification passes, ask the user: "Would you like to review the implementation with /code-review?"
   ```

   The "Shut down all teammates / Clean up the team / Report: 'All tasks complete and verified...'" steps are removed (live in guide §"Team Shutdown", lines 223-229). The exit-prompt sentence `Would you like to review the implementation with /code-review?` is retained verbatim (T9b requires `review the implementation with /code-review`).

   **Completion checks:**
   - `grep -qF 'review the implementation with /code-review' assets/skills/fbk-implement/SKILL.md` succeeds.
   - `grep -qvF 'Shut down all teammates. Clean up the team' assets/skills/fbk-implement/SKILL.md` succeeds.
   - `grep -qvF 'All tasks complete and verified. Retrospective captured at' assets/skills/fbk-implement/SKILL.md` succeeds.

7. **Must-NOT-be-removed sections** (verify these survive untouched after the edits above):

   - YAML frontmatter (lines 1-7) — first line `---`, `description:` field.
   - Read-the-guide pointer.
   - `## Input` section verbatim — `$ARGUMENTS` empty-check, `FEATURE=$ARGUMENTS`, paths block, `task.json` read + JSON-validity check.
   - `## Stage 3 Gate` section verbatim — `breakdown-gate` invocation.
   - `CLAUDE_CODE_EXPERIMENTAL_AGENT_TEAMS` env-flag check sentence.
   - `Task file:` spawn-prompt template fenced block.
   - `Would you like to review the implementation with /code-review?` exit prompt.

   **Completion checks for retentions:**
   - `head -n 1 assets/skills/fbk-implement/SKILL.md` returns exactly `---`.
   - `grep -qF 'description:' assets/skills/fbk-implement/SKILL.md` succeeds.
   - `grep -qF 'FEATURE=$ARGUMENTS' assets/skills/fbk-implement/SKILL.md` succeeds.
   - `grep -qF 'breakdown-gate' assets/skills/fbk-implement/SKILL.md` succeeds.
   - `grep -qF 'CLAUDE_CODE_EXPERIMENTAL_AGENT_TEAMS' assets/skills/fbk-implement/SKILL.md` succeeds.
   - `grep -qF 'Task file:' assets/skills/fbk-implement/SKILL.md` succeeds.
   - `grep -qF 'review the implementation with /code-review' assets/skills/fbk-implement/SKILL.md` succeeds.

8. **Run task-01's test to verify post-refactor state:**

   ```
   bash tests/sdl-workflow/test-skill-guide-dedup.sh
   ```

   The assertions covering this file (T5, T5b, T6, T7, T8, T9b, T10, T12, T13) must all report `ok`. T11c's guide-side assertion is unaffected by this task (covered by the existing implementation-guide content + task-07's removal of the env-flag line, which is task-07's scope). T5, T5b, T6 specifically must flip from `not ok` (pre-refactor) to `ok` (post-refactor) as a direct result of this task's edits.

## Files to create/modify

- `assets/skills/fbk-implement/SKILL.md` (modify)

Do not modify any other file. Do not edit `implementation-guide.md` (that is task-07's scope).

## Test requirements

This task makes the following task-01 assertions flip from `not ok` to `ok`:

- T5 (AC-03) — `Step 1 — Test tasks` AND `Step 2 — Test compilation check` both absent from `fbk-implement/SKILL.md`.
- T5b (AC-03) — `Tests are expected to fail` absent from `fbk-implement/SKILL.md`.
- T6 (AC-03) — `Cap: 2 escalation attempts per task` absent from `fbk-implement/SKILL.md`.

This task must keep the following task-01 assertions reporting `ok`:

- T7 (AC-04) — `CLAUDE_CODE_EXPERIMENTAL_AGENT_TEAMS` present in `fbk-implement/SKILL.md`.
- T8 (AC-04) — `Task file:` present in `fbk-implement/SKILL.md`.
- T9b (AC-04) — `review the implementation with /code-review` present in `fbk-implement/SKILL.md`.
- T10 (AC-04) — `breakdown-gate` present in `fbk-implement/SKILL.md`.
- T12 (AC-04) — first line `---` and `description:` present in `fbk-implement/SKILL.md`.
- T13 (AC-04) — `FEATURE=$ARGUMENTS` present in `fbk-implement/SKILL.md`.

Pre-existing tests asserting `fbk-implement/SKILL.md` content (`tests/sdl-workflow/test-code-review-skill.sh` Tests 15-16 on `review the implementation` / `code review` / `would you like` / `ask.*review`) must continue to pass without modification. The retentions enumerated in Step 7 ensure this.

## Acceptance criteria

- AC-03: `fbk-implement/SKILL.md` no longer contains the duplicated wave-loop steps, status-tracking transitions, escalation-protocol numbered list, final-verification list, retrospective field summary, or team-shutdown list.
- AC-04: Operational glue is preserved — frontmatter, `FEATURE=$ARGUMENTS` resolution, breakdown-gate invocation, env-flag check, `Task file:` spawn-prompt template, retrospective write directive, exit prompt.
- AC-05: Pre-existing `test-code-review-skill.sh` assertions on this file continue to pass.
- task-01 assertions T5, T5b, T6 flip to `ok`. T7, T8, T9b, T10, T12, T13 remain `ok`.

## Model

Haiku

## Wave

Wave 1
