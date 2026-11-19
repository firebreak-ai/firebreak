---
name: fbk-council
description: >-
  Review a Firebreak intent, design, spec or breakdown as a council discussion
  among chosen perspectives, or convene the council to discuss an open question.
argument-hint: "<unit-name or question>"
---

Resolve the Firebreak installation: use the project's `.claude/` when it contains
`fbk-scripts/fbk.py`; otherwise use `$HOME/.claude/`. Use absolute resolved paths.

For a `.fbk/` unit, read `fbk-docs/state-driven-workflow.md` and
`fbk-docs/workflow/review-selection.md` under that installation
and run `status <unit>`. Council review is available for intent, design, spec and breakdown. Follow
the saved review plan; if the human requests a change, record it with `review-plan`.
The runtime runs the council's openings, discussion and final session when
`phase-close` runs. This skill does not author an acceptance verdict.

Pass `--session "${CLAUDE_SESSION_ID}"` on each workflow command.

To convene the council on a question, read `references/consultation.md`.
