---
name: fbk-improve
description: >-
  Analyze retrospective evidence, propose targeted Firebreak improvements, and
  evaluate adopted changes. Use for /fbk-improve or requested workflow improvement.
---

Resolve the installed Firebreak directory: use the project's `.claude/` if it
contains `fbk-scripts/fbk.py`; otherwise use `~/.claude/`. Use the unit named in
`$ARGUMENTS` or the current conversation. Ask for the unit only when ambiguous.

For a unit with `.fbk/<unit>/state.json`, read the installed
`fbk-docs/workflow/improvement.md` and follow that evidence and evaluation workflow.
An explicit improvement request authorizes its analysis;
carry forward the user's existing scope and application decisions.
