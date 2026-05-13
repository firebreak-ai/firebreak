# Council Decomposition — Retrospective

## Timeline

- **Stage 1 (Spec)**: 2026-05-02 — completed; gate passed.
- **Stage 2 (Spec Review)**: 2026-05-02 to 2026-05-03 — completed; review-gate passed after one revision cycle.
- **Stage 3 (Breakdown)**: 2026-05-03 — completed; task-reviewer-gate and breakdown-gate both pass after CP2-driven revisions.
- **Stage 4 (Implementation)**: 2026-05-03 — completed; all 8 tasks landed across 3 waves; smoke test 68/68 ok; full sdl-workflow suite 61/61 pass.

## Key decisions

1. **Stage 1**: Tier prescription replaced with judgment-based council sizing — eliminated Quick/Full split, tier-selection heuristics, and auto-escalation in favor of one instruction directing the orchestrator to size the council per task. *Rationale*: the tier framing was largely descriptive scaffolding that the orchestrator can replace with judgment given a clear members table. Aggressive Necessity-Test application; collapses an entire conditional axis.
2. **Stage 1**: Orchestrator persona kept as user's main Claude (not extracted to a subagent). *Rationale*: subagent-orchestrator would lose the ability to ask the user clarifying questions during Phase 2; the interaction round has real value.
3. **Stage 1**: Reduced orchestrator persona to ~5 facilitator instructions inline in the SKILL. *Rationale*: most of the original 8 Responsibilities + 6 Critical Behaviors were either descriptive (already model default) or duplicates of each other; only ~5 instructions earned their place under Necessity Test.
4. **Stage 1**: "Topmost where always relevant" placement principle adopted as the placement rule. *Rationale*: clearer than the original "thin SKILL" framing — extraction is justified by sometimes-relevance, not by file size.
5. **Stage 1**: Always-relevant content (phases, members table, default logging, immutable core, facilitator instructions) stays inline in SKILL; only sometimes-relevant content extracts (decision protocol, conflict resolution, compaction recovery, Ralph integration, advanced observability). Five conditional leaves under `assets/fbk-docs/fbk-council/`.
6. **Stage 1**: Asset-graph detectors deferred to a preceding `asset-graph-detectors` spec; this spec consumes the orphan and link-resolution detectors but does not author them. *Rationale*: detectors are general structural infrastructure that every child spec needs; authoring them inline with this spec couples them to council scope.
7. **Stage 1**: Existing path-pinning test `test-council-skill-references.sh` deleted, not updated. *Rationale*: its target was the prior Python migration (already complete); the general detectors subsume its purpose. Updating brittle path-pinning tests perpetuates a maintenance pattern that adaptive structural detectors replace.
8. **Stage 1**: Two parent-spec updates appended during this spec's authoring: a new Cross-cutting Concerns bullet ("Adaptive structural detectors over path-pinning") and two new Decisions (Decision 7: detectors precede all child specs; Decision 8: council-decomposition direction). Q2 in parent spec marked Resolved. *Rationale*: the structural-test reframing applies to every other child spec, not just this one — capturing it in the parent prevents drift across siblings.
9. **Stage 2 (DECISION-B)**: Quick councils retain a soft default biased toward Architect+Builder+Guardian + Phase 1 alignment skip, with task-content overrides. *Rationale*: preserves user mental model and habits; the soft-default-with-override pattern is distinct from the rigid Quick/Full prescription that was removed; user-burden cost of breaking habits exceeds architectural-purity cost of one inline conditional.
10. **Stage 2 (DECISION-C)**: `decision-protocol.md` and `conflict-resolution.md` merged into single `consensus-failure.md` leaf. *Rationale*: they fire in sequence in the same code path; splitting created a real dispatch-chain ambiguity (the SKILL had no visibility into what decision-protocol produced); merging eliminated the ambiguity and the second file at trivial cost (~110 lines always loaded together when consensus fails).
11. **Stage 2 (DECISION-D)**: `observability.md` deleted. *Rationale*: non-default logging commands are operational tooling for scripts/hooks, not orchestrator-loadable context; the orchestrator only invokes the four defaults (which stay inline). The user's reframing — that these commands would be better served by hooks rather than orchestrator invocation — strengthened the rationale beyond pure progressive-disclosure to include "heading toward hookification anyway." Hookification recognized as separate future work, captured in parent spec's Future work section and project memory.
12. **Stage 2 (DECISION-F)**: Skill description updated to drop literal "team of 6" while preserving discovery-relevant keywords. *Rationale*: documentation honesty matters; description is what users and Claude's skill discovery match against; the keyword surface is preserved (architect, builder, guardian, security, advocate, analyst, council, consensus, collaboratively, clarifying, recommendations) so discovery risk is low and reversible.
13. **Stage 2 (decoupling)**: Removed hard dependency on the unauthored `asset-graph-detectors` spec; this spec is now independently verifiable via `tests/sdl-workflow/test-council-skill-structure.sh` (~50 assertions) authored as part of this spec. *Rationale*: Builder + Guardian + CP1 unanimously identified the dependency as unnecessary coupling; a 15-line shell test (which grew to ~80 lines once AC-08-style content assertions were folded in for other findings) does the verification this spec actually needs without blocking on a sibling spec.
14. **Stage 2 (parent spec update)**: New "Future work (recognized, not in scope)" section added to parent spec with logging-hookification note. *Rationale*: the hookification insight is broadly applicable but not a progressive-disclosure issue; capturing it in the parent prevents loss without forcing it into a child-spec scope it doesn't fit.

## Scope changes

- **Initial framing → final scope**: Started with my proposal of "thin SKILL trigger + tier leaves (`quick.md`, `full.md`) as their own routers + condition leaves on demand." User reframed: tier prescription itself was the violation, not just its placement. Final scope dropped tier leaves entirely (no `quick.md` / `full.md`) and replaced them with one inline sizing instruction. Net structural change: 5 conditional leaves instead of the 7 originally planned (no quick/full tier leaves; no separate members.md or orchestrator-role.md).
- **Test scope**: initially planned to author broken-paths and link-resolution detectors inline with this spec. User reframed: tests should encode general structural invariants (no orphans, all references resolve), not pin specific paths. Detectors carved out to a preceding `asset-graph-detectors` spec. This spec's test scope reduced to: delete one obsolete test, extend two existing tests with the new leaf paths.
- **Stage 2 (test scope re-expansion)**: After Stage 2 review, the hard dependency on `asset-graph-detectors` was removed. This spec now authors `tests/sdl-workflow/test-council-skill-structure.sh` as a one-shot ~80-line structural smoke test (~50 assertions covering AC-01 static content, AC-02 negative checks, AC-04/06/07 leaf content, AC-09 reachability, AC-11 trigger phrases, AC-13 quick-council soft default). The future asset-graph-detectors spec, when authored, will subsume this for cross-asset reachability checks. Net: this spec's test scope grew (one new shell test), but the dependency on a non-existent sibling spec was eliminated.
- **Stage 2 (leaf count)**: Five proposed leaves at end of Stage 1 (decision-protocol, conflict-resolution, compaction-recovery, ralph-integration, observability). Three at end of Stage 2: consensus-failure (merged from decision-protocol + conflict-resolution per DECISION-C), compaction-recovery, ralph-integration. observability.md deleted per DECISION-D.
- **Stage 2 (in-scope policy reframings)**:
  - Phase 2 facilitation rules restored inline at parity with other phases (FIND-019); had been collapsed to one line.
  - Per-phase checkpoint write-side (`session-state checkpoint`) inlined in SKILL §4.2 item 5a; previously bundled into compaction-recovery leaf which only loaded after compaction (cyclical dependency — nothing wrote the state file the recovery path depended on).
  - Facilitator instructions expanded from 5 to 9 to retain operationally load-bearing items (Phase Sequence, Phase 5.5 mandatory guard, parallel-invocation, per-phase checkpoint trigger).
  - Naming convention for non-SDL-pipeline skill leaves codified inline (`fbk-docs/<skill-name>/`) — sets precedent for parent spec Findings 6 and 7.

## Stage 1: Spec

**Clarifying questions that revealed ambiguity:**

- Q1 ("Is `/fbk-qcouncil` a separate skill or a trigger alias?") was the trigger that surfaced a deeper ambiguity. The user's response — "Is there a need to disassemble?" — reframed the question entirely: the tier distinction itself was prescription that judgment could replace. Without that question, the spec would have over-engineered toward two skill files dispatching to two tier leaves.
- Q2 (orchestrator persona placement) clarified that the user's main Claude is the orchestrator; extraction to a subagent would break Phase 2 user clarification. This wasn't obvious from the existing SKILL.md, which mixed "you" addressing the orchestrator persona with "you" addressing the user's main Claude.
- Q4 (test updates) surfaced the user's principle that tests should be structural invariants, not path-pinning assertions. This applies far beyond this spec — captured in the parent spec.

**Scope inclusions:**

- SKILL.md rewrite (refactor-then-extend)
- Five new conditional leaves under `assets/fbk-docs/fbk-council/`
- Deletion of `test-council-skill-references.sh`
- Extension of `test-old-locations-empty.sh` and `test-no-old-path-patterns.sh`
- CHANGELOG entry; README review for path references

**Scope exclusions:**

- All six council member agent files (unchanged; spawned by orchestrator)
- All Python session helpers (`session_state.py`, `session_logger.py`, `session_manager.py`, `ralph.py`) — interfaces preserved, not modified
- Council recommendation output schema, Phase 5 / 5.5 output structure
- Immutable Core security boundary (kept inline)
- Ralph loop infrastructure outside the council's checkpointing/exit-marker contract
- Authoring of asset-graph detectors (preceding spec)
- Any new top-level `fbk` commands

**Open questions deferred to later stages:**

- None outstanding. All scope decisions resolved during authoring.

**Hard dependency:** the preceding `asset-graph-detectors` spec must complete before this spec's Stage 3 implementation begins, since AC-09 verification depends on those detectors. *(Removed during Stage 2 — see Stage 2 retrospective below.)*

---

## Stage 2: Spec Review

**Perspectives invoked:** Architect, Builder, Guardian, Advocate (4-agent discussion mode). Skipped Security (no trust boundaries; Immutable Core preserved verbatim) and Analyst (judgment-based sizing intentionally non-quantifiable). Test reviewer agent invoked at CP1 independently.

**Threat model decision:** No threat model required. Rationale: context-asset refactor with no new attack surface (no new trust boundaries, no data handling changes, no new entry points, no auth/access changes). Recorded in review document.

**Initial findings count:** 7 unique blocking, 11 important, 8 informational, 1 named cross-cutting dissent.

**Review iteration count:** 1 (initial review identified all blocking issues; one revision cycle resolved them).

**Blocking findings and resolutions:**

| ID | Finding | Resolution mechanism |
|---|---|---|
| FIND-007 / CP1-5 | Hard dependency on unauthored `asset-graph-detectors` spec for AC-09 verification | Decoupled. Authored `test-council-skill-structure.sh` (~80 lines, ~50 assertions) as part of this spec. asset-graph-detectors moved from hard dependency to soft future-work item. |
| FIND-017 | `/fbk-council quick` user contract dissolved without preserving mental model | DECISION-B Path (a). Soft default biased toward Architect+Builder+Guardian + Phase 1 skip, with task-content keyword overrides. AC-13 added with grep-verifiable assertions. |
| DISSENT-1 | Builder vs Advocate on Phase 1 alignment-round skip direction | Resolved with DECISION-B Path (a) — soft default with override, not pure judgment and not rigid prescription. |
| CP1-2 | AC-08 (observability.md content) had no UV step, no test | Resolved by DECISION-D (delete observability.md). AC-08 retired; structural smoke test no longer needs that assertion. |
| CP1-3 | AC-10 (test file modifications) had no UV step | Resolved by adding UV-7 covering the test-script execution path. |
| CP1-4 | `tests/sdl-workflow/test-review-integration.sh` missing from §5.2 brownfield enumeration | Added to §5.2 with leave-alone status; AC-12 explicitly requires it continues to pass post-refactor. |
| CP1-7 | §5.1 "New tests needed" structurally empty per schema | Resolved by authoring real test entry for `test-council-skill-structure.sh` with full behavioral description, level (integration), and AC mapping. |

**Important and informational findings:** All eleven important findings resolved (most via Tier 1 mechanical revisions; FIND-008 via DECISION-C; FIND-009 via DECISION-D; FIND-018 via DECISION-F). All eight informational findings resolved (most subsumed by the Tier 1 cluster).

**Spec revisions made during Stage 2:**

- §3 rewritten to acknowledge the one user-observable change explicitly; new §3.1 for quick-council semantics
- §4.1 expanded with naming convention precedent and updated file tree (3 leaves + structural smoke test)
- §4.2 item 1 enumerates new skill description verbatim
- §4.2 item 4 expanded with three sizing branches (default, quick, common) including DECISION-B soft defaults
- §4.2 item 5a (new) — per-phase checkpoint write-side trigger
- §4.2 item 7 — Phase 1 conditional language tightened
- §4.2 item 8 — Phase 2 facilitation rules restored inline at parity
- §4.2 item 14 — single consensus-failure dispatch (merged from items 14 + 15)
- §4.2 item 15 — *(removed; merged into 14)*
- §4.2 item 16 — Ralph trigger condition tightened with status check; "When to use" decision pointer added
- §4.2 item 17 — tier-argument value specified, transparency note required
- §4.2 item 18 — *(removed per DECISION-D)*
- §4.2 item 19 — facilitator instructions expanded from 5 to 9
- §4.3 — three leaves now (consensus-failure, compaction-recovery, ralph-integration); checkpoint write/read split documented
- §4.4 migration mapping — three new rows (Phase 2 explicit, Phase 3/4 label fix, "remaining lines" explicit)
- §4.5 — adjusted leaf list, assertion-migration policy for deleted test
- §4.6 — Ralph monitoring inheritance bullet
- §4.7 — trimmed (session ID, self-eval CLI removed; Ralph dispatch fields added)
- §5.1 — new structural smoke test fully specified with ~50 assertions
- §5.2 — `test-review-integration.sh` added with leave-alone status
- §5.3 — infrastructure-dependency framing reversed (independent now; future spec subsumes later)
- §5.5 — UV-2b, UV-4b, UV-6, UV-7 added; UV-8 retired with observability.md
- AC-04 — expanded to cover both decision-protocol and conflict-resolution sections in merged leaf
- AC-05 — retired
- AC-08 — retired
- AC-09 — reframed as smoke-test-driven; future detectors are bonus, not precondition
- AC-10 — assertion-migration policy added; `test-review-integration.sh` requirement added
- AC-11 — trigger phrase verification path tightened with grep + UV pairing
- AC-12 — content-based, not line-based
- AC-13 (new) — quick-council soft default verifiable via grep
- §9 Dependencies — `asset-graph-detectors` reframed as soft future-work dependency

**Parent spec updates during Stage 2:**

- New "Future work (recognized, not in scope)" section added with logging-hookification note (surfaced during DECISION-D when user asked whether logging would be better satisfied by hooks). Recognized as separate refactor; not in scope for any of the eight findings.

**Memory updates during Stage 2:**

- New project memory `project_logging_hookification.md` capturing the hookification insight for future sessions.

**Stage 2 process observations:**

- The CP1 test reviewer caught four findings the council missed (CP1-2 AC-08 untested, CP1-3 AC-10 no UV, CP1-4 brownfield test omission, CP1-7 schema-emptiness in §5.1). Cross-validation with the council Guardian was high-value — Guardian and CP1 independently identified the asset-graph-detectors hard dependency, and CP1 found additional schema-level defects (Guardian was focused on testability per AC, not schema compliance per the spec guide).
- The user's reframing during DECISION-D ("Are the logging elements something better satisfied deterministically by a hook script?") opened a strategic insight that didn't change the immediate decision (still delete observability.md) but did add weight to the rationale (commands heading toward hookification = even less justified to document as orchestrator context). This is consistent with the user's prior pattern (per `project_phase16_spec_retro.md` memory) of reframings that collapse design problems.
- The Tier 1 / Tier 3 split (mechanical fixes done autonomously; judgment-required decisions escalated one-by-one with recommendation + justification) worked well per user-stated preference. Auto-applied 18 mechanical revisions; escalated 4 judgment items in sequence; user accepted all 4 recommendations.

**Open questions deferred to later stages:** None.

**Hard dependencies remaining:** None. Spec is independently implementable.

---

## Stage 3: Breakdown

**Compilation attempts:** 1 round of test-task compilation + 1 round of impl-task compilation + 1 revision cycle after CP2 review.

**Wave structure and rationale:**

| Wave | Tasks | Rationale |
|---|---|---|
| 1 | task-01 (test) | Author the structural smoke test. Must exist as the verification contract before any implementation lands. |
| 2 | task-02, task-03, task-04, task-05, task-06, task-07 (impl, parallel) | Six implementation tasks touching different files: 3 leaf creations, 1 SKILL rewrite (orchestrator), 2 test-infrastructure modifications. All depend on task-01. Parallelizable because they don't share files. |
| 3 | task-08 (impl) | CHANGELOG + README post-refactor documentation. Depends on Wave 2 completion because the CHANGELOG entry describes work that must already exist. |

**Task count:** 8 (1 test + 7 impl).

**Task → AC traceability:**

| AC | Test (task-01 assertions) | Impl task(s) |
|---|---|---|
| AC-01 | 1–5, 15–23, 68 | task-07 |
| AC-02 | 24–27 | task-07 |
| AC-03 | 51–55 | task-07 |
| AC-04 | 34–42 | task-04 |
| AC-06 | 43–46 | task-05 |
| AC-07 | 47–50, 67 | task-06 |
| AC-09 | 28–33 | task-04, 05, 06, 07 |
| AC-10 | 56–60 | task-02, task-03 |
| AC-11 | 6–14 | task-07 |
| AC-12 | 61–62 | task-07 |
| AC-13 | 51–55 | task-07 |
| AC-14 | 63–66 | task-08 |

12 active ACs, all covered by both test and implementation. AC-05 and AC-08 retired during Stage 2; their bullet entries were removed from the spec body during Stage 3 to satisfy the breakdown gate's AC-coverage check.

**Scope adjustments from compilation:**

- **Spec wording cleanup**: The test-task compilation agent flagged five stale references to "five new leaves" (left over from the pre-DECISION-D structure). All five were corrected to "three" before continuing.
- **AC-05 / AC-08 hard removal**: Initial drafts kept retirement markers (`*(merged into AC-04...)*`, `*(removed — observability.md deleted...)*`) for documentation continuity. The breakdown gate parses these as still-active ACs and flagged them as uncovered. Removed the bullet entries entirely; retirement context lives only in the review document and this retrospective.
- **AC-14 added during compilation**: Initial spec had no AC for documentation impact (CHANGELOG / README updates per §6.1). Adding task-08 (CHANGELOG + README impl task) without a covering AC would violate the gate invariant. Added AC-14 as a structural acceptance criterion (CHANGELOG entry exists; README updated to user-approved wording).
- **README change escalated to user**: Per project CLAUDE.md ("after CHANGELOG.md update, check README.md for any required updates; discuss proposed readme changes with the user"), the README "Assemble 6 agents" line was surfaced for user decision. User approved the soft-default-aligned wording ("Assemble specialized agents..."), and the change was bundled into task-08.
- **Tasks 02 and 03 reframed as implementation**: Initial test-task compilation classified the test-file modifications as test tasks. The breakdown gate requires every AC to have both test AND implementation coverage; AC-10 had only test coverage. Reframed tasks 02 and 03 as implementation tasks (modifying test infrastructure files is implementation work for that infrastructure). Test coverage for AC-10 then provided by extending task-01's smoke test with assertions 56–60.
- **Task-01 scope expansion**: Initial compilation gave task-01 ~50 assertions covering AC-01/02/03/04/06/07/09/11/13. CP2 + breakdown gate identified gaps for AC-10 (modified existing tests), AC-12 (downstream callers), AC-14 (CHANGELOG/README post-refactor content). Expanded task-01 to 68 assertions covering all 12 active ACs. The test became the structural-verification harness for the entire refactor, not just the SKILL.

**Test-reviewer findings (CP2):**

- **Blocking — Defect 1 (case mismatch)**: Task-01 assertion 63 used `grep -F 'Decomposed'` (capital D); task-08's specified CHANGELOG entry text led with lowercase `decomposed`. Test would fail against correct implementation. **Resolved**: Updated task-08's entry text to lead with "Decomposed the `/fbk-council` skill body" (capital D); updated assertion 63 to grep for `'Decomposed the'`.
- **Override — Finding 1 (UV-4b stale-state guard)**: Marked overridden by task-07 wiring checklist; closed anyway by adding assertion 67 (`SKILL contains 'does NOT activate Ralph mode'`) to ensure regression protection at the test level too.
- **Override — Finding 3 (tier argument value `full`)**: Marked overridden by task-07 wiring checklist; closed anyway by adding assertion 68 (`SKILL contains '--tier full'`) to ensure regression protection.
- **Informational — Finding 4 (AC-01 coverage table omitted assertion 5)**: Resolved by updating task-01 section 6 AC mapping to include assertion 5 in the AC-01 list.

**Model assignments and rationale:**

| Task | Model | Rationale |
|---|---|---|
| task-01 (test) | Sonnet | 68 enumerated assertions across 6 file targets; assertion-correctness matters; spans many ACs. |
| task-02 (impl) | Haiku | Bounded single-file extension (~4 assertions added). |
| task-03 (impl) | Haiku | Bounded mechanical: extend `files=()` array + delete companion file. |
| task-04 (impl) | Haiku | Single new file; verbatim concatenation from documented source line ranges. |
| task-05 (impl) | Sonnet | Selective migration with WRITE/READ split discipline; mistake breaks recovery cycle. |
| task-06 (impl) | Sonnet | ~177 lines content migration with diagram + YAML schema preservation. |
| task-07 (impl) | Sonnet | Orchestrator file (per task-compilation orchestrator-task rule, Sonnet minimum); ~400 lines new content; 19-item structural assembly with wiring checklist. |
| task-08 (impl) | Haiku | Two-file mechanical text edits with verbatim content specified. |

**Counts:** 8 tasks, 3 waves, 12 ACs covered. Sonnet: 4 tasks. Haiku: 4 tasks. No Opus.

**Stage 3 process observations:**

- The test-task agent caught a spec consistency defect (stale "five leaves" references after DECISION-D collapsed to three). This kind of automated cross-validation is the value-add of independent context for breakdown agents.
- The CP2 case-mismatch defect (`Decomposed` vs `decomposed`) is the kind of subtle defect that slips past human review and only surfaces when a tool runs both the test and the implementation against the same artifact. Worth carrying forward as a process note: any spec-quoted literal that the implementation rephrases creates a test-to-impl mismatch hazard. Future task-compilation should explicitly verify that spec-quoted strings used in test assertions appear verbatim in the implementation output.
- The breakdown gate's hard requirement that every AC have both test and implementation coverage forced reframing tasks 02 and 03 from "test" to "implementation" — an artificial classification for "modifying a test file" that nonetheless surfaces a real need: AC-10 is verified by task-01's structural assertions (the test side) AND realized by tasks 02+03 (the implementation side). The reframing makes the test/impl pair explicit.
- The user's "Tier 1 mechanical / Tier 3 escalate one-by-one" pattern from Stage 2 carried into Stage 3: spec inconsistencies and CP2 defects were auto-resolved when the resolution was unambiguous (case mismatch → align both); the README change was escalated to the user (judgment about external-facing copy).

**Open questions deferred to later stages:** None.

**Hard dependencies remaining:** None.

---

## Stage 4: Implementation

**Execution model:** Fallback (path b) — `CLAUDE_CODE_EXPERIMENTAL_AGENT_TEAMS` was unset; no persistent teammate pool. Direct subagent spawning via `Agent` tool, fresh context per task. Same wave protocol; no team-lead/teammate boundary, but task isolation preserved (each subagent reads only its task file + design-guidelines + pre-authoring-investigation leaves).

**Wave structure executed:**

| Wave | Tasks | Spawn pattern | Outcome |
|---|---|---|---|
| 1 | task-01 (test, Sonnet) | Single sequential | Test authored, exit 1, 21/68 ok against current main — completion gate satisfied (test catches missing implementation deterministically) |
| 2 | task-02..07 (6 impls — 3 Haiku, 3 Sonnet) | 6 parallel via single message | All complete; smoke test 64/68 ok, only the 4 expected CHANGELOG/README failures remained |
| 3 | task-08 (impl, Haiku) | Single sequential | CHANGELOG + README landed; smoke test 68/68 ok |

**Per-wave verification results:**

- Wave 1 gate: smoke test exit 1 (expected) — passes (it's a test that's *supposed to* fail until implementations land)
- Wave 2 gate: smoke test exit 1, 64/68 ok with only AC-14 failures remaining; `test-old-locations-empty.sh` 9/9 ok; `test-no-old-path-patterns.sh` 4/4 ok; `test-review-integration.sh` 14/14 ok; `test-council-agent-personas.sh` 30/30 ok
- Wave 3 gate / final: smoke test exit 0, 68/68 ok; full sdl-workflow suite 61/61 pass; no regressions

**Final verification:**

- **Structural**: All 8 tasks `status: complete`. Full test suite (61 sdl-workflow tests) passes. No dead code — every new file is reached: SKILL dispatches to all 3 leaves (smoke test assertions 28-30 verify the dispatch references, 31-33 verify the leaves exist); the structural smoke test is auto-discovered by the CI glob `for test in tests/sdl-workflow/test-*.sh`. Documentation updates landed (CHANGELOG + README per AC-14).
- **Semantic**: All 12 active ACs satisfied:
  - AC-01: SKILL retains required content (verified by structural smoke test assertions 1-5, 15-23, 68)
  - AC-02: banned headers absent (24-27)
  - AC-03/AC-13: sizing instruction with soft-default phrases (51-55)
  - AC-04: consensus-failure.md content (34-42)
  - AC-06: compaction-recovery.md content (43-46)
  - AC-07: ralph-integration.md content (47-50, 67)
  - AC-09: dispatch references resolve, leaves exist (28-33)
  - AC-10: existing tests extended, deleted test gone (56-60)
  - AC-11: trigger phrases verbatim (6-14)
  - AC-12: downstream callers preserved (61-62; test-review-integration.sh continues to pass)
  - AC-14: CHANGELOG + README updated (63-66)

**Per-task metrics:**

| Task | Wave | Model | Outcome | Notes |
|---|---|---|---|---|
| task-01 | 1 | Sonnet | complete first try | 247-line shell test, 68 assertions, transparent line-count over the spec's "~110" estimate |
| task-02 | 2 | Haiku | complete first try | 4 assertions added in correct location |
| task-03 | 2 | Haiku | complete first try | array extension + companion-file deletion both confirmed |
| task-04 | 2 | Haiku | complete first try | 116-line leaf, all 9 content terms present |
| task-05 | 2 | Sonnet | complete first try | 71-line leaf with explicit WRITE/READ split confirmed; the highest-correctness-risk leaf landed cleanly |
| task-06 | 2 | Sonnet | complete first try | 175-line leaf with diagram + YAML schemas preserved |
| task-07 | 2 | Sonnet | complete first try | SKILL 947 → 431 lines; wiring checklist all ✓; one in-scope-disclosure see below |
| task-08 | 3 | Haiku | complete first try | CHANGELOG bullet leads with capital "Decomposed" per CP2-resolved case-mismatch fix |

**Escalation count:** 0. No escalation protocol invocations.

**Failure attribution:** None — all tasks complete first attempt.

**Scope-discrepancy event (task-07):**

task-07 (SKILL rewrite) silently expanded scope to fix two pre-existing bugs in the structural smoke test (`tests/sdl-workflow/test-council-skill-structure.sh`): assertions 17 and 68 were `grep -F '--no-log' …` and `grep -F '--tier full' …`, missing the `--` argument-terminator that grep needs to stop interpreting `--no-log` and `--tier full` as flags. Without `--`, those greps return non-zero regardless of file content. The teammate added the `--` separator to both assertion blocks.

Per the new "Pause on Scope Discrepancy" framework rule (committed earlier in this session as part of brownfield discipline), the teammate should have halted, reported, and waited. Instead it fixed and disclosed in its work summary — the disclosure was clear and the fix was correct (test is now functioning).

**Lesson captured:** the agent pattern of "self-corrected and disclosed" is real-world common; the framework rule asks for halt-before-fix. The right response when the disclosed fix is correct and bounded is to accept and note (this retrospective serves that purpose). The right response when the disclosed fix is wrong or large would be to revert and re-scope. For this case, accepting was correct because (a) the fix targets a test-script bug, not the SKILL or any AC-bearing artifact; (b) the fix is two-character (`--` insertion) in two assertion blocks; (c) reverting and re-scoping would have cost a Wave 2 → escalate-to-task-01-revise → re-execute round-trip for no quality gain. Process improvement candidate: the `Pause on Scope Discrepancy` rule should explicitly enumerate exceptions for "test-script correctness fixes that the teammate's task verifies" so future teammates have clearer guidance.

**Process observations:**

- The structural smoke test as a single shared test_tasks reference for 6 parallel Wave 2 tasks worked exceptionally well. Each implementation task could verify its own correctness by running the smoke test and checking its assertion range. This is a strong pattern for context-asset refactors where AC verification reduces to "the file contains X."
- Path (b) execution (no Agent Teams) was practically equivalent to path (a) for this size of work (8 tasks, 1 day). The bottleneck was wave-level coordination (which I do as the orchestrator) rather than teammate persistence. Agent Teams would have reduced spawn overhead per task but the actual time savings are minor at this task count.
- All 4 Sonnet tasks and all 4 Haiku tasks landed first attempt. The model routing rationale (orchestrator-file → Sonnet minimum; bounded mechanical → Haiku) held up — no Haiku task escalated to Sonnet, no Sonnet task struggled with its assignment.
- The CP2-resolved case-mismatch fix (capital "Decomposed" in task-08) prevented exactly the kind of test-to-impl drift that would have manifested as a Wave 3 failure. Without that resolution, Wave 3's task-08 would have produced a CHANGELOG entry that looked correct but failed assertion 63. Catching it at CP2 saved a Wave 3 escalation.

**Outcome:** Implementation is complete. The `/fbk-council` skill is decomposed per spec; all 12 ACs verified; all 61 sdl-workflow tests pass. Behavioral preservation for downstream callers (`/fbk-spec-review`, `review-perspectives.md`) confirmed. Ready for code review.

**Hard dependencies remaining:** None.

**Future work surfaced during implementation:** None new beyond the retrospective process observation about the scope-discrepancy exception language.

---

## Stage 5: Code Review

**Date:** 2026-05-03
**Review report:** `fbk-code-review-2026-05-03-0414.md` (project root)
**Diff scope:** `git diff HEAD~1..HEAD` — commit 5f0322b

**Pipeline metrics:**
- Detector sightings: 6
- Pipeline filter (preset=full, severity=minor): 6 kept (preset=behavioral-only would drop F-06)
- Challenger verifications: 6 verified, 0 rejected, 0 reclassified
- False positive rate: 0%

**Verified findings (all 6, by category):**

| ID | Category | Severity | Type | One-line |
|---|---|---|---|---|
| F-01 | spec-ac | major | behavioral | Phase 1 hardcodes `Invoke ALL 6 agents` contradicting judgment-based sizing (SKILL.md:66) |
| F-02 | intent | major | behavioral | Session State Footer template stranded in conditional leaf — unavailable on fresh sessions |
| F-03 | spec-ac | major | behavioral | `session-manager unregister` absent from Phase 5 operational path — sessions never unregister |
| F-04 | spec-ac | major | behavioral | `compaction-recovery.md` missing Phase-Level Checkpointing command reference (AC-06) |
| F-05 | spec-ac | major | behavioral | Recovery protocol omits `session_id` adoption + transcript/key-decisions seeding (2 of 4 steps) |
| F-06 | audit-pass | minor | test-integrity | Smoke test AC-06 block omits Phase-Level Checkpointing assertion — masks F-04 |

**Why findings slipped past prior gates:**

1. **Structural smoke test catches what it asserts, not completeness against multi-item ACs.** AC-06 lists 5 required items; the test asserted 4. CP1/CP2 reviewers validated the test strategy against the spec but didn't catch the 4-of-5 coverage gap because they reviewed structure, not enumeration completeness.

2. **Verbatim carry-over of body text during SKILL rewrite was not flagged.** Line 66's "ALL 6 agents" was preserved from the source SKILL when the surrounding Phase 1 prompt was rewritten. The "Pause on Scope Discrepancy" framework rule (committed 2026-05-02 as commit 6c99cec, before this implementation) covers task-scope expansion but not "verbatim content carry-over that needs spec-recheck." Process gap.

3. **Spec-internal contradictions propagated to implementation.** The spec has two pairs of contradictions: §4.3 contents list vs AC-06 explicit list (Phase-Level Checkpointing); §4.3 Session State Footer placement vs §4.2 facilitator rule 6 (footer every session). The implementation followed the more-detailed prose (§4.3) in both cases, but the AC-06 text and behavioral correctness require the alternative.

**Cross-loop pattern observation:** Three of the six findings (F-02, F-04, F-05) cluster in the compaction-recovery leaf migration (task-05). Task-05 was assigned Sonnet specifically because of the WRITE/READ split discipline complexity flagged at compilation time — yet three correctness gaps still slipped through. This suggests the spec's compaction-recovery contents specification was insufficiently precise (multiple internal contradictions, prose enumeration vs AC enumeration mismatch) and the implementation faithfully reproduced the spec's gaps.

**Process improvement candidates:**
- Add to wiring checklist for SKILL rewrites: "verify no body-text carry-over of agent-count phrases (`6 agents`, `3 agents`, `ALL 6`) — these are governed by the sizing instruction now, not Phase prescription."
- Add to spec-review CP1: "for each AC that enumerates N content items, verify the test strategy asserts N items, not a subset."
- Resolve spec-internal contradictions during spec review (DECISION-style explicit choice) rather than letting implementation interpret them.

**Recommendation:** Fix all 6 findings before closing the implementation. F-01, F-02, F-03 are user-facing behavioral risks (broken quick councils, broken first-session footer, broken session lifecycle). F-04 and F-05 are recovery-correctness risks. F-06 closes the test loop so F-04 cannot regress silently in the future.

**Status:** Implementation complete but with 6 verified post-implementation findings. Remediation work required.

---

## Stage 5.1: Code-Review Remediation

**Date:** 2026-05-03

**Method:** User-directed inline remediation. For each finding: verify against spec, apply fix if clear, escalate to user with recommendation if spec-impact judgment required. Three findings resolved without escalation; two escalated and resolved with user judgment; one (F-06) dissolved as a test-correctness consequence of the other resolutions.

**Resolutions:**

| ID | Resolution | Notes |
|---|---|---|
| F-01 | Fixed inline (no spec impact) | SKILL.md:66 "Invoke ALL 6 agents" → "Invoke all selected council members" |
| F-02 | Fixed (escalated; user chose path a) | Session State Footer templates moved from `compaction-recovery.md` to SKILL.md (after Immutable Core, before Ralph Integration). Spec §4.3 leaf-contents list amended; AC-06 amended to drop the templates; AC-01 expanded with new item (l) for the Session State Footer in SKILL. Smoke test assertions 44–46 retargeted from $RECOVERY to $SKILL. |
| F-03 | Fixed inline (no spec impact) | `session-manager unregister` operational instruction added to end of Phase 5 in SKILL.md |
| F-04 | Spec amendment only (escalated; user chose path a) | AC-06 amended to drop "Phase-Level Checkpointing command reference" — implementation correctly followed §4.3's WRITE/READ split (Stage 2 FIND-002 resolution); AC-06 was stale text that hadn't been updated. No code changes required. |
| F-05 | Fixed inline (no spec impact) | `compaction-recovery.md` Recovery Protocol expanded from 3 steps to 5: added session_id adoption (step 2) and transcript_summary/key_decisions seeding (step 4) per spec §4.3 |
| F-06 | Closed via test additions | Added 3 new smoke test assertions (69, 70, 71) covering the remaining AC-06 items: recovery acknowledgment phrase, State Persistence schema reference, Session Cleanup commands. Smoke test now 71 assertions (was 68). AC-06 now has full enumeration coverage. |

**Verification:**
- Smoke test: exit 0, 71/71 ok (was 68/68; added 3 assertions)
- Full sdl-workflow suite: 61/61 pass
- No regressions in caller integrity tests (`test-review-integration.sh`, `test-council-agent-personas.sh`)

**Process observations:**

- The "elevate to me one at a time with recommendation" pattern worked smoothly. Both escalations had clear recommendations (paths a) that the user accepted. Total back-and-forth: 2 questions, 2 single-letter answers, 6 findings resolved.
- Two of three escalation candidates turned out to be spec-stale-text issues, not implementation bugs (F-02 had a spec contradiction; F-04 had stale AC text from before Stage 2's FIND-002 resolution). The implementation was actually faithful to the spec's intent in both cases — the spec needed amendment, not the code.
- F-06's dissolution-via-augmentation: the original sighting flagged "test asserts 4 of 5 items"; with AC-06 amended to 4 items, "test asserts 4 of 5" became "test asserts 4 of 4." But the 4 it asserts didn't match the 4 AC-06 lists post-amendment (it asserts Recovery Protocol header from the leaf and 3 Session State Footer items in the SKILL). Adding 3 new assertions for State Persistence, Session Cleanup, and acknowledgment phrase brings AC-06 coverage to 4 of 4 with proper enumeration alignment.
- One hidden coverage gap surfaced during remediation: pre-existing test never asserted State Persistence schema or Session Cleanup commands (they were items 4 and 5 of the original AC-06 5-item list, but the smoke test only had assertions for items 1, 2, 3a, 3b — Recovery Protocol, Session State Footer, two COUNCIL_STATUS markers). This gap predates the F-06 finding and was independent of it. Closed in the same remediation pass for completeness.

**Spec amendments captured:**
- §4.3: Session State Footer templates removed from compaction-recovery.md contents list; new "Note on Session State Footer placement" subsection explaining the post-implementation move and rationale.
- §4.3 (existing): "Note on the WRITE/READ split" continues to govern the Phase-Level Checkpointing placement (already correct, no change needed).
- AC-01: expanded to include item (l) — "the Session State Footer section with CONTINUE and COUNCIL_COMPLETE markdown templates verbatim (placed after Phase 5.5 / Immutable Core, before Ralph Integration dispatch — added per F-02 resolution)."
- AC-01: clarified item (h) — `session-manager unregister` is "Phase 5 cleanup, operational instruction not just reference example" (per F-03 finding distinction).
- AC-06: rewritten as 4-item AC dropping "Phase-Level Checkpointing command reference" (per F-04) and "Session State Footer markdown templates" (per F-02).

**Status:** All 6 code-review findings resolved. Implementation now satisfies amended spec ACs. Ready for re-review or to proceed to `/fbk-improve`.

---

## Stage 6: Pipeline Improvement Proposals (Deferred)

**Status:** Captured for later reassessment. Not applied during the council-decomposition cycle. Several may become moot as other progressive-disclosure-refactor child specs land — re-evaluate after siblings complete.

**Source:** `/fbk-improve council-decomposition` invoked 2026-05-03; 7 `fbk-improvement-analyst` teammates spawned in parallel against the highest-signal target assets; 17 actionable proposals collected.

**Cross-stage redundancy is intentional:** each instruction activates at a different SDL stage's agent — no per-load-path duplication. Defense-in-depth: catching the same issue at multiple stages.

### Theme A — Multi-item AC enumeration discipline

When an AC enumerates N required items, each downstream artifact must commit to N assertions, not a subset. **Root cause for F-04 (AC-06 listed 5 items; smoke test asserted 4).**

**A1 — `assets/agents/fbk-spec-author.md` (new Output quality bar)**
> When an acceptance criterion enumerates N items, the test-strategy section commits to N assertions covering those items — not a subset. Count the items and verify the assertion count matches before marking the AC done.

**A2 — `assets/fbk-docs/fbk-sdl-workflow/feature-spec-guide.md` (§7 Acceptance criteria)**
> When an AC enumerates N required items (e.g., "must contain: X, Y, Z"), record the item count as part of the AC text. Then verify that §5 "New tests needed" contains a test assertion for every enumerated item — not just a reference to the AC identifier.

**A3 — `assets/fbk-docs/fbk-sdl-workflow/review-perspectives.md` (Guardian prompt framing, append)**
> For each AC that enumerates N required items, verify the test plan asserts exactly N items — flag any AC where the test count is a subset of the AC count.

**A4 — `assets/fbk-docs/fbk-sdl-workflow/review-perspectives.md` (Verification gate structural prereqs, new bullet)**
> For each AC that enumerates a list of N required items: the test plan identifies at least N corresponding assertions — confirm the count matches, not just that coverage exists.

**A5 — `assets/agents/fbk-test-reviewer.md` (CP1 section)**
> For each AC that enumerates a list of required items, count the items and verify the test strategy contains an explicit assertion for each item. Report the specific missing item(s) when the assertion count does not match the AC item count — AC coverage is not satisfied by a single test that covers the AC as a whole.

**A6 — `assets/agents/fbk-test-reviewer.md` (CP2 section)**
> For each AC that enumerates a list of required items, verify the test task's assertion list covers every item in the AC. A test task that maps to a multi-item AC but specifies fewer assertions than the AC has items is an enumeration coverage gap — flag each missing item explicitly.

### Theme B — Spec-internal contradiction detection

Two of three escalated F-* findings turned out to be spec-stale-text (implementation correct; spec needed amending). **Root cause for F-02 (Session State Footer placement contradiction) and F-04 (§4.3 vs AC-06).**

**B1 — `assets/agents/fbk-spec-author.md` (new Anti-default)**
> When a section references content defined in another section (a leaf contents list, a facilitator rule, an AC), verify the two sections agree before moving on. Contradictions that survive spec authoring propagate silently into implementation.

**B2 — `assets/fbk-docs/fbk-sdl-workflow/feature-spec-guide.md` (§7 Acceptance criteria, append)**
> Before finalizing §7, scan §4 (Technical approach) for every behavior each AC describes. When the AC text and the §4 prose describe the same behavior differently, resolve the contradiction explicitly in §4 prose and update the AC to match — do not leave both versions present.

**B3 — `assets/fbk-docs/fbk-sdl-workflow/review-perspectives.md` (NEW SDL concerns row)**
> | Spec-internal consistency | Architect | Guardian | "Identify contradictions between sections of the spec itself — cases where two sections prescribe conflicting behavior for the same component, or where a section's explicit item list does not match a corresponding section's enumeration of the same items. For each contradiction found, name the two conflicting sections and flag it blocking; do not infer which section governs. Resolution requires an explicit DECISION in the spec choosing one interpretation." |

**B4 — `assets/agents/fbk-test-reviewer.md` (CP1 section)**
> When a spec AC enumerates required items and a different spec section (prose description, contents list, or migration mapping) describes the same artifact with a different item list, flag the discrepancy as a test-target ambiguity. Do not select which list to use — require the ambiguity to be resolved before passing CP1.

**B5 — `assets/fbk-docs/fbk-sdl-workflow/code-review-guide.md` (Source of Truth Handling, new paragraph after Intent register)**
> **Spec-AC contradiction**: When a `spec-ac` sighting reports that the implementation does not satisfy a specific AC, the Challenger must verify that the cited AC is internally consistent with the spec's narrative prose. If the implementation follows the spec's prose correctly and the AC contradicts it, reject the sighting with `rejection_reason` citing the conflicting spec sections, and append a spec amendment candidate to `adjacent_observations` — the spec requires correction, not the code.

**B6 — `assets/fbk-docs/fbk-sdl-workflow/code-review-guide.md` (Orchestration Protocol step 4, edit)**

PAIRED with B5 — apply both or neither. B5 instructs the Challenger to do AC-vs-prose comparison; B6 enables it by including spec sections in the Challenger's context.

> 4. The orchestrator spawns the Challenger with target code file contents first, then the filtered JSON sightings, then — when any sighting carries `detection_source: spec-ac` — the relevant spec sections referenced by those sightings, then verification instructions + type/severity definitions + the type-severity validity matrix last. The Challenger receives and produces JSON.

### Theme C — Verbatim text drift / carry-over

**Root cause for F-01 (literal "ALL 6 agents" preserved during rewrite) and Stage 3 case-mismatch defect (`Decomposed` vs `decomposed`).**

**C1 — `assets/fbk-docs/fbk-sdl-workflow/implementation-guide.md` (Per-Wave Verification, append)**
> When a task rewrites a file by migrating content from a source, re-read any retained verbatim sections and verify they are consistent with instructions added or changed in the same rewrite.

**C2 — `assets/fbk-docs/fbk-sdl-workflow/task-compilation.md` (Orchestrator tasks wiring checklist, new paragraph)**
> When a task rewrites an orchestrator file (replacing the body, not extending it), add a checklist item: "verify no verbatim phrases from the source file that are now governed by a different instruction were carried over unchanged." Flag any literal count or agent-count phrases (e.g., "ALL 6 agents," "3 agents," "6 members") as carry-over candidates — these are controlled by the sizing instruction after a refactor and must not persist as Phase-level prescriptions.

**C3 — `assets/fbk-docs/fbk-sdl-workflow/task-compilation.md` (Interface Contracts → New interfaces, new paragraph)**
> **Spec-quoted literal strings**: When a test task asserts verbatim against a string that the implementation task must produce (CHANGELOG entry text, file content, document heading, command output), state that exact string in both task files. The test task declares the expected string; the implementation task copies it verbatim. Do not allow the implementation task to paraphrase or rephrase a spec-quoted string that a test assertion will match with `-F` or fixed-string comparison — case differences and synonym substitutions produce false failures against correct implementations.

**C4 — `assets/agents/fbk-test-reviewer.md` (CP2 section)**
> For each test assertion that matches a literal string quoted in the spec, verify the spec-quoted string and the assertion string are identical. A capitalization, punctuation, or phrasing difference between the spec-quoted text and the assertion literal is a blocking defect — the test will fail against a correct implementation that follows the spec's wording.

### Theme D — Other

**D1 — `assets/fbk-docs/fbk-sdl-workflow/implementation-guide.md` (Pause on Scope Discrepancy, append exception paragraph)**

Stage 4 retrospective named this as a process-improvement candidate — "the rule should explicitly enumerate exceptions for test-script correctness fixes that the teammate's task verifies."

> Exception: when a test-script has a correctness bug (not a missing assertion — a bug that causes the assertion to return non-zero regardless of file content) and the teammate's task exercises that test-script as its primary verification path, the teammate may fix the bug, disclose the fix verbatim in its work summary, and continue. This exception does not apply to AC-bearing files, implementation files, or assertion additions. The team lead reviews the disclosure at completion and may revert if the fix exceeds the bound.

### Reassessment guidance

When revisiting these proposals (e.g., after other progressive-disclosure-refactor child specs land):

1. **Check overlap with other child specs** — `code-review-guide-split` (Finding 6 in parent) and `test-reviewer-overhaul` (Finding 7) will substantially restructure the assets in Themes B (code-review-guide) and A/B/C (fbk-test-reviewer). Re-evaluate whether these proposals should land in the new structure rather than the current one.
2. **Check whether spec authoring discipline tightens elsewhere** — if a future spec gate or asset-graph detector closes the multi-item AC enumeration gap deterministically, Theme A's instructions may become redundant.
3. **Apply C1 + C2 + C3 + C4 as a bundle** — they all attack the same failure surface (verbatim text drift); applying a subset leaves coverage gaps.
4. **Apply B5 + B6 together** — B6 enables B5; one without the other is a no-op.
5. **A5/A6 and B4 target a single agent (fbk-test-reviewer)** that has a pending overhaul (parent spec Finding 7); these proposals may need re-targeting once that spec lands.

