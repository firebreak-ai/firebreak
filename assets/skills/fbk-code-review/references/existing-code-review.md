---
path: standalone
---

## Conversational Review Flow

This path is a guided conversation. The user directs the review — defining scope, indicating focus areas, and providing design intent. Follow the user's direction.

## User Interaction Model

Present verified findings as conversation evidence. The user discusses findings, provides corrections, and supplies design intent that the agent cannot infer from code alone. Example user inputs: 'Focus on the auth module', 'That duplication is actually the bigger problem', 'The caching layer bypass is the real issue.'

## Intent Register

The orchestrator completes Intent Extraction (SKILL.md) before beginning this conversational flow. The intent register contains behavioral claims extracted from project documentation. During the conversation, the user may provide additional design intent — corrections, clarifications, or priorities that documentation does not capture. Update the intent register in the review report file when the user provides design intent that contradicts or extends a documented claim.

## Spec Co-Authoring

As the conversation progresses, draft spec sections from the findings and user-stated intent:

- Problem section: emerges from confirmed findings
- Goals section: emerges from the user's stated design intent
- Technical approach: emerges from discussion of how things should work

Periodically present draft spec sections for user confirmation before moving to the next area.

## Spec Output

The remediation spec uses the standard 9-section template defined in `.claude/fbk-docs/fbk-sdl-workflow/feature-spec-guide.md`. When complete, run the spec through `spec-gate.sh` to validate structure. The spec enters the existing SDL pipeline: `/spec-review` → `/breakdown` → `/implement`.

## Scope Recognition

A focused review produces a feature-level spec. A broad review may produce a project overview with child feature specs. Follow the same scope recognition used by the `/spec` skill.

## When Only Structural Issues Surface

If the review reveals only structural issues and the user confirms no design intent is needed, stay lightweight — present findings against the AI failure mode checklist and let the user confirm or dismiss. If the user later provides design intent, transition naturally into spec co-authoring.

## Finding presentation

Present verified findings ordered by severity (critical first, then major, minor, info), grouped by type within each severity tier. This ensures behavioral bugs with production impact are reviewed before structural debt.

## Retrospective

After the review completes, append the retrospective to the review report file, following the fields defined in `code-review-guide.md`.

After the retrospective is written, invoke `/fbk-improve <feature-name>` to analyze the retrospective for pipeline improvement opportunities.
