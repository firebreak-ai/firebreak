# Firebreak Pipeline Improvement Recommendations

**Date:** 2026-06-20
**Source:** `/fbk-improve` run over two retrospectives in this folder:
- `observability-substrate-retrospective.md` — a Firebreak feature (safe to reference by name).
- `inference-client-retrospective.md` — a feature in a downstream project that *uses* Firebreak. The source project is obfuscated throughout; only generalizable process lessons were carried across. No project name, environment variable, binary name, or language/tool specific to that project appears in any proposed asset text.

**How this was produced:** ten analyst agents, each reading both retrospectives plus the asset-authoring rules, each assigned one stage of the pipeline (intent, design, spec, spec-review, breakdown, implement, code-review, test-review, fresh-eyes, and the cross-cutting workflow/closeout docs). They returned 55 individual proposals. Those are consolidated here into 19 themed recommendations, with duplicates merged and the convergence noted (the same lesson surfacing independently from several stages is the strongest signal it is real).

---

## How to use this document

Each recommendation has:
- **What / why** — the change and the observation that motivates it, in plain language.
- **Targets** — the specific asset file(s) and where in them.
- **The change** — concrete enough to act on; proposed text is shown where it is short.
- **Effort** — Low / Medium / High (how much work and risk to apply).
- **Benefit** — Low / Medium / High (how much it reduces a real, recurring failure).
- **Recommendation** — my call on whether to do it now, batch it, or defer.

Pick in any order. Nothing here depends on anything else except where noted (recommendation 3 has two parts; the second is a bigger change).

**Resuming after a context clear / starting the implementation session:** this document is fully decided. Read the **summary table** (status column) for the state of every item, then **"Final disposition"** for the grouping, then **"Execution guide for a fresh session"** at the bottom for how to fan out subagents safely (partition by file, not by recommendation). Everything needed to act is in this doc.

A note on effort ratings: "Low" usually means a one-file prose addition to a guide. "Medium" usually means the same lesson applied consistently across several files, where the work is keeping the wording aligned. "High" means it changes the deterministic gate behaviour, not just documentation.

---

## Summary table

**Status legend:** ⬜ not yet discussed · ✅ confirmed · 🟢 applied (2026-06-20) · ❌ rejected

| # | Recommendation | Effort | Benefit | My call | Status |
|---|----------------|--------|---------|---------|--------|
| 1 | Diff against the locked contract, not the spec's copy of it | Medium | High | Do now | ✅ |
| 2a | Close requirement ambiguity into concrete definitions by spec completion (grill for open decisions) | Medium | High | Do now | ✅ |
| 2b | Spec gate enforces "ambiguity resolved" (spec checklist + reviewer mandate) | Medium | High | Do now | ✅ |
| 3a | Honest red-phase wording for compiled languages | Low | High | Do now | 🟢 |
| 3b | "Skeleton-first wave" structural gate change | High | High | Structural (own spec) | ✅ |
| 4 | Put shared/cross-cutting conventions inside design + review scope | Medium | High | Do now | ✅ |
| 5 | Hunt false-passing tests as a distinct review dimension | Medium | High | Do now | ✅ |
| 6 | Architect traces every inherited contract field to a population path | Low | Medium | Do now | 🟢 |
| 7a | Upgrade ALL Firebreak review agents to Opus by default | Low | High | Do now | 🟢 |
| 7b | Verify external findings before acting | Low | — | Reject — owned by external-review feature | ❌ |
| 8 | Fixes pair with a regression test; remediation gets its own pass | Low | High | Do now | ✅ |
| 9 | A point-fix to a convention needs a use-site sweep | Low | High | Do now | 🟢 |
| 10 | Progressive validation: cheap design experiments up-front; escalate to costly/constrained checks last | Low–Med | High | Do now | ✅ |
| 11 | Independent test-review as a required spec-gate condition (test plan aligned before breakdown) | Low–Med | Med–High | Do now | ✅ |
| 12 | Breakdown mechanics (six small rules) | Low–Med | Med–High | Do now (all six) | ✅ |
| 13 | *(folded into 3a)* | — | — | — | — |
| 14 | Capture the spec-gate formatting constraints | Low | Medium | Do now | ✅ (applied then reverted in review) |
| 15 | Fresh-eyes mechanics (verify, second pass, coherence reviewer) | Low–Med | Medium | Realize via #21, not per-asset | ✅ (substance) |
| 16 | Enrich the retrospective guide | Low | Medium | Do now | 🟢 |
| 17 | Doc-reconcile: surface drift, don't draft the edit | Low | Low–Med | — | ❌ skipped |
| 18 | Dead code: trace provenance, then delete | Low | Medium | Realize via #21 | ✅ |
| 19 | Challenger must read a cited design doc before ruling | Low | Medium | Realize via #21 | ✅ |
| 20 | Decompose the breakdown skill into multiple agents (planner/author split) | High | High | Structural — own design | ✅ (direction) |
| 21 | Unify reviewer assets onto one generic adversarial review shape (find→challenge→confirm) | High | High | Structural — in progress | ✅ (direction) |

---

## A standing caveat: external cross-model review is becoming its own feature

The original `/fbk-improve` run produced a whole theme recommending "consider an external cross-model review pass" notes scattered across the workflow and review guides. **That theme has been withdrawn** because you have already designed cross-model review as a dedicated Firebreak feature (passdown doc dated 2026-06-20). Hand-authoring interim notes now would duplicate the feature, create a second update target, and — worse — bake in the oversimplified version the passdown specifically corrects (the value is *model-family diversity*, not "more rounds" or "a stronger model"; and the evidence is numerator-only, so the design deliberately gates the challenger's filtering authority behind a negative control).

Two pieces survive because they are genuinely separate levers, not the cross-model feature — they are folded into recommendation 7 below.

When the passdown enters `fbk-intent`, scrub the source project name from it (it appears in three places including the intent seed). The numbers and the two validated review types carry the argument without the name.

---

## Tier 1 — High-confidence (independent convergence from 3–4 stages)

These drew the same conclusion from multiple stages working blind to each other. They are the safest, highest-value changes.

### 1. Diff against the locked contract, not the spec's transcription of it

**Status: ✅ CONFIRMED (2026-06-20).**

**What / why.** When a feature claims to implement an inherited or "locked" contract *verbatim*, reviewers must compare the code against the original contract — not against the feature spec's copy of it. In the downstream project, the single highest-severity defect (a critical) was a set of field-name and constant mismatches against the locked contract. The first review used the feature spec as its source of truth and *structurally could not* catch it, because the spec itself had transcribed the contract imprecisely. Only a review that diffed against the original contract found it. This converged independently from the design, spec, spec-review, and code-review analysts.

**Targets.**
- `fbk-docs/fbk-sdl-workflow/interface-contracts-format.md` — the description of the path/anchor `design-ref` form.
- `skills/fbk-spec-review/SKILL.md` — the council invocation section.
- `fbk-docs/fbk-sdl-workflow/code-review-guide.md` — "Source of Truth Handling," the "Spec available" entry.

**The change.** In each location, add an instruction of this shape (worded to fit each file): *when the spec states it carries a contract inherited from a broader project scope "verbatim," locate that contract and diff the code/spec entry against it field by field. A review anchored only to the feature spec cannot catch a transcription divergence — a dropped field, a renamed field, a widened type, or a changed constant.*

**Effort:** Medium — three files, and the wording should stay consistent across them.
**Benefit:** High — this class of defect is invisible to every review that stays inside the spec, and it produced a critical.
**Recommendation:** Do now.

---

### 2. Close requirement ambiguity into concrete definitions by the time the spec is complete

**Status: ✅ CONFIRMED (2026-06-20) — reshaped from the original "logging criteria" proposal.**

**The reframe.** The original proposal was about logging acceptance criteria. In discussion we recognized logging was only a *symptom*. The real target is **ambiguity**, and the rule is about *when* ambiguity is allowed to exist:

- **At intent, a generic requirement is normal and fine.** "The system should be observable / reliable / fast" is an acceptable starting point. Do not force premature precision at intent. (This explicitly *drops* the original intent-stage edits, which pushed specificity too early — they aimed at the wrong stage.)
- **By the time the spec is complete, the ambiguity must be gone.** Every field name, data shape, contract, function/class signature, and the specifics of any observable behaviour (logging is just one example) must be concrete.
- **Closure has two sources:** extracted from the existing code when the feature extends or integrates with it; decided jointly by human and agent when the piece is new.
- **Don't overburden the human.** The agent resolves the obvious details on its own. Only genuinely open decisions — the ones that actually need human direction — get surfaced, and the mechanism for surfacing them is to **grill the human one decision at a time**, not guess.
- **The spec gate enforces it.** A spec is not "complete" while this class of ambiguity is still open.

The logging field-table idea survives as a **worked example** under this principle, not as the rule itself: a criterion that asserts a component logs/emits/records is unresolved until it names what is recorded (the fields) and how a test would catch it if it broke (e.g. an injected recording logger) — "checkable by code review only" is not resolution when the behaviour is injectable.

Split into two confirmed parts:

#### 2a. Ambiguity-closure as a spec-completion discipline + grilling as the mechanism

**Targets.**
- `fbk-docs/fbk-sdl-workflow/feature-spec-guide.md` — a spec is not complete until ambiguity is closed to concrete definitions (extract-when-integrating, decide-when-new); resolve the obvious autonomously, grill for the rest.
- `agents/fbk-spec-author.md` — same discipline as an authoring obligation: surface genuinely open decisions rather than guessing; name concrete signatures/contracts/fields.
- `skills/fbk-grilling` (skill + docs) — name "ambiguous requirements that need human direction" as a primary grilling target.

**Effort:** Medium — three touch points, one consistent idea.
**Benefit:** High — generalizes and subsumes the logging trap; catches a whole class of late-surfacing defects.

#### 2b. The spec gate requires ambiguity resolved

**The honest hard part.** A deterministic parser cannot detect "ambiguity" by scanning text. Realistic enforcement comes from:
- a short **self-attestation / checklist** in the spec ("all names, signatures, and contracts defined; every open decision resolved — see grilling log"), which the gate *can* mechanically check for presence and for consistency against the grilling log; and/or
- a **reviewer mandate**: the spec-review and fresh-eyes reviewers actively hunt for leftover ambiguity and fail the spec if they find it.

A truly automated "no ambiguity remains" check would be a larger build. Whether any part of 2b needs to become a separate spec is left for later triage (out of scope for this discussion).

**Targets.** the spec gate (checklist validation), `fbk-docs/fbk-sdl-workflow/review-perspectives.md` and the fresh-eyes assets (reviewer mandate to fail on residual ambiguity).

**Effort:** Medium for the checklist + reviewer mandate; higher if a real automated check is pursued.
**Benefit:** High — turns the 2a discipline into something enforced rather than hoped-for.

---

### 3. Honest red-phase for typed/compiled languages

**Status: ✅ CONFIRMED both parts (2026-06-20). Operator note: long-wanted change, validated across several cycles.**

This has a cheap part and an expensive part. They are separable.

#### 3a. Fix the wording (cheap)

**What / why.** In a compiled or strongly-typed language, a test file cannot compile until the types it references exist. So the gate phrased "tests compile and fail before implementation" literally cannot hold at the test task's own stage for a brand-new module — there is nothing to compile against yet. The dominant defect class in the downstream implementation (around nine signature/arity mismatches across seven files) traced directly to this: test authors wrote against symbols that did not exist yet and drifted from each other, and the drift only surfaced in a burst when each module first linked. The fix is to describe the real, honest sequence: the implementer first writes an empty skeleton so the tests compile and go red, then fills it in to go green.

**Targets.**
- `fbk-docs/fbk-sdl-workflow/slice-shapes/new-contract.md` — the test-task sentence.
- `fbk-docs/fbk-sdl-workflow/implementation-guide.md` — the red-phase description.

**The change.** Reword the red-phase gate so it reads, in effect: *tests must compile and fail before the implementation is filled in. In a typed/compiled language a new module's tests cannot compile until a skeleton with the declared types and signatures exists, so the implementer co-sequences — writes the empty skeleton (tests compile, go red), then fills the bodies (tests go green).*

**Effort:** Low — two wording edits.
**Benefit:** High — it removes a gate that is currently impossible to satisfy honestly, which is what let the drift accumulate.
**Recommendation:** Do now.

#### 3b. Introduce an explicit "skeleton-first wave" (structural)

**What / why.** The deeper fix is to make the red phase *literally executable* at each test task's own stage: schedule a per-module type/stub skeleton as the first tasks, with the test tasks depending on it. Then test authors can compile-check against real signatures and the drift never accumulates.

**Why it's expensive.** This fights the current deterministic gate rules ("test tasks ordered before implementation tasks within a wave"; "dependencies must be in a strictly earlier wave"). A skeleton task is an *implementation* task that must precede its test tasks — so the gate logic, not just the prose, has to change.

**Effort:** High — touches the gate scripts and several docs, and needs its own design to avoid breaking the existing ordering guarantees.
**Benefit:** High — it would have prevented essentially all of the front-loaded-TDD drift.
**Recommendation:** Make this its own small spec rather than an `/fbk-improve` edit. 3a is the honest stopgap until then.

---

### 4. Put shared/cross-cutting conventions inside design and review scope

**Status: ✅ CONFIRMED (2026-06-20).**

**Operator-added dependency to resolve when implementing (details deferred, possibly to a dedicated spec):** this recommendation assumes an authoritative conventions source exists. It often doesn't — many projects have no formal conventions document, not even inside `CLAUDE.md`. And even where one exists, real codebases frequently *don't follow their own documented conventions consistently*. So the change must handle:
- **No conventions doc available** — define a fallback (e.g. infer conventions from the existing code, or prompt the operator) rather than assuming the doc is there.
- **Documented conventions already violated in the actual code** — decide what "align" means when the doc and the live code disagree (align to the doc? to the dominant code pattern? surface the conflict to the operator?).
The fresh-eyes edit also must add only the *convention files*, never authoring history, so the cold read stays independent.

**What / why.** A design can faithfully check the foundational contract, the requirements, and the package layout — and still silently reinvent a *shared* convention (a config shape, a constructor signature, a naming scheme) that lives in a separate cross-cutting document. In the downstream project that is exactly what happened: a shared config contract was reinvented, the design fresh-eyes pass had no reason to open the cross-cutting doc, and the drift slipped a whole gate before being caught manually at spec time. The fix is to make the cross-cutting conventions part of what design and the cold reviewer compare against whenever the feature touches shared contracts.

**Targets.**
- `fbk-docs/fbk-sdl-workflow/design-guide.md` — the fresh-eyes scope, and the contracts-page routing.
- `fbk-docs/fbk-design-guidelines/spec-design-thinking.md` — a short "shared conventions check" before finalizing the technical approach.
- `skills/fbk-fresh-eyes/SKILL.md` — the spawn step currently says "pass it *only* the artifact under review," which actively excludes the convention files; broaden it to also pass any cross-cutting convention files the artifact consumes (still no authoring history).

**The change.** Add an instruction at each point: when a feature introduces or consumes a shared contract (config, shared interface, shared sentinel set, shared event registry), read/pass the authoritative cross-cutting document and verify the artifact against it. A check against the foundational contract alone does not catch a reinvented shared convention.

**Effort:** Medium — four touch points, including one careful edit to the fresh-eyes spawn instruction.
**Benefit:** High — a reinvented shared contract slipped an entire gate.
**Recommendation:** Do now.

---

### 5. Hunt false-passing tests as a distinct review dimension

**Status: ✅ CONFIRMED (2026-06-20).** Note: strengthens the existing `test-reviewer` + test-integrity audit rather than adding a parallel system; the pattern list is a living checklist to grow over time.

**What / why.** "Do the tests pass?" (the native gate) and "is the production code correct?" (code review) are different questions from "would this test *fail* if the behaviour it guards broke?" The third question is the one nobody was asking, and a dedicated test-quality pass found false-passing tests that had survived multiple code-review rounds *and* live execution — because the defect is in the test, not the code. The concrete patterns, worth naming explicitly so a reviewer scans for them:
- A test whose input literally pre-satisfies its own assertion (the asserted value was placed in the setup, not produced by the code).
- A test that calls a low-level primitive directly, bypassing the production path it claims to cover.
- Concurrency or validation tests that discard their results — green regardless of correctness.
- A harness that asserts field *keys* are present but never checks the *values* — a wrong value still passes.
- A test pinned to a no-op seam (monkeypatching a clock the unit does not actually hold) — vacuous, and worse, it can steer the implementer into adding the wrong dependency to satisfy it.
- Coverage that is only the failure/null path, with no positive-path test proving the computation produces a correct non-null result on a field a contract displays.

**Targets.**
- `fbk-docs/fbk-sdl-workflow/detection-audits.md` — the test-integrity audit (replace the vague "is the assertion strict enough?" with the enumerated patterns).
- `agents/fbk-test-reviewer.md` — catching-power criteria (add the patterns) and final mode (positive/negative path gap).
- `fbk-docs/fbk-design-guidelines/test-authoring.md` — two short authoring rules: pair positive and negative paths; only patch a dependency the unit actually holds.

**Effort:** Medium — three files, but mostly enumerating patterns you already have in the retrospectives.
**Benefit:** High — these defects are invisible to every other gate by construction.
**Recommendation:** Do now.

---

## Tier 2 — Stage-local refinements (single clear lesson, usually one file)

### 6. The architect traces every inherited contract field to a population path

**Status: ✅ CONFIRMED (2026-06-20).** Wording nuance for implementation: lean on "especially the seams the locked contract doesn't specify" so it targets the non-obvious plumbing rather than becoming a mechanical trace of every obvious field.

**What / why.** A "narrow" design against an already-locked interface is not trivial — the criticals hide precisely in the inherited-but-not-re-derived parts: how an override reaches a sealed client, who fills a particular field, what an "unconstrained" value serializes to. Four design-stage criticals in the downstream project were exactly this shape.

**Target.** `agents/fbk-architect.md` — anti-defaults section.
**The change.** Add: when a design inherits or locks a pre-existing contract, trace every field of the locked type to a concrete population path and every promised flag/sentinel to a mechanism; do not treat "inherited" as a reason to skip the field-level trace.

**Effort:** Low — one persona edit.
**Benefit:** Medium — prevents a recurring cluster of design-stage criticals.
**Recommendation:** Do now (pairs naturally with #4).

---

### 7. Review-agent model tier (reshaped from the withdrawn cross-model theme)

**Status: ✅ 7a CONFIRMED / ❌ 7b REJECTED (2026-06-20).**

The original "recommend an external cross-model pass everywhere" theme was withdrawn (it's becoming its own feature). Two remnants were considered; one became a stronger change, the other was rejected.

#### 7a. Upgrade ALL Firebreak review agents to Opus by default — ✅ CONFIRMED

**The reshape.** The original idea was a flimsy "a stronger-model override is *available* at high-value gates" note. In discussion we rejected that framing: an override the operator must remember to invoke is not a real safeguard — defaults are what actually happen. If a stronger model catches more at these gates (and the observability build gave direct evidence: an Opus re-run of the test-reviewer caught a real coverage hole Sonnet missed), the honest move is to make Opus the default for review.

**Why it's justified.** Review gates are the highest-leverage point in the pipeline — a defect caught here is far cheaper than one that escapes. Reviews are also *low-frequency* (one spec review, one test review per checkpoint, a few detector/challenger rounds), so Opus's higher per-call cost is bounded while per-call value is very high — the opposite of the high-volume implementation agents. **Operator's deciding argument:** if we are willing to pay for an *external* supplemental model review (with its token cost), we should certainly pay for Opus on in-house reviews.

**Composes with cross-model.** Today the detector and challenger are both Sonnet — a single-model monoculture. Opus makes it an Opus monoculture; the cross-model feature adds the *family-diversity* axis separately. Orthogonal, no conflict.

**Scope: every Firebreak review agent (operator confirmed "all of them").** Change `model:` to Opus (`claude-opus-4-8`) in:
- Adversarial finding-producers: `agents/fbk-test-reviewer.md`, `agents/fbk-code-review-detector.md`, `agents/fbk-code-review-challenger.md`, `agents/fbk-fresh-eyes-reviewer.md`.
- Council (spec review): `agents/fbk-council-architect.md`, `fbk-council-builder.md`, `fbk-council-guardian.md`, `fbk-council-security.md`, `fbk-council-advocate.md`, `fbk-council-analyst.md`.

**Explicitly NOT doing yet:** asymmetric tiers (e.g. a stronger challenger than detector). Flip all review defaults to Opus uniformly first; refine later only if there's reason.

**Effort:** Low — a frontmatter `model:` change in ten agent files.
**Benefit:** High — raises the capability floor at the highest-leverage gates in the pipeline.

#### 7b. Verify externally-sourced findings before acting — ❌ REJECTED

Rejected because it is **already part of the plan for the external-review feature** (its §5: challenger-on-probation + negative control decide when external findings can be trusted to filter). Hand-authoring a thin version now would duplicate the feature and create a second place to keep in sync.

---

### 8. A fix pairs with a regression test; remediation gets its own adversarial pass

**Status: ✅ CONFIRMED (2026-06-20).** Scope when implementing: the regression-test rule bites on *behavioural and test-integrity* fixes (where the bug could silently return), not trivial mechanical fixes (typos, comments).

**What / why.** Two things the retrospectives caught:
- Two behavioral fixes shipped *without* regression tests; the detection loop missed it because it had reviewed the pre-fix code, and only the independent final test-review caught the gap.
- Several later-round findings were incomplete-fix follow-ups — the remediation itself carried defects. Fix code is new code and needs its own pass.

**Targets.** `skills/fbk-code-review/SKILL.md` — the detection/verification loop (require a regression test alongside any behavioral/test-integrity fix; treat a round in which fixes were applied as new code under review). `agents/fbk-test-reviewer.md` — final mode (flag any defect fix that lacks a regression test).

**Effort:** Low — a couple of loop-step edits.
**Benefit:** High — both gaps escaped to late stages in practice.
**Recommendation:** Do now.

---

### 9. A point-fix to a normalization/convention needs a use-site sweep

**Status: ✅ CONFIRMED (2026-06-20).** Operator framing: defense in depth — a cheaper fix-time net alongside the existing review-stage consistency audit.

**Operator-added implementation consideration:** the sweep can surface many sites. Cramming all of them into one agent's context risks diminished quality and increased hallucination. So the instruction should scale the work to the number of found sites — when the count is large, fan out to multiple subagents (each owning a disjoint subset of sites) rather than having one agent attempt the whole sweep. Decide the fan-out threshold and partitioning when implementing.

**What / why.** The single highest-severity code-review finding in the downstream project came from a fix applied at the *validation* site but not the *use* sites of the same convention. A correct-looking local fix left the rest broken.

**Target.** `fbk-docs/fbk-sdl-workflow/implementation-guide.md` — a short "lead-applied fixes" note.
**The change.** When a fix touches a normalization or convention (lowercasing at lookup, a field path, a constant name), grep for all use sites and confirm each was updated before closing the wave. A wave can pass its own tests and still ship a critical if a fix landed at one site only.

**Effort:** Low — one note.
**Benefit:** High — it directly caused the top finding.
**Recommendation:** Do now.

---

### 10. Progressive validation — cheap experiments up-front, escalate to costly/constrained checks last

**Status: ✅ CONFIRMED (2026-06-20) — generalized from the original "run live tests" proposal.**

**The reshape.** The original was framed around "run live tests against the real backend." In discussion we generalized it: the downstream project being a client for a physically-constrained resource was *incidental*. The real principle is the DevOps/CICD shape of **progressive risk reduction** — find the truth as cheaply and early as possible, and escalate to slower / more expensive / physically-constrained resources only after the bugs that cheaper checks can catch have already been iterated away.

Two applications of the one principle:
- **Design-time cheap experiments (the higher-value half).** Before a line of code, run cheap experiments to establish ground truth and align the *whole design*, rather than deferring the question to implementation. The original evidence: an assumption about an external dependency that, left unverified, would have surfaced as a late failure. **Mechanism already exists — the `code-experiment` skill** ("validate planning decisions through executable experiments"); this recommendation routes through and reinforces it, not a parallel mechanism.
- **A cost-escalating validation ladder.** Cheap/fast checks first; costly or constrained-resource checks last; the most expensive tier (validation against the genuine source of truth — a real service, real hardware, a real data sample, a real downstream system) runs before "done" *where feasible*, with a deferral recorded when it isn't. Evidence: a request-shape bug survived four static review passes because every reviewer shared the same wrong premise — reading cannot falsify a premise everyone shares; only the genuine dependency can.

**Language to workshop at implementation time:** drop "live test" — it is vague and stack-specific. Name the concept as validation against the genuine source of truth, escalating in cost.

**Targets.**
- Design: `fbk-docs/fbk-sdl-workflow/design-guide.md` / `spec-design-thinking.md` — point at the `code-experiment` skill for cheap up-front experiments that align the design before code.
- Testing strategy: `fbk-docs/fbk-sdl-workflow/feature-spec-guide.md` — the cost-escalating validation ladder (cheapest checks first; constrained/expensive last).
- Completion: `fbk-docs/fbk-sdl-workflow/implementation-guide.md` — run the most expensive/genuine-source tier before declaring complete where feasible; record an explicit deferral when not.

**Effort:** Low–Medium — broader than the original two additions (now touches design, testing strategy, and completion), but still cheap edits.
**Benefit:** High — the surviving four-rounds bug is the clearest evidence in either retrospective; this corrects a failure mode that *all* review shares (including the upcoming cross-model feature). Related to the manual-verification option in #12.

---

### 11. Independent test-review as a required spec-gate condition

**Status: ✅ CONFIRMED (2026-06-20) — strengthened from the original "sequencing note" into a gate requirement.**

**The reshape.** The original was just advice to run the test-reviewer after the council is clean. In discussion we strengthened it: make a passed test-review a **required condition of the spec/review gate**, so the spec cannot advance to breakdown until the test *plan* has been independently reviewed and aligned.
- **Stays independent of the council.** The test-review is a distinct, adversarial, per-requirement lens; it is *not* folded into the council (mixing would dilute it). The council asks "is the spec sound in shape?"; the test-review asks "for each requirement, does the planned test actually prove it?"
- **Runs after the council is clean,** against the stabilized spec, so it does its distinctive job instead of re-finding structural issues or going stale when the spec changes.
- **Reviews the test plan, not test code** — at spec stage there is no code yet; "passed" means the adversarial reviewer reaches an accepted verdict (may take a round or two of plan fixes; downstream evidence showed fast convergence).

**Composes with confirmed items:** the test-reviewer is moving to Opus (#7a) and gaining the false-passing-test pattern list (#5) — it becomes more load-bearing exactly as it becomes sharper.

**Targets.** `skills/fbk-spec-review/SKILL.md` (incorporate the independent test-review as a required step after council-clean), the spec/review gate definition (add "test-review passed" as a pass condition — the gate-enforcement piece, akin to #2b), `fbk-docs/fbk-sdl-workflow/review-perspectives.md` (sequencing + distinct-from-council framing).

**Effort:** Low–Medium — more than a doc note because it adds a gate pass-condition.
**Benefit:** Medium–High — a guaranteed test-plan alignment checkpoint before breakdown, not a suggestion.

**What / why (original evidence).** A council validates that the testing strategy is sound in *shape*; an adversarial per-criterion test-reviewer catches the specific gaps between a criterion's stated obligation and its test bullet. They are different lenses and both are needed — and the test-reviewer earns its keep only against a stable, council-clean spec (otherwise it re-finds structural blockers or works against a spec that's about to change).

**Target.** `fbk-docs/fbk-sdl-workflow/review-perspectives.md` — verification gate / sequencing note.
**Effort:** Low.
**Benefit:** Medium.
**Recommendation:** Batch with other review-perspectives edits.

---

### 12. Breakdown mechanics (six small, mostly independent rules)

**Status: ✅ ALL SIX CONFIRMED (2026-06-20).** Note on 12.5 (known gate-tooling limitations): confirmed as a cheap stopgap, but the *better* fix is to repair the tooling quirks rather than document the workarounds. Cross-link: these mechanics are the guardrails that make the breakdown-decomposition in #20 safe — more parallel authors = more cross-author drift surface, so the pinning/coherence rules (12.1, 12.2, 12.6) become prerequisites for fan-out, not afterthoughts.

All target `fbk-docs/fbk-sdl-workflow/task-compilation.md` unless noted. Each is small; you can pick à la carte.

1. **Quote exact nested schema field paths.** When a task reads/writes a structured-record field, give the full path (e.g. `asset_bundle.persona`, not "the persona field"). The one place a test drifted from the schema was the one place the task hadn't restated the nesting. *(Benefit: Med-High — caused the only compilation gap in the observability build.)*
2. **Pin shared test-helper signatures.** When several test tasks call a shared helper, pin its exact signature in each task; invented-then-guessed helper signatures were a recurring drift source across parallel authors. *(Benefit: Med.)*
3. **Detect and restructure same-wave, same-file writes.** When multiple tasks in a wave would each edit the same file (e.g. each removing its own stub), they will race; restructure so one prep step does the shared edit and each task then creates only its own file. *(Also touches `implementation-guide.md` for the lead's safe handling, and `agents/fbk-implementer.md` to flag a test that contradicts the schema rather than adding a compensating write. Benefit: Med.)*
4. **Allow a manual operator-verification gate.** When only a live end-to-end run exercises the real glue and fixtures cover the rest, a documented manual procedure is a legitimate completion gate — not a vacuous test that mocks the very glue it should verify. *(Benefit: Med.)*
5. **Record the two known gate-tooling limitations and their workarounds.** The `files_to_modify` existence check can't tell a typo from a file an earlier task creates; the task-reviewer gate lacks the cross-cutting exemption the breakdown gate has. Note both so future runs route around them instead of re-diagnosing. *(Benefit: Low-Med.)*
6. **Verify agent-persona names and workflow language.** Any task referencing an agent persona must use the installed agent's `name:` field exactly; any code-defined workflow must use the harness's actual workflow language. Both mismatches produced non-running artifacts that only external review caught. *(Benefit: Med — and directly relevant to the conformance-workflow class of task.)*

**Effort:** Low–Medium overall (each rule is a small addition; sub-rule 3 spans three files).
**Benefit:** Medium–High in aggregate.
**Decision:** ✅ all six confirmed (2026-06-20). Sub-rule 5 confirmed as a stopgap pending a real tooling fix. These pinning/coherence rules also gate the safety of the #20 breakdown decomposition.

---

### 14. Capture the spec-gate formatting constraints

**Status: ✅ CONFIRMED — applied then REVERTED in review (2026-06-20).** The first attempt wrote a "Parser constraints" section into `interface-contracts-format.md`, but a code review caught that three of the four captured rules contradict that file's actual contract-entry schema: "invariants must be last" conflicts with the documented order (where `covers` and the required `design-ref` follow `invariants`), the "seam component names" rule names a field this format does not have, and the "no AC ranges" rule guards against a syntax the inline `covers` list never offers. The constraints as captured here describe a different format than the target file. Re-do this only against the real parser behavior, and confirm which file/parser each constraint actually applies to before writing it down. The file already documents its one genuine quirk (no sub-heading per contract entry).

Original honest asterisk (still true): each quirk is really a brittle parser; the better long-term fix is to harden the parser (strip leading header numbers, accept the list field in any position, see backticked names, expand AC ranges) so authors aren't permanently taxed with remembering its quirks. Same pattern as 12.5 — document now, fix the tooling later.

**What / why.** Several mechanical spec-gate iterations were spent on formatting the parser is picky about: section headers must be unnumbered; the colon-less `invariants:` list must come last in each contract entry; both component names of a seam must appear as plain text (not backticked); acceptance-criterion ranges must be spelled out individually. None are content errors — they look correct to a human and still fail the parser.

**Target.** `fbk-docs/fbk-sdl-workflow/interface-contracts-format.md` — a short "parser constraints" section.
**Effort:** Low.
**Benefit:** Medium — saves a repeated round-trip on every spec that hits one.
**Recommendation:** Do now (pairs with #1, same file).

---

### 15. Fresh-eyes mechanics

**Status: ✅ SUBSTANCE CONFIRMED (2026-06-20) — but realize it through #21 (the unified review shape), NOT as per-asset fresh-eyes patches.**

**The reframe.** These three are valid capabilities, but they are not fresh-eyes-specific — they are generic properties of an adversarial review, and code review already implements all three. Hand-patching them onto fresh-eyes alone would create per-asset versions that the #21 consolidation then has to unwind. Map each to the generic shape instead:
- **Verify before acting** *is* the **challenge/confirm** stage of the find→challenge→confirm loop (code review's detector→challenger already does this).
- **Cross-unit coherence reviewer** is a generic review capability (code review's consistency pass) — and the load-bearing prerequisite for the #20 breakdown decomposition.
- **Second pass after edits** is just iteration-to-convergence, which an adversarial loop does naturally.

**Implementation path.** Build these into the general review shape (#21); fresh-eyes and the other lagging review types inherit them; type-specific detail lives in progressive-disclosure reference docs.

**Effort:** Low–Medium if done per-asset; effectively folded into #21 if done right.
**Benefit:** Medium standalone; higher as part of the unified shape (15.3 gates #20).

---

### 16. Enrich the retrospective guide

**Status: ✅ CONFIRMED (2026-06-20).**

**Operator context — complementary to the observability work.** The hook-router / observability-substrate changes (implemented, not yet installed) will start adding *deterministically-sourced* process details to the retrospective — involuntary data outside the agent's control (the factual spine: what happened, metrics, timings). This recommendation improves the *agent-authored* layer — the interpretation the deterministic data can't produce on its own (root-cause attribution, candidate-improvement callouts, false-negative signals). The two are complementary: deterministic facts + agent reasoning. Better agent-side instructions remain valuable as the deterministic portion grows.

**Framing guard:** prompt for these elements "if present" — surface root-cause and candidate-improvement thinking that genuinely occurred; do not manufacture hollow box-ticking entries (consistent with: ceremony exists for distillation that improves agent behaviour, not documentation for its own sake).

**What / why.** Both retrospectives are unusually useful *because* they have per-stage sections, failure attribution by root-cause class, explicit "candidate SDL improvement" callouts, and false-negative signals (what each review pass missed). The guide doesn't currently prompt for those, so they depend on the author thinking of them. The "candidate SDL improvement" callouts in particular are what feed this very `/fbk-improve` step.

**Target.** `fbk-docs/fbk-sdl-workflow/retrospective-guide.md` — the stage-section descriptions (especially breakdown, implementation, code review).
**Effort:** Low.
**Benefit:** Medium — improves the input to every future improvement run.
**Recommendation:** Do now.

---

### 17. Doc-reconcile: surface drift, don't draft the edit

**Status: ❌ SKIPPED (2026-06-20).** Lowest-stakes item; it hardens a step that already behaved correctly (the retrospective notes doc-reconcile deferred to operator review as intended), and it sits in mild tension with trust-the-agent (a draft-for-approval is not obviously wrong). Existing "operator decides" wording plus the discuss-before-apply convention are deemed sufficient.

**What / why.** Durable-doc updates (architecture overview, README, glossary, changelog) were correctly deferred to operator review per the discuss-before-apply convention. The skill's current language says "the operator decides" but doesn't forbid drafting an edit inline — an agent could read it as "produce a draft for the operator to accept," shortcutting the review.

**Target.** `skills/fbk-doc-reconcile/SKILL.md` — the advisory-only constraint.
**The change.** Add: do not propose or draft doc updates inline; surface the drift and leave the edit to the operator.
**Effort:** Low.
**Benefit:** Low–Medium.
**Recommendation:** Batch.

---

### 18. Dead code: trace provenance, then delete

**Status: ✅ CONFIRMED (2026-06-20) — realize via #21 (the unified review shape), as a review-resolution behaviour, not a one-off failure-modes-doc bolt-on.** Firm framing: the provenance trace decides — delete only when the trace confirms no purpose; surface the ambiguous ones (e.g. infrastructure intentionally shipped ahead of its first consumer) rather than auto-deleting.

**What / why.** A dead field drew a finding in *every* review round because it was noted but never removed. The cure is to trace its lineage (requirements → design → spec → task → history) to confirm no hidden purpose, then delete it — ending the recurring re-litigation cost instead of paying it each pass.

**Target.** `fbk-docs/fbk-sdl-workflow/ai-failure-modes.md` — the dead-infrastructure item.
**Effort:** Low.
**Benefit:** Medium.
**Recommendation:** Do now.

---

### 19. The challenger must read a cited design doc before ruling

**Status: ✅ CONFIRMED (2026-06-20) — realize via #21 (challenger discipline in the generic challenge/confirm stage).** Closes a false-*rejection* (a true finding thrown out), the more dangerous direction. Same root principle as #1: check the actual source of truth, don't reason about whether a claim "looks documented." Cheap, narrow, correct.

**What / why.** A binding default specified in a design document was wrongly rejected as mere "authoring guidance" because the challenger reasoned about whether it "looked enforced" instead of reading the cited document. Adjudicating a doc-sourced claim requires reading the doc.

**Target.** `agents/fbk-code-review-challenger.md` — the rejected-outcome description.
**Effort:** Low.
**Benefit:** Medium.
**Recommendation:** Do now.

---

## Tier 3 — Structural candidates surfaced in discussion

### 20. Decompose the breakdown skill into multiple agents

**Status: ✅ CONFIRMED as a direction (2026-06-20). Needs its own design — not a context-asset edit. Surfaced by the operator during the #12 discussion.**

**The concern (operator).** The breakdown stage is the most context-heavy single-agent reasoning task in the whole pipeline. One agent must hold the entire spec, every contract, the full dependency graph, and the sizing constraints *simultaneously*, and emit a large structured output (all tasks, all waves). That is precisely the load profile where single-agent quality degrades — context dilution, dropped acceptance criteria, missed dependencies. (A known symptom already in memory: the breakdown orchestrator skips task-id assignment in ~10% of sessions.) Implementation already fans out across a wave-based agent team; breakdown is the serial planning bottleneck that does not.

**Why it's well-founded.** The current breakdown already splits a little (an independent test-task author, then an impl-task author seeded with the test files) plus deterministic gates and an adversarial test-reviewer — but each author still has to hold the *whole* spec and produce *all* tasks of its type. The heavy cognitive load is undecomposed.

**Candidate decomposition seams (for the design to evaluate — not yet chosen):**
- **Planner / author split (lead candidate).** One "planner" agent produces only the task *skeleton* — the list of tasks, their files, their dependencies, and wave assignment — holding the whole spec at low resolution. Then parallel "task-body authors" each fill in a handful of task files at high resolution. This matches the actual load split: global structure (needs the whole spec's shape, not every detail) vs local detail (one task, deeply). Conceptually parallels the skeleton-first idea in #3.
- **Per-slice fan-out.** The spec already divides into slices; one agent per slice authors that slice's tasks in parallel, then a synthesis pass stitches waves and resolves cross-slice dependencies.
- **A mandatory coherence pass either way.** Fanning out *increases* cross-author contract drift (the exact risk the cross-unit coherence reviewer in #15 catches). So any decomposition needs a coherence/synthesis step that verifies every contract a producer declares matches its consumer — the signature/sentinel matrix.

**Key insight linking this to #12.** Decomposition raises the drift surface, so the #12 pinning rules (exact field paths 12.1, shared helper signatures 12.2, agent-identity 12.6) and a coherence pass become *prerequisites* for doing this safely — confirming the six is not superseded by #20; it enables it.

**Overlap with existing thinking.** Relates to the operator's standing "dynamic-workflow-consolidation" idea (firebreak wiki) — building ceremonies as orchestrated multi-agent workflows on one substrate. Breakdown is a strong candidate for that treatment.

**Effort:** High — a real design/spec, with a multi-agent orchestration and a coherence guarantee.
**Benefit:** High — attacks the single largest single-agent context burden in the pipeline.
**Next step:** a dedicated design/grilling session (not an `/fbk-improve` edit).

---

### 21. Unify the reviewer assets onto one generic adversarial review shape

**Status: ✅ CONFIRMED as a direction (2026-06-20) — already in progress per operator. Needs its own design. Surfaced during the #15 discussion.**

**The direction (operator).** The reviewer-shaped assets (there are several) are being folded together into **one generic review pattern with a built-in adversarial loop — find → challenge → confirm — usable for any review type** (code review, test-quality review, test-plan review, task review, spec review, …). Type-specific instructions live in **progressive-disclosure reference docs** within the general shape, rather than each review type re-implementing the loop. Code review already implements the loop today; the work is generalizing it so every review type inherits it.

**Why it matters here.** Several confirmed recommendations are really "properties the general review shape should have," and are best delivered *inside* #21 rather than as scattered per-asset edits:
- #5 (false-passing-test patterns) — a detection lens the shape carries.
- #8 (fix pairs with a regression test; remediation gets its own pass) — the confirm stage + re-review-the-fix behaviour.
- #11 (independent test-review as a gate) — the test-plan review type instantiated on the shape.
- #15 (verify-before-acting, second pass, coherence) — the challenge/confirm stage, iteration, and coherence pass.
- #18 (dead code: trace provenance, then delete) — a review-resolution behaviour.
- #19 (challenger reads the cited design doc) — a challenger discipline.
- The rejected #7b (verify external findings) and the cross-model feature also plug into this shape.

**Implementation guidance for those items:** prefer to realize them as generic properties of the unified shape (with type-specifics in progressive-disclosure refs). Where a review type already has the property (code review), it becomes the reference implementation; lagging types inherit it on consolidation. Avoid hand-authoring per-asset duplicates that consolidation would have to unwind.

**Effort:** High — consolidation across multiple reviewer assets plus a progressive-disclosure reference structure.
**Benefit:** High — single shape to maintain; every review type gains the full adversarial loop; removes per-asset drift.
**Next step:** a dedicated design (overlaps the operator's "dynamic-workflow-consolidation" thinking and the #20 decomposition).

---

## Final disposition (after full review, 2026-06-20)

All 19 original recommendations were discussed one at a time; two structural directions (#20, #21) surfaced during discussion. Grouped by how each will be carried out:

**Group A — confirmed direct edits (doc/persona/skill changes):**
- 1 — diff against the locked contract.
- 2a — ambiguity-closure as a spec-completion discipline + grilling for open decisions.
- 3a — honest red-phase wording for typed/compiled languages.
- 4 — cross-cutting conventions in design + review scope (carries an open dependency: handle "no conventions doc" and "code already violates the doc").
- 6 — architect traces inherited fields to a population path.
- 7a — upgrade all ten Firebreak review agents to Opus.
- 9 — use-site sweep after a convention fix (with fan-out when many sites).
- 10 — progressive validation (cheap design experiments via `code-experiment`; cost-escalating ladder; "live test" language to be workshopped).
- 12 — all six breakdown mechanics.
- 14 — spec-gate formatting constraints (stopgap; harden the parser later).
- 16 — enrich the retrospective guide (agent-authored layer; complements deterministic observability data).

**Group B — confirmed, but enforced via a gate change (more than a doc edit):**
- 2b — spec gate requires ambiguity resolved (spec checklist + reviewer mandate).
- 11 — independent test-review as a required spec-gate condition.

**Group C — confirmed substance, realize *inside* the unified review shape (#21), not as per-asset edits:**
- 5 — false-passing-test detection patterns.
- 8 — fix pairs with a regression test; remediation gets its own pass.
- 15 — verify-before-acting, second pass, cross-unit coherence.
- 18 — dead code: trace provenance, then delete.
- 19 — challenger reads the cited design doc.

**Group D — confirmed as structural directions, each needs its own design (not `/fbk-improve` edits):**
- 3b — skeleton-first wave (gate-rule change).
- 20 — decompose the breakdown skill into multiple agents.
- 21 — unify reviewer assets onto one generic adversarial review shape (Group C items roll up here; in progress).

**Rejected / skipped:**
- 7b — verify external findings before acting → owned by the external cross-model review feature.
- 17 — doc-reconcile "don't draft the edit" → skipped (hardens a step that already works; mild trust-the-agent tension).

**Suggested sequencing:** Group A first (cheapest, well-evidenced, no structural risk). Group B next (two contained gate changes). Then the structural designs in Group D — and because Group C items are best delivered *through* #21, schedule #21's design before hand-applying 5/8/15/18/19 individually. #20 and #21 are related and overlap the standing dynamic-workflow-consolidation thinking; consider designing them together.

---

## Execution guide for a fresh session (mass-addressing the simple items)

**Plan:** a new session fans out subagents to apply the simple items (Group A) in parallel, then handles the complex ones (Groups B/C/D) as separate full cycles.

**Only Group A is safe for the parallel mass pass.** Group B needs gate-definition changes; Groups C and D need design. Do not include them in the fan-out.

**Partition the fan-out BY FILE, not by recommendation.** Several Group A items edit the *same* file. If you assign one subagent per recommendation, two subagents will edit the same file concurrently and collide — the exact failure #12.3 warns about. Instead, give each subagent ownership of a file (or file cluster) and have it apply *every* Group A change that targets that file. File → recommendations map:

| File | Group A recs to apply |
|------|------------------------|
| `fbk-docs/fbk-sdl-workflow/interface-contracts-format.md` | 1, 14 |
| `fbk-docs/fbk-sdl-workflow/feature-spec-guide.md` | 2a, 10 |
| `fbk-docs/fbk-sdl-workflow/implementation-guide.md` | 3a, 9, 10, 12 (rule 3) |
| `fbk-docs/fbk-sdl-workflow/design-guide.md` | 4, 10 |
| `fbk-docs/fbk-design-guidelines/spec-design-thinking.md` | 4, 10 |
| `skills/fbk-spec-review/SKILL.md` | 1 |
| `fbk-docs/fbk-sdl-workflow/code-review-guide.md` | 1 |
| `agents/fbk-spec-author.md` | 2a |
| `skills/fbk-grilling/` (SKILL + refs) | 2a |
| `fbk-docs/fbk-sdl-workflow/slice-shapes/new-contract.md` | 3a |
| `skills/fbk-fresh-eyes/SKILL.md` | 4 (the cross-cutting-conventions edit only; the #15 mechanics are NOT Group A — they go via #21) |
| `agents/fbk-architect.md` | 6 |
| `fbk-docs/fbk-sdl-workflow/task-compilation.md` | 12 (rules 1, 2, 4, 5, 6) |
| `agents/fbk-implementer.md` | 12 (rule 3) |
| `fbk-docs/fbk-sdl-workflow/retrospective-guide.md` | 16 |

**7a is a separate trivial batch.** Change `model:` to Opus (`claude-opus-4-8`) in ten agent files: `fbk-test-reviewer`, `fbk-code-review-detector`, `fbk-code-review-challenger`, `fbk-fresh-eyes-reviewer`, and the six `fbk-council-*`. Each file is a one-line frontmatter edit, no overlap with the table above — one subagent (or the lead directly) can do all ten.

**Two Group A items are NOT pure-mechanical — flag them to their subagent (or resolve first):**
- **#4** carries an open dependency: there may be no conventions doc, or the code may already violate it. The edit must encode the fallback (infer conventions from existing code, or prompt the operator) rather than assume the doc exists — don't apply it as a naive "go read the conventions doc."
- **#10** needs the language decision (drop "live test"; name it "validation against the genuine source of truth, escalating in cost") and routes the design-time half through the existing `code-experiment` skill. Broader than a one-liner; spans four files.

**Each subagent should:** read its target file(s), read the relevant recommendation section(s) in this doc for intent (the "What / why" + "The change"), author edits that fit the file's existing voice and the project's authoring disciplines, and respect the obfuscation rule (no source-project name, env var, binary, or stack detail — generalize). Verbatim analyst diffs were not preserved in this doc; the plain-language target + change is the source of intent, and the subagent adapts it to the current asset text.

**Resuming after a context clear:** read the summary table (status column), then the "Final disposition" section above, then this execution guide. Everything needed to act is in this doc.

## What I deliberately did *not* propose

- A mandatory external-review gate — that's the planned cross-model feature, not an asset edit.
- Any change that would carry a source-project name, tool, or language detail into a Firebreak asset — the obfuscation held and should stay held.
- Removal of any existing instruction — every analyst ran a necessity check and none found an existing instruction made redundant by these additions.
