# Phase 3: Code Deduplication — Retrospective

## Factual Data

### Per-task results

| Task | Type | Wave | Model | Result | Escalations | In-session retries |
|------|------|------|-------|--------|-------------|-------------------|
| task-01 | test | 1 | Haiku | pass | 0 | 0 |
| task-03 | test | 1 | Haiku | pass | 0 | 0 |
| task-05 | test | 1 | Haiku | pass | 0 | 0 |
| task-07 | test | 1 | Haiku | pass | 0 | 0 |
| task-09 | test | 1 | Sonnet | pass | 0 | 0 |
| task-02 | impl | 2 | Haiku | pass | 0 | 0 |
| task-04 | impl | 2 | Haiku | pass | 0 | 0 |
| task-06 | impl | 2 | Sonnet | pass | 0 | 1 (variable shadowing in logging call caught by build) |
| task-08 | impl | 2 | Sonnet | pass | 0 | 0 |
| task-10 | impl | 2 | Haiku | pass | 0 | 0 |
| task-11 | test | 3 | Haiku | pass | 0 | 0 |
| task-12 | impl | 4 | Sonnet | pass | 0 | 0 |
| task-13 | test | 5 | Sonnet | pass | 0 | 0 |
| task-14 | impl | 6 | Sonnet | pass | 0 | 0 |

### Task sizing accuracy

| Task | Declared files | Actual files | Match |
|------|---------------|-------------|-------|
| task-02 | 1 | 1 | ✓ |
| task-04 | 1 | 1 | ✓ |
| task-06 | 2 | 2 | ✓ |
| task-08 | 1 | 1 | ✓ |
| task-10 | 1 | 1 | ✓ |
| task-12 | 3 | 3 | ✓ |
| task-14 | 1 | 1 | ✓ |

### Model routing accuracy

- **Haiku tasks**: 7/7 succeeded without escalation
- **Sonnet tasks**: 7/7 succeeded without escalation
- All model assignments were correct. No under-routing.

### Verification gate pass rates

- Spec gate: 2 attempts (first had numbered headings, fixed)
- Review gate: 2 attempts (first missing test infrastructure section in correct location)
- Breakdown gate: 2 attempts (first had same-wave dependencies, restructured to strict wave separation)
- Task reviewer gate: 1 attempt (pass)
- CP2 test review: 1 attempt (pass)

### Code impact (final, including code review fixes)

- 11 files modified, 6 new files created
- 376 insertions, 396 deletions (net -20 lines)
- 7 ACs satisfied across 7 findings

### Code review results

3 rounds of detection/verification. 10 total sightings across 3 rounds.

| Round | Sightings | Verified | Rejected | Fixed |
|-------|-----------|----------|----------|-------|
| 1 | 4 | 1 (F-01) | 3 | 1 |
| 2 | 2 | 2 | 0 | 2 |
| 3 | 2 | 2 (F-01, F-02) | 0 | 1 fixed, 1 deferred |

**Fixes applied during code review:**
- F-01 (R1): Options struct constructed redundantly in two caller functions → moved to shared pipeline-preparation function, shared via result struct field
- R2-S01: Dead model-name fallback in a caller function (unreachable after shared preparation resolves it) → removed
- R2-S02: Test missing field comparison → added
- R3-F02 (pre-existing): Entity ID list passed as nil in scoring function, making entity-proximity boost permanently inert → wired parameter
- R3-F01 (pre-existing): Stale skip on an error-path test → updated skip message, deferred to Phase 4 (AC-08)

### Test results (final)

**Passing packages (18):**

All 18 packages in scope passed. No regressions introduced.

**Pre-existing failures (6, unchanged from baseline):**

6 packages had pre-existing failures unrelated to Phase 3 changes: 7 test failures in the core processing package, pre-existing failures in data extraction, concurrency, configuration defaults, API handler lock contention (timeout), and an experimental module build failure.

**New tests added by Phase 3 (all passing):**

| Covers | Description |
|--------|-------------|
| AC-01 | Property extraction from recent items (4 subtests) |
| AC-02 | Scoring formula unit tests (5 subtests) |
| AC-04 | Data loading from byte input (3 subtests) |
| AC-05 | Pipeline equivalence across sync/stream paths |
| AC-06 | Index update under lock (3 subtests) |
| AC-07 | Fallback analysis with surrounding context |

**Existing tests verified passing (key regression guards):**

17 existing tests verified as regression guards across ACs 01–07, covering delegation, seam coverage, end-to-end flows, equivalence, and primary paths.

## Upstream Traceability

- **Stage 1 (spec)**: 1 iteration. Original spec from prior review cycle updated with corrected line ranges, site counts, and 9-section template compliance.
- **Stage 2 (review)**: 1 iteration with revisions. 8 blocking findings, 7 important, 1 informational. All resolved. One finding dropped from scope (fix cost exceeded duplication risk). Three key design decisions made: verbose logging, significance counting, options stay with callers.
- **Stage 3 (breakdown)**: 1 iteration. Gate required wave restructuring (dependencies must be in strictly earlier waves). 14 tasks across 6 waves.
- **Blocking findings that led to spec revisions**: 8 blocking (all resolved in spec). Notable: one finding dropped due to cross-package coupling cost, one finding required explicit logging/options decisions, one corrected a wrong test file reference.

## Failure Attribution

No task failures or escalations occurred. One in-session retry (task-06): a formula extraction required renaming a local variable to avoid shadowing the new package-level function — the agent caught this from a build error on a logging call not mentioned in the task instructions.

**Root cause of the retry**: Compilation gap — the task instructions identified the variable shadowing risk for the main formula lines but missed a subsequent logging reference that also used the shadowed name. The agent resolved it independently from the build error.

## Code Review Findings

### Introduced findings (fixed)

| ID | Type | Severity | Description | Fix |
|----|------|----------|-------------|-----|
| CR-F01 | structural | minor | Options struct constructed redundantly in two caller functions | Moved to shared preparation function, shared via result struct field |
| CR-R2-S01 | structural | minor | Dead model-name fallback (unreachable after shared preparation resolves it) | Removed dead guard |
| CR-R2-S02 | test-integrity | minor | Pipeline test missing field comparison | Added field length assertion |

### Pre-existing findings (discovered incidentally)

| ID | Type | Severity | Description | Resolution |
|----|------|----------|-------------|------------|
| CR-F02 | behavioral | major | Entity ID list passed as nil in scoring function — entity-proximity boost permanently inert (was Phase 1 finding, missed) | Fixed: wired parameter |
| CR-P3-01 | test-integrity | major | Error-path test permanently skipped — needs dependency-injection setter | Deferred to Phase 4 AC-08 |

### Rejections (7 total across 3 rounds)

- R1-S01: Empty sessions in pipeline test (correct test design for path-convergence scope)
- R1-S02: Helper equivalence test missing (existing rebuild-comparison test already covers it)
- R1-S04: Function exported unnecessarily (export required by external test package)

## Observations

- **Dropped finding**: Valid finding correctly identified but dropped at review because fix cost (new exported function, cross-package coupling) exceeded the 6-line idiom's duplication risk. Worth noting for future phases — not all duplication warrants extraction.
- **Pipeline test passed before implementation**: The pipeline equivalence test passed before the shared preparation function was extracted, confirming the two paths already produced identical inputs. The test still serves as a regression guard.
- **Code review caught residual duplication**: The implementation agents correctly extracted the shared preparation function but left options construction duplicated in both callers. The code review's detection-verification loop caught this and it was consolidated in the fix pass.
- **Code review caught prior-phase miss**: A nil-parameter wiring gap from Phase 1 was discovered incidentally. Phase 1 was supposed to either wire or remove it but missed it entirely. Fixed here with a 1-line change.
- **Pre-existing test failures**: 6 packages have pre-existing failures unrelated to Phase 3. These should be addressed separately.
- **Wave structure overhead**: The strict "dependencies must be in earlier waves" gate rule forced 6 waves for what could logically be 3 (tests, impls, sequential pairs). This added coordination overhead but no implementation risk.
