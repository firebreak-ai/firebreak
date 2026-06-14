# Design Manifest: refactored-sdl

Index of the design pages produced for this feature. Most design output lives in this feature directory and is ephemeral — deleted at squash-merge. A small durable set (the glossary, the decisions log, and the architecture/intent overview) persists in the repo instead; see the durable-artifact discipline.

Read by the design gate for the bidirectional check: every page listed under "Capabilities designed" exists under `design/`, and every page under `design/` is listed here.

Scope passes: 2026-05-28 cut the project-memory layer and the capture gate. 2026-05-29 cut complexity-classification machinery, the architectural-review-meeting, and mutation sampling; added the capability-entry model and the durable-artifact discipline; and settled the agent model. See `adr-spine.md`.

## For an agent reading this package cold

This package is self-contained: the PRD, the design pages, the decision spine, and this manifest carry everything needed to author the spec. Notes for a reader who arrives without prior context:

- `[[wikilinks]]` to firebreak concepts (e.g., `[[stage-transition-protocol]]`, `[[mid-pipeline-entry]]`, `[[council-deliberation]]`, `[[firebreak-sdl-workflow]]`) point to pages in the operator's firebreak wiki — background context, not required inputs, and they do not resolve inside this folder.
- Any citation that does **not** resolve — for example a source-material reference — is external **provenance, not a required input.** Do not reconstruct it, infer its contents, or silently work around it. If you believe you genuinely need it, **ask the operator** rather than guessing.

## Capabilities designed (new pages — `design/`)

- `design/capability-entry.md` — phases are invocable capabilities; the human enters at the scope-appropriate point; no complexity classifier.
- `design/durable-artifact-discipline.md` — the curated durable git-tracked docs (glossary, decisions log, architecture/intent overview) that outlive a feature; replaces project-memory.
- `design/technique-skill.md` — the asset-type definition for callable capabilities; agents encode expertise, skills encode mode.
- `design/slice-shapes.md` — the four test-discipline modes a slice can take; declared per-slice in the spec; per-shape instructions loaded by progressive disclosure.
- `design/hybrid-gate-pattern.md` — the general hybrid gate shape (mechanical anchor + semantic anchor on a technique-skill artifact); used by all six phase gates.
- `design/grilling-technique.md` — one-question-at-a-time ambiguity-resolution capability.
- `design/fresh-eyes-technique.md` — context-clear comprehension check; semantic anchor for intent and design gates; the council is the related existing pattern at the spec gate (no "family" framing).
- `design/quality-scan-technique.md` — Pocock-style top-five quality scan at code-review; scan-only; severity-tagged; non-blocking.
- `design/test-review-technique.md` — reading-based test-quality validation at two checkpoints; pre-lock verdict gates lock application; final-pass is the drift check.
- `design/design-manifest-concept.md` — the design-manifest pattern itself, generalized; bidirectional check against the feature directory.
- `design/fbk-intent.md` — the new intent phase skill; reads/updates the durable architecture/intent overview; produces PRD + behavior inventory + grilling log.
- `design/fbk-design.md` — the new design phase skill; writes design pages and this manifest to the feature directory, enduring decisions to the durable decisions log.

## Changes to existing assets

- `design/changes-to-existing-assets.md` — planned changes to already-shipped assets (fbk-spec, fbk-breakdown, fbk-code-review, fbk-test-reviewer, fbk-implement, fbk-spec-review, and the test-integrity-locking concept), plus the cross-cutting retrospective-append requirement. The canonical wiki pages describe current shipped state and are updated only when the change ships.

## Decisions recorded

- `adr-spine.md` (feature-directory root) — single cumulative decision spine, fifteen decisions. Notable: capability-entry (Decision 2), the agent model (Decision 4), the durable-artifact discipline (Decision 12), intent-as-sticky-alignment (Decision 13), cross-cutting integration (Decision 14), and the deferred items (Decision 15).

## Deferred (parked — `deferred/`)

- `deferred/architectural-review-meeting-pattern.md` — the iterative multi-persona design deliberation, deferred to a future cycle (one consumer; an authoring pattern, not a closure-review one). See Decision 15.
- Also deferred but without a dedicated page: project-memory + the capture gate, mutation sampling, and the council migration to general role-agents. See Decision 15 and `project-memory-brainstorm` in the firebreak wiki.

## Notes

- This design was authored in the firebreak project, which dogfoods the SDL being designed. Design pages were drafted into the firebreak wiki and consolidated here when project-memory was cut, so the package follows the same `ai-docs/<feature-name>/` convention the SDL prescribes.
- `GLOSSARY.md` carries the terms this design introduced. Removed when their concepts were cut: project-memory, capture gate, mutation sampling. Added: capability-entry, durable-artifact discipline, architecture/intent overview, decisions log.
- The design was vetted during the design phase through multiple cold fresh-eyes passes and a council review; those review records were temporary scaffolding and have been removed.
