# instruction-hygiene — Retrospective

## Stage 1: Spec Authoring

**Duration**: Extended — spec went through multiple revision cycles driven by 3 independent pre-review agents (instruction alignment, context asset quality, regression risk) before formal council review.

**Key decisions**:
- Summaries with detection heuristic triggers (not bare references, not full deletion) — driven by discovery that ai-failure-modes.md has consumers beyond the Detector (orchestrator in conversational mode)
- Added quality-detection.md loading to conversational review path — discovered during review that standalone path didn't load quality-detection.md
- Context bypass / silent error discard split added after reviewer identified it as an unaddressed redundancy
- Prompt ordering embedded in step definitions rather than as a meta-instruction — all 3 pre-reviewers converged on this
- AC-08 (token reduction) marked verified-by-inspection — not automatable without fragile word-count proxies

**What worked**: The 3-agent pre-review caught the major issues before the formal council. The Necessity Test discussion forced honest evaluation of whether summaries serve the agent or the human.

**What to improve**: The orchestrator initially skipped the intent-extraction phase of the code review (the broader evaluation context), suggesting the same instruction-following problem the spec is trying to fix applies to the orchestrator itself.

## Stage 2: Spec Review

**Council composition**: Architect + Guardian + Builder (discussion mode)
**Findings**: 7 blocking, 15 important (first pass). All resolved through spec revisions.
**Re-review**: Clean pass — 0 blocking, 6 important (4 fixed, 2 declined as nits).

**Key council contributions**:
- Architect: Found 6 existing test breakages the spec missed (test-detection-scope.sh tests 15-19, test-code-review-guide-extensions.sh test 3)
- Architect (re-review): Found pattern-label field missing from format templates — integration gap between Detector assignment and Challenger preservation
- Guardian: Mapped every AC to its test, found AC-08 gap, enumerated detection target grep list
- Builder: Challenged dedup approach (deletion vs summary), caught conversational path gap, flagged testing over-engineering

**Test reviewer**: FAIL on first pass (11 defects). All resolved. Key defects: sole absence assertions, phantom AC-08 coverage, completion gate contradictions.

## Stage 3: Task Breakdown

**Tasks**: 13 total (7 test in Wave 1, 6 implementation in Wave 2)
**AC coverage**: 13/13 ACs covered (AC-08 nominal — pass-through test documenting inspection-only verification)
**Test reviewer CP2**: FAIL on first pass (5 defects). All resolved: completion gate contradictions fixed, renumbering ambiguity clarified, phantom AC-08 coverage documented, UV-7 runtime gap acknowledged.

**Key decisions**:
- All test tasks Wave 1, all implementation tasks Wave 2 — clean separation
- All tasks Haiku model — bounded single-file markdown edits with exact replacement text
- Existing test updates in separate tasks from new test creation — independent file scopes

## Stage 4: Implementation

### Factual data

| Metric | Value |
|--------|-------|
| Tasks | 13 (7 test, 6 implementation) |
| Waves | 2 |
| All tasks pass/fail | 13 pass, 0 fail |
| Escalations | 0 |
| Model | All Haiku |
| Baseline tests (pre-implementation) | 26 passing |
| Final test count | 31 passing (26 baseline + 5 new) |
| Baseline regressions | 0 |
| Files modified | 10 (7 production + 3 existing test) |
| Files created | 5 (new test files) |

**Per-task detail:**

| Task | Type | Status | Escalations | Model |
|------|------|--------|-------------|-------|
| task-01 | test | complete | 0 | Haiku |
| task-02 | test | complete | 0 | Haiku |
| task-03 | test | complete | 0 | Haiku |
| task-04 | test | complete | 0 | Haiku |
| task-05 | test | complete | 0 | Haiku |
| task-06 | test | complete | 0 | Haiku |
| task-07 | test | complete | 0 | Haiku |
| task-08 | impl | complete | 0 | Haiku |
| task-09 | impl | complete | 0 | Haiku |
| task-10 | impl | complete | 0 | Haiku |
| task-11 | impl | complete | 0 | Haiku |
| task-12 | impl | complete | 0 | Haiku |
| task-13 | impl | complete | 0 | Haiku |

**Task sizing accuracy:** All tasks stayed within declared file scope. No task exceeded the 1-2 file constraint.

**Model routing accuracy:** All 13 tasks assigned Haiku, all succeeded on first attempt. Correct routing — bounded single-file markdown edits with exact replacement text are ideal Haiku tasks.

### Upstream traceability

- Stage 1: Multiple revision cycles. 3 pre-review agents + formal council before spec finalization.
- Stage 2: 2 council passes. First pass: 7 blocking + 15 important. Re-review: 0 blocking + 6 important (4 fixed, 2 nits declined). Test reviewer: FAIL then PASS.
- Stage 3: Test reviewer CP2: FAIL (5 defects) then PASS after fixes. Both gates passed.

### Failure attribution

No failures to attribute. All 13 tasks completed on first attempt with zero escalations. This is consistent with the task characteristics: bounded, single-file markdown edits with exact replacement text provided in the task files. Haiku was the correct model choice for this work profile.
