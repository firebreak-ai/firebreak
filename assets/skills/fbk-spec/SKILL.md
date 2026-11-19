---
name: fbk-spec
description: >-
  Work on the spec phase of a Firebreak development unit. Use when the
  human invokes /fbk-spec or asks to work on this phase.
argument-hint: "<unit-name> [request]"
---

Resolve the installed Firebreak directory: use the project's `.claude/` if it
contains `fbk-scripts/fbk.py`; otherwise use `$HOME/.claude/`. Use that resolved
absolute directory for commands and reference documents throughout this task.

The first word of this skill's arguments is the unit name; any text after it is the operator's request for this phase.

Read `fbk-docs/state-driven-workflow.md`
and `fbk-docs/workflow/spec.md` under the resolved Firebreak directory.
Use the current phase objective, artifact contract, and command interface. The hook normally enters the phase; run the
idempotent `phase-enter spec <unit>` command to confirm entry before authoring.

Session for this skill: `${CLAUDE_SESSION_ID}`. Append
`--session "${CLAUDE_SESSION_ID}"` to every new-workflow command.

Use the saved review plan for this phase. If it is pending, follow the shared
guide to recommend and record single or council review before closing.

On resumption, run `continuation <unit>` and retrieve relevant omitted sources before acting.
