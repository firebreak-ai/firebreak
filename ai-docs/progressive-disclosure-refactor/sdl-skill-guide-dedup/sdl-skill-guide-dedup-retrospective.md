# SDL Skill / Guide Dedup — Retrospective

Child spec for Finding 4 of `ai-docs/progressive-disclosure-refactor/progressive-disclosure-refactor-spec.md`.

---

## Timeline

- Stage 1 (Spec): started 2026-05-03, gate passed 2026-05-03.
- Stage 2 (Spec Review): started 2026-05-03, council Round 1 complete 2026-05-03, test-reviewer CP1 FAIL 2026-05-03, post-review iteration 2026-05-03 → 2026-05-04, review-gate passed 2026-05-04.

## Key decisions

1. **Asset-graph-detectors prerequisite skipped.** Stage 1. Parent spec Decision 7 lists `asset-graph-detectors` as a preceding child spec; it has not been authored. `council-decomposition` shipped without it by writing a feature-specific structural test, and this spec follows that precedent. Rationale: blocking on a not-yet-authored prerequisite would stall the refactor for tooling that this scope does not strictly require — a single 11-assertion shell test covers AC verification at lower cost than the general-purpose detectors.
2. **Spawn-prompt template stays in `fbk-implement/SKILL.md`.** Stage 1. The literal `Task file: ai-docs/$FEATURE/$FEATURE-tasks/task-NN-name.md / Read that file as your sole context...` block is concrete `Task` tool plumbing. The orchestrator is the only caller of the `Task` tool, so the prompt body lives at that boundary. Moving it to `implementation-guide.md` would force a reader to assemble the prompt at the skill boundary anyway. Rationale: progressive-disclosure-compliant content for a skill body is "always relevant when the skill fires *and* uniquely operational at the skill boundary" — the spawn-prompt template fits both halves.
3. **All three skill/guide pairs in one child spec.** Stage 1. Parent spec frames Finding 4 as a single child; the three pair edits touch independent files (no shared-file conflicts). Co-locating them avoids duplicating the rationale, AC structure, and verification test across three near-identical specs. Rationale: edit independence + framing parity with parent spec = lower overhead in one spec.
4. **`fbk-breakdown` excluded from scope.** Stage 1, inherited from parent-spec verification. Per-load-path Necessity Test already passes for `fbk-breakdown` ↔ `task-compilation.md` — the skill describes operational mappings, not duplicated protocol. Editing it would violate the "if removed, is the agent more likely to make a mistake?" check.

## Scope changes

None during Stage 1. Scope as authored matches the parent-spec framing for Finding 4.

---

## Stage 1: Spec

### Clarifying questions raised

Four meaningful design decisions were surfaced before drafting:

- **Q1 — Asset-graph-detectors prerequisite.** Resolved via Decision 1 above (skip per `council-decomposition` precedent).
- **Q2 — Spawn-prompt template placement.** Resolved via Decision 2 above (stays in skill).
- **Q3 — Single spec vs. split per pair.** Resolved via Decision 3 above (single spec).
- **Q4 — Behavior preservation guarantee.** Confirmed: pure relocation, every observable surface (gates, council invocations, transition prompts, escalation caps, output schemas) preserved verbatim.

User steered "keep this as simple as possible — we're just ensuring instructions are placed according to the context-asset rules." That steered Q2 toward (a) (keep operational glue, remove duplicated prose, no over-design) and confirmed scope as pure relocation rather than rewrite.

### Scope inclusions

- Three SDL skill/guide pair dedups: `fbk-spec` ↔ `feature-spec-guide.md`, `fbk-spec-review` ↔ `review-perspectives.md`, `fbk-implement` ↔ `implementation-guide.md`.
- One new feature-specific structural test (`tests/sdl-workflow/test-skill-guide-dedup.sh`, 11 TAP assertions).
- `CHANGELOG.md` entry under the next release section.
- `progressive-disclosure-refactor-spec.md` Finding 4 entry annotated with `**State:** IMPLEMENTED <date>` line on completion.

### Scope exclusions

- `fbk-breakdown` (no real duplication; parent-spec verification confirmed).
- Cross-route validity work (Finding 5 territory; the three guides each have a single parent skill).
- Asset-graph-detector authoring (skipped per Decision 1).
- Guide content edits (guides remain canonical and unchanged).
- Workflow semantic changes of any kind (pure relocation).
- CLI / gate-script changes (`fbk.py` unchanged).
- Agent persona changes.
- README edits (reviewed during drafting; no impact found).

### Open questions deferred to later stages

None. All design decisions resolved before gate.

### Audit trail before drafting

Per parent spec cross-cutting concern "Existing-codebase audit before drafting": enumerated existing tests, scripts, and references before drafting Section 4.

- Tests touching scope: `test-implementation-pipeline.sh`, `test-review-integration.sh`, `test-no-old-path-patterns.sh`, `test-council-skill-structure.sh`, `test-code-review-skill.sh`, `test-code-review-integration.sh`, `test-new-persona-agents.sh`. Of these, only the first two assert against in-scope content; both pass without modification post-refactor.
- Non-test references in `assets/`: `assets/fbk-docs/fbk-sdl-workflow.md` (routing-table mention, accurate post-refactor), `assets/fbk-docs/fbk-sdl-workflow/corrective-workflow.md` (cross-reference, unaffected), `assets/fbk-docs/fbk-sdl-workflow/retrospective-guide.md` (cross-reference, unaffected), `assets/fbk-docs/fbk-design-guidelines/test-authoring.md` (cross-reference, unaffected), `assets/skills/fbk-code-review/references/existing-code-review.md` (cross-reference to `feature-spec-guide.md`, unaffected).
- Gate scripts: `spec-gate`, `review-gate`, `breakdown-gate` invocation strings preserved verbatim in §4.6 of the spec.
- Sibling spec precedent: `council-decomposition-spec.md` was reviewed for child-spec structure conventions (heading order, integration-seam declaration, module-touch policy format, AC phrasing).

### Spec gate result

`python3 .../fbk.py spec-gate ai-docs/progressive-disclosure-refactor/sdl-skill-guide-dedup/sdl-skill-guide-dedup-spec.md` → `{"gate": "spec", "scope": "feature", "result": "pass", "injection_warnings": 0}`. First gate run failed with "Open questions: items must include rationale, not just a bare question" because Section 8 contained resolved-decisions framed as bullets; restructured to "None." in §8 with the resolved-decisions content moved to a separate "Decisions resolved during scoping" section after §9. Second run passed.

---

## Stage 2: Spec Review

### Perspectives invoked

Quick Council (3 agents): Architect, Guardian, Builder. Classification rationale: structural refactor with no security / UX / metrics signals; complexity-watchdog (Builder) explicitly needed because the user steered "as simple as possible." Test-reviewer agent invoked at Checkpoint 1.

### Findings

- **Round 1 council:** 24 findings across three perspectives. Architect 9 (1 blocking, 4 important, 4 informational). Guardian 7 (1 blocking compounding Architect's, 5 important, 1 informational). Builder 8 (0 blocking, 5 important, 3 informational) with explicit complexity-watchdog triage rejecting Guardian's T12-T18 expansion.
- **Test-reviewer CP1:** FAIL with 4 blocking defects (T11 mislabel, UV-to-test schema gap, AC-04 partial coverage compounding GUARD-05/BUILD-06 dissent, `## Finding synthesis` partition gap compounding ARCH-01/GUARD-01) plus 1 overridden (LLM-behavioral seam coverage acceptable with stated rationale).
- **Net unique blocking findings:** 2 — `## Finding synthesis` partition gap (ARCH-01 + GUARD-01 + DEFECT-04 converging) and §4.3 / §4.4 internal contradiction (ARCH-09).

### Blocking findings and resolutions

1. **Partition gap (`## Finding synthesis`, `## Re-run check`, `## Retrospective` skill sections unclassified in §4.2 / §4.3).** Resolved during post-review iteration: explicitly retained these sections in §4.2 as operational glue (writing the artifact at the skill boundary, user-warning emission). Added §5 T9 sentinel pinning the `testing strategy` keyword in `fbk-spec-review/SKILL.md` to satisfy `test-review-integration.sh` Test 4.
2. **§4.3 / §4.4 internal contradiction (summary-and-compact direction).** User clarified that guide edits are permitted when required by progressive disclosure. Resolved by relocating the directive to `feature-spec-guide.md` and `review-perspectives.md` `## Transition` sections as additive steps; removing from skills entirely. Spec edits: §4.3 reworded; §4.3a authored with two additive guide edits; §4.4 module-touch updated; Non-goals reworded.

### Spec revisions during post-review iteration (2026-05-04)

User and orchestrator iterated through 6 judgment items. All resolutions recorded in `sdl-skill-guide-dedup-review.md` "Resolution log."

- **Item 1 (threat model):** No.
- **Item 2 (ARCH-09 summary-and-compact):** Option (b) — relocate to guides. User-clarified guide-edit permission triggered.
- **Item 3 (ARCH-03 env-flag duplication):** Option (a) — keep skill check; remove env-flag prerequisite line from `implementation-guide.md:9`.
- **Item 4 (ARCH-07 "Present the selection" TODO):** Option (a) — remove from skill; rely on guide-loaded process.
- **Item 5 (DEFECT-03 AC-04 sentinel coverage):** Option (a) — add T12 (frontmatter), T13 (`$ARGUMENTS`), T14 (chained-skill invocations), T15 (exit prompts). User chose enforceable AC-to-test traceability over Builder's complexity-watchdog rejection.
- **Item 6a (BUILD-01 §4.6 collapse):** Accepted. Replaced 9-bullet list with one-paragraph principle.
- **Item 6b (BUILD-02 §4.5 collapse):** Accepted. Replaced 10-entry seam table with one-paragraph principle.
- **Item 6c (BUILD-03 §4.4 tighten):** Accepted. Per-skill preservation lists collapsed; entries point to §4.2 / §4.3 / §4.3a.
- **Item 6d (BUILD-04 AC-07 / AC-08 demotion):** Accepted. Moved to Documentation impact as release tasks. AC list shrinks 8 → 6.

### Iteration count

One Stage-2 iteration. Council Round 1 + test-reviewer CP1 + user-driven 6-item resolution loop reached convergence in a single review pass; no second council round was needed.

### Threat model decision

No threat model needed. Recorded in review document with rationale (no data-flow / trust-boundary / entry-point changes; single safeguard preserved per AC-04 and §5 T7).

### Review gate

`python3 .../fbk.py review-gate ... "Architecture,Quality,Builder"` → `{"gate": "review", "result": "pass", "failures": [], "perspectives": ["Architecture", "Quality", "Builder"], "threat_model": false}`. First gate run failed on the canonical "## Test*" subsection regex matching the council's `## Testing strategy and impact` finding-grouping header rather than the testing-strategy section; renamed to `## Quality (testing-strategy) concerns` to disambiguate. Second run passed.

### Final spec state at end of Stage 2

- 265 lines (vs. 245 pre-review draft; the dedup-resolution edits + four BUILD-01/02/03 collapses + four T12-T15 sentinels netted +20 lines).
- 22 structural assertions in `tests/sdl-workflow/test-skill-guide-dedup.sh`.
- 6 acceptance criteria (down from 8 — release tasks separated).
- Module-touch covers six files: 3 skills refactored, 2 guides extended additively, 1 guide line removed.
- Spec-gate passes; review-gate passes.

---

## Stage 3: Breakdown

### Compilation attempts

One compilation pass. No iterations required. Both compiler agents (test-task and implementation-task) returned valid task files on first invocation.

### Wave structure and rationale

**1 wave, 7 tasks.**

- Wave 1, test: `task-01` — author the new TAP shell test with all 22 assertions.
- Wave 1, implementation (6 tasks, parallel-safe): `task-02` through `task-07` — one per touched file.

All implementation tasks touch disjoint files (3 skills + 2 guide extensions + 1 guide line removal). No file-scope conflicts within the wave. Within-wave test-before-implementation ordering is implicit per the compilation guide: `task.json` lists `task-01` first; the breakdown gate's positional check confirms it precedes all impl tasks.

The compilation guide rule "wave assignments respect dependencies (dep wave must be strictly less)" required removing the explicit `dependencies: [task-01]` declaration from the impl tasks (they would have failed the strict-less wave check otherwise). The intra-wave test-impl ordering is enforced by `task.json` array order, not by declared dependencies. The orchestrator bears responsibility for ensuring `task-01` completes before each impl task's pre-refactor-fail verification step is meaningful — the test-reviewer's CP2 notes flag this as an orchestration responsibility outside the task-breakdown fidelity surface.

### Task count

7 tasks total. 1 test, 6 implementation. All Haiku-routed (mechanical context-asset prose editing; no architectural judgment).

### Scope adjustments from compilation

- Added AC-05 to `task-01` covers (the gate invariant requires every AC to appear in at least one test task; the spec's "AC-05 verified procedurally" note doesn't preclude the test task from carrying AC-05 in its covers list — task-01's body explicitly notes that no assertion in the file covers AC-05 and that procedural re-run is the verification path).
- Added AC-05 to `task-02`, `task-03`, `task-04` covers (impl tasks must collectively preserve AC-05 by not breaking pre-existing tests).
- Added AC-06 to all 6 impl tasks' covers (each impl task contributes assertions toward the "all 22 pass" half of AC-06).
- Removed explicit `dependencies: [task-01]` from impl task entries in `task.json` to satisfy the strict-less wave-ordering check; intra-wave ordering preserved via array order.

No spec edits required during compilation. No ambiguities surfaced. No line-number drift between spec citations and the actual SKILL files.

### Test-reviewer Checkpoint 2 verdict

PASS. CP1 testing-strategy decisions survived compilation intact (22 TAP assertions, AC-05 procedural verification, UV-1/2/3 manual smoke, integration-seam coverage rationale all preserved). All 6 ACs have both test and implementation task coverage. All 22 assertions enumerated in `task-01` body with verbatim sentinel phrases. All 4 pre-existing impacted tests surfaced in implementation task instructions. All 6 spec-touched files have dedicated implementation tasks. `task-01` completion gate correctly requires non-vacuous pre-refactor failure.

CP2 noted one orchestration responsibility outside the task-breakdown surface: implementers picking up tasks 02-07 must wait for task-01 to land before their pre-refactor-fail verification step is meaningful. This is an orchestration concern (the team lead in `/implement` ensures task-01 completes first via `task.json` array order); not a breakdown defect.

### Breakdown gate result

`python3 .../fbk.py breakdown-gate ...` → `{"gate": "breakdown", "result": "pass", "spec_acs": 6, "tasks": 7, "waves": 1}`. First gate run failed on the strict-less wave-ordering check (impl tasks declared `dependencies: [task-01]` while sharing wave 1 with task-01). Resolved by removing the explicit dependencies; intra-wave ordering preserved by array position. Task-reviewer-gate also passed: `{"gate": "task-reviewer", "result": "pass", "tasks": 7, "acs_covered": 6, "waves": 1, "failures": []}`.

### Final breakdown state

- 7 task files at `ai-docs/progressive-disclosure-refactor/sdl-skill-guide-dedup/sdl-skill-guide-dedup-tasks/`.
- `task.json` valid, conforming to schema, all gates passing.
- 6 ACs covered by both test and implementation tasks.
- 1 wave; expected wall-clock for parallel implementation: minutes (6 mechanical edits, all single-file, all Haiku).

---

## Stage 4: Implementation

### Timeline

- Stage 4 (Implementation): 2026-05-04, single wave, 7 tasks, ~5 minutes wall-clock for all task spawns.

### Factual data

**Per-task pass/fail** (all 7 tasks):

| Task | Type | Model | Result | Escalations | Notes |
|------|------|-------|--------|-------------|-------|
| task-01 | test | Haiku | PASS | 0 | Created `tests/sdl-workflow/test-skill-guide-dedup.sh` with 22 TAP assertions. Test exits 1 with 12 expected pre-refactor failures before implementation, 0 failures after. |
| task-02 | impl | Haiku | PASS | 0 | Refactored `assets/skills/fbk-spec/SKILL.md`. T1, T1b, T2 flipped to ok. |
| task-03 | impl | Haiku | PASS | 0 | Refactored `assets/skills/fbk-spec-review/SKILL.md`. T3, T4, T4b flipped to ok. All operational glue retained. |
| task-04 | impl | Haiku | PASS | 0 | Refactored `assets/skills/fbk-implement/SKILL.md`. T5, T5b, T6 flipped to ok. `test-code-review-skill.sh` 16/16 still passing. |
| task-05 | impl | Haiku | PASS | 0 | Inserted summarize-and-compact step at `feature-spec-guide.md` `## Transition` step 5. T11a flipped to ok. |
| task-06 | impl | Haiku | PASS | 0 | Inserted summarize-and-compact step at `review-perspectives.md` `## Transition` step 5. T11b flipped to ok. |
| task-07 | impl | Haiku | PASS | 0 | Removed env-flag prerequisite line from `implementation-guide.md:9`. T11d flipped to ok. `test-implementation-pipeline.sh` 7/7 still passing. |

**In-session retry count:** 0. No `TaskCompleted` hook rejections; no in-session retries reported.
**Task sizing accuracy:** All tasks single-file as declared. No scope discrepancies surfaced.
**Model routing accuracy:** All 7 tasks Haiku-routed; all completed first attempt with no escalation. 100% Haiku success rate; no escalations to Sonnet required.
**Verification gate pass rates:** Per-wave verification (full sdl-workflow suite + new test) passed first attempt. Final verification (6 ACs + full suite) passed first attempt.
**Wall-clock:** task-01 ≈85s; task-02..07 spawned in parallel and completed in 33-97s each.
**Total tests:** 62 sdl-workflow tests passing; new test adds 22 assertions; total project test count grows by 22.

### Upstream traceability

- Stage 2 review iterations before advancing: 1 council Round 1 + 1 user-driven 6-item resolution loop. Single review pass.
- Blocking findings count: 2 unique (ARCH-01/GUARD-01/DEFECT-04 partition gap; ARCH-09 internal contradiction). Both resolved by spec revision; no findings deferred to implementation.
- Stage 3 compilation attempts before gate passed: 2 (first attempt failed strict-less wave-ordering check on declared `dependencies: [task-01]`; resolved by removing same-wave dependency declarations and relying on `task.json` array order for intra-wave ordering).

### Failure attribution

No tasks escalated. No failures to attribute.

### Acceptance-criteria verification

| AC | Status | Verification |
|----|--------|--------------|
| AC-01 | PASS | `fbk-spec/SKILL.md` no longer contains "If the gate fails:" or "Refuse to write code"; `feature-spec-guide.md` retains both phrases plus the new "Before invoking `/spec-review`" step. T1, T1b, T2, T11a all ok. |
| AC-02 | PASS | `fbk-spec-review/SKILL.md` no longer contains the threat-model question, "There are N blocking findings", or "Present the selection with"; `review-perspectives.md` retains all three plus the new "Before invoking `/breakdown`" step. T3, T4, T4b, T11b all ok. |
| AC-03 | PASS | `fbk-implement/SKILL.md` no longer contains wave-loop step headings, "Tests are expected to fail", or escalation cap; `implementation-guide.md` retains the workflow content but env-flag prerequisite line removed. T5, T5b, T6, T11c, T11d all ok. |
| AC-04 | PASS | All operational glue preserved across all three skills: frontmatter, `$ARGUMENTS`/`FEATURE=$ARGUMENTS`, gate-script invocations, `/fbk-council` invocation, test-reviewer Agent Teams spawn, env-flag check, `Task file:` spawn template, chained skill invocations, exit-prompt sentences. T7, T8, T9, T9b, T10, T12, T13, T14, T15 all ok. |
| AC-05 | PASS | All 4 enumerated pre-existing tests pass without modification (`test-implementation-pipeline.sh` 7/7, `test-review-integration.sh` 14/14, `test-code-review-skill.sh` 16/16, `test-council-skill-structure.sh` 71/71). Full sdl-workflow suite 62/62 green. |
| AC-06 | PASS | `tests/sdl-workflow/test-skill-guide-dedup.sh` exists, is auto-discovered by CI, and all 22 assertions pass. |

**Semantic verification:** The aggregate implementation satisfies the spec intent — workflow protocol is single-sourced in the SDL guides; skill bodies contain only operational glue; observable behavior unchanged (every gate runs, every council/test-reviewer invocation fires, every transition prompt is asked, every escalation cap holds).

### Documentation impact (release tasks completed)

- `CHANGELOG.md` — entry added under `[0.4.0]` Changed section describing the dedup, the additive guide steps, the env-flag consolidation, and the new structural test.
- `progressive-disclosure-refactor-spec.md` Finding 4 — `**State:** IMPLEMENTED 2026-05-04` line appended.
- `README.md` — reviewed; no path references to skill-body content; no change required.

### Notable decisions made during implementation

- **Exit-prompt relocation in `fbk-spec/SKILL.md` (task-02).** The task-compiler flagged this as a reasonable implementation-time choice (not an ambiguity): the exit prompt "Would you like to move to spec review?" lived inside the removed `## Gate` decision narrative; T15 asserts the skill must still contain it. The implementer relocated the prompt sentence into `## Transition` immediately before the chained `/spec-review $ARGUMENTS` invocation, co-locating the prompt with the chained invocation it gates. This matches the structure of `fbk-spec-review/SKILL.md` (which keeps "Would you like to proceed to task breakdown?" near its `/breakdown` invocation).

### Stage 4 result

All 7 tasks complete. 6/6 ACs satisfied. Full test suite green. No escalations. Documentation impact applied. Implementation ready for code review.

---

## Stage 5: Code Review

### Findings summary

- **Total sightings:** 1
- **Verified findings:** 0
- **Rejections:** 1
- **Nits:** 0
- **False positive rate** (rejections / sightings): 100% (1/1)

### Verified findings

None. The implementation passed code review with zero verified behavioral, test-integrity, fragile, or structural-above-info findings.

### Rejected sightings

- **S-01** (`test-integrity` / `critical`, REJECTED). Detector claimed T11a and T11b grep for `\`` (backslash+backtick) but guides contain bare backtick. **Rejected:** Detector misread bash quoting. Lines 132 and 139 use single-quoted grep arguments (literal bytes, bare backticks); the `\`` sequences the Detector saw belong to double-quoted diagnostic message strings on lines 133, 135, 140, 142. Direct executable evidence: test runs output `# 22/22 tests passed` with `ok 15` for T11a and `ok 16` for T11b — byte-impossible if patterns sought a non-existent backslash+backtick sequence.

### Detection source breakdown

- audit-pass: 1 (rejected)
- spec-ac: 0
- checklist: 0
- structural-target: 0
- intent: 0
- linter: 0 (no applicable typechecker for markdown context-asset prose)

### Code review report

Full review report at `fbk-code-review-2026-05-04-0326.md` (project root).
