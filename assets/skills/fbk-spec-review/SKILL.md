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

When the spec states it carries a contract inherited from a broader project scope verbatim, instruct the Architect agent to locate that original contract and diff the spec's entry against it field by field — signature, every invariant, and every constant. A review anchored only to the spec's own copy cannot catch a transcription divergence: a dropped field, a renamed field, a widened type, or a changed constant.

## Finding synthesis

Write `ai-docs/<feature-name>/<feature-name>-review.md` per `review-perspectives.md` §"Review document structure". The required testing strategy coverage entries are enumerated in §"Verification gate" of the same guide.

## Council-clean confirmation

Confirm the council has reached a clean state before the independent test-review runs: every blocking finding is resolved in the spec or accepted with documented rationale and risk owner, and the review document is stabilized — no further synthesis edits pending. The test-review reads the stabilized spec, so it must not run while findings are still in motion.

## Independent test-review

With the council clean and all blocking findings resolved, run the test-review as a unified-shape instance: route through `fbk-docs/fbk-review-lenses/review-loop.md` with `test-lens.md` loaded, **spec-checkpoint** mode, cardinality 1 researcher / 1 challenger, round cap 5.

Spawn both `review-researcher` and `review-challenger` as cleared agents. The spawn materials for the researcher are the spec file (`<feature-name>-spec.md`), the test lens, and the spec schema — the council's synthesized findings are not included, and the council's output artifact must not be in the spawn set. The researcher reads cold with no council memory: it asks, for each requirement, whether the planned test would actually prove the behavior. The challenger receives only the normalized candidate findings and any cited sources, never the researcher's framing or the council's prior synthesis.

The load-bearing output is the artifact: the loop coordinator writes `ai-docs/<feature-name>/test-review-spec.md` with a `Verdict:` line of `accepted` or `needs-revision`. The gate reads that file, not the conversation. A short human-readable summary may be folded into the stage artifact, but the `test-review-spec.md` file is authoritative.

If the verdict is `needs-revision`: surface the confirmed defects, address them in the spec, then re-run the test-review pass until the artifact records `accepted`. The gate blocks until the verdict is `accepted`.

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

The gate also verifies the independent test-review verdict. It finds `test-review-spec.md` in the review file's own folder — no extra argument is needed. A missing artifact or a verdict other than `accepted` is a blocking gate failure.

## Retrospective

After the review completes, write the Spec Review section to `ai-docs/<feature-name>/<feature-name>-retrospective.md` following `.claude/fbk-docs/fbk-sdl-workflow/retrospective-guide.md`. Create the file with the feature header if it does not exist. Read the file before writing to preserve existing content from prior stages.

## Transition

If the user agrees to proceed (per the guide's transition flow), invoke `/fbk-breakdown <feature-name>`.
