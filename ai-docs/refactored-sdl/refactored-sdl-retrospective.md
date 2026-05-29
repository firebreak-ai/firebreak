# Refactored SDL — Retrospective

## Timeline

- Stage 1 (Spec): 2026-05-29 — started and completed; spec-gate passed.
- Stage 2 (Spec Review): 2026-05-29 — near-full council (Architect, Builder, Guardian, Analyst, Security) + independent checkpoint-1 test reviewer; review-gate passed; initial result FAIL (13 blocking). Revised; focused re-review (Architect, Guardian, test reviewer) confirmed all blockers resolved and test reviewer flipped to PASS. Iteration count: 2; result PASS.
- Breakdown prep: 2026-05-29 — at operator direction, dogfooded the new slice-declaration format into the spec (§Slices): twelve vertical slices with test-discipline modes, pinned interface contracts, and a four-wave dependency order (up to five parallel), all 24 ACs mapped, DAG acyclic. Reverses the earlier "format built, not used" stance; closes the review's "slices block empty / build-order edges hidden" findings. Spec-gate still passes (the current gate ignores the extra section).
- Stage 3 (Breakdown): 2026-05-29 — 35 tasks (13 test + 22 impl) across 4 waves; task-reviewer-gate + breakdown-gate pass; checkpoint-2 test review FAIL→PASS after one fix iteration (7 defects). Operator decision before compiling: full breakdown adapting around the current pipeline's code-task assumptions.

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

## Stage 3: Breakdown

**Task count / waves:** 35 tasks (13 test + 22 implementation) across 4 waves, compiled directly from the spec's §Slices block (the dogfooded decomposition drove the task structure rather than breakdown re-deriving it off the AC list). Wave 1 (foundation + prompt-asset slices + dispatcher, ~18 tasks parallel), Wave 2 (gate code + skill/doc reshapes), Wave 3 (code-review gate, which alone calls the restructured `verify_manifest`), Wave 4 (cross-cutting wiring + dogfood e2e). All 24 ACs carry a test+impl pair; DAG acyclic; dependencies confined to earlier waves.

**Compilation attempts:** one fix iteration. Deterministic gates (task-reviewer-gate, breakdown-gate) passed on the first assembly, but the independent checkpoint-2 test review returned FAIL with 7 defects (a self-fulfilling retrospective test, a missing grilling-log seam case, an internal-function import coupling in the spec-gate test, AC-08/AC-10 dropped from the code-review-gate test's covers, a stale COMMAND_MAP count, a loose ordering sentinel, and a verify_manifest signature mismatch). All seven fixed; re-review PASS, no regressions.

**Scope adjustments from compilation:** two small helper modules were added as compilation decisions so prompt-asset acceptance criteria had a real test surface: `fbk/precheck.py` (the capability-entry prerequisite probe, for AC-12) and `fbk/retro.py` (the retrospective-append helper, for AC-20). Both turn a "skill behaves correctly" claim into an importable function a unit test can exercise. Three signatures were pinned during compilation and reflected back into the spec's §Interface contracts (notably `verify_manifest(feature_dir, manifest_path=None) -> list[dict]`).

**Process note — pipeline mismatch confirmed (feeds self-improvement):** running the *current* breakdown pipeline on a spec written for the *new* one surfaced exactly the limitation this project fixes. The current breakdown gate demands a test+impl pair per AC and assumes judgment-free code tasks, but half the feature is prompt-asset authoring. Adaptations taken: the test-only cross-cutting slice got a real impl task (the SDL-index wiring); prompt-asset slices became Sonnet authoring tasks gated by shell tests; and two AC behaviors (capability-entry, retrospective-append) had to be given importable helper modules to be testable at all. This is direct evidence for the reshaped breakdown's slice-shape awareness and test-only-slice support. Tooling friction also noted: the `fbk-task-compiler` agent is read-only (Read/Grep/Glob), so its authored task content had to be harvested and written by a separate agent — a candidate for either granting it Write or changing the breakdown skill's agent wiring.

**Fresh-eyes catch (post-gate, pre-implement):** an operator-requested single cold reviewer over the task set found a gap the deterministic gates and CP2 both missed — the two headline phase skills, `fbk-intent` and `fbk-design`, had no authoring task. They fell between the intent/design *gate* slices and the technique-skills slice; the gates were satisfied because the gate code, guides, and agents were all tasked, and AC-01/AC-03 had test+impl coverage via the gate and dispatcher tasks — so nothing flagged the missing SKILL.md files. Also found: the capability-entry probe was built and unit-tested but never wired into any skill; two test↔impl contradictions (a phantom quality-scan cap, a divergent ordering sentinel) introduced during earlier fix rounds. Lesson for the reshaped breakdown: AC-level coverage checks do not guarantee asset-level completeness — a slice whose deliverables are a *set* of assets (skill + gate + guide + agent) can pass with a member missing. A cold completeness pass against the spec's asset-surface list, or an asset-surface checklist in the breakdown gate, would catch this class. Fixed: added 3 tasks (1 test + 2 impl), wired the probe into the four downstream phase skills, resolved both contradictions; gates and a re-verification confirm clean.

## Stage 4: Implementation

### Factual data

**Task execution**

- Total tasks: 38 (originally 35 at Stage 3 compile; +3 from the fresh-eyes catch in Stage 3 retrospective — `task-36` test for phase skills, `task-37` fbk-intent author, `task-38` fbk-design author).
- Distribution: 13 test tasks + 25 implementation tasks across 4 waves (Wave 1: 6 test + 12 impl = 18; Wave 2: 6 test + 10 impl = 16; Wave 3: 1 test + 1 impl = 2; Wave 4: 1 test + 1 impl = 2).
- Result: 38/38 complete, zero escalations, zero parked, zero superseded.
- Model routing: 7 Haiku tasks (5 test + 2 impl); 31 Sonnet tasks. All Haiku tasks succeeded without escalation.
- Wave width: peak parallel = 12 (Wave 1 impl step); team spawned 12 fresh `fbk-implementer` agents per the implementation-guide "fresh agent per task" rule.

**Verification gate results**

| Wave | Python pass | Shell pass | Regressions | Wave-fixes |
|---|---|---|---|---|
| Baseline | 118 | 62 | — | — |
| Wave 1 | 139 (+21) | 65 (+3) | 2 | 2 |
| Wave 2 | 204 (+65) | 66 (+1) | 2 | 2 |
| Wave 3 | 217 (+13) | 66 (+0) | 0 | 0 |
| Wave 4 | 217 (+0) | 66 (+0) | 1 | 1 |

- Final test surface: 217 python pass + 66 shell pass. Baseline preserved at every wave boundary.
- Wave 4 also adds `tests/installer/test-refactored-sdl-install.sh` (16 assertions), which is deferred — the installer downloads from upstream GitHub, so 14/16 assertions cannot pass until the assets are published. The 2 infrastructure assertions (no `assets/` leaks in installed tree; uninstall cleans up) pass locally.

**In-session retry count**

- TaskCompleted hook rejections resolved without escalation: zero observed. No teammate triggered the hook-rejection retry path.

**Task sizing accuracy**

- All 38 tasks completed within their declared file scopes. Two implementation tasks expanded scope as side-fixes that the team lead accepted:
  1. `task-34` (code_review gate impl) also patched `test_hash.verify_manifest` — fallback filename resolution when manifest was created with subdir scope but verified at parent. Flagged in summary; accepted because the patch was strictly additive and unblocked the gate test.
  2. `task-13` (installer e2e test) corrected 10 path leaks in `assets/fbk-docs/fbk-context-assets.md` (7) and `assets/skills/fbk-council/SKILL.md` (3) — adversarial grep over its own forward guard. Accepted because the fixes were the *intended* effect of the new sentinel.

**Wave-fixes by team lead**

Five small team-lead-level edits to baseline tests/assets that were rendered stale by deliberate-by-design changes in this wave's scope:

1. `tests/sdl-workflow/test-test-reviewer-extensions.sh` — retired 3 CP5 sentinels (mutation-testing criteria removed by spec).
2. `assets/skills/fbk-code-review/SKILL.md` — routed `capability-entry.md` so the new leaf was not orphaned in the wave-1 intermediate state.
3. `tests/sdl-workflow/test-hash-gate.sh` — updated to per-entry object schema (the task-26 schema rewrite).
4. `assets/skills/fbk-breakdown/SKILL.md` — typo fix on slice-shapes index route.
5. `tests/sdl-workflow/test-council-skill-structure.sh` — updated 3 dispatch-path sentinels to installed-path form (chained from task-13's path-class-1 correction).
6. `assets/skills/fbk-implement/SKILL.md` — "phase five" → "phase six" (task-35 surfaced the numbering inconsistency; the gate text said five but the documented sequence is six).

### Upstream traceability

- Stage 2 review iterations before advancing: 2 (initial FAIL with 13 blockers → revision → focused re-review PASS).
- Blocking findings count: 13 (Stage 2). All 13 led to spec revisions (none deferred).
- Stage 3 compilation attempts before gate passed: 2 attempts (initial CP2 FAIL with 7 defects → fix iteration → PASS). The fresh-eyes catch was a *post-gate* find that added 3 tasks (1 test + 2 impl) — not a compilation re-attempt, but a class of completeness defect the deterministic gates were structurally blind to (AC-coverage checks do not guarantee asset-surface completeness).

### Failure attribution

No escalations triggered, so root-cause classification of the **escalation** kind is not applicable.

Failure-adjacent observations (root-cause classification of issues caught by per-wave verification rather than by individual task failures):

- **Wave 1, capability-entry orphan**: Stage 3 compilation gap. Task-25 created `capability-entry.md` as a routed leaf, but no Wave 1 task included a route to it from any installed asset. The intended router (the phase skills) were built only in Wave 2. The breakdown left a one-wave-wide window where the leaf was unreferenced; the team-lead wave-fix routed it from `fbk-code-review` SKILL.md (a legitimate routing site for the mid-pipeline-entry probe). Class: **compilation gap** — the leaf-routing dependency was not made an in-wave invariant.
- **Wave 1, test-test-reviewer-extensions sentinels**: spec gap, but deliberate. The spec deletes CP5 mutation-testing criteria from the test-reviewer agent (task-20). The 3 affected sentinels in a baseline shell test were testing the now-retired criteria. The spec did not enumerate "baseline tests rendered stale by this refactor"; treating the retirement as expected and trimming the sentinels is the consistent action. Class: **spec gap** — the refactor's downstream test impact was not enumerated.
- **Wave 2, test-hash-gate shell-test schema**: same class as above. Task-26 explicitly rewrites the manifest schema (flat `{path: hash}` → per-entry object `{sha256, slice, test-discipline}`). The shell sentinel asserted on the old schema. The team-lead update was mechanical. Class: **spec gap** — same downstream-baseline issue as the test-reviewer case.
- **Wave 2, slice-shapes routing typo**: implementation error. Task-32's fbk-breakdown skill update wrote `slice-shapes/slice-shapes.md` instead of `slice-shapes.md` for the index route (one directory level too deep). Caught by `test-reference-integrity` at wave verification. Class: **implementation error** — instruction was clear, agent wrote the wrong path.
- **Wave 3, test_hash.verify_manifest scope mismatch**: spec gap (mild). The task-26 `verify_manifest(feature_dir)` contract assumed create and verify share a base directory. Task-34's code-review-gate calls `verify_manifest(feature_dir)` against manifests created with a `tests/` subdir scope (the fixture intentionally avoids sweeping `test-review-final.md` into the manifest). The contract did not pin the cross-scope case. Resolved with a fallback filename search; flagged in task-34's summary as scope-overlap with task-26. Class: **spec gap** — the cross-scope verification contract was not specified.
- **Wave 4, installer e2e test cannot pass locally**: known limitation, not a gap. The installer (`installer/install.sh`) downloads from upstream GitHub; local Wave 1/2 work cannot be exercised by it until published. The 14 failing assertions are the intended red state until upstream sync. Deferred; the 2 infrastructure assertions (no path leaks, uninstall cleanup) pass and form the local-verifiable subset. Class: **process gap** — the test exercises a remote operation; either a local-install harness or an explicit "deferred until upstream" mark would have made this less surprising at wave verification.
- **Wave 4, "phase five" framing**: spec gap. Task-35's completion gate text used "phase five" for the implement skill framing, but the six-phase pipeline name (intent → design → spec → breakdown → code-review → implement) puts implement at position six. The implementing agent flagged the numbering and the team lead corrected to "phase six." Class: **spec gap** — the gate text drifted from the numbering convention defined elsewhere in the same task.

### Stage 4 process notes

- **Concurrent execution with fresh agents per task delivered.** All 12 Wave 1 implementation tasks ran simultaneously without scope-overlap conflicts. Stage 3's non-overlapping-files guarantee held.
- **Idempotency safeguard.** Several agents received their task assignment after the first turn had already completed the work (mailbox re-delivery); they correctly identified the completed state and reported no further action needed. No duplicate work was performed.
- **Routing leaks were the dominant defect class.** Three of the five wave-fixes (capability-entry orphan, slice-shapes typo, council-test path form) involved leaf references that drifted from the installed-path convention. The path-class-1 invariant from the spec (installed assets reference installed paths) is correct; what's missing is *automated enforcement* — a wave-boundary lint over modified assets would have caught all three. The task-13 forward guard (Part 3 of `test-reference-integrity`) is exactly this discipline retrofitted as a sentinel.
