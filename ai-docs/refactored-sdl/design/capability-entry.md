---
title: "Capability-Entry"
type: concept
sources:
  - firebreak-sdl-workflow
tags:
  - sdl-pipeline
  - pattern
  - refactored-sdl
created: 2026-05-29
updated: 2026-05-29
---

## Capability-Entry

The model for how scope-appropriateness works in the refactored SDL: the six phases (intent → design → spec → breakdown → implementation → code-review) are **independently invocable capabilities**, and the human enters the chain at the point that fits the work. There is no complexity classifier and no recorded tier tag deciding which phases run; the operator's judgment about scope is the routing signal.

### Why this, not tier-driven depth

An earlier design ran all six phases uniformly for every dispatch-complexity tier, with the tier "modulating depth," and inserted an eval that tagged each spec with a tier. Two problems: nothing consumed the tag (routing off complexity is a separate, later project), so the eval produced a recorded value that changed no behavior; and "uniform phases for all work" is the small-feature ceremony tax made mandatory — a one-line fix crushed under six phases. Capability-entry removes the classifier and lets the human route.

The six-tier *definitions* remain in the glossary as shared vocabulary (the dispatch work uses them), but no skill or gate in this cycle acts on them.

### Entry points by scope

- **Large or unfamiliar change** — start at intent and walk the whole chain.
- **Change that adds or bends some intent** — start at design or spec, inheriting the rest from the durable docs.
- **Small change that establishes no new intent** (a bugfix, a one-line correction) — start at the spec, or go lighter still, conversationally ("here's what I want" → "how would we build this?" → "yes, do that"), never formally invoking the upstream phase skills.

How much intent and design work a piece of work warrants scales with how much project intent it changes (see [[fbk-intent]] on sticky intent) — not with a classifier output. This is the same shape as the existing corrective/fast-track workflow, where a bugfix already enters downstream.

### Relationship to mid-pipeline-entry

Capability-entry generalizes the existing [[mid-pipeline-entry]] protocol. When a phase is invoked directly, it checks that its prerequisites hold (the upstream gate is satisfiable) and, if not, reports what's missing and offers to run the upstream phase — rather than blocking. Firebreak suggests the next step; the operator decides whether to take it.

The complementary invariant: the SDL itself does **not** silently skip a phase the chain reached. Skipping is a human entry decision, never a silent SDL behavior — a phase that doesn't run cannot catch what it would have caught.

### Related

- [[mid-pipeline-entry]] — the existing protocol this generalizes
- [[fbk-intent]] — sticky intent; the amount of upstream work scales with intent change
- [[stage-transition-protocol]] — how phases hand off when the chain runs forward
- [[firebreak-sdl-workflow]]
