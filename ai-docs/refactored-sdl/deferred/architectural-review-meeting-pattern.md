---
title: "Architectural-Review-Meeting Pattern"
type: concept
sources:
  - firebreak-sdl-workflow
tags:
  - sdl-pipeline
  - pattern
  - review
  - design-phase
  - council
  - refactored-sdl
created: 2026-05-27
updated: 2026-05-27
---

## Architectural-Review-Meeting Pattern

> **DEFERRED — not part of the refactored-sdl cycle.** Considered and deferred (see the decision spine): it had only one consumer (the design phase), was the least-specified piece, and is an *authoring* pattern rather than a closure-review pattern, so it didn't belong grouped with fresh-eyes and the council. Preserved here for a future cycle. The design phase ships with grilling plus fresh-eyes instead.

A multi-persona iterative deliberation that runs during the [[fbk-design]] phase for non-trivial work. Multiple subagents — each in isolated context with a defined persona (security, architect, quality, builder, advocate, analyst, guardian) — discuss the design under consideration, exchange positions across iterations, and produce ADR entries as artifacts of the discussion itself rather than as post-hoc records.

The third variant in the [[fresh-eyes-technique]] family of context-isolated review capabilities.

### Relationship to other variants in the family

The fresh-eyes family covers three patterns sharing the same underlying machinery (cold, context-isolated review by uncontaminated agents) applied with different interaction shapes:

- **[[fresh-eyes-technique]]** — single persona, single cold pass, structured observation output. Used at intent, design, and spec gates as the semantic anchor for the [[hybrid-gate-pattern]].
- **[[council-deliberation]]** — multiple personas in parallel, each running fresh-eyes-style independently, then synthesized into a unified review document. Used at the spec gate via [[fbk-spec-review]].
- **Architectural-review-meeting** — multiple personas in iterative conversation. Personas can respond to each other's positions, refine arguments, and arrive at synthesized ADRs through the discussion. Used at the design gate via [[fbk-design]] when the dispatch-complexity tier warrants the heavier discipline.

The progression is single-pass → parallel multi-persona → iterative multi-persona. Each variant uses the same underlying capability (context-isolated review) with progressively richer interaction.

### When to invoke

[[fbk-design]] invokes the meeting style as the default deliberation pattern for non-trivial features. "Non-trivial" is calibrated by [[dispatch-complexity-tiers]]:

- **single-touch / single-module:** meeting is skipped; design proceeds without multi-persona deliberation.
- **cross-module / decomposed:** meeting is recommended; operator may skip if the design is mechanical.
- **architectural-extend / architectural-replace:** meeting is required.

The operator participates in the meeting as the deciding voice — agent personas surface positions and tradeoffs, the operator decides which positions to accept into the design.

### Participating personas

Drawn from the same roster as [[council-deliberation]]:

- [[fbk-council-architect]] — systems design, patterns, long-term technical vision
- [[fbk-council-builder]] — implementation reality, complexity assessment, pragmatism
- [[fbk-council-guardian]] — reliability, maintainability, edge cases, testing
- [[fbk-council-security]] — vulnerabilities, threat modeling, attack vectors
- [[fbk-council-advocate]] — user needs, usability, intended audience, project purpose
- [[fbk-council-analyst]] — metrics, validation, measurable outcomes
- [[fbk-council]] — the orchestration entry point

For any given meeting, the participating subset is chosen based on what the design touches. Most meetings run with three to five personas, not all of them.

### Interaction shape

The meeting proceeds in rounds:

1. **Opening positions.** Each participating persona reads the design under consideration and surfaces their initial concerns or recommendations. Independent context; no persona sees another's opening.
2. **Cross-reading.** Each persona reads the others' openings and refines their position — agreeing, disagreeing, or proposing modifications.
3. **Operator participation.** The operator surfaces their own perspective and asks questions of specific personas.
4. **Synthesis.** A synthesis pass identifies positions that reached consensus, positions that remained contested, and decisions the operator made. Each decision becomes an ADR entry.

The meeting concludes when either consensus is reached or the operator decides on contested positions. There is no fixed iteration cap — the operator decides when discussion is complete.

### Output contract

The meeting produces:

- **Decision-spine entries** appended to `ai-docs/<feature-name>/adr-spine.md`, the feature's cumulative decision spine. Each entry records the decision, the context that drove it, the alternatives considered, and the rationale.
- **Influence on design pages** — the design pages being authored during this phase incorporate the meeting's conclusions. The relationship between meeting and design pages is one-to-many; one meeting may influence multiple design pages.
- **Meeting log** in the feature directory (`ai-docs/<feature-name>/architectural-review-meeting-log.md`) — a record of positions, exchanges, and operator decisions for traceability. Ceremony product; deleted at squash-merge.

### What it does not do

- **Does not write the design pages itself.** The personas surface positions and contribute to ADRs; the authoring agent (or operator) writes the design pages incorporating those conclusions.
- **Does not gate the design phase.** The design phase's [[hybrid-gate-pattern]] gate uses [[fresh-eyes-technique]] as the semantic anchor. The meeting is part of the design phase's *authoring* work, not its closure check.
- **Does not run iteratively without operator participation.** The pattern requires operator deciding-voice presence; running it as a closed-loop multi-agent debate without operator input produces ADRs the operator never agreed to.

### Status

This is a stub. Full implementation work — defining the orchestration script, the per-persona prompts, the synthesis logic, and the meeting-log format — is its own feature within the implementation of the refactored SDL.

### Related

- [[fresh-eyes-technique]] · [[council-deliberation]] — sibling variants in the same family
- [[fbk-design]] — the phase skill that invokes the meeting
- [[fbk-council]] · [[fbk-council-architect]] · [[fbk-council-builder]] · [[fbk-council-guardian]] · [[fbk-council-security]] · [[fbk-council-advocate]] · [[fbk-council-analyst]] — participating personas
- [[hybrid-gate-pattern]] — gate context the meeting fits into
- [[dispatch-complexity-tiers]] — controls when the meeting is invoked
- [[context-isolation]] — the discipline that distinguishes meeting personas
- [[firebreak-sdl-workflow]]
