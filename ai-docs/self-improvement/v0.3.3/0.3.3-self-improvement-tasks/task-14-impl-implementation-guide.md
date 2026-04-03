---
id: task-14
type: implementation
wave: 2
covers: [AC-01, AC-02, AC-03]
files_to_modify:
  - assets/fbk-docs/fbk-sdl-workflow/implementation-guide.md
test_tasks: [task-08]
completion_gate: "task-08 tests 1-3 pass"
---

## Objective

Adds 3 operational rules to `implementation-guide.md`: hook-rejection retry cap, fresh agent per task, and foreground execution for verification and hook commands.

## Context

The implementation guide coordinates agent team execution. Three additions address observed failure modes:

- AC-01: The current escalation protocol (lines 156-166) has a 2-attempt cap for task escalation. AC-01 adds a separate cap for hook rejection retries within a single task attempt. The TaskCompleted Hook section (lines 108-123) describes hook rejections prompting in-session retries but has no cap. The new rule caps hook rejection retries at 3 per task attempt.

- AC-02: The current "Task Isolation" section (lines 65-69) describes file-scope isolation but not agent-instance isolation. The new rule mandates a fresh agent per task to prevent context pollution from prior task residue.

- AC-03: The TaskCompleted Hook section (lines 108-123) does not specify foreground/background execution mode. Background execution of verification and hook commands can produce empty output, masking failures. The new rule mandates foreground execution.

## Instructions

1. In the `## TaskCompleted Hook` section, after the paragraph ending "...the hook applies only to SDL tasks.", add a new paragraph:

```
**Hook rejection retry cap**: When a hook rejection triggers an in-session retry, cap retries at 3 per task attempt. After 3 hook rejection retries without resolution, the teammate stops retrying and reports the failure to the team lead, who initiates the escalation protocol. This prevents infinite retry loops on systemic failures (e.g., a lint rule the agent cannot satisfy).
```

2. In the `## Task Isolation` section, after the existing paragraph ending "...the teammate does not read the spec, other task files, or the task overview.", add:

```
Spawn a fresh agent for each task. Do not reuse workers across tasks — context pollution from a prior task's code, errors, or partial reasoning can cause the agent to make incorrect assumptions about the current task's codebase state. Each task execution starts with a clean agent context containing only the task file and the designated reference files.
```

3. In the `## TaskCompleted Hook` section, after the paragraph "For SDL tasks, the hook validates:" and its bullet points (ending with "No new lint errors are introduced."), add:

```
Run all verification and hook commands in the foreground. Background execution can produce empty stdout/stderr, causing validation to report success when the command never completed or silently failed. Foreground execution ensures the hook captures complete output for feedback to the teammate.
```

## Files to create/modify

- `assets/fbk-docs/fbk-sdl-workflow/implementation-guide.md` (modify)

## Test requirements

Tests from task-08: Test 1 (hook retry cap keyword), Test 2 (fresh agent per task keyword), Test 3 (foreground execution keyword).

## Acceptance criteria

- AC-01: Implementation guide contains hook-rejection retry cap (3 retries, then team lead intervenes).
- AC-02: Implementation guide contains fresh-agent-per-task rule (no worker reuse across tasks).
- AC-03: Implementation guide contains foreground execution rule for all verification and hook commands.

## Model

Haiku

## Wave

Wave 2
