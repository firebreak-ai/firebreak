# Remediation Round 2 — Intermediate Retrospective

Analysis of Phase 0 (behavioral bugs), Phase 1 (dead infrastructure), and Phase 2 (error handling & context propagation).

## Remediation Effectiveness

### Codebase State Before Remediation

Code review identified three categories of quality problems in working, shipping code:

- **Behavioral bugs** (Phase 0): Race conditions, dead sentinel guards, string literal mismatches, missing type safety on node kinds, stale struct fields. 12 distinct fixes.
- **Dead infrastructure** (Phase 1): 2,906 lines of unused code — orphaned interfaces, worker pool config, dead test helpers. Compiled and passed tests but served no purpose.
- **Error handling gaps** (Phase 2): Swallowed errors via `strings.Contains`, missing context propagation across module boundaries, a websocket handler disconnected from shutdown lifecycle.

### Fix Quality

Production code was correct across all three phases. Zero regressions introduced. The remediation incidentally improved pre-existing test health:

- Phase 0: Fixed 2 pre-existing test failures and 1 pre-existing timeout
- Phase 1: Fixed 1 pre-existing build failure in the application entry point
- Phase 2: 0 incidental fixes

Estimated pre-existing test failures reduced from 19 to ~15. Exact count unavailable — each phase reports its own delta, not a cumulative total. **Gap: future retrospectives should include cumulative test health summaries.**

### Post-Implementation Review Yield

The remediation itself introduced or left behind 13 additional issues caught by post-implementation code review:

| Phase | Findings | Critical/Major | Root Cause |
|-------|----------|----------------|------------|
| Phase 0 | 7 verified (5 fixed, 2 accepted) | 0 critical, 2 major | Test fixture inconsistencies, dead sentinel code |
| Phase 1 | 5 verified (5 fixed) | 1 critical | Wiring test outside task file scope, stale comments |
| Phase 2 | 1 verified (1 fixed) | 1 major | Placeholder context not replaced with shutdown context |

Quality problems compound — fixing one thing exposes adjacent problems. Each phase left the codebase cleaner and made remaining issues more visible (e.g., Phase 2's `isNotFoundError` extraction revealed 4 other handlers with the same `strings.Contains` anti-pattern).

## Pipeline Execution

### Task Execution

| Metric | Phase 0 | Phase 1 | Phase 2 | Total |
|--------|---------|---------|---------|-------|
| Tasks | 33 | 21 | 26 | 80 |
| Pass rate | 85% (28/33, 4 superseded) | 100% (21/21) | 100% (26/26) | 94% effective (75/80, 4 superseded, 1 post-wave fix) |
| Escalations | 0 | 0 | 0 | 0 |
| Model routing errors | 0 | 0 | 0 | 0 |

### Upstream Gate Value

Gates caught issues that would have caused implementation failures:

- **Test reviewer CP2** (Phase 1): Caught 13 uncounted test helper callers — guaranteed build failure avoided
- **Council review** (Phase 1): Caught a live production feature nearly deleted as "dead code"
- **Spec review** (Phase 0): Expanded scope on 3 findings that would have been incomplete fixes
- **Test reviewer CP1/CP2** (Phase 2): Caught 6 defects across two checkpoints before implementation

### Recurring Weaknesses

**Compilation gaps are the dominant failure mode.** Every phase had at least one instance of the task compiler not grepping broadly enough for all references to a changed symbol. The pattern: a struct field is removed or a function signature changes, and a caller outside the declared file scope breaks.

**The orchestrator skips final e2e verification.** Documented as a corrective action in Phase 1. Same gap repeated in Phase 2. A documented corrective action is insufficient — this needs a hard gate.

**Wave over-segmentation.** Phase 0's 7-wave plan had 3 waves emptied by Sonnet agents correctly fixing all compile errors in scope. The breakdown overestimates required isolation for struct field changes.

## Test Coverage Patterns

### Mechanical reliability, semantic shallowness

All 29 test tasks passed on first attempt, but post-implementation review found tests that pass while testing the wrong thing:

- Three scoring reranker test fixtures had store nodes set to one kind while candidates used another. The mock store doesn't validate node kind on lookup, so tests passed with internally contradictory scenarios.
- An entity score preservation test used zero-value node kind instead of an explicit value — passing by accident, not by design.

These are test-integrity findings, not test-failure findings. The tests compile, run, and pass. They don't prove what they claim to prove.

### Coverage gaps trace to the spec, not the implementation

Both accepted gaps in Phase 0 were debug-only code paths where the spec prescribed testing but the function had no testable return path. The spec author didn't verify observability before requiring a test. Phase 2's missed call site was a compilation gap — the test existed but wasn't updated.

**Tests that should exist but don't are a spec/planning problem. Tests that exist but are wrong are an agent judgment problem.**

### Pre-existing test failures as persistent drag

The 19-failure baseline complicates every verification step. Snapshot-based regression detection can't distinguish "newly broken" from "flaky and unlucky" — one retrieval test was confirmed flaky only after it appeared as a regression. The remediation reduced this count by ~4, but did not target pre-existing failures as a primary objective.

### Model suitability for test authoring

Haiku writes correct, instruction-following tests. Sonnet writes more complete tests — all three tasks that went beyond declared scope were Sonnet. The fixture inconsistencies (wrong node kinds) came from Haiku agents following instructions literally without questioning semantic consistency.

**Haiku is well-suited for mechanical test updates. Sonnet is better when the test requires understanding the scenario being modeled.**

## Open Questions for Remaining Phases

1. Should pre-existing test failures be targeted as a remediation phase, or left as background noise?
2. Should the task compiler be required to grep for all call sites of any changed symbol, not just the ones the spec enumerates?
3. What mechanism can enforce final e2e verification as a hard gate rather than a documented corrective action?
