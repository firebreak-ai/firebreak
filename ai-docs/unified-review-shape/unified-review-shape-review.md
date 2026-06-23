# Unified Review Shape — Spec Review

Perspectives: Architecture, Quality, Over-engineering / pragmatism

**Mode:** discussion (3 agents). **Spec gate:** pass (structural). **Council state:** CLEAN after one revision round. All six blocking findings were resolved by spec revision and re-verified by the agent that raised each (re-verification confirmed against live code, not prose). Three convergent/important follow-ons from the re-verification were also folded in. The resolution log is at the end of this document. The independent test-review may now run against the stabilized spec.

**Threat model determination:** No structured threat model. Rationale: the feature introduces no new external entry point, no auth/access-control change, no data store, and no external API. It is an internal reorganization of the review pipeline. One security-flavored property — the agent isolation invariant (no researcher framing reaches the challenger) — is reviewed structurally under Architectural soundness and Quality rather than as a STRIDE threat model. (A finding below notes that one existing trust-boundary control, the round-log allowlist projection, is at risk from a spec decision — that is recorded as a blocking quality/architecture finding, not a new threat surface.)

---

## Architectural soundness

The shape itself is sound — clean separation of loop / lens / preset / role, correct vertical decomposition, no parallel-path defect. The blockers are all on the no-break surface: the spec under-enumerated the callers its own no-break promise must repoint.

**Blocking — Agent registry names are bare, not `fbk-`-prefixed; the repointing targets are wrong as written.**
The spec names the four agents to remove using their filenames (`fbk-code-review-detector`, etc.), but the `name:` frontmatter that `subagent_type` callers actually resolve is the bare form for three of four: `code-review-detector`, `code-review-challenger`, `test-reviewer`; only `fbk-fresh-eyes-reviewer` is prefixed. A migration that greps for the prefixed names misses every real caller. Resolution: the spec must repoint by the real registry names (bare for three, prefixed for one), state the two new agents' exact `name:` values, and define the grep that must return zero hits as the bare names.

**Blocking — Three unenumerated Python callers on the production telemetry path.**
The no-break promise omits three files that hardcode the old agent names: `fbk/shapes.py` (`_PERSONA_TO_SHAPE` maps `test-reviewer` and `code-review-detector` to the "review" work-shape, consumed by `harvest.py`), `fbk/capture/known_agents.py` (`FALLBACK_AGENTS` lists all four), and `tests/test_shapes.py` (asserts the mappings). After the rename, spawns of the new agent names resolve to no shape → "unmapped persona" warning → the observability telemetry record loses these reviews. Resolution: add all three to the module-touch policy and decide whether to add the new names (and keep or drop the old) in the shape and known-agent tables.

**Blocking — Two unenumerated skill callers that depend on the detector's mode mechanism.**
`fbk-quality-scan` spawns `fbk-code-review-detector` in "quality-opportunity mode" and `fbk-doc-reconcile` spawns it in "doc-reconciliation mode." Both are declared untouched non-goals, yet both depend on the multi-mode detector being deleted. The new generic researcher persona has no modes. Removing the detector silently orphans both working callers. Resolution: either keep these two on a surviving agent, or fold their modes into the lens mechanism (a quality-opportunity lens and a doc-reconcile lens) and enumerate them as repoint targets — a real decision that widens the no-break surface.

**Important — `project_round_entries()` test impact is understated (see also the blocking quality finding).** The only production caller is `code_review.py`; the change does not break it. But the existing test pins exact list equality against `_PROJECTION_EXPECTED`, not a superset — the fixture must be rewritten, not appended to.

**Important — `coherence-gate` registration point named imprecisely.** The mechanism is the `COMMAND_MAP` dict in `fbk/__init__.py` (mirroring the eight existing `*-gate` entries), not an argparse subparser in `fbk.py` (a pure dispatcher). The spec should name `fbk/__init__.py:COMMAND_MAP` as the edit point.

**Informational — coherence breakdown-spawn insertion point verified to exist.** `fbk-breakdown/SKILL.md` runs `task-reviewer-gate` then invokes `test-reviewer` directly then proceeds to the breakdown gate; the three spec edits land cleanly between those steps.

**Informational — contract drift: all 8 IF-S contracts are absent from the design page, by deliberate design, and acceptable.** `design/contracts.md` mints no IF-D registry and routes each spec contract to a named design-page location; no count/name mismatch. The only cost is that a later iteration has no design-origin anchor to diff against — prose is the only backstop. Worth a decisions-log note if IF-D registries become standard.

**Informational — the cross-model model-slot (IF-S-06 / AC-12) is named but not pinned.** "Model selected per preset" names no concrete config key or location. No consumer exists this iteration (cross-model is a non-goal), so it does not block — but the slot is "named," not "clean"; the first cross-model preset will have to invent the field.

---

## Quality: testing strategy and impact

**Blocking — The `severity_breakdown` projection claim is not additive; it reverses a tested trust-boundary control, putting AC-01 and AC-11 in direct conflict.**
`project_round_entries()` is an allowlist projector whose documented purpose is dropping untrusted keys before they reach the capture events file. Two tests lock this: `test_valid_round_file_emits_event` asserts the literal string `severity_breakdown` does **not** appear in the events file ("must not survive gate projection"), and `test_round_log_projected_before_event_write` pins projection to raised/survived/enum-severity only. So "enrich the gate to carry `severity_breakdown` through projection" (AC-01) cannot coexist with "every existing gate test stays green" (AC-11) — they contradict. This finding directly reverses the operator's earlier "enrich the gate" decision, which rested on the field being "silently dropped" rather than being a deliberate, tested control. Resolution requires an operator decision (see below): keep the events-path projection locked and surface the per-severity metric on a different, non-trust-boundary output, or explicitly relax the control with stated justification and named test rewrites.

**Blocking — The isolation-invariant seam test (AC-05) is vacuous; the feature's central safety property has no real covering test.**
Normalization is a prose instruction to the loop coordinator, not a callable function. A test that constructs an object and checks its keys exercises nothing about whether the real skill strips researcher framing before injecting into the challenger spawn — which is where a leak would happen. Resolution: either make normalization an actual callable in the Python layer the preset must route through (so a unit test on real `normalize()` has teeth), or honestly downgrade AC-05's verification to the source-of-truth tier — inspect a real challenger spawn payload during a live two-role run — and stop claiming a seam test covers it.

**Blocking — "Recorded unresolvable" (AC-07) names a status the challenger schema does not define.**
IF-S-03's status values are verified / verified-pending-execution / rejected / rejected-as-nit. "Unresolvable" is none of them. A test cannot assert a state the contract has no field for. Resolution: add an `unresolvable` status (or an explicit field) to IF-S-03 and define where the record lands, then say what the test asserts. (Paired with AC-06's "named loud failure," which likewise never says what the error contains or how a test asserts it — specify the observable: e.g., the launcher raises a named error containing the unresolved lens path and exits non-zero.)

**Important — "Structurally identical" (AC-04) is weak enough to pass on a content regression.** The baseline test checks three headings + dash format + empty-critical result, all of which a gutted fresh-eyes (fewer detection passes) still satisfies on a clean input. Tighten: run AC-04 against a fixed input with a planted critical defect and assert that specific observation still appears.

**Important — AC-13 / AC-14 / AC-15 verification methods are real but must become named executable checks, not process promises.** AC-13: a grep over `assets/**` asserting zero occurrences of the four bare agent names as `subagent_type` (cheap, catches the partial-migration defect). AC-14: a test asserting the test-integrity audit appears in `shared-detection.md`, no longer in `detection-audits.md`, and is referenced by both lenses. AC-15: a lens-section parser enumerating the required sections from `lens-format.md` per lens — and it must handle the conditional sections (verdict contract vs. observation format) or it will false-fail fresh-eyes.

**Important — `test_gates_review.py` is unmentioned in the impacted-tests list.** A test file literally named for review must be checked for overlap before the no-break set is called complete.

**Informational — mocking justification honest, validation ladder well-ordered.** No defect; matches the real test code.

**Informational — the degenerate fresh-eyes round-history (`survived == raised`) deserves one explicit unit assertion**, and confirm it is in-memory bookkeeping only — fresh-eyes writes no round artifact today, and "external behavior unchanged" should explicitly exclude any new on-disk write.

---

## Over-engineering / pragmatism

**Blocking — "Only the gate layer changes" is false: the loop coordinator's validation machinery lives in `pipeline.py`, hardcoded to code-review's domain.**
The live code-review skill delegates schema validation, the type-severity validity matrix, domain/severity filtering, and to-markdown conversion to `fbk/pipeline.py`, which hardcodes `VALID_TYPES`, `VALID_COMBINATIONS`, and `REQUIRED_FIELDS` to code-review's vocabulary. The design's loop says the coordinator validates against enums "defined in the loaded lens," but today that validation only knows code-review's enums. For test / coherence / task / test-plan presets to route through the same loop, either `pipeline.py` becomes lens-parameterized (a real, untested-in-spec code change that contradicts the prose-substrate-only claim B-021), or each non-code preset validates in prose with no script backing (abandoning the deterministic validation code-review relies on, and re-creating the per-type divergence this feature exists to kill). This decision must be made and scoped before convergence; it changes the size of the work, the test plan (zero `pipeline.py` tests are named), and the `lens-format.md` contract (lenses must then carry a machine-readable matrix).

**Important — Code review is not a "thin preset"; the label understates the largest slice.** ~70% of the 141-line skill survives migration (intent extraction with a user checkpoint, linter pre-work, broad-scope multi-unit review with cross-unit dedup, the four-pass post-loop sequence, stuck-agent recovery). Only the loop body lifts. The `code-review-preset` slice description and effort estimate should say so; "thin preset" is accurate only for fresh-eyes and test-review.

**Important — Test-review gaining a challenger is a behavior change mislabeled `contract-preserving`.** The verdict line is byte-identical, but the verdict *value* can flip — a finding that reaches the verdict today can be rejected by the new challenger. At the pre-lock checkpoint that changes the gate outcome (it triggers hash-lock application). Relabel the slice as a behavior change with a preserved artifact format, and add a source-of-truth test case where the challenger overturns a finding, so the new path is exercised, not just the format.

**Important — The agent-removal step is a forced big-bang; pin deletion as the terminal action.** There is no safe intermediate state — the moment the agent files are deleted, every still-unrepointed caller breaks. Recommend the spec name the exact grep that must return zero hits before deletion and make "old agent file removed" the last action in the wave, after every repoint lands and a source-of-truth SDL pass is green.

**Important — Sequencing: stage the four no-live-caller presets behind the three live migrations.** Not a scope reversal (all six still ship). Recommend wave order: (1) loop-spine + role-agents + lens-format; (2) the three live presets + spec-review handoff + agent removal, prove no-break; (3) coherence / test-plan / task as additive new skills. Make the wave boundary explicit so greenfield authoring does not interleave with the contract-preserving cutover.

**Informational — Confirm coherence's input exists at breakdown time.** The coherence lens reads `design/contracts.md` + the spec's seams section. Be explicit that "contracts.md absent entirely" routes to trivial-accept (AC-10), not to the IF-S-01 missing-source loud failure.

---

## Cross-model review (GPT-5.5, operator-requested)

After the council reached clean, the operator requested two independent GPT-5.5 (high reasoning) passes via the Codex CLI: a fresh-eyes review of the spec (coherence, disambiguity, module organization) and a separate review of the test plan. Both returned "revise/strengthen first" and **found four Critical issues the in-pipeline council missed** — the cross-model diversity value the unified shape is being built to formalize, demonstrated on its own spec. All resolved in revision round 2.

**Critical (spec pass):**
- `id` ordering contradiction — the validator's `REQUIRED_FIELDS` includes `id`, but the design assigns sighting IDs *after* validation and the researcher omits `id`; finding-mode candidates could all be rejected. Resolved: the researcher-candidate `required` set excludes `id`; the pipeline assigns `S-NN` after validation (IF-S-01, IF-S-09, pipeline.py bullet, lens-format §4).
- `pipeline.py` parameterization under-specified — no lens-matrix format, loader, CLI path, or `fbk-presets.json` replacement. Resolved: pinned `load_lens_matrix()` → `LensVocabulary`, the `lens-matrix` block, `validate_sighting(finding, vocab)`, and the domain/severity-filter replacement (IF-S-09, AC-16, tests).
- Coherence gate bypassable — wired only into breakdown; a direct `/fbk-implement` runs only the breakdown gate. Resolved: `coherence-gate` enforced on the `fbk-implement` prerequisite path (AC-19, IF-S-05, module-touch, slice, structural test).
- Wave ordering orphaned `test-reviewer` — agent deletion in wave 2, but `task-review-preset` (which repoints breakdown's live caller) in wave 3. Resolved: `task-review-preset` moved into the repoint wave; deletion remains terminal.

**Critical (test-plan pass):** the AC-13 zero-caller grep searched `subagent_type` fields, but Firebreak skills name agents in prose; resolved to a prose grep over active assets. Scan-mode bypass and the unresolvable status both need coordinator-level / structural assertions rather than model behavior; resolved.

**Substantive, both passes:** stale spec non-goal (quality scan), stale `design/contracts.md` "enrich the gate" note, design pages lacking `output_mode`/scan, `unresolvable` missing from `role-agents.md`, round-log `severity` semantics undefined, task-review blocking semantics undefined, and several "manual source-of-truth" seams (coherence-subagent wiring, council exclusion, cited-source injection) that can be **repeatable structural asset tests** against the stable Markdown skills — all resolved, with the source-of-truth tier narrowed to only the model-behavioral halves.

The design pages (`review-loop.md`, `lens-format.md`, `role-agents.md`, `coherence-lens.md`, `contracts.md`) were updated alongside the spec so the installed reference docs do not ship stale. Spec gate re-run after round 2: pass, zero injection warnings.

## Threat Model

Decision: **No** structured threat model. Rationale: this feature reorganizes the internal review pipeline — no new external entry point, no authentication or access-control change, no data store, and no external API. The one security-flavored property, the agent isolation invariant (no researcher framing reaches the challenger), is reviewed structurally under Architectural soundness and Quality and is now backed by a real `normalize()` unit test plus a source-of-truth spawn-payload inspection. No project-level threat-model update is warranted. (Operator confirmed this determination.)

## Testing strategy coverage

The spec's testing strategy carries all three required categories; the independent test-review verified each requirement maps to a test that would fail on a regression (verdict: accepted after one revision round).

- **New tests needed:** present — unit tests for `normalize()`, the parameterized validator and its backward-compat path, the coherence gate, telemetry-table resolution, and the scan-mode bypass; integration tests for the loud-lens-failure and unresolvable-source seams and the scan-only output contracts; structural tests for lens conformance, single-source detection, and the zero-caller grep; and source-of-truth checks for the four prose-orchestration seams.
- **Existing tests impacted:** present — `test_gates_code_review.py` (no change, trust boundary preserved), `test_shapes.py` (new agent names), `test_capture_report_integration.py`, `test_gates_intent.py`/`test_gates_design.py` (fresh-eyes, no change), `test_gates_review.py`/`test_gates_breakdown.py`/`test_gates_task_reviewer.py` (checked, no overlap), and `test_pipeline.py` (default-fallback green).
- **Test infrastructure changes:** present — new test files (`test_gates_coherence.py`, `test_pipeline_normalize.py`, `test_lens_format.py`), coherence-review fixtures in each verdict state, and a planted-critical-defect fresh-eyes baseline. No mocking introduced.

Note carried from the independent test-review: the four prose-orchestration seams (handoff routing, cited-source positive path, council exclusion, coherence subagent) are verified by a single manual source-of-truth SDL pass, not a repeatable automated test — the correct ceiling for the prose substrate. They should graduate to automated assertions if they ever move into code.

## Summary

| Severity | Count | Concern split |
|---|---|---|
| Blocking | 6 | Architecture 3, Quality 3, Pragmatism 1 (the pipeline.py finding) — counting the severity_breakdown finding once under Quality |
| Important | 8 | Architecture 2, Quality 3, Pragmatism 3 |
| Informational | 7 | — |

Three blocking findings required an operator decision before the spec could be revised to a clean state: (1) the `severity_breakdown` trust-boundary conflict — which reverses the earlier "enrich the gate" call; (2) the `pipeline.py` parameterization-vs-prose decision — which determines whether this feature touches executable validation code beyond the gate layer; (3) the fate of `fbk-quality-scan` and `fbk-doc-reconcile`, which depend on the multi-mode detector this feature deletes. The remaining blockers (bare agent names, the three telemetry-path Python callers) and all important findings were mechanical spec corrections once those decisions landed.

---

## Resolution log (revision round 1)

**Operator decisions (three blockers):**
- Round-history metric → **keep the trust boundary locked.** Gate left unchanged; loop writes only allowlisted round fields; per-severity detail moves to the human report. Reverses the earlier decision.
- Validation machinery → **parameterize `pipeline.py` per-lens.** The matrix/required-field validation is generalized to read the active lens's vocabulary (default code-review), and `normalize()` is added so the isolation invariant is unit-testable.
- Orphaned skills → **fold quality-scan and doc-reconcile into the shape** as degenerate scan-only presets; detector deletes cleanly. PRD non-goal reversed; behaviors B-025/B-026 added.

**Mechanical resolutions:** agent repointing now uses the real bare registry names; the three telemetry-path files (`shapes.py`, `known_agents.py`, `test_shapes.py`) are in scope with a covering test; agent deletion pinned as the wave's terminal action; coherence-gate registration named at `fbk/__init__.py:COMMAND_MAP`; code-review relabeled (not a thin preset); test-review relabeled `contract-evolving` with the verdict-value flip and an overturn test; the isolation test grounded on the real `normalize()` callable; `unresolvable` added to the challenger status enum; AC-04 grounded on a planted-defect baseline; AC-13/14/15 made named executable checks; `test_gates_review.py` checked (no overlap).

**Re-verification (each agent re-checked its own blockers against live code): all six resolved.** The re-verification surfaced three new non-blocking follow-ons, all folded in:
- **Scan-only validator collision** (Architect + Builder, convergent): quality-scan/doc-reconcile outputs are not finding-shaped and would be rejected by the shared validator. Resolved by a lens **output-mode** declaration (`finding` | `scan`); `scan`-mode presets bypass `validate_sighting()` and are checked structurally. (AC-18, IF-S-10, new subsection.)
- **AC-16 backward-compat** (Guardian): the parameterized validator must behave byte-identically for existing single-argument callers. Added as an explicit assertion. (AC-16.)
- **AC-15 discriminator** (Guardian): the output-mode flag is the machine-readable signal the lens conformance check reads, replacing a hardcoded read-only allowlist. (AC-15.)

Council clean. Spec gate re-run: pass, zero injection warnings.

## Implementation escalation — task-24 (review-loop spine), attempt 1

**Wave:** 1
**Check failed:** Paired structural test `test_review_loop_cited_source_asset.py` — 2 of 4 assertions failed after verbatim install of the drafted `review-loop.md`.

**What went wrong:** The draft expressed two AC-07 contract points in human prose that the test pins as literal tokens:
1. `TestCitedSourceInjection` requires the literal field name `source_of_truth_ref` co-located (≤500 chars) with an inject/collect instruction. The draft said "source-of-truth reference field" (prose), never the field name.
2. `TestUnlocatableSourceRouting` requires, near `unresolvable`, both a not-located token and a no-ruling phrase (`does not issue|no ruling|without a ruling|...`). Neither the draft loop nor the challenger matched the no-ruling regex ("rather than ruling without the source" / "cannot rule ... without it").

**Resolution:** Per the test author's stated intent (adjust the asset, not the regex) and because `source_of_truth_ref` is the real schema field `normalize()` preserves, revise `review-loop.md` with minimal prose edits to name the field by its identifier near the inject step and to state the unlocatable→unresolvable, no-ruling rule explicitly. Single-file edit, within task-24 scope.

## Implementation defect — code-lens.md non-conformance (surfaced by task-04, Wave 4)

**Check failed:** `test_lens_format.py` — 1 of 28 assertions: `code-lens.md` is missing the universal `## Lens identity` section heading. Its identity content sits in the document preamble with no heading; the other six lenses all carry the heading.

**Attribution:** Implementation error in task-30's deliverable (`code-lens.md`). lens-format.md lists "Lens identity" as a universal section; the conformance test correctly pins it. Fix = wrap the existing preamble identity content under a `## Lens identity` heading. Single-file edit within task-30 scope; the test is not loosened.
