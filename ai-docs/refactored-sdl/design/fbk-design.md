---
title: "/fbk-design (skill)"
type: entity
sources:
  - firebreak-sdl-workflow
tags:
  - skill
  - sdl-pipeline
  - phase-skill
  - design-phase
  - refactored-sdl
created: 2026-05-26
updated: 2026-05-29
---

## /fbk-design

The second phase of the refactored SDL. Takes the PRD and behavior inventory from [[fbk-intent]] and produces design artifacts — module list, dependency graph, schemas, interface contracts, decomposition rationale, and decision records — written to the feature directory. New phase upstream of the existing [[fbk-spec]] — separates the design (capability list and shape) from the technical spec (slice declarations and execution plan).

### Outputs

All design output lives in the feature directory and is deleted at squash-merge with the rest of the feature directory:

- **Design pages** under `ai-docs/<feature-name>/design/` — one page per capability, describing its shape, contracts, and decomposition rationale.
- **Enduring decisions** appended to the project's durable **decisions log** — append-only, git-tracked, updated in the feature branch and merged with the change. Plus any shift in project shape reflected in the durable **architecture/intent overview**.
- **Design manifest** at `ai-docs/<feature-name>/design-manifest.md` — the [[design-manifest]]. Indexes every design page produced during this phase.

The design pages are ephemeral working memory — they sharpen the spec and are squashed away at closeout. What persists is the durable record (the decisions log and the architecture/intent overview); see the decision spine on the [[durable-artifact-discipline]]. A heavier cross-feature memory layer is out of scope — see the project-memory brainstorm.

### Technique skills used

- [[grilling-technique]] — invoked when design choices arise that have multiple reasonable options. The technique surfaces each choice to the operator with recommendation and tradeoff; the resolution informs which design page is written.
- [[fresh-eyes-technique]] — invoked at gate closure on the design pages and manifest.

Drafting is delegated to a context-isolated **general-purpose senior architect** agent in authoring mode — the skill orchestrates, the agent drafts. (The same architect definition can serve in review mode elsewhere — e.g., as the architecture voice on the spec council; see the decision spine on the agent model. The design gate's own review is fresh-eyes, not the architect.)

### Design deliberation

Design choices are worked out through [[grilling-technique]] — the agent surfaces each structural choice with recommendation and tradeoff, the operator decides — and closed with the [[fresh-eyes-technique]] check. An iterative multi-persona "architectural-review-meeting" was considered for higher-complexity work and deferred; see the decision spine. The design phase ships with grilling plus fresh-eyes.

### Schemas-from-design (greenfield) versus schemas-from-existing (brownfield)

The new-vs-existing distinction:

- **New schemas** are designed during this phase, regardless of greenfield-vs-brownfield context. Design records them as page content with both prose contract and typed contract sections. If the schemas are constrained by external systems (a fixed API the feature must integrate with), those external constraints are inputs to design, not outputs.
- **Existing schemas** are detected and included as constraints, not redesigned. Brownfield work that doesn't change schemas reads existing schemas via AST scan or codebase inspection and reflects them in the design pages as "existing — this feature operates against this schema." The design phase does not re-author existing schemas.

The delimiter is compatibility-vs-design, not greenfield-vs-brownfield.

### Gate

The design gate uses the [[hybrid-gate-pattern]]:

- **Mechanical anchor:** bidirectional check between the design manifest and the design pages in the feature directory. Every manifest entry exists as a file under `ai-docs/<feature-name>/design/` (manifest → files). Every design page present in that directory appears in the manifest (files → manifest). Both directions must check out.
- **Semantic anchor:** [[fresh-eyes-technique]] report on the design pages and manifest. The fresh-eyes reviewer reads each manifest-listed page cold and surfaces unclear, contradictory, or under-defined sections.

### Position in the SDL

```
... /fbk-intent → intent gate → /fbk-design → design gate → /fbk-spec → ...
```

[[mid-pipeline-entry]] applies: if invoked directly, design must check that the intent gate has passed. If it hasn't, design reports what's missing and offers to run intent first. The reverse also holds — an operator with a clear enough idea may skip design entirely and start at [[fbk-spec]]; design is a capability, not a forced step.

### Stage transition

Follows [[stage-transition-protocol]]:

1. Write all artifacts to disk — design pages and the design manifest to the feature directory; enduring decisions to the durable decisions log; any shape change to the architecture/intent overview.
2. Append the design phase's section to the feature retrospective (per the retrospective guide).
3. Summarize the completed design (one paragraph: what capabilities were designed, what decisions were recorded, what's ready for spec).
4. Compact context.
5. Invoke `/fbk-spec <feature-name>` with operator approval.

### Out-of-ceremony invocation

Not designed for out-of-ceremony use. Design is positioned between intent and spec — its inputs are PRD + behavior inventory, its outputs are feature-directory design pages plus a manifest. Operators wanting standalone design notes can write to the feature directory directly.

### Related

- [[fbk-intent]] · [[fbk-spec]] · [[fbk-breakdown]] · [[fbk-code-review]] — sibling phase skills
- [[grilling-technique]] · [[fresh-eyes-technique]] — technique skills invoked
- [[design-manifest]] — what design produces to index its pages
- [[durable-artifact-discipline]] — where enduring decisions and shape changes persist
- [[hybrid-gate-pattern]] · [[stage-transition-protocol]] · [[mid-pipeline-entry]]
- [[firebreak-sdl-workflow]]
