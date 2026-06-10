# Retrospective — interface-contracts

## Timeline

- Stage 1 (Intent): started 2026-06-07, completed 2026-06-09.
- Stage 2 (Design): started 2026-06-09, completed 2026-06-09.
- Stage 3 (Spec): started 2026-06-09, completed 2026-06-09.
- Stage 4 (Spec Review): started 2026-06-09, completed 2026-06-09 — initial result fail (six blocking findings); operator chose to revise immediately; all six resolved and test-reviewer re-review returned accepted; final result pass.
- Stage 5 (Breakdown): started 2026-06-09, completed 2026-06-09 — 11 tasks, 3 waves; two spec/design gaps bounced back and resolved at the gate-checks source of truth; a latent breakdown-gate regex bug found and fixed; both gates pass and the checkpoint-2 test review returned accepted.
- Stage 6 (Implementation): started 2026-06-09, completed 2026-06-09 — all 11 tasks complete and verified across 3 waves; one task escalated once (gate wiring, resolved on the second attempt after discovered corrective work); three latent defects surfaced and were fixed during integration; full suite green except four documented pre-existing failures (merge blocker, not feature regressions).

## Key decisions

1. **Two sibling SDL features, no parent** (intent). The brainstorm work-order queued `interface-contracts` and `wave-commit-model` as siblings closing different trust gaps (carry-through vs agreement). Coupling them would be the over-scoping pattern the brainstorm diagnoses. This feature scoped to carry-through only.
2. **Reconciliation surfaces at spec review** (intent grilling). The deterministic gate handles the design-says-more failure mode; spec review (LLM judgment) handles the spec-says-more and renames; temporal drift after spec gate passed is operator-handled with no automatic re-trigger mechanism.
3. **Spec-side escape hatches with free-text rationale** (intent grilling). `## Excluded contracts` for design-enumerated contracts the spec drops; `## Uncovered acceptance criteria` for ACs intentionally without a contract. Symmetric pattern, both gate-enforced for non-empty rationale. Design pages are not back-updated — they are ephemeral scaffolding deleted at squash-merge.
4. **AC coverage check added as 8th deterministic gate check** (intent grilling). Every `AC-NN` in the spec's acceptance criteria must be covered by some contract's `covers:` list OR documented in `## Uncovered acceptance criteria` with rationale.
5. **Three-value `design-ref` scheme** (intent grilling). Path/anchor for design-enumerated entries; `pre-existing` for blast-radius brownfield entries; `none` reserved for the genuinely-absent case. Semantically distinct cases preserve downstream-agent signal.
6. **Bootstrap exemption for this feature itself** (intent fresh-eyes round 3). This feature's own design and spec are exempt from the new gate checks. The standardized shape of `design/contracts.md` is itself this feature's design deliverable; the gate ships as part of this feature's implementation. Enforcement begins on the next feature after this one ships.
7. **Blast radius is agent-computed via reference tooling, not author judgment** (design grilling, operator override). The spec-authoring agent derives the dependent set ("find all callers/importers") deterministically from the declared changed modules; the human is never involved and it is not left to soft judgment. The gate verifies the entries' shape, not the set's completeness. Per-language completeness verification is a deferred follow-on because the gate is language-blind and runs in arbitrary target projects.
8. **Separate identifier namespaces, `IF-D-NN` and `IF-S-NN`** (design grilling, operator override). Design mints `IF-D-NN`; spec mints `IF-S-NN`; carried contracts keep the design id verbatim. Collision is structurally impossible, replacing the intent-era flat `IF-NN` sketch and the deferred collision policy.
9. **Four new checks live in a new `contracts.py` gate module** (design). Mirrors the prior decision that put the code-review gate in its own module; keeps `spec.py` focused and the new checks testable in isolation.
10. **Design contracts page parsed via level-two `IF-D-NN` headings** (design). Reuses the spec gate's existing heading-based parsing; prose mentions of ids do not count.
11. **Seam coverage is a case-insensitive substring heuristic** (design). The PRD already declares this check an approximation; no new `components:` field is added. The error message states the heuristic nature.
12. **Contract-drift detection extends the architecture reviewer's brief** (design). A semantic check belongs in the review layer, not the deterministic gate; no gate code change, and that reviewer is effectively always engaged for features with contracts.
13. **Gate activation is unconditional** (spec grilling, operator decision). The four checks run on every feature spec rather than behind a backward-compat hinge. The operator chose strongest enforcement over the recommended composite hinge, accepting that every in-flight spec must carry the section (one sentence suffices) and a `design/contracts.md`, and that the existing `test_gates_spec.py` pass-fixtures are migrated to match.
14. **New format guidance lives in two routed leaves, not folded into the guides** (spec, progressive-disclosure rule). The detailed entry schemas apply only when an author has contracts to write — a sub-condition — so they belong in separately-routed leaves (`design-contracts-standard.md`, `interface-contracts-format.md`) gated by that condition. The guides keep only the always-required minimal instruction plus a conditional route. Two leaves, not one, because the design-page and spec-section schemas differ and are reached by different parent routes.
15. **This spec dogfoods the new sections** (spec). It carries the five design contracts plus one spec-minted blast-radius entry under `## Interface contracts`, and routes the four documentation/process criteria through `## Uncovered acceptance criteria` — the first worked spec-layer example of the format.
16. **Breakdown uses legacy task.json, not slice-aware mode** (breakdown). The gate's slice-aware path requires a pre-lock hash manifest over tests that do not exist until implementation, so it cannot be honestly satisfied at breakdown; the established practice (every prior feature) is legacy mode. The slice disciplines still shaped task authoring.
17. **The empty-section message and the `design-ref` rule pinned at the gate-checks source of truth** (breakdown, operator decisions). Two underspecifications both task-authoring agents bounced back: an unpinned present-but-empty teaching string, and a self-contradictory `design-ref` validity rule. Resolved to the operator-approved wording and to "valid when `pre-existing`, `none`, or contains `/` or `#`."
18. **The latent breakdown-gate AC-extraction bug fixed in place** (breakdown, operator decision). The gate's acceptance-criteria regex was not line-anchored and mis-captured an inline section mention; fixed to match the sibling gates. Follow-ups: reinstall to update the read-only installed copy, and add a regression test plus changelog entry.

## Scope changes

- **Initial scope:** seven deterministic gate checks (per Session 2 brainstorm work-order).
- **Final scope:** eight deterministic gate checks. AC coverage added during intent grilling (key decision 4) as a structural mirror of the existing slice→behavior coverage pattern.
- **Initial scope did not name escape hatches.** Intent grilling decisions 3 and 4 introduced `## Excluded contracts` and `## Uncovered acceptance criteria` as structured spec-side bypasses, both rationale-enforced by the gate.
- **Blast-radius enumeration moved from author judgment to agent-computed (design).** The intent phase deferred the "touched module" bound as an open question; design resolved it by making the spec-authoring agent compute the dependent set with reference tooling and limiting the gate to shape verification. This narrows the gate's responsibility (no completeness check) and adds a deferred follow-on (per-language completeness verification).
- **Identifier scheme changed from flat `IF-NN` to split namespaces (design).** The intent PRD's single-sequence sketch is superseded; the spec phase reconciles the PRD prose and behavior inventory to the `IF-D-NN` / `IF-S-NN` form.
- **Asset surface grew by two routed leaves (spec).** The design pages `contracts-standard.md` and `spec-sections.md` are ephemeral, so the spec phase added permanent installed homes for their guidance — `design-contracts-standard.md` and `interface-contracts-format.md` — rather than folding the detail into the always-loaded phase guides.
- **Gate activation hardened from "begins on the next feature" to unconditional (spec).** The operator chose to run the four checks on every feature spec, which converts the bootstrap exemption into a test-fixture migration: the existing `test_gates_spec.py` pass-fixtures gain the no-contracts section and a `design/contracts.md`.
- **Unconditional-activation blast radius was wider than the spec captured (implementation).** Beyond the planned `test_gates_spec.py` fixtures, the live gate also broke three CLI-driven shell gate-tests and required a no-contracts migration of four `tests/fixtures/specs/*-spec.md` files plus a shared `design/contracts.md`. A circular import forced extracting two shared text helpers into a new neutral module (`fbk/gates/sections.py`). None of this was in any task's declared scope — all discovered and fixed during Wave 2 integration.

## Stage 1: Intent

### Clarifying questions that revealed what the work is and why

Two waves of question-resolution:

**First wave — open-question interview before grilling** (operator answered in conversation, not in formal grilling log):
- Reconciliation surfaces at spec review (basis for grilling Q1).
- `## Interface contracts` section required even when empty; single-sentence rationale satisfies.
- Identifier inheritance: spec carries design's `IF-NN` numbers, never renumbers.
- Spec enumerates full blast radius on touched modules (not just new/changed), so breakdown can scope tests.
- `design/contracts.md` required for every feature; single-sentence file is sufficient when no contract changes.

**Second wave — formal grilling via `/fbk-grilling`** (logged in `grilling-log-intent.md`):
- Reconciliation failure-mode coverage (Q1) — confirmed gate + spec review covers modes 1 and 2; mode 3 (post-gate or mid-stream drift) is operator-handled.
- Deliberately-dropped contracts (Q2) — resolved as `## Excluded contracts` spec-side with free-text rationale; gate error message states two resolution paths.
- Covers semantics / AC coverage (Q3) — resolved as 8th deterministic gate check; `## Uncovered acceptance criteria` is the sibling escape hatch.
- `design-ref` brownfield blast-radius (Q4) — resolved as three-value scheme (path/anchor, `pre-existing`, `none`).

### Artifacts produced

- `prd.md` — 10-section PRD with eight functional requirements (B-001..B-010) and three deferred open questions.
- `behavior-inventory.yaml` — ten B-NNN behaviors with bidirectional consistency to the PRD.
- `grilling-log-intent.md` — four `### `-headed decision blocks with `Confirmed:` reflect-back lines per the grilling protocol.
- `fresh-eyes-intent.md` — reduced report; `## Critical` is empty after four rounds of revision; Reduction record documents the disposition of every round-4 critical for audit.

### Fresh-eyes process notes

Four rounds of fresh-eyes ran before the gate passed. Each round flagged criticals; the PRD was revised between rounds.
- Round 1: foundational ambiguities (agreed shape undefined; conflicting field lists; marker conflation; blast radius unbounded; AC/seam conventions undefined). Major revision.
- Round 2: tighter criticals (`IF-NN` form undefined; "carry" not operationally defined; path not qualified). Surgical revision.
- Round 3: bootstrap exemption surfaced; hollow-carry tradeoff stated explicitly; identifier-collision deferred. Substantial revision.
- Round 4: gate-path resolution, design-anchor parse format, seam-coverage rule, blast-radius completeness. Surgical revision; reduction step + tightening pass after.

The cold-reader review pattern surfaces a new layer of ambiguity each round because each fix exposes the next-deeper question — the onion-peeling effect. Knowing when to stop is operator judgment. After round 4, remaining findings were design-altitude rather than intent-altitude, so the next round was called off in favor of a tightening pass that compressed dense paragraphs in the Functional requirements section.

### Open questions deferred to later stages

- **Bound of "touched module" for blast-radius enumeration** (B-002) — deferred to design.
- **Mechanical rule for seam-coverage matching** (B-008) — deferred to design.
- **Identifier-collision policy** when design is re-edited after spec mints entries (B-001) — deferred to design.

## Stage 2: Design

### Module shape and contracts proposed

The design splits into five concerns, each owning one invariant: the normative schema for the design contracts page (`contracts-standard.md`), this feature's own worked instance of it (`contracts.md`), what the spec author writes (`spec-sections.md`), what the gate reads (`gate-checks.md`), and the edits to neighboring assets (`skill-and-review-changes.md`), plus an `overview.md` for the cold reader.

The code lands in a new `fbk/gates/contracts.py` module exporting four checks — structural completeness, design-anchor walk, AC-coverage, and light seam-coverage — that `spec.py` imports and calls in its feature-scope branch. The data crossing that boundary is the spec text (all four checks) plus the feature directory (design-anchor only) inbound, and a list of failure strings outbound. This feature's own contracts (`IF-D-01`..`IF-D-05`) are the first worked instance of the standard, consistent with the bootstrap exemption.

### Decisions appended to the durable decisions log

Six decisions were appended to `docs/decisions-log.md` (all 2026-06-09, status accepted): blast-radius derivation via reference tooling; separate `IF-D` / `IF-S` identifier namespaces; the new `contracts.py` gate module; heading-based parsing of the design contracts page; the seam-coverage substring heuristic; and contract-drift elevation through the architecture reviewer's brief. The decision-by-decision grilling record is in `grilling-log-design.md`. Two of the six overrode the architect's first recommendation — blast radius and identifier collision — both pushing the feature harder toward deterministic enforcement over soft judgment.

### Decomposition rationale

Vertical slices by ownership boundary: the standard, the worked instance, the author-facing format, the gate algorithm, and the neighboring-asset edits each live on their own page, so a change to the spec format does not force an edit to the gate algorithm page and vice versa.

### Fresh-eyes process notes

One cold review round ran before the design gate. It surfaced four critical observations: the PRD-vs-design identifier-scheme divergence (no reconciliation note), a missing `re.MULTILINE` on the design-anchor regex, a "five other fields" phrasing that read as a field-count contradiction, and a dead `feature_dir` parameter on the structural check. It also surfaced two substantive algorithm gaps that the gate's own checks would otherwise have missed: AC-coverage counted ACs mentioned anywhere in the contracts body rather than only in `covers:` lists, and the empty-rationale rule for the two escape-hatch sections was asserted but never implemented in any check. All were fixed; the remaining observations were cosmetic or correct-by-design and are recorded with their disposition in `fresh-eyes-design.md`.

### Open questions deferred to later stages

- **Per-language blast-radius completeness verification** — a follow-on capability; this feature's gate verifies shape only.
- **Deep field-level validation of the design contracts page itself** (e.g., rejecting an empty `invariants` in `design/contracts.md`) — not performed by the design-anchor walk; a possible follow-on.
- **PRD and behavior-inventory reconciliation to the `IF-D-NN` / `IF-S-NN` scheme and the exact no-contracts sentence** — to be done at the spec phase.

## Stage 3: Spec

### Clarifying questions that revealed ambiguity

The design package was unusually complete — function signatures, parse rules, exact error wording, and integration points were all pinned, and the six design decisions were already settled in `grilling-log-design.md`. So the spec phase narrowed to three genuine "how" decisions, two of which exposed gaps the design pages left open:

1. **Where the new format guidance lives.** The design pages that define the formats (`contracts-standard.md`, `spec-sections.md`) are ephemeral — deleted at squash-merge — yet future authors need a permanent installed home. Initial framing offered fold-into-guides versus new-leaves; the operator redirected to the progressive-disclosure rule ("every instruction in a loaded asset must apply every time the asset loads"). Applying it resolved the question cleanly: the detailed schemas apply only when an author has contracts to write, so they belong in two separately-routed leaves, with the guides keeping only the always-required minimal instruction plus a conditional route.
2. **The activation gap.** The design pages call the four checks unconditionally in `spec.py`, but the structural check treats a missing section as a failure — which would break every existing spec and `test_gates_spec.py` fixture the moment the gate runs, contradicting the PRD's "enforcement begins on the next feature." The design never specified an activation condition. Surfaced with a recommended composite hinge (section OR design page present); the operator instead chose unconditional activation for strongest enforcement, accepting the fixture migration as the cost.
3. **Whether this spec dogfoods the new sections.** Bootstrap-exempt and therefore optional; the operator chose to dogfood, making the spec the first worked spec-layer example.

### Scope inclusions and exclusions

- **Included beyond the design's named asset surface:** two new routed leaves (`design-contracts-standard.md`, `interface-contracts-format.md`) carrying the format detail the ephemeral design pages held; the migration of existing spec-gate test fixtures forced by unconditional activation.
- **Carved into six slices** by ownership boundary: the gate module, the spec-gate wiring (the one contract-evolving slice, carrying the fixture migration as its retired-tests entry), three independent documentation slices (one per leaf/guide pair plus the review brief), and a cross-cutting dogfood-verification slice. Ten of the apparent inter-slice dependencies are pinned-contract references, not build-order edges, so wave 1 runs four slices in parallel.
- **Excluded (held to siblings or follow-ons):** the wave/commit model; semantic signature comparison in the deterministic gate; design-page snapshotting; per-language blast-radius completeness verification.

### Open questions deferred to later stages

None at the spec gate. One reconciliation item is recorded as a dependency rather than an open question: the installed `feature-spec-guide.md` and the `/fbk-spec` skill text still show the older slice vocabulary (`unit | integration | e2e | contract`) while the gate enforces `new-contract | contract-preserving | contract-evolving | cross-cutting` — a stale-doc drift to fix separately; it does not affect this gate run.

## Stage 4: Spec Review

### Perspectives invoked

Classified to three council perspectives in discussion mode — Architect (architectural soundness), Builder (over-engineering/pragmatism), Guardian (testing strategy) — plus the independent test-reviewer at checkpoint 1. Security was not invoked and no threat model was produced (operator-confirmed: no trust boundaries, no data handling, no external interaction; the gate reads local operator-authored files). Advocate and Analyst were folded into the trio's briefs. The signature-change caller-grep mandate did not trigger — the spec extends `spec.py` main() and regression-protects a pre-existing contract but renames or removes no existing symbol's signature; the Architect verified callers are unaffected regardless. The review document is `interface-contracts-review.md`; the structural review gate passes (`Architecture,Builder,Quality`, no threat model). Iteration count: 1.

### Blocking findings and resolutions

Six blocking findings, all resolved by immediate revision (operator chose revise-now); the test-reviewer re-review then returned accepted. They formed two reinforcing clusters and were cheap to fix — none was design rework.

1. **Test-fixture migration mischaracterized (Guardian, authenticated against the real test file).** The spec claims the failure-path tests are unaffected by unconditional activation. They are not: the shared `run_spec_gate` helper writes no `design/contracts.md`, so every pass-test fails the design-anchor check and the testing-strategy sentinel test (`SLICES_SPEC_WITHOUT_TS_AC`) starts failing for the wrong reason while its assertion stays green — a silent test-intent corruption. Resolution path: enumerate the three concrete helper edits now and correct the line-135 claim.
2. **Exact teaching-error strings diverge across design pages (Guardian, confirmed).** The "section missing" and "page not found" strings differ between `gate-checks.md` and `design/contracts.md`, so the message-assertion tests can't be written deterministically. Resolution path: make `gate-checks.md` the single source of truth and reconcile `contracts.md`.
3–6. **Test-strategy assertion strength (test-reviewer, needs-revision).** UV-1 has no specifically named test (AC‑17); "an uncovered AC fails" is silent-failure-shaped (AC‑10); the design-anchor and seam-coverage message tests use advisory language (AC‑08/09/11); the module-interface test asserts `list` not `List[str]` (AC‑12). These collapse into one corrective action — assert the exact teaching string in every message-quality test — which depends on resolving finding 2 first.

The two clusters reinforce: the council found the canonical strings don't exist; the test-reviewer found the tests that must assert them are described too loosely. Fixing the divergence unblocks the assertion-strength fixes.

### Six important and seven informational findings

Important: multi-section `section_body` reads unstated; section-ordering independence unasserted; no-contracts match mode unpinned and the sentence literal duplicated (recommend a single shared module constant); seam-heuristic false-positive guidance thin; three named edge cases untested (present-but-empty section, each valid design-ref form passing, mid-prose arrow); escape-hatch cross-check between the two checks that share a section parser; shell tests written as grep-the-literal rather than structural (a pattern this project already has a retrospective on). Informational highlights: integration points verified solid against the real `spec.py`; the four-check and two-leaf splits are right-sized; the IF-D/IF-S namespace is a readability decision, not the gate-enforced collision-safety the spec frames it as; the in-flight-spec migration cost (other branches) is absent from Dependencies; the proposed reference-integrity test duplicates existing repo-wide coverage.

### Spec revisions

Applied 2026-06-09 to clear all six blocking findings:

- **`gate-checks.md`** declared the single source of truth for every teaching-error string (with the implementation defining each message as a shared module constant), removing the drift surface.
- **`design/contracts.md`** had four divergent error-string literals aligned to the canonical wording or converted to references — the reviewers spotted two; reconciliation surfaced two more.
- **Spec testing strategy** rewritten so every failure-path case asserts the exact teaching string (not a non-empty return); added named cases for the UV-1 real-entry pass, the present-but-empty section, each valid `design-ref` form, and the mid-prose-arrow guard; tightened the module-interface assertion to element-type (`str`).
- **Spec "Existing tests impacted"** corrected: the "failure-path tests unaffected" claim was wrong under unconditional activation; replaced with the three concrete helper edits (`_MINIMAL_VALID_SECTIONS`, an unconditional `design/contracts.md` write in `run_spec_gate`, rebuild of `SLICES_SPEC_WITHOUT_TS_AC`) and the silent sentinel-corruption they prevent. Added the shared no-contracts-sentence module constant to the test-infrastructure note.

Both gates re-pass (spec gate, review gate) and the test-reviewer re-review returned accepted. The six important findings remain open as breakdown-level detail (parse-robustness notes, structural shell tests); they do not block the transition.

### Process note

Council and test-reviewer converged independently on the same root cause (the error-string assertion problem) from opposite directions — strong signal the finding is real rather than an artifact of one reviewer's framing. Authenticating the two highest-stakes claims directly against `spec.py` and `test_gates_spec.py`, rather than relaying the subagents' word, caught one Architect overstatement (a claim that the spec's own seams would self-fail the heuristic — they don't, because the `design-ref` path values carry the component substrings) before it reached the review document.

## Stage 5: Breakdown

Breakdown compiled 2026-06-09. Both deterministic gates pass and the checkpoint-2 test review returned accepted.

### Wave structure and task count

Eleven tasks across three waves, one test/impl pair per slice (the cross-cutting slice is test-only):

- **Wave 1** (eight tasks, four pairs, no build-order predecessors): the gate module (`contracts.py` + its unit tests), the design-contracts-standard leaf (+ design-guide route), the spec-side format leaf (+ feature-spec-guide route + glossary terms), and the architecture-reviewer drift brief. Each pair runs test-before-impl.
- **Wave 2** (one pair): the spec-gate wiring — imports the four checks from the Wave 1 module and calls them after the slice check. The test task migrates the existing `test_gates_spec.py` fixtures (contract-evolving) and adds wiring-proof tests; the impl task is the orchestrator-file edit.
- **Wave 3** (one test-only task): the end-to-end dogfood that drives the assembled, wired gate through the six user-verification steps.

Wave boundaries follow the spec's slice `depends-on` edges: the three documentation slices carry only a soft (shape) dependency on the gate, so they author independently in Wave 1; only the wiring and the dogfood carry real build-order edges.

### Mode decision: legacy task.json, not slice-aware

The breakdown gate supports a slice-aware mode (per-task `slice_shape` + a `test-hashes.json` pre-lock manifest), but it is unexercised in this repo — no feature has ever produced a `test-hashes.json`, and the most recent slice-spec'd feature (refactored-sdl) shipped a legacy manifest with every `slice_shape` null. Activating slice-aware mode would require hash-locking tests that do not exist yet at breakdown time (test files are authored during implementation), so a genuine pre-lock review is impossible here. The breakdown therefore uses legacy mode. The slice disciplines still governed how the tasks were authored — red-phase requirement, test-only cross-cutting, documented retired tests for the contract-evolving slice — they just do not flip the gate's unused hash-lock hinge. The pre-lock test-review step was correctly skipped (no contract-preserving slice locks pre-existing tests, and no test files exist on disk to lock).

### Two spec/design gaps resolved during compilation

Both independent task-authoring agents bounced back the same two underspecifications; both were resolved at the single source of truth (the design gate-checks page) after operator decisions, then the bounce-back markers were cleared:

1. **Empty-section teaching string was unpinned.** The gate-checks page pinned an exact failure message for every structural case except the present-but-empty `## Interface contracts` section, yet the spec requires the test to assert an exact, distinct string. Pinned the operator-approved wording.
2. **The `design-ref` validity rule contradicted itself.** The page said a valid `design-ref` was "any non-empty string that is not a reserved literal," which would accept everything — but the spec's own test demands the bare token `whatever` be rejected. Resolved to: valid when `pre-existing`, `none`, or a path/anchor form (contains `/` or `#`); bare tokens rejected. One task-authoring agent had silently papered over this by inventing a rule, which is exactly the kind of design decision compilation must not delegate to the implementation agent — caught and made explicit.

### AC-17 attribution (cross-cutting coverage)

The dogfood slice is cross-cutting and test-only, so its acceptance criterion has no paired implementation task. Under legacy AC-coverage every criterion needs both a test and an impl task, so the end-to-end criterion was attributed to the wiring impl — the terminal integration whose implementation the dogfood verifies. Its implementation is genuinely distributed across the gate module and the wiring; the verification itself lives in the test-only dogfood task.

### Tooling defect found and fixed (dogfooding payoff)

The breakdown gate falsely failed the (valid) breakdown, claiming five acceptance criteria were absent from the spec. Root cause: the gate's acceptance-criteria extraction regex was not anchored to line start, so it latched onto an inline `## Acceptance criteria` mention in the spec's prose (before the real heading) and captured the wrong region — where the criteria are written "AC-01 through AC-07," yielding only the endpoint tokens. The sibling gates (task-reviewer, spec) already use line-anchored extraction and were unaffected. This is a latent defect that will mis-fire on any spec that names the section in prose — which the interface-contracts feature actively encourages. Fixed the source regex to line-anchored (matching the siblings) per operator decision; the breakdown then passed cleanly. Two follow-ups remain: the installed gate copy is on a read-only filesystem and needs a reinstall to pick up the fix, and the fix itself has no regression test or changelog entry yet.

### Test review

Checkpoint-2 test review returned accepted: all fourteen canonical teaching strings reproduced verbatim in the unit-test task, all four named traps covered (body-scan, line-anchor, every-element-is-`str`, present-but-empty vs missing), red-phase validity confirmed for all test tasks, contract-evolving migration framed as update-not-delete, cross-cutting confirmed test-only through the real gate CLI. One non-blocking finding (the leaf shell tests grep for a routed filename and a conditional clause without proximity, a weak proxy for conditional routing) was overridden — the actual progressive-disclosure behavior is a spec-review concern, not mechanically testable here. Left as a known proxy limitation rather than gold-plating the shell tests.

## Stage 6: Implementation

### Per-task metrics (factual)

| Task | Type | Model | Result | Escalations | In-session retries |
|---|---|---|---|---|---|
| Unit tests for the four contract checks | test | Sonnet | pass | 0 | 0 |
| New `contracts.py` gate module | impl | Sonnet | pass | 0 | 0 |
| Design contracts-standard leaf test | test | Haiku | pass | 0 | 0 |
| Design contracts-standard leaf + route | impl | Sonnet | pass | 0 | 0 |
| Spec contracts-format leaf test | test | Haiku | pass | 0 | 0 |
| Spec contracts-format leaf + route + glossary | impl | Sonnet | pass | 0 | 0 |
| Reviewer drift-brief test | test | Haiku | pass | 0 | 0 |
| Reviewer drift-brief extension | impl | Sonnet | pass | 0 | 0 |
| Spec-gate wiring tests | test | Sonnet | pass | 0 | 0 |
| Wire the four checks into the spec gate | impl | Sonnet | pass (attempt 2) | 1 | 0 |
| End-to-end dogfood | test | Sonnet | pass | 0 | 0 |

- **Wave structure:** Wave 1 (8 tasks: 4 test + 4 impl, all independent), Wave 2 (1 test + 1 impl, wiring), Wave 3 (1 test, cross-cutting dogfood).
- **Model routing accuracy:** all three Haiku tasks (bounded grep-based shell tests) succeeded without escalation. The one escalation was on a Sonnet task and was caused by an upstream defect, not model capability — routing held.
- **Verification gates:** Wave 1 passed per-wave verification first time. Wave 2 required two rounds of discovered corrective work before passing. Wave 3 passed first time. Inter-wave baseline regression held at every boundary.
- **Pre-existing failures (excluded from baseline, merge blocker):** four shell tests already failed at the implementation baseline — one genuine content drift (`ai-failure-modes.md` item count) and three installer tests that cannot pass on the read-only `~/.claude` sandbox. Captured in the review log; must be fixed/re-verified before merge.

### Task sizing accuracy (actual files vs. declared scope)

Every task except the wiring stayed exactly within its declared file scope. The wiring task's declared scope was correct, but completing it required three pieces of discovered work outside any task's scope:
- a new neutral module `fbk/gates/sections.py` (shared text helpers),
- a one-rule change to the committed `contracts.py` (`check_ac_coverage` no-contracts exemption) plus a re-fixtured unit test,
- migration of four `tests/fixtures/specs/*-spec.md` files and a new shared `tests/fixtures/specs/design/contracts.md`.

### Upstream traceability (factual)

- Stage 2 (spec review) iterations before advancing: 1 (six blocking findings, all resolved, re-review accepted).
- Blocking findings: 6, all leading to spec revisions.
- Stage 3 (breakdown) compilation: gate passed after a latent breakdown-gate regex bug was fixed (the same line-anchoring bug re-encountered at the start of implementation because the fix lives in source but the installed copy is on a read-only mount).

### Failure attribution (AI judgment)

Only one task escalated (gate wiring), but it surfaced three distinct latent defects. Classifying each by root cause:

1. **Circular import between the spec gate and the contracts module — Compilation gap.** `contracts.py` imported two text helpers from `spec.py`; wiring made `spec.py` import `contracts.py` back. The breakdown did not anticipate that the shared helpers needed a neutral home. Fixed by extracting them to `fbk/gates/sections.py` (no lazy-import workaround). Reversible, fully test-covered.

2. **AC-coverage vs. the no-contracts form — Spec gap (internal inconsistency).** The `check_ac_coverage` invariant prose demands every AC be covered or excused with no exception, but UV-3 and UV-4 together specify enforcement only when contracts exist and a vacuous pass for the no-contracts form. The two cannot both hold. Followed the authoritative UV steps: the check now passes vacuously on the no-contracts form, and the one unit test that had encoded the contradictory reading was re-fixtured. **Spec correction owed:** the invariant prose should state the no-contracts exemption so the spec agrees with itself.

3. **Shell gate-tests blast radius — Spec gap (incomplete impact analysis).** The spec's impact analysis keyed on which test files *import* `contracts.py`, concluding no other suite was touched. That rule misses every test that drives the gate end-to-end through its CLI over fixtures. Three such shell tests broke; fixed by migrating the four pass-expecting fixtures and adding a shared no-contracts design page. **Process note for fbk-improve:** impact analysis for a gate-behavior change should enumerate behavior consumers (CLI/e2e tests, golden fixtures), not just module importers.

### Observations carried forward (not fixed this run)

- **Multi-line `invariants:` block parsing (unconfirmed).** A test agent reported that sub-bullet `invariants` blocks confuse the contract-entry field parser; a direct reproduction did not reproduce the claimed covers-missing failure, so the trigger is uncharacterized. The canonical entry format is single-line, so this blocks nothing. Follow-up: a targeted parser unit test and an explicit support-or-reject decision.
- **Installed gate copy is stale and read-only.** The breakdown-gate AC-regex fix and now the whole interface-contracts gate live in `assets/` source but not in the installed `~/.claude/fbk-scripts/` copy. A reinstall is needed before the installed gate enforces the discipline; tests in this run ran against source.
- **Pending documentation (release-time, discuss-first per project convention):** `CHANGELOG.md` Added/Changed entries and any `README.md` updates were deferred — the project treats CHANGELOG as a tagged-release artifact and requires README changes to be discussed before applying. GLOSSARY terms and the two routed leaves (the substantive new docs) are done.
