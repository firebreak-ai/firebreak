# Refactored SDL — Retrospective

## Timeline

- Stage 1 (Spec): 2026-05-29 — started and completed; spec-gate passed.
- Stage 2 (Spec Review): 2026-05-29 — near-full council (Architect, Builder, Guardian, Analyst, Security) + independent checkpoint-1 test reviewer; review-gate passed; initial result FAIL (13 blocking). Revised; focused re-review (Architect, Guardian, test reviewer) confirmed all blockers resolved and test reviewer flipped to PASS. Iteration count: 2; result PASS.
- Breakdown prep: 2026-05-29 — at operator direction, dogfooded the new slice-declaration format into the spec (§Slices): twelve vertical slices with test-discipline modes and a six-wave dependency order (up to four parallel), all 24 ACs mapped, DAG acyclic. Reverses the earlier "format built, not used" stance; closes the review's "slices block empty / build-order edges hidden" findings. Spec-gate still passes (the current gate ignores the extra section).

## Key decisions

1. **One consolidated feature spec** rather than a project overview + per-feature specs (Stage 1). Rationale: operator's call; the consolidation keeps decomposability because slice declarations inside the spec are where breakdown carves the work. The recommendation had been project-level given the ~22-asset scope, but the single-feature-directory layout and the markdown-asset nature made one spec workable.
2. **`fbk-grilling` is a new firebreak asset adapted from Matt Pocock's grill-me skill** (Stage 1). Rationale: firebreak must ship and install its own asset; the external `/grill-me` is itself an adaptation of Pocock's skill and carries a source-link credit, so `fbk-grilling` sits in the same lineage and must carry the same attribution (name + GitHub source link).
3. **New mechanical gate checks are additive and backward-compatible** (Stage 1). Rationale: the spec-gate slice checks fire only when a slices block is present; breakdown/test-hash/code-review additions preserve existing tests — satisfying the backward-compatibility requirement for in-flight specs.
4. **This spec is written in the current SDL format, not the new slice-declaration format it designs** (Stage 1). Rationale: it is consumed by the current breakdown and gated by the current spec-gate; the new format is a deliverable, not the medium.
5. **Prompt-asset behavior is verified by gate unit tests + shell integration tests + manual end-to-end UV steps, not fabricated unit tests** (Stage 1). Rationale: skills/agents/docs have no unit-test surface; honesty over a generic "add unit tests."
6. **Durable docs live at `docs/decisions-log.md` and `docs/architecture-overview.md`** (Stage 1). Rationale: operator-confirmed; sets the installer manifest entries and the routing references in the intent and design skills.
7. **Quality-scan attribution left as pattern-credit, not a "skill adapted from" line** (Stage 1). Rationale: the design credits a described Pocock *practice* for the top-five scan, not a specific skill we clone — a weaker form of borrowing than the grill-me case; operator declined adding a stronger attribution.

## Scope changes

- Initial recommendation was project-level (overview + feature map + per-feature specs). Operator chose a single consolidated feature spec covering the whole refactoring. No behavioral scope was added or removed by this choice — only the document structure.

## Stage 1: Spec

**Clarifying questions that revealed ambiguity:**

- *Spec scope* — project overview vs. one consolidated feature spec vs. feature-map-only. Resolved to one consolidated feature spec by operator choice, against the standing recommendation of project-level treatment.
- *Grilling provenance* — whether `fbk-grilling` duplicates a Pocock skill the way the local grill-me does. Investigation found the local `/grill-me` is explicitly "adapted from Matt Pocock's grill-me skill" with a source link; this revealed `fbk-grilling` is in the same lineage and drove the source-link attribution requirement (AC-19). The quality-scan, by contrast, credits a described practice, not a cloned skill.
- *Durable-doc locations* — confirmed `docs/decisions-log.md` and `docs/architecture-overview.md`.

**Scope inclusions:** all ~22 assets in one spec — two new phase skills (intent, design), four technique skills (grilling, fresh-eyes, quality-scan, test-review), three new agents, two modified agents, three modified skills (spec, breakdown, code-review), two doc-only reframed skills (spec-review, implement), new/modified gate scripts (intent, design, spec, breakdown, test-hash, code-review), the concept docs, the always-on disciplines into CLAUDE.md and the authoring rules, the durable-artifact discipline, and the installer manifest wiring.

**Scope exclusions (standing non-goals, carried from the PRD):** hooks, state machine, config layer, audit log; AST schema-extraction tooling; a project-memory system beyond plain markdown; council-agent migration; mutation sampling; complexity-classification eval/tier tags. Plus: no rewrite of existing gate behavior beyond the named additive checks, and no retroactive application of the new format to in-flight specs.

**Open questions deferred to later stages:**

- The exact per-slice work-unit handoff artifact from the spec's slices block to the parallel breakdown sub-steps — deferred to the breakdown reshaping work, to be pinned in `task-compilation.md` during implementation. (Stage 2 escalated this: it determines whether the breakdown gate is extended or rewritten, so it should be resolved in the revision, not deferred.)
- Whether the code-review gate logic extends `review.py` or lands in a new `code_review.py` — Stage 2 recommends resolving to `code_review.py` now to avoid dragging the council's `review-gate` tests into the blast radius.

## Stage 2: Spec Review

**Perspectives invoked:** Architect, Builder, Guardian, Analyst, Security (near-full council, dropping Advocate — the operator is the user and Builder covered scope creep), plus the independent checkpoint-1 test reviewer. Classification rationale: high-stakes (the change reshapes the SDL the project itself runs on — dogfooding) with multiple signals firing (new boundaries, new gate code, an unusual prompt-asset testing story, soft success metrics, agent-consumed artifacts).

**Result:** FAIL — 13 blocking, 11 important, 8 informational. The independent test reviewer also returned FAIL (5 blocking defects, all corroborating the Quality findings). Review-gate passed structurally. Threat-model determination: No (internal single-operator tooling; sole trust boundary is artifact prompt-injection, already a tracked finding).

**Blocking findings (themes), to resolve in revision:**
- Gate-code "extend" claims that are actually rewrites: the test-lock manifest is a flat auto-discovered scan product, not a per-entry curated record (AC-07); the test-reviewer agent is checkpoint-keyed and its contract-widening is a refactor.
- Internally contradictory gate integrations: the breakdown gate's AC-coverage invariant fights the cross-cutting (test-only) and contract-preserving (impl-without-new-test) slice shapes while the spec claims the checks are "preserved"; the backward-compat hinge was applied only to the spec gate.
- Incomplete caller enumeration for the `review-gate` symbol (missed the `fbk-breakdown` runtime caller, the `validate_review` import, and the code-review shell tests); the conditional deferral violates the spec schema.
- A phantom integration point: "register every asset in the installer manifest" — the installer auto-discovers via `find`; the only real registration is `COMMAND_MAP`.
- A path-class contradiction: durable docs at `docs/` are referenced by installed skills but sit outside the install boundary the spec's own constraint governs.
- An undefined, load-bearing "no-shadow-tests" check that conflicts with `verify_manifest`'s existing UNEXPECTED-fails behavior.
- Missing injection-detection parity for the two new gates (they read the furthest-upstream agent-authored artifacts).
- Testing coverage holes: AC-18 has no test/UV; the AC-09 capability-entry test only checks "no hard failure," not content; AC-14's preserve-prior-stages is untested; UV-7/8/9 are unmapped; the grilling-log seam has no end-to-end test; the spec-gate regression test can't catch the regression it targets.

**Spec revisions:** revision 2 cleared all 13 blocking findings — gate "extend" claims reclassified as rewrites (test-lock manifest, test-reviewer agent); breakdown/test-hash/code-review gate plans made shape-aware and backward-compatible behind a slice-metadata hinge; full `review-gate` caller enumeration; the phantom installer-manifest language removed (the installer auto-discovers); a third path class defined for durable docs; injection-detection parity added via a shared `fbk/injection.py`; the testing holes (AC-18/now-AC-19, AC-09/now-AC-12, AC-14/now-AC-20, the UV mappings, the grilling-log seam, the spec-gate regression) closed. Operator decisions taken during the revision: cheap-invariant slice enforcement only; durable docs at `docs/`; threat-model skip. The focused re-review then closed a final set of edges (code-review ordering sentinel test, shadow-test negative case, omitted impacted shell test, structured `verify_manifest` return).

**Convergence note:** three independent perspectives (Architect, Builder, Guardian) and the test reviewer landed on the same core defects (test-lock manifest rewrite, breakdown-gate shape conflict, caller enumeration). High convergence was a strong signal these were real, not stylistic — and is the main argument for the near-full council on a high-stakes dogfooding change.

**Process note:** the consolidated single spec made the review heavy (one FAIL with 13 blockers across ~22 assets) but the slice-metadata backward-compat hinge and the cheap-invariant enforcement choice kept the resolution tractable. A project-level decomposition would have spread these findings across several smaller reviews.
