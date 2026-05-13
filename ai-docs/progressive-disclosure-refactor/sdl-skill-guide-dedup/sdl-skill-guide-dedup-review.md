Perspectives: Architecture, Quality, Builder

# SDL Skill / Guide Dedup — Spec Review

Stage 2 review of `ai-docs/progressive-disclosure-refactor/sdl-skill-guide-dedup/sdl-skill-guide-dedup-spec.md`. Council assembled in Quick mode (Architect, Guardian, Builder) per the spec-review classification: structural refactor, no security/UX/metrics signal.

Total findings: 24 across three perspectives + 5 from test-reviewer Checkpoint 1. Severity-summarized: 2 blocking (1 unique, 1 compound) + 4 from test-reviewer, 14 important, 8 informational. Builder applied Complexity-Watchdog triage to Round 1 findings; the resolution column under each finding records the council's converged action.

**Final review result: PASS after spec revisions.** All blocking and important findings resolved through user-confirmed decisions on items 1-6 of the post-review iteration. The "Resolution log" section at the end of this document records each decision with rationale.

---

## Architectural soundness

### Blocking

**[ARCH-01 / GUARD-01] Partition gap: `## Finding synthesis` and `## Re-run check` sections of `fbk-spec-review/SKILL.md` are unaccounted for in §4.2 / §4.3.**

`assets/skills/fbk-spec-review/SKILL.md:41-45` (`## Finding synthesis`) directs the skill to write the review document, set the `Perspectives:` metadata line, organize findings by SDL concern, and tag severity. The same structure rules live in `assets/fbk-docs/fbk-sdl-workflow/review-perspectives.md:80-95`. Likewise `fbk-spec-review/SKILL.md:27` (`## Re-run check`) duplicates `review-perspectives.md:97-99`. The spec lists neither section under §4.3 (removals) nor §4.2 (retentions). The implementer has no resolution.

Compounding test impact (Guardian): the literal phrase `testing strategy` appears in `fbk-spec-review/SKILL.md` only at line 45 inside `## Finding synthesis`. `tests/sdl-workflow/test-review-integration.sh` Test 4 (lines 52-57) asserts `grep -qiE 'checkpoint 1|spec review' "$SKILL_FILE" && grep -qi 'testing strategy' "$SKILL_FILE"`. If the implementer reads §4.3 as "remove duplicated workflow content" and removes `## Finding synthesis`, T4 fails — directly contradicting AC-05.

**Resolution (council-converged):** Add explicit §4.2 retentions for `## Finding synthesis` (operational: writes the review file) and `## Re-run check` (operational: skill-side user warning before overwrite). Update AC-04 to enumerate them. Add to §5: a sentinel pinning the literal `testing strategy` keyword in `fbk-spec-review/SKILL.md` (covers Test 4's load-bearing dependency). Apply same partition-gap fix to `## Retrospective` skill sections in `fbk-spec` (lines 44-46) and `fbk-spec-review` (lines 77-80) — operational glue that writes the retrospective file, retain explicitly.

### Important

**[ARCH-09] Internal contradiction: §4.3 implies a guide edit but §4.4 / Non-goals forbid guide edits.**

§4.3's bullet for `fbk-spec/SKILL.md:48-52` reads: *"This summary-and-compact direction is general guide content; move it once to the guide if not already present, remove from skill."* `feature-spec-guide.md:147-156` does NOT contain the summarize-and-compact instructions. So §4.3 implies a guide edit. But §4.4 declares all three guides "leave alone — already canonical," and Non-goals (line 32) commits to "guides remain canonical and unchanged in scope." Same issue applies to `fbk-spec-review/SKILL.md:81-89` analogous Transition prose.

**Resolution:** Resolve to one direction. Recommended: drop the "move it once to the guide" clause; the summary-and-compact direction is removed from the system. If User-facing-behavior §3 needs the summarize-before-handoff behavior, that is a separate retain-in-skill operational glue decision and §4.2 should enumerate it. Document the chosen resolution in the §4.4 module-touch checklist.

**[ARCH-03] `CLAUDE_CODE_EXPERIMENTAL_AGENT_TEAMS` env-flag check is duplicated bidirectionally — guide retains it after refactor.**

`implementation-guide.md:9` already states "Require the `CLAUDE_CODE_EXPERIMENTAL_AGENT_TEAMS` flag before spawning any teammates." §4.2 retains the same check in `fbk-implement/SKILL.md`. Post-refactor both files contain the env-flag check — the same Necessity violation pattern this spec is otherwise dismantling.

**Resolution:** Acknowledge the duplication explicitly in §4.5 (the seam description "skill checks env flag and spawns teammates; guide owns wave-width selection") with a one-line rationale: the guide's mention is reader-facing reference, not an instruction the orchestrator follows; the operational gate is in the skill. Alternatively, amend the Non-goals to permit the small guide edit removing the env-flag mention from `implementation-guide.md:9`. Either is acceptable; the spec must pick one.

**[ARCH-07] §4.6 last bullet ("Present the selection...") is an unresolved TODO masquerading as a runtime-value entry.**

The bullet reads: *"verify whether this lives only in the guide post-edit; if any caller depends on the skill emitting it, retain in skill. Default: rely on guide."* This is a decision deferred to implementation time, not a preserved-string contract. The phrase appears in current `fbk-spec-review/SKILL.md:31` and `review-perspectives.md:17,19`. §3 commits "Present the selection with a one-line rationale per agent" as observable behavior.

**Resolution:** Resolve now. Either (a) explicitly remove from skill, rely on guide-loaded process, add T-sentinel asserting skill does not contain the phrase; or (b) retain as one-line operational glue in §4.2. Default-to-guide if undecided.

### Informational

**[ARCH-04] Read-then-write retrospective rule duplicated across all three skills + retrospective-guide.md.** Out of Finding 4 scope; surface to parent spec for a future cross-skill retrospective-routing child spec. No change to this spec required.

**[ARCH-05] §4.5 seam #5 wording understates that guide owns the verbatim prompt-string source.** Optional one-sentence clarification per affected seam.

**[ARCH-06] §4.4-equivalent Migration mapping table is missing relative to the `council-decomposition-spec.md` precedent.** Optional. The §4.3 narrative carries equivalent information.

**[ARCH-08] `fbk-breakdown/SKILL.md:97` Transition prose pattern-matches removed prose; out of scope.** Add to "Decisions resolved during scoping": breakdown's shorter Transition is out of scope for Finding 4; future audit may standardize.

---

## Quality (testing-strategy) concerns

### Important

**[GUARD-02] Two impacted tests are not enumerated: `test-code-review-skill.sh` Tests 15-16 and `test-council-skill-structure.sh` Test 61.**

`tests/sdl-workflow/test-code-review-skill.sh` Tests 15-16 grep `fbk-implement/SKILL.md` body for `review the implementation` / `code review` / `would you like` / `ask.*review`. The exit prompt at line 97 ("Would you like to review the implementation with /code-review?") satisfies them; spec retains it per §4.2, so they pass — but the spec's enumeration of impacted tests names neither. Similarly `test-council-skill-structure.sh` Test 61 greps `fbk-spec-review/SKILL.md` for `/fbk-council`, which §4.2 retains; not enumerated.

**Resolution:** Add both to §5 "Existing tests impacted." Generalize AC-05 to "All pre-existing tests in `tests/sdl-workflow/` pass without modification" or enumerate the two additions. Add a sentinel pinning the verbatim exit-prompt in `fbk-implement/SKILL.md`: `grep -q 'review the implementation with /code-review' fbk-implement/SKILL.md`.

**[GUARD-03] T5 sentinel for wave-loop step headings is brittle to harmless renames; failure mode not characterized.**

T5 asserts `fbk-implement/SKILL.md` does NOT contain "Step 1 — Test tasks" / "Step 2 — Test compilation check". An implementer renaming the headings while retaining the duplicated narrative passes T5 incorrectly.

**Resolution:** Add ONE paired positive-content sentinel per skill (not per assertion — Builder's complexity push-back applies). Recommended: T5b (`fbk-implement/SKILL.md` does NOT contain `tests are expected to fail`). One added sentinel covers paraphrase risk for the wave-loop step. Apply same one-extra-sentinel pattern to T1 (`fbk-spec/SKILL.md` does NOT contain `Verify that the testing strategy enumerates all callers`).

**[GUARD-04] T11 (guide-side positive assertions) is monolithic and ambiguous on failure.**

T11 covers six conceptually distinct grep targets in one assertion line. A single guide-side phrasing change fails T11 with no information on which target tripped.

**Resolution (council-converged, complexity-watchdog tie-break):** Split T11 into THREE assertions, one per guide file (T11a feature-spec-guide, T11b review-perspectives, T11c implementation-guide). Each can multi-grep for its file's load-bearing phrases on a single line. Reject Guardian's six-way split — three is right-sized.

### Informational

**[GUARD-05] AC-04 enumeration omits frontmatter, `$ARGUMENTS`, conditional reads, chained invocations.** Builder ruled these as exhaustiveness theater (BUILD-06): existing `test-review-integration.sh` Test 2 (frontmatter) and other tests cover most cases at runtime; UV-1/2/3 smoke covers the rest. Guidance: add frontmatter to AC-04's enumerated list (already implicit). Do not add T12-T18 sentinels. Council deferred to Builder's complexity authority on this point; minority view (Guardian) recorded.

**[GUARD-06] UV-1/UV-2/UV-3 are not deterministically verifiable without running a full pipeline.** §3's claim "every observable surface is identical" is supported only by static-grep assertions in §5, not by end-to-end equivalence. Resolution: downgrade §3's claim to "every observable surface is preserved by the operational-glue assertions in §5; full-pipeline equivalence is verified by UV-1/UV-2/UV-3 manual smoke runs at gate, not by the structural test." This is a wording fix, not a test addition.

**[GUARD-07] T2 sentinel "Refuse to write code" leaves guide-side preservation unverified.** Low-likelihood failure mode. Folds into T11a's expanded grep-target list per GUARD-04 resolution.

---

## Over-engineering / pragmatism

### Important

**[BUILD-01] §4.6 enumerated preserved-strings list is read-once template overhead; collapse to one paragraph.**

The list enumerates 11 specific runtime strings already verbatim in the SKILL files. Implementer's job is "delete duplicated prose; do not touch operational glue." Once SKILL files are open, all strings are read, not just 11.

**Resolution (council-converged):** Replace §4.6 with a one-paragraph principle: *"The implementer must preserve every literal runtime string in the current SKILL files — gate-script invocation lines, env-flag names, the `Task file:` template, exit-prompt sentences, chained-skill invocation lines. The structural test in §5 asserts the load-bearing subset; everything else is preserved by reading the existing file before editing."* Cuts ~12 lines.

**[BUILD-02] §4.5 integration-seam table duplicates §4.2 + §4.3 in another shape; collapse.**

The 10-entry seam table restates the partition `§4.2 + §4.3` already establish per-skill. Task compiler produces same tasks with or without §4.5.

**Resolution (council-converged):** Collapse §4.5 to one closing sentence at end of §4.2: *"At each seam, the skill owns operational glue (gate calls, env-flag, spawn template, chained invocation) and the guide owns workflow narrative. The structural test asserts the partition holds."* Cuts ~12 lines.

**[BUILD-03] §4.4 module-touch policy lists three guides only to say "leave alone."**

Six checklist entries, three are no-ops. Non-goals already states guides are unchanged.

**Resolution:** Reduce §4.4 to three lines (one per touched skill) plus a single closing sentence: *"Guides are not edited; they are already canonical."*

**[BUILD-04] AC-07 (CHANGELOG entry) and AC-08 (parent-spec State line) are process bookkeeping, not behavioral acceptance criteria.**

Failing to append the State line does not make the refactor wrong; it makes the dashboard stale. ACs are gate-checked behaviors, not changelog hygiene.

**Resolution:** Move AC-07 and AC-08 out of Acceptance criteria into Documentation impact as release tasks. AC list shrinks from 8 to 6, all of which are behavioral failure-mode preventers.

**[BUILD-06] Reject Guardian's T12-T18 expansion (frontmatter, `$ARGUMENTS`, conditional reads, chained invocations, positional ordering).**

Tally: T12-T18 grow the test from 11 to 18+ assertions, ~30 lines to ~60+. The proposed failure modes (frontmatter dropped, ordering reversed) are caught by existing tests + UV smoke. No new sentinel justifies its maintenance cost.

**Resolution (council-converged, Builder tie-break on complexity):** REJECT T12-T18 wholesale. Spec retains the 11-assertion test plus T11 split into 3 (per GUARD-04) plus the two paired-sentinel additions per GUARD-03 plus the single GUARD-02 exit-prompt sentinel. Net: 11 → 14 assertions (T1-T10, T11a-T11c, T1b, T5b — collapsing the GUARD-02 addition into T9-extension). Guardian's minority position recorded.

### Informational

**[BUILD-05] Reject Guardian's six-way T11 split as exhaustiveness theater.** Folded into GUARD-04 resolution: 3 sub-assertions, not 6.

**[BUILD-07 — meta]** Architect's blocking partition gap (ARCH-01) and internal contradiction (ARCH-09) and env-flag bidirectional dup (ARCH-03) are all real and worth fixing. Not every Round 1 finding is over-build.

**[BUILD-08 — meta]** Spec exceeds the size of work it describes; Round 1 expansions risk significant over-build. Apply BUILD-01 through BUILD-04 to bring spec back to ~190 lines pre-Round-1; accept narrow Architect partition fixes (~10 lines net). Net: post-revision spec stays roughly at current length, absorbs the critique, matches user's "as simple as possible" steer.

---

## Council-converged action list

These are the spec edits required to clear the review. Each maps to a finding above.

1. **(blocking)** Add §4.2 retention bullets for `## Finding synthesis`, `## Re-run check`, and the per-skill `## Retrospective` operational sections in `fbk-spec-review/SKILL.md` and `fbk-spec/SKILL.md`. Update AC-04 enumeration.
2. **(blocking)** Add a sentinel to §5 pinning the literal `testing strategy` keyword in `fbk-spec-review/SKILL.md` (operational sentinel for `test-review-integration.sh` Test 4).
3. **(important)** Resolve the §4.3 / §4.4 / Non-goals contradiction: drop the "move to guide" clause from §4.3 and document chosen resolution.
4. **(important)** Acknowledge env-flag bidirectional duplication in §4.5 with one-line rationale, OR amend Non-goals to permit the small guide edit. Pick one.
5. **(important)** Resolve the §4.6 "Present the selection..." TODO. Default: remove from skill, rely on guide; add T-sentinel asserting absence in skill.
6. **(important)** Enumerate `test-code-review-skill.sh` Tests 15-16 and `test-council-skill-structure.sh` Test 61 in §5 "Existing tests impacted." Generalize AC-05 wording.
7. **(important)** Split T11 into T11a (feature-spec-guide), T11b (review-perspectives), T11c (implementation-guide). Each multi-greps its file's load-bearing phrases.
8. **(important)** Add T1b (`fbk-spec/SKILL.md` does NOT contain `Verify that the testing strategy enumerates all callers`) and T5b (`fbk-implement/SKILL.md` does NOT contain `tests are expected to fail`). One paraphrase-catcher per major skill.
9. **(important)** Add T-exit-prompt: `fbk-implement/SKILL.md` contains `review the implementation with /code-review`.
10. **(important)** Collapse §4.6 to a one-paragraph principle (BUILD-01). Cut ~12 lines.
11. **(important)** Collapse §4.5 to a single closing sentence at end of §4.2 (BUILD-02). Cut ~12 lines.
12. **(important)** Reduce §4.4 to three skill entries plus a one-line "guides not edited" closing (BUILD-03). Cut ~5 lines.
13. **(important)** Move AC-07 (CHANGELOG) and AC-08 (parent-spec State line) out of Acceptance criteria into Documentation impact (BUILD-04). AC list shrinks 8 → 6.
14. **(informational)** Add to "Decisions resolved during scoping": `fbk-breakdown` Transition asymmetry (ARCH-08), retrospective rule cross-skill duplication out of scope for this spec (ARCH-04).
15. **(informational)** Downgrade §3's "every observable surface is identical" to acknowledge UV-1/2/3 are manual smoke verifications (GUARD-06).

Net assertion count: 11 → 14. Net spec length: roughly unchanged (additions from 1-9 balanced by collapses in 10-13). The post-revision spec stays inside the user's "as simple as possible" steer while resolving every blocking and important finding.

---

## Dissenting views

**Guardian vs Builder on test-suite expansion.** Guardian advocated splitting T11 into 6, adding T12-T18 (frontmatter, `$ARGUMENTS`, conditional reads, chained invocations, three positional-ordering assertions). Builder rejected as exhaustiveness theater that violates the parent spec's own progressive-disclosure principle when applied to specs themselves. **Resolution:** Per the conflict-resolution rule "Quality vs Speed → Guardian on critical paths; Builder on non-critical," the SDL skill bodies are not on the critical path (the orchestrator is, and runtime smoke catches breakage). Builder's complexity-watchdog tie-break stands. Guardian's expansions T12-T18 rejected; the paired-sentinel pattern accepted in narrowed form (one extra sentinel per affected skill, not per negative assertion). Three-way T11 split accepted as compromise vs. Guardian's six-way and Builder's keep-monolithic.

**Architect vs Builder on minor enumerations.** Architect surfaced 4 informational findings (ARCH-04, ARCH-05, ARCH-06, ARCH-08). Builder downgraded most to optional. **Resolution:** ARCH-04 and ARCH-08 fold into "Decisions resolved during scoping" (one-line each); ARCH-05 and ARCH-06 dropped as discretionary. No conflict-resolution rule needed; Architect concurred via the Complexity Watchdog logic.

---

## Decision protocol used

Task type: Reasoning (architectural placement decisions, partition judgments, complexity tradeoffs). Method: discussion + Complexity-Watchdog tie-break per the conflict-resolution rules. No formal weighted vote required — Builder's tie-breaking authority on implementation complexity carried the disputed sentinel-expansion issue.

---

## Testing strategy

### New tests needed

Spec authors `tests/sdl-workflow/test-skill-guide-dedup.sh` per §5. After post-review revisions (items 2-5), the test contains 22 TAP assertions: T1, T1b, T2, T3, T4, T4b, T5, T5b, T6, T7, T8, T9, T9b, T10, T11a, T11b, T11c, T11d, T12, T13, T14, T15. Each is `grep -q` / `grep -qv` against committed files; total runtime <1s.

### Existing tests impacted

Spec enumerates (per item 6 in council action list, applied during revisions): `tests/sdl-workflow/test-implementation-pipeline.sh`, `tests/sdl-workflow/test-review-integration.sh` (Tests 3-8), `tests/sdl-workflow/test-code-review-skill.sh` (Tests 15-16), `tests/sdl-workflow/test-council-skill-structure.sh` (Test 61). All pass without modification under the converged §4.2 retentions (including the new partition resolution for `## Finding synthesis`).

### Test infrastructure changes

None. The new test uses the existing TAP-format shell-test pattern in `tests/sdl-workflow/`. CI auto-discovers via the existing glob `for test in tests/sdl-workflow/test-*.sh`.

---

## Checkpoint 1 verdict (test-reviewer)

**Test reviewer verdict: FAIL initially; resolved during post-review iteration.** 4 blocking defects, 1 overridden. The test reviewer evaluated the spec against the §5 schema strictly (independent of the council discussion). All blocking defects addressed during items 1-6 of the post-review iteration (see Resolution log).

**[DEFECT-01]** T11 mislabeled — affects AC-05, AC-01, AC-02, AC-03. T11 asserts guide-side prose preservation (covers AC-01/02/03's "the equivalent prose remains in the guide" half), but is labeled AC-05. AC-05 ("All pre-existing tests pass without modification") has no sentinel in "New tests needed." **Resolution:** Re-label T11 as AC-01/02/03; AC-05 verification is the act of running existing tests at gate, which is procedurally captured by UV-5. Add a note to §5 stating "AC-05 is verified by re-running the enumerated existing tests post-refactor; no new sentinel is needed because the pre-existing tests are themselves the assertion."

**[DEFECT-02]** UV-1/UV-2/UV-3 have no corresponding entry in "New tests needed" — affects AC-04. The spec schema requires each UV step to map to at least one entry in "New tests needed" (`feature-spec-guide.md:49`). UV-1/2/3 are full LLM pipeline runs and cannot be exercised by the structural test. **Resolution:** Add explicit "not automatable — LLM pipeline behavioral verification" rationale to §5 with an inline mapping note: "UV-1/2/3 are manual smoke verifications; they are not represented in 'New tests needed' because the LLM-orchestrated pipeline is not exercisable by the TAP shell-test infrastructure."

**[DEFECT-03]** AC-04 partially uncovered: 4 of 9 enumerated items have no sentinel test — affects AC-04. Items uncovered: (1) frontmatter, (2) `$ARGUMENTS` resolution, (8) chained skill invocations, (9) exit-prompt sentences. **Conflict with council Round 1:** Builder's BUILD-06 rejected Guardian's T12-T18 covering exactly these items as exhaustiveness theater. Test-reviewer is operating on schema-strict AC traceability, not design grounds. **Resolution required from user:** the test reviewer's CP1 verdict cannot be overridden by the council's complexity-watchdog tie-break — schema gaps in AC-to-test traceability are a procedural defect even when the underlying assertions are arguably superfluous. Two options: (a) Accept the test-reviewer's finding: add T12-T15 covering the four items (cost: ~4 sentinels, ~8 lines of test code); (b) Narrow AC-04's enumeration to the items that *are* covered, removing items 1, 2, 8, 9 from AC-04 with rationale that they are preserved by reading-the-existing-file rather than by sentinel — this aligns AC-04 with the test surface and resolves the gap on the AC side rather than the test side. Builder's complexity argument supports (b); Guardian's exhaustiveness argument supports (a). Either is schema-compliant. The user picks.

**[DEFECT-04]** `## Finding synthesis` not classified in §4.2 / §4.3 — affects AC-05. Compounds and confirms ARCH-01 / GUARD-01. The implementer has no instruction to preserve `## Finding synthesis`, and the only occurrence of `testing strategy` (asserted by `test-review-integration.sh` Test 4) lives there. **Resolution:** Already in council action item #1 (add §4.2 retention bullet). Add T-sentinel for `testing strategy` keyword (action item #2). Both pre-existing council resolutions cover this defect.

**[DEFECT-05 — overridden]** Integration seam coverage gap with no rationale. The 10 declared seams have zero e2e tests. The override is valid (LLM-behavioral seams are not automatable in TAP shell infrastructure) but the spec must state the rationale. **Resolution:** Add one sentence to §5: "Integration seams are LLM-behavioral and not automatable in the current TAP infrastructure; UV-1, UV-2, UV-3 are the manual verification path." Folds into council action item #15 (downgrade §3 wording per GUARD-06).

### Test strategy review impact on overall review

Per the spec-review protocol: **test-reviewer FAIL → overall review result is FAIL.** The spec must be revised to address DEFECT-01, DEFECT-02, DEFECT-03, DEFECT-04 before advancing to breakdown. DEFECT-05 is a wording fix.

DEFECT-03 in particular requires user input — the council's complexity tie-break and the test-reviewer's schema-strict finding produced different defensible answers, and only the user can pick which to apply.

---

## Threat model determination

**Decision: No threat model needed.**

**Rationale:** The refactor is pure prose relocation across three context-asset files. No data flow changes, no trust-boundary changes, no new entry points, no auth / access-control changes, no external APIs. The single safeguard in scope (`CLAUDE_CODE_EXPERIMENTAL_AGENT_TEAMS` env-flag check) is preserved per AC-04 and asserted by §5 T7. The integrity of the spawn-prompt template is a context-asset-file integrity concern (project-level, outside this feature) and is pinned verbatim by §5 T8. A formal threat model would produce a "no new trust boundaries" rationale-only document. Recorded per the spec-review protocol; user concurred 2026-05-03.

---

## Resolution log (post-review iteration)

User and orchestrator iterated through the review's blocking and important findings on 2026-05-04. Each decision is recorded with the option chosen and the rationale.

**Item 1 — Threat model.** No threat model needed (recorded above).

**Item 2 — ARCH-09 summary-and-compact direction.** Option (b): move the directive to the guides as additive transition steps; remove from skills. User clarified that guide edits are permitted when required by progressive disclosure. The directive is workflow-protocol-level (it describes stage→stage transition behavior). Spec edits: §4.3 reworded; §4.3a authored with two additive guide edits; §4.4 module-touch updated; §5 T11a/T11b extended to assert guide-side prose; Non-goals reworded.

**Item 3 — ARCH-03 env-flag duplication.** Option (a): keep skill-side check; remove env-flag prerequisite line from `implementation-guide.md:9`. The env-flag check is a gate-like operational invocation; only the skill executes it. Spec edits: §4.3 reworded for `fbk-implement` Team Setup; §4.3a extended with the guide-side removal; §4.4 module-touch updated; §5 T11d added (negative assertion on guide).

**Item 4 — ARCH-07 "Present the selection" TODO.** Option (a): remove from skill, rely on guide-loaded process. The classification process is owned by `review-perspectives.md` lines 5-19; the skill restating it is duplication. Spec edits: §4.6 TODO bullet replaced with single sentence stating guide ownership; §5 T4b added (negative assertion on skill); §5 T11b extended to assert positive guide-side phrase.

**Item 5 — DEFECT-03 AC-04 sentinel coverage.** Option (a): add four sentinels (T12 frontmatter, T13 `$ARGUMENTS`, T14 chained-skill invocations, T15 exit prompts). User chose enforceable AC-to-test traceability over Builder's complexity-watchdog rejection. Spec edits: T12-T15 added; UV-4 / AC-06 assertion counts updated to 22.

**Item 6a — BUILD-01 §4.6 collapse.** Accepted. §4.6 bullet list replaced with one paragraph; classification-rationale ownership note retained.

**Item 6b — BUILD-02 §4.5 collapse.** Accepted. §4.5 collapsed from 10-entry table to one paragraph stating the seam principle plus reference to §5 + UV-1/2/3.

**Item 6c — BUILD-03 §4.4 tighten.** Accepted. Per-skill preservation lists in §4.4 collapsed; each entry now points to §4.2 / §4.3 / §4.3a.

**Item 6d — BUILD-04 AC-07 / AC-08 demotion.** Accepted. AC-07 (CHANGELOG) and AC-08 (parent-spec State line) moved from Acceptance criteria to Documentation impact as release tasks. AC list shrinks 8 → 6.

**Final spec state:** 265 lines (vs. 245 pre-review draft). Spec-gate passes. 22 structural assertions in `tests/sdl-workflow/test-skill-guide-dedup.sh`. 6 ACs, all behavioral failure-mode preventers. Module-touch covers six files (3 skills refactored, 2 guides extended additively, 1 guide line removed).
