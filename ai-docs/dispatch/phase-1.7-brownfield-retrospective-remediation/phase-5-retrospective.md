# Phase 5: Graph & World Consistency — Retrospective

## Factual Data

### Task Summary

| Task | Type | Model | Status | Escalations | Files Modified |
|------|------|-------|--------|-------------|----------------|
| task-01 | test | Haiku | complete | 0 | graph namespace test (created) |
| task-02 | test | Haiku | complete | 0 | graph memory test (comments) |
| task-03 | test | Sonnet | complete | 0 | graph namespace internal test (created) |
| task-04 | test | Haiku | complete | 0 | schema test (created) |
| task-05 | test | Haiku | complete | 0 | graph traverser test (modified) |
| task-06 | test | Sonnet | complete | 0 | world interface test, world context test (created), app wiring test (modified) |
| task-07 | test | Haiku | complete | 0 | graph edge indexed test (created) |
| task-08 | test | Haiku | complete | 0 | graph relationship dedup test (created) |
| task-09 | test | Haiku | complete | 0 | entity type mapping test (created) |
| task-10 | test | Haiku | complete | 0 | data importer test (modified) |
| task-11 | test | Haiku | complete | 0 | session test (modified) |
| task-12 | test | Sonnet | complete | 0 | search scoring test (created) |
| task-13 | test | Haiku | complete | 0 | search index fields test (created) |
| task-14 | test | Sonnet | complete | 0 | tokenizer test (created) |
| task-15 | impl | Haiku | complete | 0 | schema constants |
| task-16 | impl | Sonnet | complete | 0 | graph memory operations |
| task-17 | impl | Haiku | complete | 0 | graph memory operations (verified already done by task-16) |
| task-18 | impl | Haiku | complete | 0 | graph traverser |
| task-19 | impl | Haiku | complete | 0 | chat engine |
| task-20 | impl | Sonnet | complete | 0 | world manager, app wiring |
| task-21 | impl | Sonnet | complete | 0 | graph store |
| task-22 | impl | Haiku | complete | 0 | entity processing, memory consolidation |
| task-23 | impl | Sonnet | complete | 0 | graph store |
| task-24 | impl | Haiku | complete | 0 | data importer |
| task-25 | impl | Haiku | complete | 0 | session management, chat engine |
| task-27 | impl | Sonnet | complete | 0 | search index |
| task-28 | impl | Sonnet | complete | 0 | search interfaces, search index |
| task-29 | impl | Sonnet | complete | 0 | search tests, search manager |
| task-30 | impl | Sonnet | complete | 0 | shared tokenizer (created), fuzzy search, search index |

### Execution Summary

- **Total tasks**: 29 (14 test + 15 implementation)
- **Waves**: 10
- **Escalations**: 0
- **Parked tasks**: 0
- **Task-26 removed**: Merged into task-24 during breakdown (both modified the same data importer file)

### Model Routing

- **Haiku tasks**: 15 (all succeeded)
- **Sonnet tasks**: 14 (all succeeded)
- **Model routing accuracy**: 100% — no Haiku tasks required escalation to Sonnet

### Post-implementation fixes (team lead)

After Wave 10, the team lead fixed two test/impl mismatches:
1. **Search index fields test**: Test expected a single-struct parameter for the incremental index function, but implementation used individual string parameters. Updated test to match actual signature.
2. **Tokenizer test**: Test called a shared tokenizer function name that wasn't exported by the teammate's implementation. Created the proper shared function, wired the search index tokenizer to delegate to it, and restored Unicode-aware helper functions used by the fuzzy search path.

### Verification Results

- **Baseline**: 1799 passing, 24 pre-existing failures
- **Final**: 1761 passing (skipping 4 known-hanging tests), 21 failing — all pre-existing
- **Regressions**: 0
- **New test failures**: 0

### Known Issues Not Addressed

- A pre-existing database deadlock in the metadata update function (iterates records while removing them in the same transaction). The dual-namespace leak IS fixed (the write function now uses the correct prefix so the delete step targets the correct namespace), but the function itself deadlocks before completing. This is a pre-existing production bug, not introduced by this phase.

## Upstream Traceability

- **Spec review iterations**: 1 (council review produced 4 blocking findings, all resolved in spec before breakdown)
- **Blocking findings**: 4 (namespace prefix mechanism, read-side alignment, world wiring design tension, bare-string test approach)
- **Spec revisions from findings**: All 4 blocking findings led to spec changes
- **Test reviewer iterations**: 2 (CP1 at spec review: FAIL with 7 defects; CP2 at breakdown: FAIL with 7 defects — all resolved)
- **Breakdown gate attempts**: 3 (file scope conflicts, wave ordering, acceptance criteria coverage)

## Failure Attribution

No task escalations occurred. Two post-implementation fixes were needed:

1. **Index function test/impl mismatch** (Compilation gap): The test task was compiled before the implementation task and assumed a single-struct parameter. The implementation task used individual string parameters. The compilation agents didn't coordinate on the API shape — the test agent assumed one design, the impl agent chose another. Both followed their task files correctly, but the task files didn't specify the exact function signature.

2. **Shared tokenizer naming** (Compilation gap): The test task expected a specific function name. The implementation task implemented the Unicode fix as helper functions rather than a standalone shared function. The task file mentioned the expected function name but the teammate took a different approach. The team lead reconciled by creating the proper function and wiring both paths to it.

## Firebreak Observations

- **Firebreak 0.3.1 improvement**: No wave-level failures or escalations needed. This is a notable improvement over the previous phase which had multiple escalations. The updated Firebreak tooling handled wave sequencing and file scope conflict detection correctly.
- **Wave count**: 10 waves for 29 tasks. The high wave count was driven by multiple tasks needing to modify the same file serially (a consequence of the file scope conflict fix from 0.3.1), resulting in several single-task waves at the tail end. This root cause was not apparent from the retrospective data as originally written — the observation attributed it to the test/impl separation rule, which was already resolved. Retrospective instructions may need to capture per-wave task counts or file-scope serialization chains to make this kind of structural cause visible.
- **Task-17 was redundant**: task-16 already made all the changes task-17 was supposed to make. The task was correctly completed as "verified already done," but the breakdown could have merged them.

## Code Review Results

**Sighting counts**: 18 total sightings (9 production, 9 test integrity). 14 verified findings, 1 rejected, 3 weakened to no finding.
**Verification rounds**: 1 (converged in a single detection-verification pass)
**Detection source breakdown**: 16 spec-ac, 1 checklist, 1 nit-only

### Verified Findings

| ID | Category | AC | Description |
|----|----------|-----|-------------|
| F-01 | semantic-drift | AC-04 | Write function uses singular predicate name while save function uses plural — keyword predicate split |
| F-02 | semantic-drift | AC-01 | Metadata read function uses bare string literals instead of schema constants |
| F-03 | structural | AC-10 | Full-collection edge query still uses full table scan, not updated to indexed iterator |
| F-04 | semantic-drift | AC-01 | Entity processing uses bare string property keys for source metadata |
| F-05 | nit | AC-01 | Search manager uses bare "type" string in query filters (functionally correct due to prefix stripping) |
| F-06 | semantic-drift | AC-16 | Fuzzy search case normalization is ASCII-only; shared tokenizer uses Unicode-aware normalization |
| F-07 | nit | AC-16 | Capitalization detection uses ASCII-only uppercase check |
| F-08 | structural | AC-08 | World manager stored in app struct but never invoked at runtime — dead state |
| F-09 | semantic-drift | AC-01 | Metadata update write path uses bare string literals instead of schema constants |
| F-10 | test-integrity | AC-01 | Keyword test only checks non-nil, doesn't verify actual values |
| F-11 | test-integrity | AC-04 | Namespace leak test allows either namespace to win; should assert correct namespace wins |
| F-12 | test-integrity | AC-05 | Inverse relationship test accepts any non-empty inverse, not specific expected values |
| F-13 | test-integrity | AC-08 | App wiring test checks field non-nil but not that it's used in the processing pipeline |
| F-14 | nit | AC-16 | Test name references pre-fix bug behavior, misleading post-fix |

### Finding Quality

- **False positive rate**: 1/18 rejected, 3/18 weakened to no finding = 22% non-actionable
- **Breakdown by origin**: 10 introduced, 3 pre-existing, 1 nit
- **Breakdown by category**: 5 semantic-drift, 2 structural, 4 test-integrity, 3 nit

### Code Review Remediation

All 14 findings resolved:

| ID | Resolution |
|----|-----------|
| F-01 | Fixed — predicate name unified to plural form |
| F-02 | Fixed — metadata read function uses schema constants |
| F-03 | Accepted — full-collection scan is correct (no anchor node for indexing), comment added |
| F-04 | Fixed — new schema constant added, entity processing uses constants |
| F-05 | Fixed — search manager uses schema constant for type filter |
| F-06 | Fixed — case normalization delegates to standard library Unicode-aware function |
| F-07 | Fixed — capitalization detection uses standard library Unicode uppercase check |
| F-08 | Accepted — manager is for future multi-context support, comment added |
| F-09 | Fixed — metadata update uses schema constants |
| F-10 | Fixed — keyword test verifies actual values |
| F-11 | Fixed — namespace leak test asserts correct namespace wins |
| F-12 | No fix needed — relationships are intentionally one-directional (self-inverse) |
| F-13 | No fix needed — test correctly verifies wiring per acceptance criterion |
| F-14 | Fixed — test renamed to reflect correct post-fix behavior |

**10 fixed, 2 accepted with comments, 2 no fix needed.**

## Process Gaps

### Missed post-review finalization step

The orchestrator failed to finalize the retrospective and invoke `/fbk-improve` after code review remediation. The code review guide specifies post-output steps: (1) append findings summary to retrospective, (2) offer `/fbk-improve`. The findings were appended correctly, but the skill transition prompt was omitted after remediation completed. This caused the user to have to remind the orchestrator of the next step.

**Root cause**: The code review skill instructions specify the `/fbk-improve` offer in the post-output steps, but after switching to interactive remediation (fixing findings one at a time), the orchestrator lost track of the skill's remaining steps. The remediation discussion shifted context away from the skill protocol.

**Recommendation**: After completing remediation of code review findings, the orchestrator should checkpoint against the skill's step list before returning control to the user.

### Post-impl path is a dead-end — finalization steps unreachable

Cross-phase analysis (Phase 4 and Phase 5 both exhibit the same missed-finalization failure) identified a structural routing problem in the code review skill instructions. The missed finalization is not a context-attention problem — it's an instruction ordering problem.

SKILL.md routes the agent at line 16 to `references/post-impl-review.md` for post-implementation reviews. That file terminates at its Output section ("Produce findings only"). The agent treats the reference file as the complete instruction set for the path and never returns to SKILL.md.

The finalization steps exist in three locations, none reachable from the post-impl execution path:
1. **SKILL.md lines 62-63** — "invoke `/fbk-improve`" — appears after the routing section, but the agent was sent to the reference file at line 16 and never reads past the routing decision.
2. **code-review-guide.md lines 73-76** — "Post-output steps" — nested inside the Orchestration Protocol section as methodology guidance, not in the agent's execution thread.
3. **0.3.1 added post-output steps to code-review-guide.md** — this was the Phase 4 fix, but it added instructions to a guide document, not to the execution path the agent follows.

The standalone review path is less affected because it's conversational — the user naturally drives toward completion. The post-impl path is non-interactive, so no user presence pulls the agent back to remaining steps.

**Recommendation**: Each execution path must terminate with its own finalization steps. Add a Finalization section to the end of `post-impl-review.md` containing the retrospective append and `/fbk-improve` invocation. This supersedes Proposals 3, 4, and 6, which attempted behavioral fixes (hardened wording, checkpoints) for what is fundamentally a routing problem.

## Improvement Proposals from `/fbk-improve`

7 proposals generated from 3 analysts reviewing task-compilation.md, implementation-guide.md, and fbk-code-review/SKILL.md.

### task-compilation.md

**Proposal 1: Require explicit function signatures for greenfield cross-task interfaces**
- **Target**: Interface Contracts section
- **Change**: Add rule that test+impl tasks sharing a greenfield function must state the exact signature in both task files. The test task declares it first; the implementation task copies it verbatim.
- **Observation**: Both post-impl fixes were test/impl agents independently inferring different API shapes from the same spec
- **Necessity**: Without this, agents compile from the same spec but produce incompatible function signatures. Both compilation gaps followed this exact pattern.

**Proposal 2: Add redundancy merge check before finalizing task list**
- **Target**: Codebase-Grounded Compilation section
- **Change**: Add instruction to scan for tasks modifying the same file for overlapping purposes and merge them. Document the merge in the task's Context section.
- **Observation**: One task was redundant (a prior task already made all the changes), consuming a wave slot for zero productive work
- **Necessity**: No existing instruction checks for task overlap. Completeness rules push toward more tasks without a countervailing merge check.

### fbk-code-review/SKILL.md

**Proposal 3: Add post-remediation checkpoint section**
- **Target**: After Retrospective section
- **Change**: Add section requiring re-check of remaining steps after interactive remediation completes. "Complete both steps even if remediation was interactive."
- **Observation**: Orchestrator lost track of skill steps during interactive finding-by-finding remediation, skipping the improvement analysis offer
- **Necessity**: No re-entry point exists after mode shift from batch to interactive remediation.

**Proposal 4: Harden the improvement analysis instruction**
- **Target**: Final line of SKILL.md
- **Change**: Replace suggestive wording with "This step is required regardless of whether remediation was batch or interactive. Do not return control to the user before completing it."
- **Observation**: Current wording reads as suggested rather than mandatory, allowing the agent to skip it after long interactive sessions
- **Necessity**: Removes ambiguity that let the agent skip the finalization step.

### implementation-guide.md

**Proposal 5: Schema/constant drift check in per-wave verification**
- **Target**: Per-Wave Verification section
- **Change**: Add grep-based bare-string scan as a verification step when the spec defines schema constants
- **Observation**: 5 semantic-drift findings all survived wave execution and per-wave verification undetected
- **Necessity**: Current verification catches test/lint failures but not "did agents use schema constants everywhere the spec requires."

**Proposal 6: Post-code-review finalization checkpoint in Final Verification**
- **Target**: Final Verification section
- **Change**: Add instruction to re-read code review skill step list after all findings are resolved
- **Observation**: Same root cause as proposals 3/4 — interactive remediation lost the finalization step
- **Necessity**: Implementation guide is the orchestrator's primary reference; anchoring the checkpoint here catches it even if the code review skill instructions are forgotten.

### fbk-improve skill and improvement analyst agent

**Proposal 8: Execution path tracing in improvement analysis**
- **Target**: `fbk-improve/SKILL.md` (Improvement Analysis section) and `fbk-improvement-analyst.md` (Workflow section)
- **Change**: After individual per-asset analysis completes, add a path-tracing pass. The orchestrator identifies assets that route to other assets (skills referencing reference files, docs referencing leaf docs). For each routing chain, spawn one analyst with the full chain as its scope — not individual files, but the execution path an agent would follow. The analyst traces the path end-to-end and checks whether the retrospective's process gap observations survive or are explained by the path structure.
- **Observation**: The improvement analyst diagnosed the missed-finalization gap as "agent lost track of steps" (a behavioral problem) in both Phase 4 and Phase 5. Six proposals across both phases prescribed harder wording and checkpoints. The actual root cause was a routing dead-end: SKILL.md sends the agent to post-impl-review.md, which terminates without finalization steps, and control never returns. This is only visible by tracing the execution path across files. Each analyst saw one file in isolation — the SKILL.md analyst proposed fixes to SKILL.md; `post-impl-review.md` was either not assigned or analyzed without awareness of its role as a routed-to dead end.
- **Necessity**: Per-file analysis cannot detect cross-file routing problems. The same misdiagnosis recurred across two improvement cycles because the analyst methodology doesn't include path tracing. Without this change, routing dead-ends will continue to be misattributed to behavioral causes and "fixed" with instruction hardening that doesn't address the structural problem.

## Corrective Actions

### Execution path completeness test

Cross-phase analysis of the missed-finalization bug (Phase 4 and Phase 5) revealed the root cause was a routing dead-end in the code review skill, not a behavioral/attention problem. The existing `test-reference-integrity.sh` checks structural connectivity (no orphans, no broken links) but not execution path completeness (does every routed-to path reach all required terminal steps).

Created `tests/sdl-workflow/test-execution-paths.sh` — a self-enforcing structural test that:

1. Discovers all skills with `references/` directories (execution handoffs)
2. Extracts the last `##` section from each SKILL.md (the terminal/finalization section)
3. Checks that every reference file contains that section heading and any skill invocations (`/fbk-*`) within it

The test requires no manifest or external configuration. It derives required steps directly from SKILL.md, so adding a new finalization section to a skill automatically fails the test until all reference files are updated. Same forcing-function pattern as `test-reference-integrity.sh` for orphaned files.

Current results: 4 failures, all correct — both `post-impl-review.md` and `existing-code-review.md` are missing the `## Retrospective` section and the `/fbk-improve` invocation.

**Attribution**: The `/fbk-improve` skill surfaced the process gap but misdiagnosed the root cause in both Phase 4 and Phase 5, attributing it to behavioral causes (agent losing track of steps) rather than structural ones (routing dead-end). The correct diagnosis and test design required manual cross-phase analysis and execution path tracing that the per-file analyst methodology could not perform. Proposal 8 (execution path tracing in improvement analysis) would equip the analyst to follow routing chains across files rather than evaluating each file in isolation, improving its chances of detecting this class of cross-cutting concern in future runs.

**Proposal 7: Same-wave test+impl pairing guidance**
- **Target**: Wave Execution section
- **Change**: Add note that test+impl pairs with non-overlapping file scopes can coexist in the same wave with explicit ordering (test runs before impl)
- **Observation**: 10 waves for 29 tasks — attributed to strict separate-wave rule combined with file scope prevention
- **Necessity**: Reduces wave count without sacrificing isolation guarantees. The current strict rule is more conservative than necessary when file scopes don't overlap.

## Linting Baseline (Pre-Phase 6)

First linter integration established at the Phase 5 boundary. Prior to this point, no automated linting was configured — all code quality findings came from the adversarial code review pipeline.

### Cross-Phase Results (golangci-lint, default + aggressive linters)

**Default linters** (errcheck, staticcheck, govet, unused, gosimple, ineffassign):

| Category | Full codebase | Introduced by remediation (phases 0-5) | Pre-existing |
|----------|--------------|----------------------------------------|-------------|
| Production | 30 | 2 | 28 |
| Test | 50 | 19 | 31 |
| Experimental | 20 | 17 | 3 |
| **Total** | **100** | **38** | **62** |

**Aggressive linters** (+ gocognit, gocyclo, dupl, gocritic, revive):

| Linter | Full codebase | Introduced by remediation |
|--------|--------------|--------------------------|
| Cognitive complexity (>30) — production | 20 functions | 0 |
| Cognitive complexity (>30) — test | 15 functions | 5 (structural AST scan tests, inherently complex) |
| Code duplication (dupl) | 0 | 0 |
| Cyclomatic complexity (gocyclo) | 0 | 0 |
| Style/idiom (revive) | 50 | — (predominantly unused-parameter in test mocks) |

### Interpretation

Remediation introduced 2 production lint issues across ~39K lines of changes and 404 files touched (both unchecked error returns). Pre-existing code contains 28 production lint issues and 20 functions exceeding cognitive complexity thresholds — these represent the baseline that future phases can target.

Linter findings measure the floor (obvious bugs, style violations), not the ceiling (behavioral fidelity, architectural coherence). The 14 code review findings from this phase — semantic drift, dead state, test integrity gaps — were all invisible to linters. The adversarial review pipeline and linting are complementary, not redundant.

### Linter Integration with Code Review

The code review skill integrates with any project-configured linter. Prior to Phase 6, no linters were configured — all quality findings came from the Detector/Challenger pipeline alone. With linting now available, the code review agent can delegate mechanical checks (unchecked errors, unused variables, style violations) to the linter and focus attention on the behavioral and structural issues that linters cannot detect. Expected effects: reduced false positives on mechanical issues, improved finding quality on issues requiring spec-aware reasoning.
