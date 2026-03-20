# Task 04: Create Threat Modeling Guide

## Objective

Create the leaf doc that guides agents through STRIDE-based threat modeling and project model maintenance.

## Context

This doc loads on-demand during Stage 2 when the user decides a threat model is needed. It is not always loaded — only when threat model determination = yes.

### When this doc loads

The `/spec-review` skill handles threat model determination (active user decision). If the user says yes, the skill instructs the agent to read this doc for the detailed modeling process.

### Project-level threat model

A reusable project-level threat model lives at `ai-docs/threat-model.md`. It captures the project's overall threat landscape. Feature-specific threat models compare against and extend this model.

The project model is actively maintained — feature reviews propose additions, removals, and modifications. Changes are not limited to additions. A bug fix may alter a threat's severity. A refactored feature may invalidate trust boundaries or remove assets. Keeping the model accurate requires the same rigor as adding to it.

### Feature-level threat model

Produced at `ai-docs/<feature-name>/<feature-name>-threat-model.md`. Required sections:

1. **Assets** — What the feature protects or exposes (data, credentials, sessions, etc.)
2. **Threat actors** — Who might attack (external users, malicious insiders, automated bots, etc.)
3. **Trust boundaries** — Where trust levels change (client/server, internal/external service, user/admin)
4. **Data flows** — How data moves across trust boundaries
5. **Threats** — Using STRIDE categories:
   - **S**poofing: Can an attacker impersonate a legitimate entity?
   - **T**ampering: Can data be modified in transit or at rest?
   - **R**epudiation: Can actions be performed without accountability?
   - **I**nformation disclosure: Can sensitive data leak?
   - **D**enial of service: Can availability be degraded?
   - **E**levation of privilege: Can an attacker gain unauthorized access levels?
6. **Mitigations** — Controls for each identified threat (existing or proposed)
7. **Residual risks** — Threats accepted without full mitigation, with rationale and risk owner
8. **Proposed project model updates** — Specific additions, removals, or modifications to the project-level threat model, with rationale for each change. The user reviews and approves these before the project model is updated.

### Modeling process

1. Read the project-level threat model if it exists. Understand the current threat landscape.
2. Analyze the feature spec for new trust boundaries, data flows, and entry points.
3. Security agent leads the analysis. Architect contributes when the feature introduces new system boundaries or modifies existing ones.
4. For each component of the feature: enumerate assets, identify trust boundaries, trace data flows, apply STRIDE to each data flow crossing a trust boundary.
5. For each threat: assess likelihood and impact, propose mitigations.
6. Identify changes to the project model — what the feature adds, modifies, or invalidates.

### Sensitivity

Threat models document assets, attack surfaces, trust boundaries, and residual risks — information an attacker could use as a roadmap. All threat model artifacts are excluded from version control.

Naming convention (deterministic, for `.gitignore`):
- Project-level: `threat-model.md`
- Feature-level: `<feature-name>-threat-model.md`
- `.gitignore` rule: `*threat-model*`

## Instructions

1. Create `home/dot-claude/docs/sdl-workflow/threat-modeling.md`.
2. Read `home/dot-claude/docs/context-assets.md` for authoring principles. Apply them.
3. Write for the agent performing threat modeling — direct imperatives.
4. Structure the doc:

   - **Feature threat model structure** — The 8 required sections with content guidance for each.
   - **STRIDE categories** — Brief definitions and example questions per category. These are essential reference — the agent needs them during analysis.
   - **Modeling process** — Step-by-step: read project model, analyze spec, enumerate assets, apply STRIDE, propose mitigations, identify project model changes.
   - **Project model maintenance** — How to propose updates (additions, removals, modifications). Emphasize that changes require user approval before the project model is modified.
   - **Sensitivity** — Gitignore rule, naming convention, why these docs are excluded from version control.

5. The STRIDE categories and feature model structure are the highest-value content — include them in full. The process steps are important but more natural to the agent.
6. Target: 100-140 lines.

## Files to Create/Modify

- **Create**: `home/dot-claude/docs/sdl-workflow/threat-modeling.md`

## Acceptance Criteria

- AC-04: Enables STRIDE-based threat models and project model updates with all 8 required sections
- AC-15: Follows authoring principles

## Model

Sonnet

## Wave

1
