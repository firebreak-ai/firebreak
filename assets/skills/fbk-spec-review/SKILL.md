---
name: fbk-spec-review
description: >-
  Review a completed Firebreak specification using its saved single-reviewer
  or council plan. Use when asked to review or validate a feature spec.
argument-hint: "<unit-name>"
---

Resolve the Firebreak installation: use the project's `.claude/` when it contains
`fbk-scripts/fbk.py`; otherwise use `$HOME/.claude/`. Use absolute resolved paths.

For a `.fbk/` unit, load `fbk-docs/state-driven-workflow.md` and
`fbk-docs/workflow/review-selection.md` under that installation.
Run `status <unit>`, confirm spec is open, and follow its recorded review choice.
If the choice is pending, use the applicable user/project preference or ask with
a brief recommendation. Record it through `review-plan`, then run `phase-close spec`.
The runtime performs review and commits acceptance; the skill does not write a
separate review verdict. For accepted specs, use `workflow/repairs.md` for a
correction covered by recorded repair authority; other rework needs an authorized reopen.

Pass `--session "${CLAUDE_SESSION_ID}"` on each workflow command. Review fidelity
to intent and design, observable behavior, edge cases, and whether tests prove
those behaviors. Existing design decisions remain authoritative unless a defect
shows they cannot satisfy the requirements.
