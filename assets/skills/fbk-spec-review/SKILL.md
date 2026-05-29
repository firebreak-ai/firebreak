---
description: >-
  SDL spec review using council agents. Use when reviewing, validating,
  or checking a completed feature specification. Invokes security,
  architecture, and quality review perspectives.
argument-hint: "[feature-name]"
---

This skill is phase three of the six-phase SDL; its review artifact serves as the semantic anchor that the spec gate reads to determine whether the spec is ready to advance.

Read `.claude/fbk-docs/fbk-sdl-workflow/review-perspectives.md` before proceeding — it defines classification signals, SDL concerns, invocation modes, threat-model determination, review document structure, and the verification gate.

## Argument

If `$ARGUMENTS` is empty, ask: "Which feature would you like to review?" Use the provided name as `<feature-name>`.

## Load spec

Read `ai-docs/<feature-name>/<feature-name>-spec.md`. If the file does not exist, report: "No spec found at that path. Run `/fbk-spec <feature-name>` to create one."

## Prior stage gate

Run: `python3 "$HOME"/.claude/fbk-scripts/fbk.py spec-gate ai-docs/<feature-name>/<feature-name>-spec.md`

If it exits non-zero, report the failures from stderr and offer: "Run `/spec <feature-name>` to address the missing sections." Do not proceed to review.

## Re-run check

If `ai-docs/<feature-name>/<feature-name>-review.md` already exists, warn the user it will be replaced entirely, then proceed.

## Council invocation

Classify which agents to invoke and in which mode per `review-perspectives.md` §"Classification process"; present the classification rationale before proceeding. Invoke `/fbk-council` with the classified agents per §"Invoking the council". For any spec that removes, renames, or changes a symbol's signature, additionally instruct the Architect agent to grep for all callers of the changed symbol and flag any the spec does not enumerate.

## Finding synthesis

Write `ai-docs/<feature-name>/<feature-name>-review.md` per `review-perspectives.md` §"Review document structure" before invoking the test-reviewer. The required testing strategy coverage entries are enumerated in §"Verification gate" of the same guide.

## Test strategy review

Invoke the test reviewer agent (`test-reviewer`) as an Agent Teams teammate with checkpoint 1 context. Pass the spec file and the spec schema as the artifact set. The test reviewer evaluates independently — it has no memory of the council review discussion and no access to council findings.

If the test reviewer returns FAIL: add its findings to the review document under a "Test Strategy Review" heading within the findings. Set the overall review result to fail. Include each defect the test reviewer identified, tagged with the AC it affects.

If the test reviewer returns PASS: add "Test strategy review: pass" to the review document as an informational note.

## Threat model determination

Run threat-model determination per `review-perspectives.md` §"Threat model determination" before invoking the gate. If a threat model is created, its path becomes the gate's third argument; otherwise omit the third argument.

## Gate invocation

Run the review gate with the classified perspectives as a comma-separated list:

```
python3 "$HOME"/.claude/fbk-scripts/fbk.py review-gate \
  ai-docs/<feature-name>/<feature-name>-review.md \
  "<perspective1>,<perspective2>,..." \
  [ai-docs/<feature-name>/<feature-name>-threat-model.md]
```

Omit the third argument if no threat model was created. Report any failures from stderr.

## Retrospective

After the review completes, write the Stage 2 section to `ai-docs/<feature-name>/<feature-name>-retrospective.md` following `.claude/fbk-docs/fbk-sdl-workflow/retrospective-guide.md`. Create the file with the feature header if it does not exist. Read the file before writing to preserve existing content from prior stages.

## Transition

If the user agrees to proceed (per the guide's transition flow), invoke `/fbk-breakdown <feature-name>`.
