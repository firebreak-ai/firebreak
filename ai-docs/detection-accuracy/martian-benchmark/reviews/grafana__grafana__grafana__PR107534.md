# Code Review: grafana__grafana__grafana__PR107534

**PR**: Advanced Query Processing Architecture
**URL**: https://github.com/grafana/grafana/pull/107534
**Instance**: grafana__grafana__grafana__PR107534
**Date**: 2026-04-08

## Intent Register

### Intent Claims

1. `runSplitQuery` filters hidden/empty queries and applies template variable interpolation before time-based splitting
2. `runShardSplitQuery` filters hidden/empty queries and applies template variable interpolation before shard-based splitting
3. Both splitting paths use `datasource.applyTemplateVariables(query, scopedVars, filters)` per-query instead of the batch `interpolateVariablesInQueries`
4. Template variables like `$__auto` and `$step` are resolved before query execution in both split paths
5. `querySplitting.ts` gains interpolation it previously lacked — this is a bug fix
6. `shardQuerySplitting.ts` reorders operations: filtering now precedes interpolation (was interpolation-then-filter)
7. `request.filters` is now passed to `applyTemplateVariables` in both paths (was missing from shard path's old `interpolateVariablesInQueries` call)
8. Tests verify interpolation results by inspecting the first `runQuery` call's targets

### Intent Diagram

```mermaid
graph TD
    subgraph querySplitting
        A[request.targets] --> B[filter: !hide]
        B --> C[filter: has expr]
        C --> D[applyTemplateVariables]
        D --> E[partition: split vs non-split]
        E --> F[partition: logs vs metrics]
    end

    subgraph shardQuerySplitting
        G[request.targets] --> H[filter: has expr]
        H --> I[filter: !hide]
        I --> J[applyTemplateVariables]
        J --> K[splitQueriesByStreamShard]
    end

    subgraph "Old shardQuerySplitting (removed)"
        L[request.targets] --> M[interpolateVariablesInQueries]
        M --> N[filter: has expr]
        N --> O[filter: !hide]
    end
```

---

## Verified Findings

### F-01 | test-integrity | major

**Location**: `querySplitting.test.ts`, "Interpolates queries before execution" test
**Detection source**: checklist (item 4 — non-enforcing tests)
**Current behavior**: Test asserts interpolation by inspecting only `datasource.runQuery.mock.calls[0][0].targets[0]` — the first `runQuery` call. In time-split execution, `runQuery` is called once per time chunk. Interpolation in subsequent calls is never verified.
**Expected behavior**: A test claiming "Interpolates queries before execution" should verify all `runQuery` invocations receive interpolated queries, or scope its name to "first call."
**Evidence**: Diff lines 19-20 confirm `mock.calls[0][0]` is the sole assertion index. The existing test comment "3 days, 3 chunks, 3 requests" (diff line 26) confirms multiple `runQuery` calls in execution.
**Pattern**: non-enforcing-test-name-assertion-mismatch

### F-02 | test-integrity | major

**Location**: `shardQuerySplitting.test.ts`, "Interpolates queries before execution" test
**Detection source**: checklist (item 4 — non-enforcing tests)
**Current behavior**: Same pattern as F-01. Test asserts `mock.calls[0][0].targets[0]` only. In shard-split execution, `runQuery` is called once per shard group. Only the first shard call is inspected.
**Expected behavior**: Same as F-01 — assertion scope should match test name.
**Evidence**: Diff lines 78-82 confirm `mock.calls[0][0]`. Existing test comment "5 shards, 3 groups + empty shard group, 4 requests" (diff line 87) confirms multiple calls.
**Pattern**: non-enforcing-test-name-assertion-mismatch

### F-03 | fragile | minor

**Location**: `shardQuerySplitting.test.ts`, call count assertion
**Detection source**: checklist (item 1 — bare literals)
**Current behavior**: `expect(datasource.applyTemplateVariables).toHaveBeenCalledTimes(5)` uses bare literal `5`. Value derives from shard fixture `['1', '10', '2', '20', '3']` (5 values) with no named constant or comment connecting them.
**Expected behavior**: Count should derive from or reference the fixture length.
**Evidence**: Diff line 93 (`toHaveBeenCalledTimes(5)`) and diff line 60 (`mockResolvedValue(['1', '10', '2', '20', '3'])`).
**Pattern**: bare-literal

### F-04 | test-integrity | major | verified-pending-execution

**Location**: `querySplitting.test.ts` and `shardQuerySplitting.test.ts`, "Interpolates queries before execution" tests
**Detection source**: checklist (items 4, 13)
**Current behavior**: Both tests assert `targets[0].step` equals `'5m'` after interpolation. The `replace` mock replaces `'$step'` with `'5m'`. Whether production `applyTemplateVariables` actually routes `step` fields through template variable replacement is not demonstrated in the diff. If it only interpolates `expr`, the `step` field would remain `'$step'` at runtime, but the test mock configuration could mask this.
**Expected behavior**: Test should demonstrate or reference the production path that routes `step` through replacement.
**Evidence**: Diff lines 19-20 and 80-81 show `step` assertions. `replace` mock at diff lines 12-14 and 69-71. `applyTemplateVariables` implementation absent from diff.
**Pattern**: mock-permissiveness-masking-constraints

### F-05 | structural | minor

**Location**: `querySplitting.ts` (lines 37-38) and `shardQuerySplitting.ts` (lines 123-125)
**Detection source**: structural-target (semantic drift)
**Current behavior**: `querySplitting.ts` filters `!query.hide` first, then `query.expr`. `shardQuerySplitting.ts` filters `query.expr` first, then `!query.hide`. The end result is identical but the ordering is inconsistent across parallel splitting paths being unified by this PR.
**Expected behavior**: Parallel splitting paths should use the same filter ordering to support the unification intent.
**Evidence**: Confirmed directly from the diff.
**Pattern**: semantic-drift

### F-06 | test-integrity | minor

**Location**: `shardQuerySplitting.test.ts`, `applyTemplateVariables` mock in `beforeEach`
**Detection source**: checklist (item 13 — mock permissiveness)
**Current behavior**: Mock mutates `query.expr` in place and returns the same object reference. Because the original `request.targets[0]` is mutated, a hypothetical bug passing `request.targets` directly (bypassing `.map()`) would produce the same observable values as correct behavior. Impact is on the existing "Interpolates queries before running" test (diff line 93), not the new "Interpolates queries before execution" test (which creates a fresh datasource).
**Expected behavior**: Pure-transform mock (creates new object) to distinguish "mapped result used" from "original mutated object used."
**Evidence**: Diff lines 56-59 (mock) and lines 91-93 (assertion using this mock).
**Pattern**: mock-permissiveness-masking-constraints

### F-07 | test-integrity | minor

**Location**: `querySplitting.test.ts` and `shardQuerySplitting.test.ts`, both "Interpolates queries before execution" tests
**Detection source**: checklist (item 6 — non-enforcing test variants)
**Current behavior**: Both tests dereference `mock.calls[0][0]` without a preceding assertion that `runQuery` was called. If `runQuery` is never called, `mock.calls[0]` is `undefined` and the dereference throws `TypeError` rather than a meaningful assertion failure.
**Expected behavior**: Guard assertion like `expect(datasource.runQuery).toHaveBeenCalled()` before the `calls[0]` dereference.
**Evidence**: Diff lines 19-20 (querySplitting) and lines 78-81 (shardQuerySplitting).
**Pattern**: non-enforcing-test-variant

### F-08 | behavioral | minor

**Location**: `querySplitting.ts` and `shardQuerySplitting.ts`, both filter-then-map chains
**Detection source**: intent (item 4)
**Current behavior**: Both files filter on `query.expr` truthiness before calling `applyTemplateVariables`. A query with `expr: '$QUERY_EXPR'` (truthy) passes. If interpolation resolves to empty string, `expr: ''` reaches `runQuery`. In `shardQuerySplitting.ts` this is a regression: old code interpolated first, then filtered, which would have caught empty-after-interpolation.
**Expected behavior**: Empty-expr filter should run after interpolation (`.map(applyTemplateVariables).filter(q => q.expr)`), or `applyTemplateVariables` should guarantee non-empty returns.
**Evidence**: Diff lines 119-129 (shardQuerySplitting.ts old→new), lines 35-41 (querySplitting.ts).
**Pattern**: filter-order-regression

---

## Findings Summary

| ID | Type | Severity | Description |
|----|------|----------|-------------|
| F-01 | test-integrity | major | querySplitting test asserts only first `runQuery` call |
| F-02 | test-integrity | major | shardQuerySplitting test asserts only first `runQuery` call |
| F-03 | fragile | minor | Bare literal `5` in call count assertion |
| F-04 | test-integrity | major | `step` field interpolation path not demonstrated |
| F-05 | structural | minor | Filter ordering inconsistency across parallel paths |
| F-06 | test-integrity | minor | Mutating mock masks map vs original reference |
| F-07 | test-integrity | minor | Missing guard before `calls[0]` dereference |
| F-08 | behavioral | minor | Empty-expr filter runs pre-interpolation |

**Totals**: 8 findings — 3 major, 5 minor | 0 critical | 0 info

---

## Retrospective

### Sighting Counts

- **Total sightings generated**: 15 (S-01 through S-15)
- **Verified findings at termination**: 8 (F-01 through F-08)
- **Rejections**: 5 (S-04, S-06, S-08, S-12, and round 3 convergence: S-13 duplicate, S-14 re-report, S-15 info-level)
- **Nit count**: 1 (S-06 rejected as nit — parallel test duplication across distinct functions)

**By detection source**:
- checklist: 10 sightings (S-01, S-02, S-03, S-05, S-08, S-09, S-10, S-13, S-14, S-15 partial)
- structural-target: 3 sightings (S-06, S-07, S-15)
- intent: 2 sightings (S-04, S-11)
- spec-ac: 0 (no spec available)
- linter: 0 (N/A — diff-only review)

**Structural sub-categorization**: semantic drift (F-05)

### Verification Rounds

- **Round 1**: 8 sightings → 5 findings (F-01–F-05), 3 rejections
- **Round 2**: 4 sightings → 3 findings (F-06–F-08), 1 rejection
- **Round 3**: 3 sightings → 0 new findings (1 duplicate, 1 re-report, 1 info-level). Convergence reached.
- **Total rounds**: 3

### Scope Assessment

- **Files reviewed**: 4 (2 production, 2 test)
- **Diff size**: ~130 lines
- **Review type**: diff-only benchmark, no repository access

### Context Health

- **Round count**: 3 (converged naturally)
- **Sightings-per-round trend**: 8 → 4 → 3 (declining)
- **Rejection rate per round**: 37.5% → 25% → 100%
- **Hard cap reached**: No

### Tool Usage

- **Project-native tools**: N/A (diff-only review, no project tooling)
- **Grep/glob fallback**: N/A (diff provided as file)

### Finding Quality

- **False positive rate**: TBD (pending user review)
- **False negative signals**: None reported
- **Origin breakdown**: All 8 findings are `introduced` (created by the changes under review)

### Intent Register

- **Claims extracted**: 8 (derived from diff structure — no external documentation available)
- **Sources**: Diff analysis only
- **Findings attributed to intent comparison**: 2 (F-08 from intent item 4, F-05 from intent item 6 context)
- **Intent claims invalidated during verification**: 0

### Observations

- The diff is a well-focused refactoring with a clear purpose (unifying interpolation paths). Most findings are test-integrity issues rather than production behavioral bugs.
- F-08 (filter-before-interpolation) is the most significant production-facing finding — it represents a behavioral regression in `shardQuerySplitting.ts` where the old code handled empty-after-interpolation queries correctly.
- The test suite heavily relies on inspecting `mock.calls[0][0]` which covers only the first execution batch. For splitting functions whose primary purpose is multi-batch execution, this pattern systematically under-tests the core behavior.
- F-04 (verified-pending-execution) cannot be definitively confirmed without access to the `applyTemplateVariables` implementation. The finding is structurally sound but requires execution-level verification.
- Linter output: N/A (isolated diff review with no project tooling available)
