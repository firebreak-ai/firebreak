# Task 06: Create Implementation Guide

## Objective

Create the leaf doc that provides detailed Stage 4 (Implementation) guidance for agents managing team-based wave execution.

## Context

This doc is loaded by the `/implement` skill when Stage 4 is active. It guides the team lead through setting up the agent team, executing waves, handling verification failures, and producing the retrospective.

### Team setup

1. Read task overview. Verify Stage 3 gate passes.
2. Create an agent team. Team lead (main thread) coordinates; teammates execute tasks.
3. Spawn teammates matching maximum wave width. Teammates persist across waves — after completing a wave's tasks, they claim next wave's tasks when the team lead unblocks them.
4. Agent teams require the `CLAUDE_CODE_EXPERIMENTAL_AGENT_TEAMS` flag.

### Wave execution protocol

The team lead advances one wave at a time. Within each wave, test tasks before implementation tasks.

For each wave:
1. **Test tasks**: Create native tasks for the wave's test tasks. Each task description includes the path to its task file. Teammates claim and execute.
2. **Test compilation check**: When all test tasks complete, verify tests exist and compile (they should fail — implementation doesn't exist yet).
3. **Impl tasks**: Create native tasks for the wave's implementation tasks. Teammates claim and execute.
4. **Per-wave verification**: Run after all impl tasks complete (see below).
5. **On failure**: Re-plan protocol (see below). Next wave does not start until current wave passes.
6. **Wave checkpoint**: Summarize and offer commit (see below).
7. **Final wave**: After checkpoint, run final verification.

Create native tasks wave by wave, not all upfront. This gives the team lead explicit wave advancement control.

### Task isolation

Each teammate reads its task file as the sole instruction context. The teammate does not read the full spec, other task files, or the task overview. Stage 3 guarantees non-overlapping file scopes within the same wave — no concurrent-edit conflicts.

### TaskCompleted hook

Configure a `TaskCompleted` hook that validates per-task prerequisites before any task can be marked complete:
- Full test suite passes (not just the task's new tests — all tests)
- No new lint errors
- Changed files are within the task's declared file scope

The hook exits with code 2 (reject with feedback) on failure, preventing task completion and returning failure output to the teammate.

**Hook scoping**: The TaskCompleted hook is configured in user-global settings (`~/.claude/settings.json`) and fires on every `TaskCompleted` event. The script scopes itself via context check: it parses the task description for an SDL task file path pattern (`ai-docs/*/tasks/task-*.md`) and exits 0 immediately (pass-through) if no match. This approach was chosen because skill-scoped hooks do not propagate to teammates (they are session-local), and dynamic configuration is fragile.

### Escalation from hook to re-plan

Hook rejections → teammate retries in-session using failure output as feedback. These are within-session retries and do NOT count toward the 2-attempt re-plan cap.

If the teammate cannot resolve after in-session attempts (goes idle or messages team lead) → team lead initiates re-plan protocol.

### Per-wave verification

Team lead runs after all wave tasks complete:
- Full test suite passes (all unit, integration, e2e across the project — confirms wave's new tests pass AND existing behavior not broken)
- No new lint errors introduced
- No uncommitted merge conflicts

The TaskCompleted hook catches most failures per-task. Per-wave verification is the aggregate cross-task check.

### Wave checkpoint

After each wave's verification passes:
1. **Summary**: What this wave accomplished — tasks completed, what was implemented, any re-plans and why.
2. **Test results**: Which tests pass, including new/updated and full existing suite.
3. **Commit offer**: "Would you like to commit before continuing to the next wave?" Draft commit message from wave summary if accepted.

This applies to every wave including the final one.

### Re-plan protocol (on failure)

1. Collect structured error report: which task, which check, specific error output.
2. Write failure summary to the feature's review artifact (`<feature-name>-review.md`): task, attempt, what went wrong, verification output.
3. Revise the task file in place. Original preserved in git history.
4. Send revised task to an idle teammate, or spawn replacement. The failing teammate does not retry — the team lead has the external signal (test/lint output) to make a meaningful revision. This satisfies the external feedback rule.
5. Cap: 2 re-plan attempts per task, then escalate to user.

### Final verification

**Structural** (deterministic):
- All tasks completed and individually verified
- Full test suite passes (definitive feature gate)
- No dead code introduced (files created but unused)
- Documentation updates completed per spec's documentation impact section

**Semantic** (human review):
- Spec acceptance criteria satisfied by the aggregate implementation — not just that tests pass, but that the result meets spec intent

### Retrospective

After final verification, the team lead writes `ai-docs/<feature-name>/<feature-name>-retrospective.md`:

**Factual data** (no AI judgment):
- Per-task: pass/fail, re-plan count, re-plan reasons, model used
- Task sizing accuracy: actual files modified vs. declared scope
- Model routing accuracy: Haiku tasks that succeeded vs. required escalation
- Verification gate pass rates
- Wall-clock time per wave (if available)

**Upstream traceability** (factual):
- Stage 2 review iterations before advancing
- Blocking findings count; how many led to spec revisions
- Stage 3 compilation attempts before gate passed

**Failure attribution** (AI judgment):
- For each re-planned task: root cause as **spec gap** (spec was underspecified), **compilation gap** (task missed something spec covered), or **implementation error** (task was correct, agent failed to follow it)

### Team shutdown

After final verification and retrospective:
1. Shut down all teammates.
2. Clean up the team.
3. Summarize: "All tasks complete and verified. Retrospective captured at `<path>`. Implementation is ready for your review."

## Instructions

1. Create `home/.claude/docs/sdl-workflow/implementation-guide.md`.
2. Read `home/.claude/docs/context-assets.md` for authoring principles. Apply them.
3. Write for the team lead agent running Stage 4 — direct imperatives.
4. Structure the doc:

   - **Team setup** — Creating the team, spawning teammates, the experimental flag requirement.
   - **Wave execution** — The step-by-step protocol per wave. This is the doc's core — be precise.
   - **Task isolation** — What teammates read and don't read. Non-overlapping scope guarantee.
   - **TaskCompleted hook** — What it checks, how to configure/scope it, exit code behavior.
   - **Per-wave verification** — Aggregate checks after wave completion.
   - **Wave checkpoint** — Summary, test results, commit offer.
   - **Re-plan protocol** — Error collection, failure summary, task revision, escalation cap.
   - **Final verification** — Structural and semantic checks.
   - **Retrospective** — Data to capture in each category.
   - **Team shutdown** — Cleanup and summary.

5. Wave execution and re-plan protocol are the highest-value sections — these define behavior the agent cannot infer. TaskCompleted hook scoping is a design decision that needs clear guidance.
6. Target: 160-220 lines. This is the most complex stage.

## Files to Create/Modify

- **Create**: `home/.claude/docs/sdl-workflow/implementation-guide.md`

## Acceptance Criteria

- AC-06: Enables team wave execution with verification gates, re-plan protocol, and retrospective
- AC-15: Follows authoring principles

## Model

Sonnet

## Wave

1
