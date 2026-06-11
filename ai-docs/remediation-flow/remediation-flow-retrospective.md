# Remediation Flow — Retrospective

## Timeline

- **Stage 1 (Spec)**: started ~2026-05-13 (initial parent-spec draft committed from v0.2 wiki architecture); resumed and completed 2026-05-15 (closing-ambiguity pass + spec gate pass).
- **Stage 2 (Spec Review)**: 2026-05-15. Four council perspectives invoked in parallel; 42 findings synthesized into review document; threat-model determination = skip with rationale; review gate pass.

## Key decisions

Each numbered entry names the decision, the rationale in one line, and the stage that made it. The parent spec's `## Decisions resolved during scoping` section carries the full rationale per entry; this is the short index.

1. **Firebreak shape = filesystem absence via worktree sparse-checkout** (Stage 1 — initial drafting). Physical absence is structurally stronger than prompt-level discipline; tool-dispatch denial demoted to floor against absolute-path escapes.
2. **Per-module compile/test feedback = typed interface contracts paired with prose** (Stage 1 — initial drafting). Prep stage deterministically transforms typed contracts into stubs/mocks; keeps "greenfield-with-contract" claim honest.
3. **Prep stage inserted as a pipeline stage** (Stage 1 — initial drafting). Separates the deterministic transform (contract → scaffold) from the creative rewrite work; firebreak is physically engaged by prep, not declared by prose.
4. **Behavior inventory schema = two-tier** (Stage 1 — initial drafting). Mechanical `B-NNN` ID + agent-facing block (rendered downstream) + operator-facing block (traceability only, never rendered). Structural contamination firewall at the inventory layer.
5. **Feature 1 gate framing = operator judgment informed by per-capita measurement** (Stage 1 — initial drafting). Single-dev project cannot sustain a fully mechanical rubric; the discipline that matters is articulating criteria before seeing data and not tweaking mid-experiment.
6. **Cycle ID format = `NNN-<slug>`** (Stage 1 — closing-ambiguity pass, 2026-05-15). Sequence preserves machine sort order; slug gives at-a-glance recognition.
7. **Behavior IDs cycle-local only** (Stage 1 — closing-ambiguity pass). Cross-cycle continuity is speculative infrastructure; add an optional separate mapping artifact later if needed.
8. **Module IDs cycle-local; cycle-id prefix in path supplies global uniqueness** (Stage 1 — closing-ambiguity pass). Consistent philosophy with cycle-local behavior IDs.
9. **Cycle scope = operator-chosen** (Stage 1 — closing-ambiguity pass). Variable from a single module to a whole codebase; matches what Features 1, 1.5, and 8 already imply.
10. **Wave order = algorithmic topological default + operator override at move-list approval** (Stage 1 — closing-ambiguity pass). Algorithmic default minimizes operator labor on the common case; explicit override preserves authority on irregular cases.
11. **Feature 1 read-isolation = physical separation in fresh directory** (Stage 1 — closing-ambiguity pass). Manual analogue of Feature 3's worktree firebreak; validating at Feature 1 scale is itself evidence for whether Feature 3 is worth building.
12. **Caller-update timing = per-module incremental** (Stage 1 — closing-ambiguity pass). Each module's rewrite + its callers commits atomically before the next module begins; keeps the codebase out of long-lived "many modules in flight" states.
13. **Remediation branch model = operator-managed, per-module commits, squash-merge at operator discretion** (Stage 1 — closing-ambiguity pass). Firebreak's worktree lives off an operator-created remediation branch; merge-back to main/version is outside Firebreak's responsibility.
14. **Interface stance dropped from parent runtime-precision** (Stage 1 — closing-ambiguity pass). Original terms (`faithful` | `corrected`) carried unintended LLM priors; concept deferred to Feature 4's typed-contract authoring design with terminology-hygiene review.
15. **Project glossary as repo-wide infrastructure** (Stage 1 — closing-ambiguity pass). `GLOSSARY.md` at repo root, first-class artifact, referenced from `.claude/CLAUDE.md`. Entries accrete at point of use with hygiene review at spec-review or asset-authoring time.
16. **Move-record minimum schema (8 fields) pinned in parent runtime-precision** (Stage 1 — closing-ambiguity pass). Inferable from terms parent already commits to; Feature 4 child spec extends with per-type semantics.
17. **External evidence principle pinned in parent; categories deferred to Feature 5** (Stage 1 — closing-ambiguity pass). Pre-flight reads *about* the slop code, not the slop code itself; category enumeration is calibration work for Feature 5.
18. **Different-bad-pathology positive-signal nuance** (Stage 1 — closing-ambiguity pass). A meaningful drop in quantity/severity of slop-sightings is a positive signal even when distribution shifts to different AI-failure-mode shapes; elimination is aspirational.
19. **Pre-flight feature dependency = Intent Extraction ∧ Worktree Firebreak ∧ Rearchitecture** (Stage 1 — closing-ambiguity pass). Pre-flight's heuristics calibrate from all three features' actual experience; the dependency graph was incomplete and is now updated.

## Scope changes

- **Pipeline diagram restructured** (Stage 1 — closing-ambiguity pass). Original diagram showed a single CALLER-UPDATE WAVE block after the per-module loop; restructured to show per-module caller-update as the final step inside the per-module loop body, with per-module commits to the operator-managed remediation branch. The "single end-wave" reading was an explicit alternative; per-module incremental was chosen for tighter codebase-state guarantees.
- **Feature 7 renamed from "Caller-Update Wave Tightening" to "Per-Module Caller-Update Tightening"** (Stage 1 — closing-ambiguity pass). "Wave" carries firebreak-specific meaning (per-wave verification inside `/fbk-implement`); using it for the cross-module phase was a terminology collision and contributed to the original ambiguity.
- **GLOSSARY.md and CLAUDE.md changes added to scope** (Stage 1 — closing-ambiguity pass). The terminology-hygiene discussion surfaced during the "interface stance" grilling; rather than defer, the glossary infrastructure was bootstrapped as part of this Stage 1 (skeleton glossary at repo root + CLAUDE.md reference).

---

## Stage 1: Spec

### Clarifying questions that revealed ambiguity

The closing-ambiguity pass on 2026-05-15 surfaced ambiguities along three layers:

**Explicit open questions (project-level)** — these were already flagged in §6 of the parent spec at drafting time:
1. Cycle ID format
2. Behavior ID cross-cycle stability
3. Module ID namespacing

All three resolved in the same direction (cycle-local, with cycle-id prefix in path supplying global uniqueness for downstream IDs). The consistency was deliberate: each decision reinforced the next.

**Latent ambiguities surfaced by re-reading the spec with fresh eyes:**
4. "Cycle" was used everywhere as a load-bearing concept but never defined. Resolved by adding a Cycle and wave order subsection at the top of Architecture.
5. "Foundation-first wave order" was referenced multiple times without saying who determines it. Resolved as algorithmic-topological with operator override.
6. "Operator-enforced read-isolation" (Feature 1) was named but never operationally specified. Resolved as physical separation in a fresh working directory.
7. Caller-update wave timing was ambiguous between single end-wave and per-module incremental. Resolved as per-module incremental (the diagram and Feature 7 wording were updated).
8. Cycle-branch lifecycle (the "merge back" annotation) was undefined. Resolved as operator-managed remediation branch; Firebreak doesn't own merge-back.
9. "Interface stance: faithful | corrected" was listed in runtime-precision without definition; the user redirected to a broader concern about terminology hygiene and a repo-wide glossary. Resolved by dropping interface stance from the parent and bootstrapping `GLOSSARY.md` as repo-wide infrastructure.
10. Move-record schema was promised by an integration seam but never delivered. Resolved by pinning an 8-field minimum schema in runtime-precision.
11. "External evidence only" for pre-flight was named but never defined. Resolved by pinning the principle (pre-flight reads *about* the slop, not the slop itself) in the parent, deferring category enumeration to Feature 5.
12. "Different-bad-pathology" outcome class was undefined. Resolved with the volume-axis nuance — a meaningful drop in quantity/severity is a positive signal even with shifted distribution.
13. Feature 5 dependency mismatch between prose and dependency graph. Resolved in favor of the prose (depends on Features 2, 3, and 4).

**Editorial / stale-text fixes from the same pass:**
- Vision paragraph 2 still described the firebreak at "the tool-dispatch layer" (v0.2 architecture language) — rewritten to match the resolved worktree firebreak shape.
- Runtime-precision `B-NNN` and `ML-<cycle-id>` lines had stale TBD notes — updated with the resolved values.
- Runtime-precision `tier model in §5` cross-reference was broken (§5 of the overview is Cross-cutting concerns; tier model lives in Feature 5) — fixed.
- Cross-cutting `Behavior inventory ID stability` paragraph still framed cross-cycle stability as an open question — rewritten to reflect the cycle-local resolution.
- The three resolved project-level open questions were left dangling in §6; moved to Decisions resolved during scoping.
- Feature 3 §6 open questions (sparse-checkout cadence, CLAUDE.md per-stage selection) were over-broad; narrowed to what's actually still open after parent-spec resolutions.

### Scope inclusions / exclusions

**Included in the parent spec (this Stage 1 artifact):**
- Project vision and the load-bearing market hypothesis context
- Full architecture: pipeline shape (with per-module incremental caller-update), reuse-vs-new boundary table, integration seam checklist, runtime value precision (with cycle and wave-order definitions, move-record minimum schema, ID format conventions)
- Technology decisions: build on Claude Code + Firebreak SDL; worktree-based isolation; filesystem absence as primary firebreak; `/goal` only downstream of firebreak; structural analysis as meta-analysis; hypothesis-gating discipline; terminology hygiene + glossary infrastructure
- Feature map (8 features) with progress gates, fallback paths, and explicit hypothesis-gating per feature
- Dependency graph (revised structure)
- Cross-cutting concerns: firebreak as cross-cutting infrastructure, inclusion manifest format, per-stage CLAUDE.md rule, two-tier behavior inventory, typed interface contracts, defense-in-depth methodology, behavior inventory ID stability, retrospective field extensions, hypothesis-gating discipline, wiki cross-references, no new runtime
- Open questions §6 — Feature-N-child-spec deferred items only (project-level all resolved)
- Decisions resolved during scoping — full rationale for each resolved decision

**Deliberately excluded from the parent spec (deferred to child specs):**
- Feature 1 pre-experiment commitment doc filesystem location and structure (Feature 1 child spec)
- Tier model semantics (Tier 0/1/2/3 definitions) — Feature 5 child spec
- Recognition-over-recall UX mechanics — Feature 2 child spec
- Adversarial decomposition pass mechanism — Feature 4 child spec
- Inversion test fixtures — Feature 4 child spec
- Stakes-tier time budgets — Feature 4 child spec
- Council identity for intent / rearchitecture stages — Feature 2 and Feature 4 child specs
- Specific language toolchain selection for typed-contract → stub transform — Feature 3 child spec
- Specific structural-analysis tool selection — Feature 4 child spec
- Pre-flight evidence-richness category enumeration and weights — Feature 5 child spec
- `out-of-scope.md` and `decomposition-rationale.md` content structure — Feature 4 child spec
- Concept formerly known as "interface stance" — Feature 4 child spec (with `GLOSSARY.md` hygiene review)

**Out of project scope entirely (deferred indefinitely):**
- Market launch / external customer use of remediation flow
- AI-built codebase remediation as a productized service
- Cross-language structural analysis beyond Python and TypeScript

### Open questions deferred to later stages

All Feature-N child-spec items in §6 of the parent spec carry explicit "Resolve in Feature N child spec" rationale. Project-level open questions section is now empty. The Feature-N items are not blocking spec-review of the parent; they will block the corresponding child spec from passing its own gate.

### Author's notes

The Stage 1 work occurred in two distinct phases:

**Phase A (2026-05-13):** Initial parent-spec draft consolidated from three wiki sources (v0.2 architecture synthesis, phased delivery plan, source brainstorm across four sessions). Five major design decisions resolved during this phase, recorded as the original entries in Decisions resolved during scoping.

**Phase B (2026-05-15):** Closing-ambiguity pass plus structural and editorial cleanup. The skill's `Closing ambiguity` instruction (added between Phase A and Phase B) drove a systematic grill of remaining ambiguities. Two re-read passes were conducted: the first revealed eight latent ambiguities; the second confirmed no further substantive items after the writeback. Fourteen additional decisions resolved during this phase. The terminology-hygiene reframe and the `GLOSSARY.md` bootstrap were a notable departure from the planned scope of the pass — surfaced organically when the "interface stance" definition question revealed that the underlying issue was repo-wide.

The spec is hypothesis-gated. Stage 2 spec-review applies before any child spec begins. Feature 1 (the validation experiment) is the load-bearing gate for every feature past it.

---

## Stage 2: Spec Review

### Perspectives invoked

Four council perspectives in parallel, in discussion-style independent reads rather than full council interactive loop. The `/fbk-spec-review` skill is feature-spec-shaped; this project-level overview required adaptation. The council members were invoked directly via `Agent` rather than through `/fbk-council` to support batch findings synthesis (the council skill is interactive-loop-shaped).

- **Architect (`council-architect`)** — architectural soundness; SDL prompt framing emphasized pattern consistency with existing Firebreak, integration-point existence verification (the agent did read `/fbk-spec`, `/fbk-spec-review`, `/fbk-breakdown`, `/fbk-implement`, `/fbk-code-review`, `/fbk-council` skill files, `task-compilation.md`, `implementation-guide.md`, `retrospective-guide.md`, `review-perspectives.md`, and `~/llm-wiki/wiki/entities/goal-command.md`), and convention-visibility for child-spec consumption
- **Builder (`council-builder`)** — over-engineering / pragmatism; SDL prompt framing emphasized the spec's hypothesis-gating discipline and single-developer scope
- **Analyst (`council-analyst`)** — measurability; SDL prompt framing emphasized that operator-judgment looseness is acceptable for single-developer hypothesis-gated work but gate framings shouldn't be infinitely elastic
- **Security (`council-security`)** — threat modeling; SDL prompt framing emphasized contamination-as-threat-actor rather than classical adversarial security; explicit cue that the firebreak is structurally security-shaped but the threat differs

Skipped: Guardian (no AC or test plan at parent level), Advocate (user-impact concerns weak at project-overview stage; the operator is the spec author).

### Findings summary

**42 findings total** across the four perspectives.

| Perspective | Blocking | Important | Informational | Total |
|---|---|---|---|---|
| Architectural soundness | 2 | 7 | 1 | 10 |
| Over-engineering / pragmatism | 1 | 7 | 2 | 10 |
| Measurability | 2 | 8 | 2 | 12 |
| Threat modeling | 4 | 4 | 2 | 10 |
| **Total** | **9** | **26** | **7** | **42** |

**Cross-agent convergence themes** (multiple perspectives independently found related issues):
1. **Defense-in-depth taxonomy is inflated** — Builder F-B1 said three of six layers aren't real defenses; Security F-SEC-02/03/04 said the Semantic, Functional, and Post-hoc layers are mislabeled. Strong independent agreement that the six-layer claim is rhetorical rather than structural.
2. **Council ceremony is heavier than it earns** — Builder F-B2 said triple-council won't survive a real cycle; Security F-SEC-02 added that council members above the firebreak are themselves contaminated.
3. **Hypothesis-gating discipline is uneven** — Builder F-B10 (blocking) called out that the spec commits "no investment beyond Feature 1" while simultaneously bootstrapping repo-wide glossary infrastructure, three-council ceremony, and a six-layer defense taxonomy.

### Threat model determination

**Decision**: skip — no formal `remediation-flow-threat-model.md` artifact at this stage. Security perspective surfaced 11 findings (3 blocking) that carry project-level threat awareness without a separate document. Rationale: blocking security findings (F-SEC-01 above-firebreak contamination surface, F-SEC-02 contaminated council layer, F-SEC-05 worktree escape paths, F-SEC-06 tool-dispatch denial scope) are the load-bearing threat-model gaps — resolving them in parent spec or Feature 3 child spec is more useful than parallel artifact authoring. Authoring a formal STRIDE-style document before Feature 1 validates the firebreak hypothesis would be investment ahead of evidence.

### Test strategy review

**Skipped with rationale**. The test-reviewer agent evaluates test strategy at SDL checkpoint 1 against acceptance criteria. A project-level overview has no AC and no test plan — testing is owned per-feature in child specs. The first child spec to enter Stage 2 (Feature 1) will be the first artifact the test-reviewer evaluates for this project.

### Iteration count

Two iterations.
- **Iteration 1** (2026-05-15): review gate passed on first run after threat-model determination was recorded. 9 blocking findings surfaced.
- **Iteration 2** (2026-05-15 → 2026-05-16): all 9 blocking findings resolved through parent-spec edits (not accepted with rationale). Pure-editorial residue (A6 caller-update wave references) swept first; then each blocking finding grilled with the user one at a time, in detail, with recommendation and justification. Spec gate re-confirmed after each substantive edit. Review document's Resolutions section records per-finding outcome.

### Blocking findings + resolutions

All 9 blocking findings resolved through spec edits:

- **A1** (wave terminology): resolved by `GLOSSARY.md` entry defining "wave" as a generic concept; no rename.
- **A2** (path conventions for reused skills): resolved by pinning per-module artifacts under `.firebreak/remediation/<cycle-id>/modules/<module-id>/`; reused skills modified via cycle context (Feature 3 deliverable). Resolves A7 collaterally.
- **F-SEC-01** (above-firebreak contamination surface): resolved by moving per-module spec and spec-review INSIDE the firebreak; above-firebreak set reduced to three stages with named structural defenses.
- **F-SEC-02** (Semantic defense layer contaminated): resolved by restructuring defense-in-depth to two real defenses + Supporting Controls. Resolves F-B1, F-SEC-03, F-SEC-04 collaterally.
- **F-SEC-05** (worktree escape paths): resolved by new "Firebreak coverage" subsection enumerating six escape paths with default mitigations.
- **F-SEC-06** (tool-dispatch denial scope, Bash gap): resolved by same Firebreak coverage subsection adding allowlist-by-default tool-dispatch scope for in-worktree stages.
- **F1** (per-capita methodology): resolved by Feature 1 "Required commitment doc fields" pinning denominator (function count from named tool) and floor methodology (≥3 fresh modules with recorded model version + temperature).
- **F2** (meaningful volume drop threshold): resolved by same Required commitment doc fields mandating an operator-pinned numeric threshold with rationale, set after floor measurement but before rewrite review; pre-registered via git history.
- **F-B10** (hypothesis-gating discipline pre-judges Features 2–8): resolved by new top-level "Decisions revisitable after Feature 1" section enumerating revisitable (schema/ceremony) vs fixed (naming, cross-cycle, hypothesis) decisions.

Important and informational findings: 5 important findings resolved collaterally with blocking-finding fixes (A6, A7, F-B1, F-SEC-03, F-SEC-04). The remaining 21 important + 7 informational findings are deferred to either child specs (most are Feature-N-specific) or to a future revision pass after Feature 1's outcome lands. Each remaining finding's description in the review document carries an actionable resolution for the relevant child-spec author.

### Skill adaptation notes

The `/fbk-spec-review` skill is feature-spec-shaped. Three adaptations were made for project-level overview review:

1. **Spec file path** — skill reads `<feature-name>-spec.md`; this project's artifact is `<feature-name>-overview.md`. Adapted by pointing the council prompts directly at the overview path.
2. **Council invocation** — skill instruction says route through `/fbk-council`. That skill is an interactive synchronous loop with clarifying-questions phase, which doesn't fit batch-synthesis review. Adapted by invoking `council-architect`, `council-builder`, `council-analyst`, `council-security` directly via `Agent` in parallel.
3. **Test strategy review** — skill invokes `test-reviewer` agent for checkpoint 1; not applicable at project-overview stage (no AC, no test plan). Adapted by skipping with rationale recorded in both the review document and this retrospective.

These adaptations should inform a future improvement: either add explicit project-overview-mode handling to `/fbk-spec-review`, or document that project-overviews use a parallel review skill with different gate requirements. Captured as a candidate Firebreak improvement.
