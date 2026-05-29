---
title: "Hybrid Gate Pattern"
type: concept
sources:
  - firebreak-sdl-workflow
  - firebreak-readme
tags:
  - sdl-pipeline
  - pattern
  - gate
  - architecture
  - refactored-sdl
created: 2026-05-26
updated: 2026-05-28
---

## Hybrid Gate Pattern

The general shape every phase gate takes in the [[firebreak-sdl-workflow]]: a deterministic mechanical check that validates structure, plus a semantic check anchored on a verifiable artifact produced by a [[technique-skill]] (typically [[fresh-eyes-technique]] for the intent and design gates, the existing [[council-deliberation]] for the spec gate, and [[quality-scan-technique]] plus [[test-review-technique]] for the code-review gate). The mechanical part is hook-ready — it can migrate to deterministic enforcement when hooks support it. The semantic part anchors on the technique-skill's structured output so the gate has something concrete to inspect rather than re-running judgment.

Formalizes the existing [[deterministic-verification-gates]] two-layer pattern (structural + semantic) by specifying *how* the semantic layer surfaces its verdict — through a technique-skill artifact that the gate can mechanically inspect.

### Why this shape

Pure mechanical gates miss semantic problems — a structurally-valid spec can still be confused about what it's specifying. Pure semantic gates are non-deterministic — same artifact, two LLM runs, different verdicts. The pattern combines both:

- **Mechanical check** is fast, free, deterministic. Catches structural problems (missing sections, malformed manifest, no tests written, etc.). Hook-ready.
- **Technique-skill artifact** is the semantic check's output. The technique skill (fresh-eyes, quality-scan, test-review) runs once and produces a structured artifact — a list of observations, findings, or verdicts. The gate then mechanically checks that the artifact exists, has expected shape, and meets the gate's bar (e.g., "no critical findings").

The result: gates have deterministic gate logic *over* a semantic check's output. The semantic work happens in the technique skill (where its expense and non-determinism are contained); the gate's verdict on whether to advance is deterministic given the artifact.

### Anatomy of a hybrid gate

```
Phase produces ceremony artifacts → write to feature directory
                                  ↓
Technique skill runs → produces structured output (e.g., fresh-eyes-report.md)
                     ↓
Phase skill may run reconciliation step
  (e.g., dedup fresh-eyes observations against grilling decision log)
                     ↓
Gate runs mechanical check:
  • Phase artifacts present and structurally valid (deterministic)
  • Technique-skill artifact present and structurally valid (deterministic)
  • Technique-skill artifact's verdict meets bar (deterministic over the artifact)
                     ↓
                  Pass / Fail
```

The technique-skill artifact is the *verifiable anchor* — its presence and content are what the gate inspects, not the underlying phase work. This means the gate's verdict is reproducible: running the gate twice on the same files produces the same result.

### Per-gate detail (six SDL phases)

The refactored SDL has six phases, each with a hybrid gate:

| Gate | Mechanical anchor | Semantic anchor |
|------|------------------|-----------------|
| **Intent** | PRD + behavior inventory present and structurally valid (sections match the PRD format used by this project); grilling decision log present | [[fresh-eyes-technique]] report on PRD + behavior inventory, after phase-skill deduplication against the grilling log |
| **Design** | [[design-manifest]] present; bidirectional check (every manifest entry exists as a design page in the feature directory, and every design page in the directory appears in the manifest) | [[fresh-eyes-technique]] report on design pages, after deduplication against the grilling log |
| **Spec** | Spec file structurally valid; slice declarations present with `test-discipline` field per slice; every behavior in the inventory covered by at least one slice; design pages referenced by the spec exist | [[council-deliberation]] (the existing multi-persona spec review via [[fbk-spec-review]]), after deduplication against the grilling log |
| **Breakdown** | Each slice's work units match its declared shape (per [[slice-shapes]]); size constraints met; pre-lock [[test-review-technique]] verdict gates lock application before the gate runs (locks are not applied if pre-lock verdict is needs-revision); operator confirms breakdown ran cleanly | Bounce-back mechanism — if breakdown produced oversized work units it bounces the slice back to spec rather than completing. Completing without bounce-back is itself the executability check |
| **Implementation** | Per-task `TaskCompleted` hook runs project tests and linter; [[test-integrity-locking]] hash check passes per task; per-wave verification gates pass | No dedicated semantic anchor at the implementation gate — semantic discipline was established upstream (the locked tests are the contract); semantic review happens downstream at code-review |
| **Code-review** | Tests pass; [[test-integrity-locking]] hash check passes (locked test files unchanged); no shadow tests added; quality-scan artifact present with structured findings | [[quality-scan-technique]] top-five findings (severity: critical / substantive / minor); [[test-review-technique]] final-pass verdict (accepted / needs-revision), with any drift surfaced as findings |

### Hook-readiness

The mechanical portion of each gate is implemented as a Python script under [[fbk-scripts]] (`fbk.py <gate-name>`). Today the script is invoked explicitly by the phase skill at stage transition. As Claude Code's hook surface expands (currently `TaskCompleted` is the only true hook — wired in `settings.json` to run per-task verification), gates can migrate to event-driven enforcement — the same `fbk.py` invocation, triggered by a hook event rather than by skill body code.

The semantic anchor's artifact (technique-skill output) is also hook-inspectable. The gate script can be re-run on the same files at any time and produce the same verdict.

### What this replaces

The existing [[deterministic-verification-gates]] pattern documents structural + semantic as separate layers but leaves the semantic layer to "human or AI judgment" without specifying how that judgment becomes a gate input. The hybrid gate pattern fixes that: the semantic layer's judgment is a technique-skill artifact; the gate's verdict is mechanical given the artifact.

In effect, the existing two-layer pattern is preserved — only the second layer's interface to the gate is now formalized.

### When fresh-eyes is not the (single-persona) anchor

The breakdown gate uses executability rather than fresh-eyes — the bounce-back mechanism *is* the semantic check; no separate review step is needed at breakdown closure.

The spec gate uses [[council-deliberation]] (the existing multi-persona spec review invoked via [[fbk-spec-review]]) rather than a single fresh-eyes pass. Same underlying discipline (cold, context-isolated review) applied with specialist personas.

The design gate uses fresh-eyes as the gate's semantic anchor. (An iterative multi-persona design deliberation during authoring was considered and deferred — see the decision spine.)

Code-review's semantic anchor is multi-source — both [[quality-scan-technique]] and [[test-review-technique]] produce artifacts the gate consumes. The pattern accommodates multiple anchors per gate when the phase's concerns are not single-axis.

### Related

- [[deterministic-verification-gates]] — the existing two-layer pattern this formalizes
- [[fresh-eyes-technique]] · [[council-deliberation]] — the cold-review patterns providing semantic anchors (fresh-eyes at intent/design, council at spec)
- [[quality-scan-technique]] · [[test-review-technique]] · [[grilling-technique]] — other technique skills
- [[design-manifest]] · [[test-integrity-locking]] — mechanical anchors used by specific gates
- [[stage-transition-protocol]] · [[mid-pipeline-entry]] — protocols that depend on gate verdicts
- [[fbk-scripts]] — where the mechanical portion is implemented
- [[external-feedback]] — the principle hybrid gates implement at every transition
- [[firebreak-sdl-workflow]]
