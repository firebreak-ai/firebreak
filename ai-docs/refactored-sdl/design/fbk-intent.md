---
title: "/fbk-intent (skill)"
type: entity
sources:
  - firebreak-sdl-workflow
tags:
  - skill
  - sdl-pipeline
  - phase-skill
  - intent-phase
  - refactored-sdl
created: 2026-05-26
updated: 2026-05-29
---

## /fbk-intent

The first phase of the refactored SDL. Produces the PRD (the "what" — feature behavior, user-facing contract, edge cases, acceptance criteria) and the behavior inventory (the structured list of behaviors the PRD describes). New phase upstream of the existing [[fbk-spec]] — separates product-level decisions ("should we?") from technical decisions ("how?") so the product question is answered before the technical question.

Formalizes the upstream separation proposed in [[firebreak-spec-grilling-brainstorm]]'s Proposal 1.

### Inheriting and updating project intent

Intent is sticky — it carries across features (see the decision spine). Before drafting, /fbk-intent reads the project's durable architecture/intent overview to inherit what the project already is and wants; for an established project most intent is inherited and the phase captures only the delta. When the feature shifts project intent — a convention, a direction, a constraint — the durable overview is updated in the feature branch so the change merges with the code. The per-feature PRD captures the feature-specific intent; the sticky part lands on the durable overview.

### Outputs

- `ai-docs/<feature-name>/prd.md` — Product Requirements Document. Behavioral content only; no implementation details, no file targets, no code paths.
- `ai-docs/<feature-name>/behavior-inventory.yaml` — structured list of behaviors with IDs, descriptions, and (for brownfield work) any links to existing behaviors being modified or replaced.
- `ai-docs/<feature-name>/grilling-log-intent.md` — record of grilling exchanges during PRD authoring (separate ceremony artifact, consumed by the phase skill's fresh-eyes deduplication step).

All three artifacts live in the feature directory and are ceremony products — deleted at squash-merge.

### Technique skills used

- [[grilling-technique]] — invoked when product-level ambiguity surfaces that the agent cannot close by inference. Behavior-inventory completeness questions, user-flow edge cases, and acceptance-criteria boundaries are typical grilling subjects.
- [[fresh-eyes-technique]] — invoked at gate closure on the PRD and behavior inventory.

The operator interview runs in the skill's own context; PRD drafting is delegated to a context-isolated **requirements/product author** agent, so the draft is produced cold (see the decision spine on the agent model).

### Gate

The intent gate uses the [[hybrid-gate-pattern]]:

- **Mechanical anchor:** PRD file present with required sections (Vision, Problem statement, Goals and non-goals, Use cases, Functional requirements, Non-functional requirements, Edge cases and failure modes, Dependencies, Success metrics, Open questions); behavior inventory present with consistent IDs; no behaviors referenced in PRD that aren't in the inventory; no inventory items that aren't referenced in the PRD; grilling log present.
- **Semantic anchor:** [[fresh-eyes-technique]] report on the PRD + behavior inventory, after the phase-skill deduplication step against the grilling log. Bar: no critical observations open after deduplication.

The grilling log itself is *not* read by fresh-eyes — fresh-eyes runs cold. The phase skill compares fresh-eyes' raw report against the grilling log and removes observations that map to grilling-log resolutions. The reduced report is what the gate consumes.

### Position in the SDL

```
operator → /fbk-intent → intent gate → /fbk-design → design gate → /fbk-spec → ...
```

The intent phase is the first stage. It is invoked directly by the operator with a feature name and a description (which can be terse — grilling will draw out the rest).

[[mid-pipeline-entry]] does not apply to intent — there is no prior gate to check. But intent does check its *own* gate as a precondition to advancing. Intent is also optional under capability-entry: work that establishes no new project intent (a bugfix, a small change in an established project) can skip intent and enter downstream at spec or lighter — see the decision spine.

### Scope discipline at intent

The intent phase produces behavioral content only. It does **not** produce design (capabilities, dependency graphs, schemas) or any technical decisions. Intent uses grilling for ambiguity resolution and fresh-eyes for the gate's semantic anchor; no multi-persona deliberation runs at this phase.

If the work is large or architecturally significant, intent says so in plain language in the PRD's `Vision` or `Problem statement`, so the operator can choose appropriate depth (capability-entry). There is no tier-classification step.

### Stage transition

Follows [[stage-transition-protocol]]:

1. Write all artifacts to disk; update the durable architecture/intent overview if project intent shifted.
2. Append the intent phase's section to the feature retrospective (per the retrospective guide).
3. Summarize the completed intent (one paragraph: what behaviors are captured, what's ready for design).
4. Compact context.
5. Invoke `/fbk-design <feature-name>` with operator approval.

### Out-of-ceremony invocation

Not designed for out-of-ceremony use. The intent phase is specifically the entry to the SDL — its outputs are inputs to design. Operators wanting to think through a PRD-shaped artifact without the full SDL should use [[grilling-technique]] directly (`/grill-me`).

### Related

- [[fbk-design]] · [[fbk-spec]] · [[fbk-breakdown]] · [[fbk-implement]] · [[fbk-code-review]] — downstream phase skills
- [[grilling-technique]] · [[fresh-eyes-technique]] — technique skills invoked
- [[firebreak-spec-grilling-brainstorm]] — the proposal this phase implements
- [[hybrid-gate-pattern]] · [[stage-transition-protocol]] · [[mid-pipeline-entry]]
- [[capability-entry]] — intent is the full-chain entry point; small work that inherits intent may enter downstream instead
- [[firebreak-sdl-workflow]] · [[spec-driven-development]]
