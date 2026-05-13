Perspectives: Architect, Builder, Guardian, Advocate

# Council Decomposition — Spec Review

**Spec under review:** `ai-docs/progressive-disclosure-refactor/council-decomposition/council-decomposition-spec.md`
**Stage:** 2 (Spec Review)
**Mode:** Discussion (4 agents, not full 6)
**Session ID:** council-20260502-205326
**Date:** 2026-05-02

Skipped Security (no trust boundaries; Immutable Core preserved verbatim per AC-01) and Analyst (judgment-based sizing is intentionally non-quantifiable).

---

## Summary

Three blocking findings, eleven important findings, eight informational findings, and one named cross-cutting dissent. The decomposition design is structurally sound — integration seams verified accurate against the four Python modules, sibling skill patterns assessed, behavioral preservation framing identified — but verification rigor lags design rigor, the user-facing contract under `quick` is dissolved more aggressively than the spec acknowledges, and a hard sibling-spec dependency creates ordering risk that a 15-line shell script could obviate.

---

## Findings by SDL concern

### Architectural soundness

**FIND-001 — Dissolved Execution Guidelines content is operationally load-bearing**
- **Severity:** important
- **Spec section:** §4.2 item 19, §4.4 (lines 617–660 row)
- **Source:** Architect (FINDING-A1)
- **Gap:** §4.4 maps current SKILL.md lines 617–660 ("The Orchestrator (You)" + "Execution Guidelines") to "REDUCED to 5 facilitator instructions; rest dissolves under Necessity Test." Several specific instructions in that range are operationally load-bearing and not covered by the 5 facilitator items in §4.2 item 19: lines 641–642 (Phase Sequence mandatory order including Phase 5.5 + Session State Footer), lines 644–647 (the explicit "Phase 5.5 is MANDATORY" guard against orchestrators skipping it), lines 649–653 (per-phase `session-state checkpoint` invocation trigger — this is the WRITE side that the recovery leaf depends on; see FIND-002), line 654 ("Parallel Invocation: use a SINGLE message with multiple Task tool calls" — load-bearing for Phase 1 and Phase 3 performance).
- **Resolution:** Expand §4.2 item 19 from 5 to ~8–9 facilitator instructions to cover Phase Sequence ordering, Phase 5.5 mandatory guard, per-phase checkpoint trigger, and parallel-invocation pattern. Alternatively, retain a minimal "Execution Guidelines" subsection inline. Update §4.4 row to enumerate which specific lines from 617–660 survive vs. dissolve, not delegate the decision to Necessity Test at compile time.

**FIND-002 — Checkpoint instruction loaded only on the path it depends on**
- **Severity:** important
- **Spec section:** §4.3 (compaction-recovery.md contents), AC-06, §4.2 item 5
- **Source:** Architect (FINDING-A7)
- **Gap:** The compaction-recovery leaf is loaded ONLY when `recovery-check` returns `recovering: true`. But the leaf is also said to contain "Phase-Level Checkpointing command reference (`session-state checkpoint` invocation pattern…)". That checkpoint command must run during NORMAL operation after each phase to seed the state file that recovery later reads — not only during recovery. If checkpoint instructions live only in the compaction-recovery leaf and the leaf only loads on resume, the orchestrator never sees the checkpoint instruction during the session that should be writing checkpoints. Cycle breaks: nothing writes the state file, recovery never has anything to recover.
- **Resolution:** Split the checkpoint instruction from the recovery-protocol instruction. Inline the per-phase `session-state checkpoint` invocation pattern in the SKILL (it always applies, at every Phase end), and keep only the read-side recovery protocol in `compaction-recovery.md`. Realigns with the parent spec's "topmost where always relevant" principle: checkpointing is always relevant during a live session; recovery is conditionally relevant only on resume.

**FIND-003 — Naming convention for non-SDL-pipeline skill leaves is unstated**
- **Severity:** important
- **Spec section:** §4.1
- **Source:** Architect (FINDING-A3)
- **Gap:** All five sibling skills (`fbk-spec`, `fbk-spec-review`, `fbk-implement`, `fbk-breakdown`, `fbk-code-review`) externalize content to leaves under `assets/fbk-docs/fbk-sdl-workflow/` (or `fbk-design-guidelines/`). Verified by reading each SKILL. None use a skill-name-mirrored directory. The spec's choice of `assets/fbk-docs/fbk-council/` is a new directory-naming convention. Not necessarily wrong (`/fbk-council` isn't part of the SDL pipeline so `fbk-sdl-workflow/` would misclassify it), but the spec doesn't name the convention being established or its rationale. Future child specs (parent's Findings 6–7) will face the same choice — the architectural question should be settled here since this spec sets the precedent.
- **Resolution:** Add a brief paragraph in §4.1 naming this as an intentional convention: "Council content lives at `assets/fbk-docs/fbk-council/` rather than `fbk-docs/fbk-sdl-workflow/` because /fbk-council is not part of the SDL pipeline. Skills outside the SDL pipeline that need conditional leaves use `fbk-docs/<skill-name>/`." Codifies a precedent for parent spec Findings 6 and 7.

**FIND-004 — Migration mapping table has gaps and inherits a label defect**
- **Severity:** important
- **Spec section:** §4.4
- **Source:** Architect (FINDING-A4)
- **Gap:** Specific gaps verified against current SKILL.md: lines 60–62 (umbrella "## Discussion Phases" header — survival unspecified); lines 264–291 mapped as "Phase 4" but lines 273–291 are labeled "**Prompt template for Phase 3:**" in source (a pre-existing labeling defect — template appears under Phase 4 heading); inter-section `---` dividers and blank lines (292–293, 498–499, 555–557, 614–616, 661–663, 752, 770) — survival unspecified individually; lines 39 and 57 (the two Quick Council "skip Phase 1" instructions inside the Council Tiers block) — mapped as "REPLACED" but the explicit skip-Phase-1 semantic is operational behavior, not tier prescription (see FIND-005).
- **Resolution:** Tighten the mapping table to either (a) include a final row "all unmapped lines (separators, blank lines, umbrella headers): regenerated as needed in rewritten SKILL" or (b) remove the line-range column in favor of section names since line-range pinning at this granularity leaks implementation detail without being exhaustive. Fix the Phase 3/Phase 4 prompt template label inversion explicitly during the rewrite.

**FIND-005 — Tier registration argument for Python CLIs is unspecified**
- **Severity:** informational
- **Spec section:** §4.2 item 17, §4.7, AC-01
- **Source:** Architect (FINDING-A6)
- **Gap:** The current `session-manager` CLI signature is `register <session-id> <tier>` (verified at session_manager.py:218–224); it requires the tier argument. With Quick/Full removed, what value does the orchestrator pass for `<tier>`? Current SKILL.md line 80 passes `[quick|full]` based on tier selection. Post-refactor, tier no longer exists as a concept; the registration argument needs a defined value. Same for `session-logger init --tier [quick|full]`.
- **Resolution:** §4.2 item 17 (or §4.7) specifies the value passed for `--tier`. Options: pass `full` always (consistent with default at session_logger.py:124), pass derived value like `judged-N` where N is council size, or extend the Python CLIs to make `--tier` optional. Pick one and document.

**FIND-006 — Ralph integration seam not explicitly enumerated in §4.6**
- **Severity:** informational
- **Spec section:** §4.6, §4.5 (ralph.py "leave alone")
- **Source:** Architect (FINDING-A5)
- **Gap:** §4.6 enumerates integration seams for `session-state`, `session-logger`, and `session-manager` subcommands but does not enumerate `ralph.py`. §4.5 lists ralph.py as "leave alone." Current SKILL.md does not directly invoke `ralph.py` subcommands — those are external user-facing controls. The new `ralph-integration.md` leaf will document Ralph monitoring; if it migrates lines 932–947 verbatim, it uses `session-state show` and `jq`, not `ralph.py`. Worth confirming explicitly that the leaf should NOT introduce `ralph.py` invocations that don't exist in the current SKILL.
- **Resolution:** Add one bullet to §4.6: "Ralph integration leaf monitoring commands inherit the current SKILL's `session-state show` + `jq` pattern; no `ralph.py` CLI invocations are added to the skill side."

### Pragmatism / over-engineering

**FIND-007 — Decouple from unauthored asset-graph-detectors spec**
- **Severity:** blocking
- **Spec section:** §9 (Dependencies), §5.1, AC-09, UV-6, UV-7
- **Source:** Builder (FINDING-B3) + Guardian (FINDING-G1) — same finding from two perspectives
- **Gap:** Spec hard-blocks on `asset-graph-detectors` (a sibling spec that doesn't exist yet) for AC-09, UV-6, UV-7, and all of §5.1. The verification this spec actually needs is trivial: prove five files exist at named paths and prove the SKILL contains `read assets/fbk-docs/fbk-council/<leaf>.md` strings for each. That's a 15-line shell script. The general-purpose orphan walker and dual-path link resolver delivered by asset-graph-detectors are valuable, but this spec doesn't need them — it needs to know its own five leaves are reachable from its own SKILL. Coupling means: if asset-graph-detectors slips, this spec cannot ship its acceptance criteria; if asset-graph-detectors scopes down, AC-09 is partially un-verifiable; if the detectors have bugs in their first release, this spec inherits those bugs as test failures unrelated to its own work.
- **Resolution:** Author a one-shot verification script as part of this spec — e.g., `tests/sdl-workflow/test-council-leaves-present.sh` — that does (a) `test -f` for each of the five leaf paths and (b) `grep -F` for each of the five `read assets/fbk-docs/fbk-council/<leaf>.md` references in SKILL.md. Replace AC-09 with this concrete check. Keep asset-graph-detectors as a separate, parallel improvement that subsumes this script later — but do not block this spec on it. Move it from "Dependencies" (hard) to "Future" (soft).

**FIND-008 — Merge decision-protocol.md and conflict-resolution.md into one leaf**
- **Severity:** important
- **Spec section:** §4.1, §4.3, §4.2 items 14 and 15, AC-04, AC-05
- **Source:** Builder (FINDING-B1)
- **Gap:** Two leaves are proposed for what is actually a single sequential code path: when Round 1 fails to converge, decision-protocol.md fires; when its output surfaces an unresolved conflict, conflict-resolution.md fires. They never fire independently in the unhappy path. Combined size ~110 lines, well within accepted leaf sizes (compaction-recovery is ~78, ralph-integration is ~177). Keeping them split forces two file-read hops mid-phase and creates a non-obvious dispatch chain — the spec puts both dispatches in the SKILL, but the SKILL has no visibility into what the decision-protocol leaf produced (so what triggers the second hop?). Real ambiguity gap.
- **Resolution:** Merge into a single `consensus-failure.md` leaf containing both sections. Single SKILL dispatch line: "When Round 1 of Phase 3 ends without consensus, read `assets/fbk-docs/fbk-council/consensus-failure.md` and apply the decision protocol; if it surfaces an unresolved conflict, apply the conflict-resolution rules in the same leaf." Drop AC-04 and AC-05 in favor of one merged AC. Update §4.4 migration rows.

**FIND-009 — observability.md has no concrete trigger condition**
- **Severity:** important
- **Spec section:** §4.3 (observability.md), §4.2 item 18
- **Source:** Builder (FINDING-B2)
- **Gap:** observability.md is a ~50-line command reference (SKILL lines 664–751 minus the four defaults that stay inline). The condition that gates it ("when a non-default logging operation is needed") has no clear trigger inside the council phases. The non-default commands (`contribution`, `tool-use`, `outcome`, `show`, `permission-request`) are mostly invoked by hooks or for post-hoc inspection — not by the orchestrator during a live session. A "load this leaf when you need it" instruction without a concrete trigger produces dead documentation OR defensive loading on every session (worse than inline).
- **Resolution:** Pick one of two paths and commit. Either (1) delete observability.md entirely; the non-default commands belong in the script's `--help` output and in the hook implementations, not as orchestrator-loadable context — the orchestrator already has the four defaults inline, which is what it actually invokes; or (2) name a concrete trigger in §4.2 item 18: e.g., "When Phase 3 calls for full-content contribution logging instead of character-count logging." Builder recommends (1).

**FIND-010 — Trim §4.7 runtime value precision to load-bearing items only**
- **Severity:** informational
- **Spec section:** §4.7
- **Source:** Builder (FINDING-B5)
- **Gap:** Two items in §4.7 are ceremony rather than precision: (a) "Council session ID format: `council-$(date +%Y%m%d-%H%M%S)`" — implementation detail of the Python helpers, not something the SKILL rewrite can change; (b) "Phase 5.5 self-eval logger invocation: `python3 ... session-logger self-eval ... --confidence <float>`" — CLI signature owned by Python helpers, not a runtime value the refactored SKILL can get wrong.
- **Resolution:** Trim §4.7 to values the SKILL rewrite actually authors fresh: trigger phrases (rewritten section), recovery-check JSON field names (used in dispatch logic the SKILL writes), literal status markers, subagent type strings, five leaf paths. Drop session ID format and self-eval CLI signature.

**FIND-011 — Test deletion rationale couples to the wrong thing**
- **Severity:** informational
- **Spec section:** §4.5, AC-10
- **Source:** Builder (FINDING-B6)
- **Gap:** The spec deletes `test-council-skill-references.sh` on the grounds that "the orphan and link-resolution detectors from the preceding `asset-graph-detectors` spec subsume its purpose." If FIND-007 lands (decouple), this rationale evaporates. Either the deleted test's assertions are still needed (and a replacement must come from this spec), or they're not (and the deletion stands regardless of asset-graph-detectors). The spec conflates the two cases.
- **Resolution:** Read `tests/sdl-workflow/test-council-skill-references.sh` independently; decide whether its assertions are still meaningful post-refactor. See also FIND-014.

### Testing strategy

**FIND-012 — No automated structural smoke test for the 947-line rewrite**
- **Severity:** important
- **Spec section:** §3, §5.5 UV-1 through UV-7, AC-01, AC-11
- **Source:** Guardian (FINDING-G2)
- **Gap:** A 947-line file rewrite has zero automated regression coverage for behavioral preservation. The spec relies entirely on manual UV steps. UV-1 (substantive council session) and UV-5 (dissent-induced decision-protocol fire) require the user to trigger a real LLM-driven session and judge schema equivalence by eye — exactly the kind of check that gets skipped on hotfix nights. Specific failure modes that escape: (a) trigger phrase silently dropped during rewrite, (b) frontmatter `name:` field accidentally renamed and breaking the skill loader, (c) one dispatch one-liner mis-typed and leaf is unreachable, (d) immutable-core block deleted as part of "facilitator persona reduction," (e) Phase 5 output schema headings reordered.
- **Resolution:** Author `tests/sdl-workflow/test-council-skill-structure.sh` covering: (1) SKILL.md exists and is non-empty; (2) frontmatter parses and contains `name: fbk-council`; (3) all nine trigger phrases from §4.6 appear verbatim (one assertion per phrase, so failure names which phrase regressed); (4) each of the five `assets/fbk-docs/fbk-council/<leaf>.md` paths is referenced at least once in SKILL.md; (5) each of the five leaf files exists; (6) the five required headers are present in SKILL: `Council Members`, `Phase 5: Consensus Output`, `Phase 5.5`, `Immutable Core`, `Trigger Phrases`. Structural smoke test, not a behavioral oracle, but catches every mechanical regression a markdown rewrite can introduce. True behavioral equivalence (output-schema-shape comparison) requires an end-to-end harness out of scope here; document that gap explicitly.

**FIND-013 — AC-11 grep verification path is unauthored**
- **Severity:** important
- **Spec section:** AC-11
- **Source:** Guardian (FINDING-G3)
- **Gap:** AC-11 says trigger phrases are "verifiable by grep" but does not commit any test to the repo that performs the grep. "Verifiable by grep" plus "live invocation behavior verified by UV-1 and UV-2" means a human is expected to either run grep themselves or run a real council session. In practice indistinguishable from "trigger phrases work, trust me."
- **Resolution:** Either (a) fold the per-phrase grep assertions into FIND-012's structure test so AC-11 has real automated verification, or (b) restate AC-11 as "trigger phrases must appear verbatim per `tests/sdl-workflow/test-council-skill-structure.sh`" and remove the "verifiable by grep" hand-wave. Add a grep assertion specifically for the literal string `--no-log` in the SKILL since the flag-parsing instruction is the second-most-likely place for a rewrite typo.

**FIND-014 — Test deletion loses anti-regression value not covered elsewhere**
- **Severity:** informational
- **Spec section:** §4.5, AC-10
- **Source:** Guardian (FINDING-G4)
- **Gap:** `test-council-skill-references.sh` asserts four things: (1) SKILL contains `session-manager` dispatcher reference, (2) SKILL contains `session-logger` dispatcher reference, (3) no `~/.claude/skills/fbk-council/session-` substrings remain, (4) no `~/.claude/skills/fbk-council/ralph-` substrings remain. Assertions (1) and (2) remain valuable post-refactor: §4.2 items 17 and 6 require both dispatcher refs to stay inline. The orphan/link detectors do NOT cover "this specific dispatcher invocation pattern still exists in this skill" — they cover reachability of leaves, not presence of inline command strings. Assertions (3) and (4) are anti-regression guards against re-introducing pre-Python-migration paths.
- **Resolution:** Before deleting, port assertions (1)–(4) into `test-no-old-path-patterns.sh` (already being extended per §4.5) or into FIND-012's new structure test. Then delete. Update AC-10 to mention the migration of these four assertions so reviewers know nothing was silently lost.

**FIND-015 — AC-01 through AC-08 and AC-12 have testability defects**
- **Severity:** important
- **Spec section:** AC-01 through AC-08, AC-12
- **Source:** Guardian (FINDING-G5)
- **Gap:** AC-01 is a compound assertion bundling ~12 separately-checkable preservation claims. A single failure tells the implementer "AC-01 failed" with no traceability. AC-02 is testable but no test in §5.2 performs it. AC-03 is untestable as written ("judgment by orchestrator," "criteria for smaller-vs-larger sizing" are subjective). AC-04 through AC-08 each say a leaf "exists and contains" — only "exists" is concretely testable; "contains" needs grep assertions per item, none authored. AC-12 uses line-bound references that will silently break if files re-flow.
- **Resolution:** (1) Decompose AC-01 into AC-01a through AC-01l, OR commit FIND-012's structure test and reference each sub-claim's test ID from AC-01. (2) Add negative-grep test for AC-02 (banned section headers absent). (3) Rewrite AC-03 as "the sizing instruction enumerated in §4.2 item 4 appears verbatim in SKILL.md" — literal-text check, not a quality judgment. (4) Add per-leaf header-presence grep assertions for AC-04..AC-08 (e.g., AC-04: assert `decision-protocol.md` contains `Weighted Voting`, `Evidence-Based Consensus`, `Reasoning`, `Knowledge`). (5) Change AC-12 to content-based, not line-based: "`review-perspectives.md` contains a reference to `/fbk-council` and that trigger remains valid."

**FIND-016 — Ralph false-trigger on stale council-state.json**
- **Severity:** informational
- **Spec section:** §3, §4.2 item 16, UV-4
- **Source:** Guardian (FINDING-G6)
- **Gap:** §4.2 item 16 trigger condition: "presence of `~/.claude/council-logs/council-state.json` with a non-empty `task` field at session start, OR explicit invocation via `/ralph-loop`." The first half is fragile — a stale council-state.json from a prior crashed session has a non-empty `task` field and would falsely trigger Ralph integration on a fresh `/fbk-council` invocation. UV-4 does not test the negative case.
- **Resolution:** Add UV-4b: pre-seed `council-state.json` with a stale completed-but-not-cleaned-up session (status COUNCIL_COMPLETE), invoke `/fbk-council` fresh, observe orchestrator does NOT enter Ralph mode. Tighten the trigger condition in §4.2 item 16 to require `status: CONTINUE` AND `iteration` < `max_iterations`.

### User impact / behavioral preservation

**FIND-017 — Quick contract dissolves user mental model without preserving fallback semantics**
- **Severity:** blocking
- **Spec section:** §3 (User-facing behavior), §4.2 item 4, §5.5 UV-2
- **Source:** Advocate (FINDING-V1)
- **Gap:** Today's `/fbk-council quick` and `/fbk-qcouncil` carry a hard contract: exactly Architect+Builder+Guardian, skip Phase 1 alignment, 1 round. Users invoking quick for "should we extract this function?" know precisely which voices opine and can predict output shape. Under the new spec, the orchestrator picks members per task — same trigger may yield Architect+Builder, Architect+Guardian+Security, Builder+Advocate, depending on judgment. The "Architect+Builder+Guardian for technical opinions" muscle memory breaks. §4.2 item 7 also makes Phase 1 "run on every council session regardless of size" — quick loses its protocol-level latency advantage too. UV-2 only weakly hints at this ("biased toward smaller council size") without binding. §3 frames as "the orchestrator's judgment replaces the prior 3-agent prescription" without naming the user-value lost: predictability of voices, predictability of latency.
- **Resolution:** Strengthen quick semantics in §4.2 item 4 to a soft default rather than a pure hint. Concrete language: "When the trigger is `quick` or `/fbk-qcouncil`, default to a 3-agent council biased toward Architect + Builder + Guardian unless task content explicitly requires a different domain (e.g., the task names security, users/UX, or metrics — substitute the relevant member). Default to skipping the Phase 1 alignment round for quick councils; run it only if agents request it during discussion." Preserves the user's mental model (quick = small, technical, fast) while still allowing judgment override. Update UV-2 to assert this default behavior.

**FIND-018 — Skill description "team of 6" is no longer accurate**
- **Severity:** important
- **Spec section:** §4.2 item 1, AC-01
- **Source:** Advocate (FINDING-V2)
- **Gap:** Current frontmatter description: "team of 6 specialized agents who discuss tasks collaboratively." Under judgment-based sizing, a session may now spawn 2, 3, 4, or 5 agents — "6" is no longer accurate. AC-01 requires frontmatter retained, preserving a now-misleading description. Skill discovery surfaces this string; users expect six voices and may be surprised when fewer arrive.
- **Resolution:** Update the description. Concrete proposal: "Assembles the development council — a team of specialized agents (selected per task from architect, builder, guardian, security, advocate, analyst) who discuss collaboratively, ask clarifying questions, and work toward consensus recommendations." Drop the literal "6". Update §4.2 item 1 from "(unchanged: ... existing description)" to enumerate the new description verbatim. Add an AC asserting the new description is in place.

**FIND-019 — Phase 2 facilitation rules dropped entirely**
- **Severity:** important
- **Spec section:** §4.2 item 8, AC-01
- **Source:** Advocate (FINDING-V3)
- **Gap:** §4.2 item 8 reduces Phase 2 to a single line: "Phase 2: User Clarification (only if Phase 1 produced user-required clarifications)." Current SKILL.md lines 155–164 carry three concrete instructions: present only filtered questions that survived alignment; group by theme rather than by agent; wait for user responses before proceeding. The one-line spec drops all three. Consequence: clarifications get presented per-agent redundantly instead of grouped by theme; user sees a wall of repeated questions. AC-01 enumerates "Phases 0 through 5 with their full prompt templates" — Phase 2 should be at parity.
- **Resolution:** Expand §4.2 item 8 to retain Phase 2 inline at parity with Phases 0, 1, 3, 4, 5. Concrete content: (a) trigger condition (only if Phase 1 produced clarifications), (b) "Present only the filtered questions that survived internal alignment", (c) "Group by theme rather than by agent (reduces redundancy)", (d) "Wait for user responses before proceeding to Phase 3", (e) "If Phase 1 resolved all questions internally, skip to Phase 3". Three-to-five-line block, not a one-liner. Update AC-01.

**FIND-020 — Ralph "When to Use" guidance moves out of always-loaded context**
- **Severity:** important
- **Spec section:** §4.2 item 16, AC-07, §4.3 (ralph-integration.md)
- **Source:** Advocate (FINDING-V4)
- **Gap:** Current SKILL.md lines 917–929 ("Best Practices" + "When to Use Ralph + Council") help users *deciding whether to use Ralph at all*. Spec moves it into ralph-integration.md, which loads only "when invoked inside a Ralph loop." Users who haven't decided on Ralph cannot reach the guidance that would help them decide. The guidance arrives only after the choice is made — opposite of when it's useful.
- **Resolution:** Either (a) keep a one-line decision pointer in the SKILL's Ralph dispatch — change §4.2 item 16 to also include: "For multi-iteration tasks (multi-phase implementation, complex refactoring, exploratory work where scope may evolve), see `assets/fbk-docs/fbk-council/ralph-integration.md` before invoking. Not appropriate for quick one-off questions, time-sensitive work, or tasks with unclear success criteria." Two sentences preserve the always-relevant decision aid. Or (b) move the "When to Use" subsection into a top-level Ralph documentation file users can read independently. Recommended: (a).

**FIND-021 — Logging transparency note dropped**
- **Severity:** informational
- **Spec section:** §4.2 item 17
- **Source:** Advocate (FINDING-V5)
- **Gap:** Current SKILL.md line 85 carries a one-sentence user-facing note: "Session logging is **automatic by default**. Use `/fbk-council --no-log` to disable logging for a session." Transparency framing — "you are being logged unless you opt out." §4.2 item 17 covers parser behavior but does not require this transparency note be retained.
- **Resolution:** Add to §4.2 item 17 a one-sentence transparency requirement: "The SKILL states inline that session logging is automatic by default, that logs are written under `~/.claude/council-logs/`, and that `--no-log` suppresses the four default logging commands." Add an AC asserting this sentence appears.

**FIND-022 — §3 contradicts itself on behavioral preservation**
- **Severity:** informational
- **Spec section:** §3
- **Source:** Advocate (FINDING-V6)
- **Gap:** §3 opens with "The user observes no behavioral change" then immediately documents a behavioral change for `/fbk-council quick`. Two statements contradict. Documentation-honesty issue affecting how downstream readers reason about the change.
- **Resolution:** Rewrite §3's opening: "Trigger phrases, output schemas, and downstream caller contracts are preserved. The one user-observable change is council composition under `/fbk-council quick` and `/fbk-qcouncil`: the orchestrator now selects members by task content rather than the fixed Architect+Builder+Guardian triple. All other invocation paths produce equivalent output to the current SKILL." Then list equivalences.

---

## Cross-cutting dissent

**DISSENT-1 — Should `quick` carry deterministic behavior or pure judgment?**

Three findings touch the same underlying tension:

- **FIND-A2** (Architect): The spec's §4.2 item 7 introduces a behavioral change ("Quick invocations now run Phase 1") masked as a structural refactor; the spec should explicitly mark this as intended OR preserve the prior skip behavior.
- **FIND-B4** (Builder): The "judgment call inline" Phase 1 alignment-skip language smuggles a tier-shaped conditional back into the spec under the guise of judgment. Should be removed entirely; Phase 1 runs unconditionally on every session.
- **FIND-V1** (Advocate, blocking): `quick` carries a user contract (3 agents, skip Phase 1) that the spec dissolves without preserving the user's mental model. Should be a soft default, not a pure hint.

**Builder's position:** Conditional-on-council-size behavior IS the tier prescription this refactor was supposed to eliminate. Inconsistent Phase 1 behavior across sessions is the variance the refactor is supposed to fix; smuggling a size-conditional re-introduces it. Recommends: remove the conditional, run Phase 1 unconditionally, accept short alignment rounds on small councils as cheap.

**Advocate's position:** Users have built habits around quick = predictable small council + no Phase 1 latency. Pure judgment-based sizing breaks these habits without naming the cost. Recommends: preserve quick as a soft default biased toward Architect+Builder+Guardian + Phase 1 skip, with judgment override.

**Architect's position:** Whichever direction is chosen, name it explicitly in §3 user-facing behavior and §4.2 item 7 — the current spec wording ("runs on every council session regardless of size" + "skip the alignment-round step only when small enough") is internally inconsistent and will confuse the task compiler.

**Resolution required:** User decision needed. The two paths produce different ACs and different user-facing behavior. Builder's path is more architecturally pure; Advocate's path is more user-friendly for existing habits.

---

## Testing strategy assessment

Per review-perspectives.md, this section covers new tests, impacted tests, infrastructure.

**New tests needed:**

- `tests/sdl-workflow/test-council-skill-structure.sh` (per FIND-012) — structural smoke test for the rewritten SKILL: frontmatter validity, trigger phrase presence, dispatch path resolution, leaf-file existence, required header presence. Also absorbs the AC-11 grep work (FIND-013) and the migrated assertions from `test-council-skill-references.sh` (FIND-014).
- `tests/sdl-workflow/test-council-leaves-present.sh` (per FIND-007) — minimal one-shot fallback for AC-09 in lieu of asset-graph-detectors. ~15 lines; can later be subsumed when general detectors land.

**Existing tests impacted:**

- `tests/sdl-workflow/test-council-skill-references.sh` — currently spec marks for deletion. After FIND-014, must port assertions (1)–(4) before deleting.
- `tests/sdl-workflow/test-old-locations-empty.sh` — extension per spec §5.2 stands.
- `tests/sdl-workflow/test-no-old-path-patterns.sh` — extension per spec §5.2 stands; absorbs migrated assertions from FIND-014 if those don't go to the new structure test.
- `tests/sdl-workflow/test-council-agent-personas.sh` — leave alone (unchanged).

**Test infrastructure changes:**

- None new beyond the two shell tests above. The asset-graph helper (and its broader detector suite) is no longer a hard dependency under FIND-007.

---

## Threat model determination

**Decision: No threat model required. (Confirmed by user 2026-05-02.)**

Security-relevant characteristics summary:
- **Data touched:** None new. Session logs, state files, and council content are unchanged in shape and storage.
- **Trust boundaries crossed:** None new. The orchestrator continues to be the user's main Claude; no new subagent spawn boundaries.
- **New entry points:** None. All trigger phrases preserved; no new skills exposed.
- **Auth/access control changes:** None.
- **Immutable Core:** Preserved verbatim per AC-01 (the security boundary against recursive self-modification stays inline in SKILL).

**Rationale:** Context-asset refactor with no new attack surface. Security agent was not invoked because no Security-classification signal fires on this spec.

---

## Test Strategy Review

**CP1 verdict: FAIL.** Test reviewer evaluated independently against the spec schema and identified 7 blocking defects. Several overlap with Guardian findings (cross-validation strengthens those); four are new and Guardian-uncaught.

**CP1-1 — UV-1 through UV-5 have no entry in "New tests needed"**
- Affects: UV-1, UV-2, UV-3, UV-4, UV-5
- Schema requires: each UV step maps to at least one e2e or integration test entry; mapping must be explicit.
- Gap: §5.1 says "None new"; UV-1 through UV-5 are manual-only. Schema does not have a "manual-only" exemption.
- Resolution: either add structural test entries in §5.1 covering UV-1 through UV-5 (grep-based dispatch/trigger/header presence), or amend §5.1 to formally invoke a "manual-only" exemption for behavioral UVs with documented rationale.
- Cross-references: overlaps with FIND-012 (Guardian) and FIND-013 (Guardian).

**CP1-2 — AC-08 has no test coverage and no UV step**
- Affects: AC-08
- Gap: §5.5 UV-step-to-AC mapping omits AC-08 entirely. The orphan/link-resolution detectors cover AC-09 (reachability) but not AC-08 (observability.md content).
- Resolution: add UV-8 verifying observability.md is read on a non-default operation, OR add grep-based content-presence test for the six elements AC-08 requires. New finding — not previously surfaced by council.

**CP1-3 — AC-10 has no UV step**
- Affects: AC-10
- Gap: §5.5 mapping omits AC-10. Schema requires every AC to be verifiable by a single automated check or reproducible manual step.
- Resolution: add UV step "Run `bash tests/sdl-workflow/test-old-locations-empty.sh` and `bash tests/sdl-workflow/test-no-old-path-patterns.sh`. Observable outcome: both exit 0. Confirm `test-council-skill-references.sh` is absent." Add to §5.5 mapping. New finding.

**CP1-4 — `test-review-integration.sh` omitted from §5.2**
- Affects: AC-12, §5.2
- Gap: `tests/sdl-workflow/test-review-integration.sh` Test 6 (`grep -qi 'council' "$SKILL_FILE"`) and Test 8 directly validate the AC-12 guarantee that fbk-spec-review preserves its council invocation. Spec does not list this test in §5.2; implementer will not be alerted to keep it passing.
- Resolution: add to §5.2: "`tests/sdl-workflow/test-review-integration.sh` — tests that `fbk-spec-review/SKILL.md` references council. Leave alone: trigger name is preserved. This test must continue to pass." New finding — Guardian missed this brownfield search.

**CP1-5 — AC-09 verification depends on tests that don't exist**
- Affects: AC-09, §5.1, §5.3, §9
- Gap: `tests/sdl-workflow/test-asset-graph-orphans.sh` and `test-asset-graph-links.sh` and the `fbk asset-graph` Python helper do not exist. Spec is non-functional as written if handed to a task compiler today.
- Resolution: same as FIND-007 — decouple from `asset-graph-detectors`, add a 15-line fallback shell test for the five leaf paths and dispatch references.
- Cross-references: same finding as FIND-007 (Builder + Guardian).

**CP1-6 — AC-01 static content has no automated check**
- Affects: AC-01
- Gap: AC-01 enumerates 12 distinct content elements that must be present in rewritten SKILL.md. UV-1 (live invocation) can verify behavioral output but not static content properties (frontmatter structure, exact trigger phrase set, Complexity Watchdogs note retained, exact 5-facilitator-instruction texts, all 5 dispatch one-liners). AC-11 covers the trigger phrases subset; the rest has no automated check.
- Resolution: split AC-01 into a structural AC (static content presence, verified by extended `test-old-locations-empty.sh` or new structure test) and a behavioral AC (verified by UV-1).
- Cross-references: overlaps with FIND-012 (Guardian) and FIND-015 (Guardian).

**CP1-7 — §5.1 "New tests needed" is structurally empty while UV-6/UV-7 reference dependency-spec tests**
- Affects: §5.1
- Gap: Schema requires "New tests needed" to enumerate test entries with behavioral description, level, and AC mapping. §5.1 says "None new"; UV-6/UV-7 reference tests from a dependency spec but those entries are not transcribed into §5.1 with the required format.
- Resolution: amend §5.1 to include entries for the two dependency-delivered tests with behavioral descriptions, level (integration), and AC mapping, OR add a "Tests delivered by dependency spec; see `asset-graph-detectors` §5.1" note. New finding.

**Council Phase 1 also passing items confirmed by CP1 (no overlap with defects above):**
- §5.4 mocking justification correctly states N/A
- §4.6 integration seam declaration is thorough; no undeclared module interactions
- AC-11 grep specification and AC-12 caller specification are concrete enough where they are specified
- Test descriptions in §5.5 use action→outcome format per schema

---

## Overall result

**Initial review: FAIL** with 7 unique blocking findings. **After spec revision (2026-05-02 / 2026-05-03): all blocking findings resolved.** The user revised the spec in two phases:

**Phase 1 — Tier 1 mechanical revisions (auto-applied per user instruction):**
- FIND-001 — facilitator instructions expanded from 5 to 9, restoring Phase Sequence + 5.5 mandatory + parallel-invocation + checkpoint-trigger
- FIND-002 — checkpoint write-side inlined in SKILL §4.2 item 5a; compaction-recovery leaf holds read-side only
- FIND-003 — naming convention paragraph added in §4.1 (sets precedent for parent spec Findings 6 + 7)
- FIND-004 — migration mapping tightened with Phase 2 row, Phase 3/4 label correction, "remaining lines regenerated" explicit row
- FIND-005 — tier registration value specified as literal `full` in §4.2 item 17 + §4.7
- FIND-006 — Ralph monitoring inheritance bullet added to §4.6
- FIND-007 / CP1-5 — decoupled from `asset-graph-detectors`; `tests/sdl-workflow/test-council-skill-structure.sh` authored as part of this spec
- FIND-010 — §4.7 trimmed (session ID format and self-eval CLI signature removed)
- FIND-011 — test deletion rationale corrected to cite assertion migration, not detector subsumption
- FIND-012 / FIND-013 / FIND-015 (partial) / CP1-2 / CP1-6 / CP1-7 — all resolved by authoring `test-council-skill-structure.sh` with ~50 enumerated assertions covering AC-01 (static), AC-02 (negative), AC-04 through AC-09, AC-11
- FIND-014 — assertion migration policy specified before deletion of `test-council-skill-references.sh`
- FIND-016 — Ralph trigger condition tightened to require `status: CONTINUE` + iteration check; UV-4b added for stale-state negative case
- FIND-019 — Phase 2 facilitation rules restored inline at parity with other phases
- FIND-020 — Ralph "When to use" decision pointer added inline in §4.2 item 16
- FIND-021 — logging transparency note required inline
- FIND-022 — §3 rewritten to acknowledge the one user-observable change explicitly; §3.1 added
- CP1-1 — UV-1 through UV-5 mapped against the structural smoke test (which covers AC-01 static / AC-02 negative / AC-04..09 / AC-11)
- CP1-3 — UV-7 added covering AC-10
- CP1-4 — `test-review-integration.sh` added to §5.2 with leave-alone status

**Phase 2 — Tier 3 user-judgment decisions (escalated one at a time, recommendations + justifications provided):**
- **DECISION-B (FIND-017 + DISSENT-1) → Path (a) selected.** Quick councils retain a soft default biased toward Architect+Builder+Guardian + Phase 1 alignment skip, with task-content overrides (substitute Security/Advocate/Analyst when domain keywords appear). New AC-13 added with grep-verifiable assertions. UV-2 strengthened; UV-2b added for override-path verification.
- **DECISION-C (FIND-008) → Path (b) selected.** `decision-protocol.md` and `conflict-resolution.md` merged into single `consensus-failure.md` leaf — eliminates dispatch-chain ambiguity. AC-04 expanded; AC-05 retired. Structural smoke test consolidated.
- **DECISION-D (FIND-009) → Path (a) selected.** `observability.md` deleted. The four default logging commands stay inline; non-default commands are operational tooling for scripts/hooks, not orchestrator context. User additionally raised the hookification insight; recognized as separate future work, captured in parent spec's Future work section and project memory. AC-08 retired; UV-8 retired.
- **DECISION-F (FIND-018) → Path (a) selected.** Skill description updated to drop literal "6" while preserving all discovery-relevant keywords. AC-01 part (a) updated; structural smoke test assertion 2 updated with positive + negative grep checks.

**Final leaf count: three (consensus-failure, compaction-recovery, ralph-integration), down from the initially proposed five.** Spec gate passes after each revision. All seven unique blocking findings closed; eleven important findings closed; eight informational findings closed (most subsumed by other resolutions).

**Result: PASS post-revision.** Spec is ready to advance to Stage 3 task breakdown.

---

## Verdicts

| Agent | Verdict |
|---|---|
| Architect | approve with revisions |
| Builder | approve with revisions |
| Guardian | approve with revisions |
| Advocate | block |

**Aggregate council recommendation:** Spec is structurally sound but needs revision before Stage 3. Three blocking issues, eleven important, eight informational, one cross-cutting dissent requiring user decision.

**Blocking findings to resolve before Stage 3:**

1. FIND-007 (sibling-spec hard dependency)
2. FIND-017 (quick contract dissolution)
3. DISSENT-1 (Phase 1 alignment-round skip direction)
