---
name: fbk-implement
description: >-
  Work on the implement phase of a Firebreak development unit. Use when the
  human invokes /fbk-implement or asks to work on this phase.
argument-hint: "<unit-name> [request]"
---

Resolve the installed Firebreak directory: use the project's `.claude/` if it
contains `fbk-scripts/fbk.py`; otherwise use `$HOME/.claude/`. Use that resolved
absolute directory for commands and reference documents throughout this task.

The first word of this skill's arguments is the unit name; any text after it is the operator's request for this phase.

Read `fbk-docs/state-driven-workflow.md`
and `fbk-docs/workflow/implementation.md` under the resolved Firebreak directory.
Use the current phase objective, artifact contract, and command interface. The hook normally enters the phase; run the
idempotent `phase-enter implement <unit>` command to confirm entry before authoring.

Run the test tasks first, then `test-checkpoint <unit>`, which reviews the tests
and locks them on pass; only then run the implementation tasks, and close implement
once they are done.

Every task, test or implementation, runs in its own subagent: launch one subagent per task, as
many per wave as the wave has tasks. The lead coordinates; doing work a task
describes in the lead session means something has gone wrong.

Session for this skill: `${CLAUDE_SESSION_ID}`. Append
`--session "${CLAUDE_SESSION_ID}"` to every new-workflow command.

On resumption, run `continuation <unit>` and retrieve relevant omitted sources before acting.
