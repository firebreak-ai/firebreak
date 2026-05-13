---
id: task-07
type: implementation
wave: 1
covers: [AC-03, AC-04, AC-06]
files_to_modify:
  - assets/fbk-docs/fbk-sdl-workflow/implementation-guide.md
test_tasks: [task-01]
completion_gate: "task-01 assertion T11d (`CLAUDE_CODE_EXPERIMENTAL_AGENT_TEAMS` absent from `implementation-guide.md`) passes"
---

## Objective

Remove the env-flag prerequisite line at `assets/fbk-docs/fbk-sdl-workflow/implementation-guide.md:9`, consolidating the `CLAUDE_CODE_EXPERIMENTAL_AGENT_TEAMS` operational gate to single-source ownership in `fbk-implement/SKILL.md` (where task-04 retains it).

## Context

Per spec §4.3a, the env-flag prerequisite line currently duplicated bidirectionally between `fbk-implement/SKILL.md` and `implementation-guide.md` is consolidated to skill-side. The skill is the orchestration boundary that actually performs the env-flag check (gate-like operational invocation, not narrative); the guide does not own runtime gate logic. Task-04 retains the env-flag check in `fbk-implement/SKILL.md`; this task removes the corresponding line from the guide.

The line to remove is on line 9 of the current file. Surrounding `## Team Setup` content (the team-setup intro paragraph at line 3, the interrupted-session pointer at line 5, the "Create an agent team..." paragraph at line 7, and the wave-width spawn instruction at line 11) is unchanged.

## Instructions

Read the current file (`assets/fbk-docs/fbk-sdl-workflow/implementation-guide.md`) before editing. The line range below matches the current state of the file as of compilation time.

1. **Site 1 — Remove line 9 (env-flag prerequisite sentence) from `## Team Setup` section.**

   The current `## Team Setup` opening (lines 1-11) reads:

   ```
   ## Team Setup

   Verify Stage 3 gate passes before proceeding. Read `task.json` in the task directory (`ai-docs/<feature-name>/<feature-name>-tasks/task.json`) to understand wave structure, task count, model assignments, and current task statuses.

   If any tasks have `status` other than `not_started`, a prior session was interrupted. See "Resuming Interrupted Sessions" below.

   Create an agent team. You (main thread) are the team lead — you coordinate and do not execute tasks. Teammates execute tasks.

   Require the `CLAUDE_CODE_EXPERIMENTAL_AGENT_TEAMS` flag before spawning any teammates. If the flag is not set, stop and inform the user.

   Spawn teammates equal to the maximum wave width across all waves. Teammates persist across waves — after completing a wave's tasks, they claim the next wave's tasks when you unblock them.
   ```

   Remove only the env-flag sentence (line 9):

   ```
   Require the `CLAUDE_CODE_EXPERIMENTAL_AGENT_TEAMS` flag before spawning any teammates. If the flag is not set, stop and inform the user.
   ```

   Also remove the surrounding blank line so the result reads cleanly. After the edit, the section becomes:

   ```
   ## Team Setup

   Verify Stage 3 gate passes before proceeding. Read `task.json` in the task directory (`ai-docs/<feature-name>/<feature-name>-tasks/task.json`) to understand wave structure, task count, model assignments, and current task statuses.

   If any tasks have `status` other than `not_started`, a prior session was interrupted. See "Resuming Interrupted Sessions" below.

   Create an agent team. You (main thread) are the team lead — you coordinate and do not execute tasks. Teammates execute tasks.

   Spawn teammates equal to the maximum wave width across all waves. Teammates persist across waves — after completing a wave's tasks, they claim the next wave's tasks when you unblock them.
   ```

   The team-setup intro, the interrupted-session pointer, the team-lead role description, and the wave-width spawn instruction all survive verbatim.

   **Completion checks:**
   - `grep -qvF 'CLAUDE_CODE_EXPERIMENTAL_AGENT_TEAMS' assets/fbk-docs/fbk-sdl-workflow/implementation-guide.md` succeeds (no match).
   - `grep -qvF 'Require the' assets/fbk-docs/fbk-sdl-workflow/implementation-guide.md` returns appropriately — note: a broader `grep -qF 'Require the'` may match other content; the targeted check is `! grep -qF 'CLAUDE_CODE_EXPERIMENTAL_AGENT_TEAMS' "$IMPL_GUIDE"`.
   - `grep -qF 'Verify Stage 3 gate passes before proceeding' assets/fbk-docs/fbk-sdl-workflow/implementation-guide.md` succeeds (preceding paragraph preserved).
   - `grep -qF 'Spawn teammates equal to the maximum wave width' assets/fbk-docs/fbk-sdl-workflow/implementation-guide.md` succeeds (following paragraph preserved).
   - `grep -qF 'Create an agent team' assets/fbk-docs/fbk-sdl-workflow/implementation-guide.md` succeeds.

2. **Verify other guide content is unchanged.** No section other than the line removal in `## Team Setup` is edited. The structural / semantic checklist in `## Final Verification`, the escalation protocol, the wave-execution steps, and all other sections remain verbatim.

   **Completion checks for unchanged content** (these must all pass — they correspond to T11c which asserts these substrings remain in the guide):

   - `grep -qF 'Step 1 — Test tasks' assets/fbk-docs/fbk-sdl-workflow/implementation-guide.md` succeeds.
   - `grep -qF 'Cap: 2 escalation attempts per task' assets/fbk-docs/fbk-sdl-workflow/implementation-guide.md` succeeds.
   - `grep -qF 'No dead code introduced' assets/fbk-docs/fbk-sdl-workflow/implementation-guide.md` succeeds.

3. **Run task-01's test to verify post-edit state:**

   ```
   bash tests/sdl-workflow/test-skill-guide-dedup.sh
   ```

   T11d (`implementation-guide.md` does NOT contain `CLAUDE_CODE_EXPERIMENTAL_AGENT_TEAMS`) must flip from `not ok` to `ok` as a direct result of this task's edit. T11c (positive assertions on `Step 1 — Test tasks`, `Cap: 2 escalation attempts per task`, `No dead code introduced`) must remain `ok`.

4. **Run pre-existing tests to verify no regression:**

   ```
   bash tests/sdl-workflow/test-implementation-pipeline.sh
   ```

   This pre-existing test asserts `implementation-guide.md` contains hook retry cap, fresh-agent rule, and foreground-execution rule. None of those are affected by removing the env-flag line. The test must continue to pass without modification (per spec testing strategy).

## Files to create/modify

- `assets/fbk-docs/fbk-sdl-workflow/implementation-guide.md` (modify)

Do not modify any other file. Do not edit `fbk-implement/SKILL.md` (that is task-04's scope; the env-flag check stays there).

## Test requirements

This task makes the following task-01 assertion flip from `not ok` to `ok`:

- T11d (AC-03 / AC-04) — `CLAUDE_CODE_EXPERIMENTAL_AGENT_TEAMS` absent from `implementation-guide.md`.

This task must keep the following task-01 assertion reporting `ok`:

- T11c (AC-03) — `Step 1 — Test tasks` AND `Cap: 2 escalation attempts per task` AND `No dead code introduced` all present in `implementation-guide.md`.

Pre-existing test `tests/sdl-workflow/test-implementation-pipeline.sh` must continue to pass without modification (asserts hook retry cap / fresh-agent rule / foreground-execution rule — none affected by this edit).

## Acceptance criteria

- AC-03: The env-flag prerequisite line is removed from `implementation-guide.md`. The env-flag check now lives only in `fbk-implement/SKILL.md` (retained by task-04).
- AC-04: The skill-side env-flag check (retained by task-04) remains the single operational gate.
- AC-05: Pre-existing `test-implementation-pipeline.sh` continues to pass.
- task-01 assertion T11d flips to `ok`. T11c remains `ok`.

## Model

Haiku

## Wave

Wave 1
