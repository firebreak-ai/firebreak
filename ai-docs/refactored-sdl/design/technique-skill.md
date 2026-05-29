---
title: "Technique-Skill"
type: concept
sources:
  - firebreak-sdl-workflow
tags:
  - sdl-pipeline
  - pattern
  - asset-type
  - refactored-sdl
created: 2026-05-26
updated: 2026-05-26
---

## Technique-Skill

A capability extracted into its own callable skill because multiple consumers benefit from invoking it with a stable interface. Distinct from a phase skill (which orchestrates a stage of the SDL) and from an agent (which embodies a persona). Capability-not-shape: the technique skill defines *what the capability does*, not where in the SDL it gets used.

A consumer counts as one of:

1. **Multiple phase skills.** When two or more SDL phases need the same capability (e.g., [[grilling-technique]] is used by intent, design, and spec).
2. **The operator out-of-ceremony.** When there's a significant and common scenario where a human operator would invoke the capability standalone, the human counts as a consumer (e.g., `/grill-me` to think through a decision).

Extraction is triggered when two consumers exist. Extraction is individually cheap; over-extraction (a technique skill that only ever has one consumer) adds asset-management overhead without payoff.

### Anatomy

Every technique skill defines:

- **Input contract.** What the caller hands in (file paths, prose, artifacts, parameters).
- **Output contract.** What the caller receives back — typically a structured artifact written to a specified location, plus a verdict line consumable by mechanical gates.
- **Persona / interaction shape.** How the technique conducts itself (e.g., grilling is one-question-at-a-time-with-reflect-back; fresh-eyes runs cold in isolated context; quality-scan is scan-only).
- **Out-of-ceremony invocation.** The `/<technique-name>` command and what arguments it accepts.
- **What it does not do.** Explicit limits — typically the kind of fix or action the technique deliberately leaves to the caller.

### The four technique skills in refactored-sdl

| Technique | Primary consumers | Out-of-ceremony use |
|-----------|-------------------|---------------------|
| [[grilling-technique]] | intent, design, spec | Operator decision-thinking |
| [[fresh-eyes-technique]] | intent and design gates; spec gate uses the existing [[council-deliberation]] via [[fbk-spec-review]] | Operator pre-circulation review |
| [[quality-scan-technique]] | code-review | Ad-hoc diff inspection |
| [[test-review-technique]] | breakdown (pre-lock, gates lock application), code-review (final) | Audit existing or third-party tests |

Fresh-eyes is a standalone technique; the existing [[council-deliberation]] is a related multi-persona cold-review pattern used at the spec gate. (An iterative multi-persona "architectural-review-meeting" variant was considered and deferred — see the decision spine.) See [[fresh-eyes-technique]] for the relationship.

### Relationship to phase skills and agents

- **Phase skill.** Orchestrates a stage of the SDL. Invokes technique skills as part of producing the stage's output. Maintains the ceremony products (PRD, design manifest, spec, slice declarations, task bundles, etc.).
- **Agent.** A persona (e.g., [[fbk-test-reviewer]], [[fbk-implementer]]) embodied as a context-isolated subagent. An agent definition encodes a *role and expertise*; the skill it pairs with supplies the *mode and task*, so one agent definition can serve multiple skills and modes (a senior architect both drafts and critiques a design — the skill sets which). Agents are often the concrete persona that carries out a technique.
- **Technique skill.** The capability with a stable interface. Composed *by* phase skills, possibly embodied *as* agents.

The asset taxonomy here aligns with the [[asset-type-taxonomy]] discipline: skills are triggers + routing; agents own persona; leaves own instructions; technique skills are the capability layer between them.

### Related

- [[asset-type-taxonomy]] — the broader asset categorization this fits into
- [[trigger-asset-vs-reference-asset]] — extraction criterion
- [[grilling-technique]] · [[fresh-eyes-technique]] · [[quality-scan-technique]] · [[test-review-technique]] — the four techniques
- [[firebreak-sdl-workflow]]
