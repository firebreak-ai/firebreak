---
description: >-
  Ambiguity resolution through structured questioning. Use when stress-testing
  a plan or design, resolving open decisions one at a time, or grilling a
  spec to surface hidden assumptions before committing to an approach. Raises
  each open question with full context, a concrete recommendation, and
  justification — then waits for the operator's answer before moving on.
argument-hint: "[topic or feature-name]"
# Source: adapted from Matt Pocock's grill-me skill — https://github.com/mattpocock/skills/blob/main/skills/productivity/grill-me/SKILL.md
---

This skill resolves ambiguity by asking one question at a time. It works in-ceremony (attached to a feature and phase) and out-of-ceremony (invoked standalone on any topic).

## How it works

Identify all open decisions for the given topic or feature. Sort them from most consequential to least.

A primary target is the requirement still stated in general terms that needs human direction to make concrete — a field, data shape, contract, signature, or observable behavior the work cannot pin down on its own. Raise each one as its own decision: name what is still loose, recommend a concrete definition, and let the operator confirm or redirect. Leave the routine details that have one sensible answer out of the queue; grill only what genuinely needs a human to settle.

Ask one question at a time. For each question:

1. State the decision in plain language — describe what is being decided, not a reference number or abbreviation.
2. Give your recommendation and the reasoning behind it.
3. Wait for the operator's answer.
4. Reflect the answer back to confirm: restate what you understood before recording it.

Move to the next question only after the answer is confirmed. Soft cap: stop after roughly 10 questions and summarize what remains rather than continuing indefinitely.

## Decision log (in-ceremony)

When invoked with a feature name and phase (for example: `/fbk-grilling my-feature intent`), write a decision log to:

```
ai-docs/<feature>/grilling-log-<phase>.md
```

The log contains one block per decision, using this exact shape:

```markdown
### <decision-slug>

- Question: What is being decided, in plain language.
- Recommendation: The agent's recommended answer and why.
- Answer: What the operator decided.
- Confirmed: The reflected-back restatement the operator confirmed.
```

The `Confirmed:` line is required in every block. It makes the reflect-back step an observable property of the log rather than an assumed behavior.

## Out-of-ceremony use

When invoked without a feature or phase, run the same loop — one question at a time, recommendation, reflect-back — but write no file. Summarize the decisions reached at the end of the session.

## Entry

If `$ARGUMENTS` is set, parse it as `<feature> <phase>` (space-separated). If both are present, operate in-ceremony and write the log. If only a topic is provided with no phase, operate out-of-ceremony.

If `$ARGUMENTS` is empty, ask the operator what topic or decision set to grill before beginning.
