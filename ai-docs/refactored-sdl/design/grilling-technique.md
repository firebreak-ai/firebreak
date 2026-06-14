---
title: "Grilling Technique"
type: concept
sources:
  - firebreak-spec-grilling-brainstorm
  - firebreak-sdl-workflow
tags:
  - sdl-pipeline
  - pattern
  - technique-skill
  - grill-me
  - human-in-the-loop
  - refactored-sdl
created: 2026-05-26
updated: 2026-05-26
---

## Grilling Technique

The one-question-at-a-time ambiguity-resolution capability invoked when an artifact's content requires operator judgment that the agent cannot close by inference. Surfaces decisions with full natural-language context, the agent's recommendation, and the justification — then waits for the operator's answer before moving to the next question. A defined [[technique-skill]] that phase skills invoke and that operators may also invoke out-of-ceremony (e.g., `/grill-me <topic>`).

Promotes the existing ad-hoc grilling practice — documented in [[firebreak-spec-grilling-brainstorm]] — into a first-class, callable capability with a stable interface.

### Why this exists as a separate technique

Multiple phases face the same shape of problem: the agent has produced something that contains decisions the operator should make rather than the agent guessing at. Without a defined technique, each phase invents its own grilling shape, with varying quality. With a defined technique, every phase invokes the same capability and the operator gets a consistent interaction across the SDL.

The technique also has independent value out of ceremony — `/grill-me` invoked alone is a useful operator tool for thinking through a decision, designing a fix, or auditing a draft document. The human counts as a second consumer beyond the phase skills, which justifies extracting the capability per the [[trigger-asset-vs-reference-asset]] discipline.

### Interaction shape

The technique works through three steps per question:

1. **Surface the question with full natural-language context.** The framing must be answerable by an operator who has *not* re-read the source artifact. Identifier-only references (e.g., "F1", "AC-NN", "B-NN") are insufficient. The technique restates the question in plain language, names what's actually being decided, and surfaces any constraints the answer must respect.

2. **Present the agent's recommendation and justification.** The agent commits to a recommended answer and explains the reasoning, including the tradeoff being made. This prevents the question from becoming a Socratic interrogation that the operator has to think through from scratch.

3. **Wait for the operator's response, then reflect back to confirm.** The operator answers, overrides, or asks a follow-up. Before moving to the next question, the technique reflects the operator's answer back in its own words ("So you want X because Y — confirming before I write that down"). The reflect-back catches misinterpretation cheaply, before the answer has propagated into downstream artifacts.

Only when the current question is resolved does the technique move to the next one.

### Plain-language register

Questions are phrased in plain language understandable to a non-coder technical lead. Terms-of-art from the codebase or methodology (e.g., "AC", "behavior inventory", "manifest") are used only when they're already established between operator and agent. Otherwise the technique uses descriptive language for the subject ("the validation requirement", "the list of behaviors we wrote down").

This is not a stylistic preference — it's an integrity check. If a question cannot be phrased clearly, the artifact backing it is likely underspecified. Clear phrasing is the bar.

### When to invoke (in-ceremony)

The phase skills invoke grilling whenever an artifact contains decisions the agent should not close by inference:

- **[[fbk-intent]]** — open product-level questions in the PRD or behavior inventory.
- **[[fbk-design]]** — design choices where multiple reasonable options exist (e.g., schema source for greenfield-vs-brownfield boundaries, architectural patterns where ADR-worthy decisions surface).
- **[[fbk-spec]]** — slice declarations and test-discipline modes where the choice is judgment, not derivation.

The skills decide when to grill; grilling is the *how*, not the *when*.

### When to invoke (out of ceremony)

`/grill-me <topic>` can be invoked by the operator at any time. The operator hands in either a topic ("I want to think through whether we should X") or an artifact ("grill me on this draft"). The technique works the same way — one question at a time, full context, recommendation, reflect-back. No phase context is required.

### Input/output contract

**Input:**
- Source artifact or topic (file path, prose, or operator instruction)
- Open questions list (optional — if absent, the technique identifies them itself)

**Output:**
- Updated source artifact with resolutions inline (when applicable)
- Decision log: one entry per question, recording the question text, the recommendation, the operator's answer, and any rationale they offered

The decision log is a separate ceremony artifact — *not* the gate's semantic anchor. Phase skills write the log to the feature directory (e.g., `ai-docs/<feature-name>/grilling-log-<phase>.md`) for traceability and as input to the phase skill's fresh-eyes deduplication step. The log is deleted at squash-merge along with other ceremony products.

The fresh-eyes report (produced separately by [[fresh-eyes-technique]] running cold) is the semantic anchor for the gate. The phase skill compares the fresh-eyes report against the grilling log to remove duplicate ambiguities before the gate consumes the reduced report.

### What it does not do

- **Does not auto-resolve.** Even questions with obvious answers go through the operator. The technique is for things the agent should not close by inference.
- **Does not batch-present.** A list of items elevated together fails to engage the operator's judgment on individual items; the technique always elevates one at a time.
- **Does not skip the recommendation step.** A question without a recommendation is a Socratic puzzle. The technique always commits to a recommended answer.
- **Does not skip the reflect-back step.** Even when the operator's answer seems unambiguous, the technique reflects it back. The cost is one line; the cost of misinterpretation propagating into the artifact is much higher.

### Iteration cap

Grilling has a soft iteration cap — typically ten questions per invocation, with explicit operator confirmation to continue past it. The cap exists because grilling sessions that produce more than ten open questions usually indicate that the upstream artifact is poorly scoped, and the right move is to step back and reframe rather than push through.

### Related

- [[firebreak-spec-grilling-brainstorm]] — the brainstorm this technique formalizes
- [[fresh-eyes-technique]] · [[quality-scan-technique]] · [[test-review-technique]] — sibling technique skills
- [[fbk-intent]] · [[fbk-design]] · [[fbk-spec]] — phase skills that invoke grilling
- [[external-feedback]] — the discipline grilling implements at decision moments
- [[hybrid-gate-pattern]] — the gate framework; the grilling decision log is a separate ceremony artifact consumed by the phase skill's deduplication step, not the gate's semantic anchor
- [[firebreak-sdl-workflow]] · [[spec-driven-development]]
