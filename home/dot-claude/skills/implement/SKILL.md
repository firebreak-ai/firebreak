---
description: >-
  Implement a feature from compiled task files. Use when implementing,
  building, or executing a task breakdown. Manages parallel agent team
  with wave-based execution and verification gates.
argument-hint: "[feature-name]"
---

Read `home/dot-claude/docs/sdl-workflow/implementation-guide.md` for the complete wave execution protocol, verification rules, re-plan protocol, checkpoint format, and retrospective structure. Follow that doc at every step below.

## Input

If `$ARGUMENTS` is empty, ask: "Which feature do you want to implement? Provide the feature name (matching the directory under `ai-docs/`)."

Set `FEATURE=$ARGUMENTS`. Paths used throughout:
- Task manifest: `ai-docs/$FEATURE/$FEATURE-tasks/task.json`
- Tasks dir: `ai-docs/$FEATURE/$FEATURE-tasks/`
- Spec: `ai-docs/$FEATURE/$FEATURE-spec.md`
- Review log: `ai-docs/$FEATURE/$FEATURE-review.md`
- Retrospective: `ai-docs/$FEATURE/$FEATURE-retrospective.md`

Read `task.json`. Verify it exists and is valid JSON conforming to the task manifest schema in `home/dot-claude/docs/sdl-workflow/task-compilation.md`. If missing or malformed, stop and tell the user what is absent.

## Stage 3 Gate

Run:

```
"$HOME"/.claude/hooks/sdl-workflow/breakdown-gate.sh \
  "ai-docs/$FEATURE/$FEATURE-spec.md" \
  "ai-docs/$FEATURE/$FEATURE-tasks/"
```

If exit code is non-zero, report the failures and offer to run `/breakdown` to recompile the tasks. Do not proceed.

## Team Setup

Check that `CLAUDE_CODE_EXPERIMENTAL_AGENT_TEAMS` is set. If not, stop and inform the user — teammates cannot be spawned without this flag.

Check `~/.claude/settings.json` for a `TaskCompleted` hook entry. If missing, warn: "Per-task verification will not fire. Failures may only surface at per-wave verification." Ask whether to proceed.

From `task.json`, determine the maximum wave width (the largest number of tasks in any single wave). Create an agent team. Spawn teammates equal to the maximum wave width. Teammates persist for the full run — they claim new tasks as each wave opens.

Task files specify a model (Haiku or Sonnet). Use the `model` parameter when spawning teammates to match the task assignments.

## Wave Loop

Process waves in order. Do not create tasks for wave N+1 until wave N passes per-wave verification. Create native tasks wave by wave — never all upfront.

For each wave, follow the protocol in the implementation guide exactly:

**Step 1 — Test tasks**: Read this wave's test task list from `task.json` (tasks with matching `wave_id` and `type: "test"`). Set each task's `status` to `in_progress` in `task.json`. For each test task, create a native task whose description includes the full path to the task file:

```
Task file: ai-docs/$FEATURE/$FEATURE-tasks/task-NN-name.md
Read that file as your sole context and execute it.
```

Wait for all test-task native tasks to reach completed status. Set each completed task's `status` to `complete` in `task.json` and record the teammate's work summary in the `summary` field.

**Step 2 — Test compilation check**: Verify new tests exist and compile. Tests are expected to fail (no implementation yet) — a compile failure is the problem, not a test failure. If tests do not compile, treat as task failure and invoke the re-plan protocol before proceeding.

**Step 3 — Implementation tasks**: Create native tasks for this wave's implementation tasks (tasks with matching `wave_id` and `type: "implementation"`). Set each task's `status` to `in_progress` in `task.json`. Use the same format — full task file path in the description, matching the task's assigned model. Wait for all to complete. Set each completed task's `status` to `complete` and record the `summary`.

**Step 4 — Per-wave verification**: Run the checks specified in the implementation guide (full test suite, lint, no merge conflicts). If any check fails, invoke the re-plan protocol. Do not advance to the next wave until the current wave passes.

**Step 5 — Wave checkpoint**: Summarize the wave, report test results, and offer a commit. Follow the checkpoint format in the implementation guide.

**Step 6 — Final wave only**: After the checkpoint, proceed to final verification.

## Re-Plan Protocol

When a task fails and the teammate cannot resolve it in-session, follow the re-plan protocol in the implementation guide:

1. Collect a structured error report.
2. Set the task's `status` to `tests_fail` in `task.json` and write the failure details to `summary`.
3. Append a failure summary to `ai-docs/$FEATURE/$FEATURE-review.md`.
4. Revise the task file in place.
5. Assign the revised task to an idle teammate or spawn a replacement. Set `status` back to `in_progress`. The failing teammate does not retry.
6. Cap: 2 re-plan attempts per task. After 2 failures, set `status` to `parked` with a `note`, escalate to the user, and halt the wave.

## Final Verification

After the final wave checkpoint, run the structural and semantic checks defined in the implementation guide:

- **Structural**: All tasks completed and verified. Full test suite passes. No dead code (no files created but unused). Documentation updates completed per the spec's documentation impact section.
- **Semantic**: Spec acceptance criteria are satisfied by the aggregate implementation — confirm the result meets spec intent, not just that tests pass.

Report any gaps. Do not write the retrospective until final verification passes, or until the user explicitly accepts with known gaps documented.

## Retrospective

Write `ai-docs/$FEATURE/$FEATURE-retrospective.md`. Include the factual data, upstream traceability, and failure attribution sections defined in the implementation guide.

## Team Shutdown

Shut down all teammates. Clean up the team. After final verification passes, ask the user: "Would you like to review the implementation with /code-review?" Follow the existing stage-transition pattern — summarize what was verified and offer the next stage. Report: "All tasks complete and verified. Retrospective captured at `ai-docs/$FEATURE/$FEATURE-retrospective.md`. Implementation is ready for your review."
