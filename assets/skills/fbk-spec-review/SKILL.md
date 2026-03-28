---
description: >-
  SDL spec review using council agents. Use when reviewing, validating,
  or checking a completed feature specification. Invokes security,
  architecture, and quality review perspectives.
argument-hint: "[feature-name]"
---

Read `.claude/fbk-docs/fbk-sdl-workflow/review-perspectives.md` before proceeding — it defines classification signals, SDL concerns, invocation modes, and review document structure.

## Argument

If `$ARGUMENTS` is empty, ask: "Which feature would you like to review?" Use the provided name as `<feature-name>`.

## Load spec

Read `ai-docs/<feature-name>/<feature-name>-spec.md`. If the file does not exist, report: "No spec found at that path. Run `/spec <feature-name>` to create one."

## Prior stage gate

Run: `.claude/hooks/fbk-sdl-workflow/spec-gate.sh ai-docs/<feature-name>/<feature-name>-spec.md`

If it exits non-zero, report the failures from stderr and offer: "Run `/spec <feature-name>` to address the missing sections." Do not proceed to review.

## Re-run check

If `ai-docs/<feature-name>/<feature-name>-review.md` already exists, warn the user it will be replaced entirely, then proceed.

## Classification

Analyze the spec and project context using the classification signals and SDL concerns table from `review-perspectives.md`. Determine which agents to invoke and in which mode (solo / discussion / full council). Present the selection with a one-line rationale per agent. Proceed unless the user adjusts.

## Council invocation

Invoke `/fbk-council` with the classified agents. For each agent, frame the prompt with:
- The SDL concern that agent owns
- The exact prompt framing from the SDL concerns table
- Relevant spec sections scoped to that agent's focus

## Finding synthesis

Write `ai-docs/<feature-name>/<feature-name>-review.md`. Start the file with a `Perspectives:` metadata line listing the invoked perspectives as a comma-separated list. Organize findings by SDL concern, not by agent. Tag each finding with severity: `blocking`, `important`, or `informational`. Findings must be specific and actionable — omit generic observations.

Include a testing strategy section covering: new tests needed, existing tests impacted, and test infrastructure changes. Mark any category with "none" and justification if empty.

## Test strategy review

Invoke the test reviewer agent (`test-reviewer`) as an Agent Teams teammate with checkpoint 1 context. Pass the spec file and the spec schema as the artifact set. The test reviewer evaluates independently — it has no memory of the council review discussion and no access to council findings.

If the test reviewer returns FAIL: add its findings to the review document under a "Test Strategy Review" heading within the findings. Set the overall review result to fail. Include each defect the test reviewer identified, tagged with the AC it affects.

If the test reviewer returns PASS: add "Test strategy review: pass" to the review document as an informational note.

## Threat model determination

Summarize the feature's security-relevant characteristics: data touched, trust boundaries crossed, new entry points, auth/access control changes.

Ask the user: "Does this feature need a threat model?" Record the decision and rationale in the review document regardless of the answer.

- **If yes**: Read `.claude/fbk-docs/fbk-sdl-workflow/threat-modeling.md`. Guide creation of `ai-docs/<feature-name>/<feature-name>-threat-model.md`.
- **If no**: Record decision and rationale (e.g., "No new trust boundaries, no data handling changes"). Security findings from the Security agent still appear in the review.

## Gate invocation

Run the review gate with the classified perspectives as a comma-separated list:

```
.claude/hooks/fbk-sdl-workflow/review-gate.sh \
  ai-docs/<feature-name>/<feature-name>-review.md \
  "<perspective1>,<perspective2>,..." \
  [ai-docs/<feature-name>/<feature-name>-threat-model.md]
```

Omit the third argument if no threat model was created. Report any failures from stderr.

## Transition

If blocking findings exist: "There are N blocking findings. Would you like to revise the spec to address them, or accept with documented rationale?"

If the user accepts blocking findings, record the rationale and risk owner in the review document before advancing.

If all resolved: "The review is structurally complete. Would you like to proceed to task breakdown?"

Before invoking the next stage: confirm all artifacts are written to disk, then summarize (feature name, number of findings by severity, threat model decision, gate result). Compact context before invoking the next skill. Then invoke `/breakdown <feature-name>`.
