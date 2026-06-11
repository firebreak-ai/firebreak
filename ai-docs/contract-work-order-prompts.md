# Prompts — contract-sequencing work-order rollout

Three prompts, run in order. Each is self-contained — paste into a fresh session after `/clear`.

Source of truth for all three: the brainstorm at slug **`firebreak-contract-sequencing-enumeration-brainstorm`** in the firebreak wiki (`.firebreak-wiki/sources/` and `.firebreak-wiki/wiki/summaries/`). Session 3 of that brainstorm holds the grilled work-order; both intent prompts treat the brainstorm as input material, not substitute.

---

## Prompt 1 — Slice-block hygiene fix

```
Pick up the slice-block hygiene fix from the firebreak wiki brainstorm at slug
`firebreak-contract-sequencing-enumeration-brainstorm` (see Session 3's work-order,
item 1 — "Hygiene fix PR").

This is a small bug-fix PR, not an SDL feature. No intent/PRD/design ceremony.

**Branch policy:** branch off the current `refactored-sdl` branch as
`fbk/slice-block-hygiene` (or similar). Merge back into `refactored-sdl` when done.

**Scope:**
1. Vocabulary alignment for the slice block. The gate (`assets/fbk-scripts/fbk/gates/spec.py`
   + `slices.py`) wins; update `assets/fbk-docs/fbk-sdl-workflow/feature-spec-guide.md`
   to match. Canonical vocabulary: `test-discipline: <new-contract |
   contract-preserving | contract-evolving | cross-cutting>` with field `covers:`.
2. Update any examples elsewhere in the docs that show the old vocabulary.
3. Fix `assets/fbk-docs/fbk-sdl-workflow/design-guide.md` Transition prose — currently
   asks "Would you like to move to task compilation?" but the design SKILL correctly
   invokes `/fbk-spec`. Same-family seam-break.
4. Add a regression test that exercises the canonical vocabulary against the gate.

**Two embedded decisions to grill before writing code** (use `/fbk-grilling` or just
walk them with the operator one at a time):

- **Fate of `contract:` and `retired-tests:` slice-block fields.** The current guide
  defines them; the gate does not read them. Options: (a) retire entirely — they
  capture intent the new vocabulary already covers; (b) relocate elsewhere if they
  capture intent the new vocabulary doesn't. Walk what each field was meant to do and
  whether any in-flight spec depends on them.
- **Coverage-backfill slice shape.** Options: (a) add `coverage-backfill` as a fifth
  shape with its own definition; (b) document that pure coverage-backfill maps to
  `cross-cutting` with a sentence explaining why. Wave-commit-model (later SDL
  feature) is robust to either — this is a taxonomy/documentation call.

**When done:**
- Open a PR into `refactored-sdl`.
- Append a one-line entry to `.firebreak-wiki/log.md` per wiki convention noting the
  hygiene fix shipped (slug `firebreak-contract-sequencing-enumeration-brainstorm`,
  reference the PR).
- Update the open-brainstorms Concluded entry at
  `.firebreak-wiki/wiki/syntheses/open-brainstorms.md` to add "Hygiene fix shipped as
  PR #N" or similar.

Read the brainstorm's Session 3 first to ground yourself in why this is being done.
```

---

## Prompt 2 — `interface-contracts` intent phase

**Run only after the hygiene fix has merged into `refactored-sdl`.**

```
Start the SDL for the `interface-contracts` feature. This is the first of two sibling
SDL features queued by the firebreak wiki brainstorm at slug
`firebreak-contract-sequencing-enumeration-brainstorm` (see Session 3's work-order,
item 2).

Run only the **intent phase** in this session — `/fbk-intent`. Do not advance to PRD,
design, spec, breakdown, or implement; each later phase gets its own session.

The brainstorm is **input material, not substitute.** It did the diagnostic work;
intent does the generative work (architecture, external interfaces, behavior list).
Use the brainstorm's diagnosis to inform intent, but produce the structured intent
artifacts the downstream agents will actually consume.

**Feature dir:** `ai-docs/interface-contracts/intent/`.

**Scope locked by the work-order:**
- Adds a `## Interface contracts` section to the spec authoring guide and the gate.
- Seven deterministic gate checks (section presence; five-field completeness per
  entry; `IF-NN` identifier pattern; non-empty `covers:`; AC-existence check on every
  covered ID; design-anchor completeness check; light seam-coverage approximation).
- LLM-judgment checks pushed to spec review, not the gate (mapping fit; signature
  correctness; missed-contract detection beyond the seam approximation; brownfield
  modifies-existing-contract detection).
- **Includes design-side standardization** — locks down `design/contracts.md` shape +
  identifier scheme so the design-anchor check is a hard check, not opportunistic.
  Touches `fbk-design/SKILL.md` and `assets/fbk-docs/fbk-sdl-workflow/design-guide.md`.

**Grill at intent (key open question):**
- **Reconciliation policy** — what happens when the spec evolves past design's
  contracts list (added a contract, renamed one, deleted one)? Who reconciles, when,
  and under what gate? The brainstorm flagged this as a real unknown; the design-anchor
  check is meaningless without an answer. Walk failure modes: stale design list vs
  evolved spec; spec edits that should but don't propagate to design; design edits that
  should but don't propagate to spec.

**Out of scope for `interface-contracts`:**
- Wave/commit model changes to breakdown/implement (those land in `wave-commit-model`
  later).
- Status taxonomy split (`parked` / `accepted-incomplete` — folded into
  `wave-commit-model`).

Read the brainstorm's Sessions 1–3 in full before drafting intent artifacts.
```

---

## Prompt 3 — `wave-commit-model` intent phase

**Run only after `interface-contracts` has shipped end-to-end.**

```
Start the SDL for the `wave-commit-model` feature. Second of two sibling SDL features
queued by the firebreak wiki brainstorm at slug
`firebreak-contract-sequencing-enumeration-brainstorm` (see Session 3's work-order,
item 3).

Run only the **intent phase** in this session — `/fbk-intent`. Do not advance to PRD,
design, spec, breakdown, or implement; each later phase gets its own session.

The brainstorm is **input material**. Sessions 1–2 grilled 11 questions about the
wave/commit model — those decisions are pre-decided inputs to intent, not open
questions to re-grill. They land in intent as architectural constraints. The
brainstorm's "Consolidated wave/commit sequence" (Session 2) is the load-bearing
shape; treat it as the starting point.

**Feature dir:** `ai-docs/wave-commit-model/intent/`.

**Scope locked by the work-order:**
- Wave/commit overhaul of breakdown + implement. Three sequential waves with commit
  boundaries: Wave 1 contracts + caller migration → Wave 2 tests → Wave 3 parallel
  subagents with per-task retry-until-pass → resolution dialog (when parked tasks
  exist) → Wave 4 integration tests → operator-reviewed squash.
- Retires `test-hashes.json`; the lock medium becomes commit + `git diff`.
- Lint/build gate at every wave boundary using project's existing tools (per-ecosystem
  detection).
- Branch policy: hard requirement, auto-create `fbk/<feature-name>` from HEAD if on a
  protected branch.
- Push policy: local-only until squash-at-completion.
- Wave 3 = parallel subagents, per-task retry-until-pass loop scoped to `test_tasks`,
  max-attempts default 3 (configurable), max-attempt exhaustion → task marked
  `parked` for operator disposition.
- Resolution dialog before Wave 4: per-task disposition (revise & rerun / revise spec
  & rerun / implement manually / accept-as-known-incomplete / mark superseded).
- Status taxonomy split: `parked` (transient, "needs operator disposition") +
  `accepted-incomplete` (terminal, "operator chose to ship without"). `superseded`
  already exists.
- Wave 3-vs-Wave 4 test classification derived from the integration-seam declaration
  (already required + already validated by test reviewer). Per-test-task `wave-class`
  override for integration tests not tied to a declared seam.
- Commit authorship: implement skill auto-commits at each wave boundary; final squash
  message generated and presented to operator for review before commits.

**Grill at intent (likely open questions):**
- Test interference in parallel execution — flagged in the brainstorm as
  project-config concern, not Firebreak's design responsibility. Decide whether
  Firebreak documents this for operators or stays silent.
- Coverage-backfill slice-shape handling — wave model handles it correctly regardless
  (single-wave, no agreement gap); decide whether intent needs to call this out
  explicitly or trusts the hygiene fix's resolution.
- Hook/extension points for projects that want different commit message conventions
  or different lint/build commands than the auto-detected default.
- Anything intent surfaces that wasn't on the brainstorm's radar.

**Out of scope for `wave-commit-model`:**
- The `## Interface contracts` section and design-anchor check (already shipped in
  `interface-contracts`).
- Slice-block vocabulary (already shipped in hygiene fix).

**Dependency note:** this feature consumes the `## Interface contracts` section
shipped by `interface-contracts` — Wave 1 pulls contracts directly from that section.
Intent should make the dependency explicit.

Read the brainstorm's Sessions 1–3 in full before drafting intent artifacts.
```

---

## Notes for the operator

- **Don't run more than one of these prompts at once** in the same project sandbox.
  Strict sequential per the work-order; sandbox containers prevent simultaneous
  in-project sessions anyway.
- **Branch state when each prompt starts:**
  - Prompt 1: branch off `refactored-sdl` to a hygiene-fix branch; merge back.
  - Prompt 2: on `refactored-sdl` (or whichever is current) after hygiene fix has
    merged. Intent is docs-only — no implementation branch needed yet.
  - Prompt 3: same as Prompt 2 — on the current development branch, intent is
    docs-only. The implement skill itself handles branch later (auto-creates
    `fbk/wave-commit-model` per its own grilled policy).
- **Where progress lives:** wiki log (`.firebreak-wiki/log.md`) for hygiene-fix and
  brainstorm-status updates; feature dirs under `ai-docs/<feature>/` for SDL
  artifacts.
- **If you reorder or re-scope:** the brainstorm's Session 3 work-order is the
  canonical decision record. Update it (append a Session 4 or similar) before
  starting a session against a different shape, so the prompts and the brainstorm
  don't drift.
