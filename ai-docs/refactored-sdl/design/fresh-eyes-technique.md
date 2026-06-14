---
title: "Fresh-Eyes Technique"
type: concept
sources:
  - firebreak-sdl-workflow
tags:
  - sdl-pipeline
  - pattern
  - technique-skill
  - review
  - context-isolation
  - refactored-sdl
created: 2026-05-26
updated: 2026-05-26
---

## Fresh-Eyes Technique

A context-clear comprehension check. A reviewer (typically a subagent in isolated context) reads the artifact cold — without the authoring agent's context, working memory, or self-narration — and surfaces what doesn't make sense as structured observations. Used as the semantic anchor for the intent and design gates in the [[hybrid-gate-pattern]] (the spec gate uses the related, existing council pattern). A defined [[technique-skill]] that phase skills invoke.

The reviewer does not have authority to fix; it has authority to *observe*. Fixes go back to the authoring agent or operator. The fresh-eyes artifact is what the gate consumes.

### Why this exists as a separate technique

When the same agent that authored an artifact reviews it, the review is invalid — the agent reads its own intentions onto the text and confirms what it meant rather than what's written. This is the [[external-feedback]] principle. Fresh-eyes operationalizes the principle by providing the artifact to a reviewer who has not seen the authoring session.

Multiple phases need this capability: intent (does the PRD make sense to a reader who hasn't been in the conversation?) and design (does the design page actually convey the intended capability?). One defined technique covers both. The spec gate uses the related, existing council pattern rather than single-persona fresh-eyes.

Fresh-eyes also has potential out-of-ceremony value — an operator drafting a doc or RFC may want a fresh-eyes pass before circulating it — but the in-ceremony use case is its primary justification.

### Interaction shape

The technique is invoked by handing in an artifact (a single file or a small set of related files) and getting back a structured observation list. The reviewer follows three steps:

1. **Read cold.** The reviewer's context is initialized only with the artifact and the technique's instructions. No conversation history, no prior session memory, no operator preamble beyond "read this and tell me what doesn't make sense."

2. **Surface observations.** The reviewer enumerates passages, claims, or sections that are unclear, contradictory, under-defined, or that depend on knowledge the reader doesn't have. Each observation cites the specific location (file + line range or section header) and states the issue concretely.

3. **Categorize by severity.** Observations are classified as critical (would block a downstream agent from executing), substantive (would produce wrong work), minor (would slow a reader down). The gate consuming the output decides what bar to enforce — typically "no critical observations open."

The reviewer does *not* propose fixes. A fix requires authoring context the reviewer deliberately doesn't have. Fixes go back to the authoring agent or operator with the observation list as input.

### Output shape

A structured markdown file with one entry per observation:

```markdown
# Fresh-Eyes Report: <artifact>

## Critical

### <observation slug>
- **Location:** <file>:<line range or section>
- **Issue:** <one-line description>
- **Detail:** <what specifically does not make sense, in concrete terms>

## Substantive

…

## Minor

…
```

The file lives in the feature directory and is named after the artifact reviewed (e.g., `fresh-eyes-design.md`, `fresh-eyes-spec.md`). The gate reads this file for its semantic verdict on whether the artifact can advance.

### When to invoke (in-ceremony)

| Gate | Artifact reviewed | Bar |
|------|-------------------|-----|
| Intent | PRD + behavior inventory | No critical observations open |
| Design | Design pages (feature directory) + design manifest | No critical observations open |
| (Spec gate uses the existing [[council-deliberation]] instead — see below) | | |
| (Breakdown gate uses executability check instead — see [[hybrid-gate-pattern]]) | | |
| Code-review | Final artifact + change diff | (Code-review uses [[quality-scan-technique]] and [[test-review-technique]] instead) |

### Context isolation discipline

The reviewing subagent runs in a context isolated from the authoring agent. Operationally this means the technique spawns a subagent (or invokes an out-of-process reviewer skill) rather than asking the authoring agent to "step back and re-read." Self-review is invalid by construction.

The isolation is the same discipline that justifies the [[council-deliberation]] pattern's separate-perspective agents — independent context is what produces independent judgment.

### What it does not do

- **Does not fix.** Surface only. Fixes belong to the authoring agent or operator.
- **Does not bring in external knowledge.** The reviewer evaluates the artifact's *self-coherence and clarity*, not its alignment with external best practices. If the artifact is internally consistent and clear, fresh-eyes passes — even if a different design would have been preferable.
- **Does not run as the authoring agent.** Self-review is invalid; the technique enforces context isolation as a precondition.

### Relationship to the council

Fresh-eyes is a standalone technique — a single cold reviewer producing structured observations, used at the intent and design gates. The [[council-deliberation]] pattern (the existing multi-persona spec review, via [[fbk-spec-review]]) is a *related* cold-review pattern used at the spec gate: multiple specialist personas review independently and their findings are synthesized. Both rest on the same discipline, but fresh-eyes is not a "family" abstraction over the council, and the council is not rebuilt here — it already ships.

(An earlier design grouped fresh-eyes, the council, and an iterative multi-persona "architectural-review-meeting" into a formalized family. The meeting was deferred — see the decision spine — and the family framing was dropped: a formalized family of two, one of which already exists and isn't changing, was a thin abstraction. If the meeting returns later, the family framing can return with it.)

The shared disciplines:

- **Cold context** — reviewers do not have authoring conversation history. Self-review by the authoring agent is invalid by construction.
- **Structured output** — observations have a defined shape consumable by gates and operators.
- **No fix authority** — reviewers surface; fixes go back to the authoring agent or operator.

### Phase-skill deduplication step

When the gate consuming a fresh-eyes report runs in a phase that also produced a grilling decision log, the phase skill runs a deduplication step between fresh-eyes producing its raw output and the gate inspecting it:

1. Fresh-eyes produces its raw report cold.
2. The phase skill reads the raw report and the grilling log, comparing fresh-eyes observations against ambiguities already raised and resolved during grilling.
3. Observations that map to a grilling-log resolution are removed from the report. The reduced report is what the gate consumes.

This preserves fresh-eyes' cold-context discipline (it does not read the grilling log) while preventing the operator from being asked to address ambiguities already addressed.

### Related

- [[external-feedback]] — the principle fresh-eyes implements
- [[context-isolation]] — the discipline fresh-eyes enforces operationally
- [[council-deliberation]] — the existing multi-persona cold-review pattern used at the spec gate
- [[grilling-technique]] · [[quality-scan-technique]] · [[test-review-technique]] — other technique skills
- [[hybrid-gate-pattern]] — fresh-eyes reports serve as semantic anchors for intent and design gates; the council serves the spec gate
- [[fbk-intent]] · [[fbk-design]] · [[fbk-spec]] — phase skills that invoke fresh-eyes or the council
- [[firebreak-sdl-workflow]]
