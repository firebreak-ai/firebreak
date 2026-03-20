## Team Setup

Verify Stage 3 gate passes before proceeding. Read `task.json` in the task directory (`ai-docs/<feature-name>/<feature-name>-tasks/task.json`) to understand wave structure, task count, model assignments, and current task statuses.

If any tasks have `status` other than `not_started`, a prior session was interrupted. See "Resuming Interrupted Sessions" below.

Create an agent team. You (main thread) are the team lead — you coordinate and do not execute tasks. Teammates execute tasks.

Require the `CLAUDE_CODE_EXPERIMENTAL_AGENT_TEAMS` flag before spawning any teammates. If the flag is not set, stop and inform the user.

Spawn teammates equal to the maximum wave width across all waves. Teammates persist across waves — after completing a wave's tasks, they claim the next wave's tasks when you unblock them.

---

## Wave Execution

Create native tasks wave by wave, not all upfront. This gives you explicit advancement control.

For each wave:

**Step 1 — Test tasks**: Create native tasks for the wave's test tasks. Each task description includes the path to its task file. Teammates claim and execute.

**Step 2 — Test compilation check**: When all test tasks complete, verify that the new tests exist and compile. Tests are expected to fail at this point — the implementation does not exist yet. If tests do not compile, treat as a task failure and invoke the re-plan protocol.

**Step 3 — Implementation tasks**: Create native tasks for the wave's implementation tasks. Teammates claim and execute.

**Step 4 — Per-wave verification**: Run after all implementation tasks complete. See "Per-Wave Verification" below.

**Step 5 — On failure**: Invoke the re-plan protocol. Do not advance to the next wave until the current wave passes verification.

**Step 6 — Wave checkpoint**: Summarize the wave and offer a commit. See "Wave Checkpoint" below.

**Step 7 — Final wave only**: After the checkpoint, run final verification.

---

## Status Tracking

Update `task.json` after every status change. Status transitions:

1. **Assignment**: Set `status` to `in_progress` when assigning a task to a teammate.
2. **Completion**: Set `status` to `complete` and write the teammate's work summary to `summary` when the task passes verification.
3. **Test failure**: Set `status` to `tests_fail` when an implementation task's tests don't pass. Invoke the re-plan protocol.
4. **Escalation**: Set `status` to `parked` with a `note` explaining the failure when the re-plan cap is exhausted.
5. **Superseded**: Set `status` to `superseded` with a `note` when a re-plan replaces the task or the user removes it from scope.

The team lead writes `task.json` after each update — teammates do not modify it directly. The teammate reports its work summary to the team lead, who records it.

---

## Resuming Interrupted Sessions

When `task.json` contains tasks with `status` other than `not_started`:

1. **`complete` tasks**: Skip. Read their `summary` fields for context on what was already built.
2. **`in_progress` tasks**: Partial implementation exists. Evaluate the current state of the files in the task's scope before reassigning. The teammate must be informed that prior work exists to avoid duplication.
3. **`tests_fail` tasks**: Prior implementation failed verification. Treat as a re-plan candidate — read the `summary` and verification output before reassigning.
4. **`parked` tasks**: Awaiting human input. Do not resume without user confirmation.
5. **`superseded` tasks**: Skip.

Resume at the earliest incomplete wave. A wave is incomplete if any of its tasks are not `complete` or `superseded`.

---

## Task Isolation

Each teammate reads its task file as its sole instruction context. The teammate does not read the spec, other task files, or the task overview.

Stage 3 guarantees non-overlapping file scopes within the same wave. Concurrent-edit conflicts cannot occur within a wave.

---

## Per-Task Readiness Check

Before writing code, each implementation agent performs a lightweight readiness check covering only what couldn't be verified at breakdown time:

1. **Prior-wave files exist**: Every file referenced in the task's interface contracts that was created by a prior wave (not pre-existing) is present.
2. **Tests compile**: For implementation tasks, the paired test task's tests compile (they should fail, but they should compile). Test tasks skip this item — they are creating the tests, not consuming them.
3. **Build succeeds**: The repo builds/compiles successfully in its current state.
4. **Contract staleness check**: When interface contracts reference a file modified by a prior wave (detectable from git diff between baseline and current state), re-read the file and verify the specific conventions cited in the contracts still hold. This is a targeted check of specific claims, not a full codebase survey.

If any check fails, the agent reports the specific mismatch without attempting implementation. This saves token spend and gives the team lead a precise failure to diagnose.

**Sequencing**: The inter-wave regression check (below) runs between waves as a wave-advancement gate. The readiness check runs per-task within a wave as a pre-implementation gate. Sequence: Wave N completes → baseline regression check → Wave N+1 starts → each task in N+1 runs readiness check before coding.

---

## Inter-Wave Baseline-Snapshot Regression Check

The baseline is the set of tests that pass when wave execution begins. After each wave, the baseline tests must still pass. Any baseline test that now fails is a regression — the wave is not advanced until it's resolved.

### Baseline capture

Before Wave 1 starts, run the full test suite and capture results to `ai-docs/<feature>/baseline-snapshot.json` — a list of test identifiers (file path + test name) with pass/fail status. Only passing tests enter the baseline. Tests already failing are excluded automatically.

The baseline is stored as a file so interrupted sessions can resume with the correct baseline.

### Inter-wave check

After each wave completes and before the next wave starts, run the full test suite and compare results against the baseline snapshot. Any test that was "pass" in the baseline and is now "fail" is a regression. On failure, the wave is not advanced — the team lead diagnoses the regression and either fixes it or parks the feature.

### Final verification

After the last wave, run the full test suite — all tests, not just the baseline. At this point, every test (including all newly-created tests from test-writing waves and all diagnostic tests from corrective workflows) should pass. Any failure here means the feature is not complete.

---

## TaskCompleted Hook

Configure a `TaskCompleted` hook in user-global settings (`~/.claude/settings.json`). The hook fires on every `TaskCompleted` event.

The hook script scopes itself via context check: parse the task description for an SDL task file path matching `ai-docs/*/tasks/task-*.md`. If no match, exit 0 (pass-through) — the hook applies only to SDL tasks.

For SDL tasks, the hook validates:

- The full test suite passes — not just the task's new tests, but all tests in the project.
- No new lint errors are introduced.

Exit code 2 (reject with feedback) on any failure. This prevents task completion and returns the failure output to the teammate as feedback.

**Escalation from hook rejections to re-plan**: Hook rejections prompt the teammate to retry in-session using the failure output as feedback. In-session retries do not count toward the 2-attempt re-plan cap. When the teammate goes idle or messages you without resolving the failure, initiate the re-plan protocol.

---

## Per-Wave Verification

Run after all implementation tasks in the wave complete:

- Full test suite passes — all unit, integration, and e2e tests across the project. This confirms wave acceptance criteria are met and existing behavior is not broken.
- No new lint errors introduced.
- No uncommitted merge conflicts.
- File scope respected: compare `git diff --name-only` against the union of declared file scopes from all tasks in this wave. Flag any changed file that does not match a declared scope using path-prefix matching. Scope checking runs here (not per-task) because concurrent teammates share git state — per-task diffs cannot isolate individual contributions.

The TaskCompleted hook catches test and lint failures per-task. Per-wave verification adds the aggregate cross-task checks: merge conflicts and file scope.

---

## Wave Checkpoint

After per-wave verification passes:

1. **Summary**: What this wave accomplished — tasks completed, what was implemented, any re-plans and their reasons.
2. **Test results**: Which tests pass, including new/updated tests and the full existing suite.
3. **Commit offer**: Ask "Would you like to commit before continuing to the next wave?" Draft a commit message from the wave summary if the user accepts.

Apply this checkpoint to every wave, including the final one.

---

## Re-Plan Protocol

Initiate when a task fails and the teammate cannot resolve it in-session.

1. Collect a structured error report: which task, which check failed, and the specific error output.
2. Set the task's `status` to `tests_fail` in `task.json` and write the failure details to `summary`.
3. Append a failure summary to `ai-docs/<feature-name>/<feature-name>-review.md`: task ID, attempt number, what was attempted, what went wrong, and the verification output.
4. Revise the task file in place. The original is preserved in git history.
5. Assign the revised task to an idle teammate or spawn a replacement. Set `status` back to `in_progress`. The failing teammate does not retry — you have the external signal (test/lint output) to make a meaningful revision.
6. Cap: 2 re-plan attempts per task. After 2 failures, set `status` to `parked` with a `note` and escalate to the user.

---

## Final Verification

Run after the final wave's checkpoint.

**Structural** (deterministic):

- All tasks are completed and individually verified.
- Full test suite passes.
- No dead code introduced — no files created but left unused.
- Documentation updates completed per the spec's documentation impact section.

**Semantic** (human review):

- Spec acceptance criteria are satisfied by the aggregate implementation. Confirm the result meets spec intent, not just that tests pass.

---

## Retrospective

Write `ai-docs/<feature-name>/<feature-name>-retrospective.md` after final verification.

**Factual data** (no AI judgment):

- Per-task: pass/fail, re-plan count, re-plan reasons, model used.
- Task sizing accuracy: actual files modified vs. declared scope.
- Model routing accuracy: Haiku tasks that succeeded vs. required escalation.
- Verification gate pass rates.
- Wall-clock time per wave if available.

**Upstream traceability** (factual):

- Stage 2 review iterations before advancing.
- Blocking findings count and how many led to spec revisions.
- Stage 3 compilation attempts before gate passed.

**Failure attribution** (AI judgment):

- For each re-planned task: classify root cause as one of:
  - **Spec gap** — the spec was underspecified or ambiguous.
  - **Compilation gap** — the task instructions missed something the spec covered.
  - **Implementation error** — the task instructions were correct but the agent failed to follow them.
- Base the classification on comparing the failure output against the task file and the spec.

---

## Team Shutdown

After final verification and retrospective:

1. Shut down all teammates.
2. Clean up the team.
3. Summarize: "All tasks complete and verified. Retrospective captured at `ai-docs/<feature-name>/<feature-name>-retrospective.md`. Implementation is ready for your review."
