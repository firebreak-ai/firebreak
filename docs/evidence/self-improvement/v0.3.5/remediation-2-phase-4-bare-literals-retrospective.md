# Retrospective: Brownfield Remediation — Bare Literals Phase (Anonymized)

> Anonymized for sharing with Firebreak. Project-specific identifiers replaced with generic descriptions. All metrics, timings, and process observations are unchanged.

## Timeline

| Stage | Started | Completed |
|-------|---------|-----------|
| Stage 1: Spec | 2026-04-03 | 2026-04-03 |
| Stage 2: Spec Review | 2026-04-03 | 2026-04-03 |
| Stage 3: Breakdown | 2026-04-03 | 2026-04-03 |
| Stage 4: Implementation | 2026-04-03 | 2026-04-03 |

**Wall clock time (session start to final commit):** 3 hours 13 minutes.

**Scope:** Replace bare string and numeric literals with named constants across a Go monorepo. 14 production files, 12 test files, 1 new file. One behavioral addition (metrics timestamp population). This was the 4th phase of a multi-phase remediation cycle running under Firebreak 0.3.4.

## Key decisions

1. **Remove 3 findings from scope** (Stage 1) — Codebase verification confirmed all three were resolved in prior phases. Including them would be false work.

2. **Widen one finding's scope** (Stage 1) — Original spec described 3 sites in one file. Codebase search found 5 additional bare string sites in a sibling file and 10+ in test files. All sites must use the same constants for consistency.

3. **Narrow one finding: constant already exists** (Stage 1) — A constant for one of the target strings was already present in the schema package. Only two other strings needed new constants. Avoids duplicate constants.

4. **Correct line numbers** (Stage 1) — Prior phase work shifted line numbers from the original review. Updated to actual current locations.

## Scope changes

- 3 findings removed (resolved in prior phases)
- 1 finding expanded (additional sites in sibling file + tests)
- 1 finding narrowed (constant already exists)

## Stage 1: Spec

**Clarifying questions / ambiguity resolved:**
- No user clarifying questions were needed. All scope decisions were resolved by codebase verification.

**Scope inclusions:**
- All remaining 16 findings from the original spec (after pruning 3 resolved ones)
- 1 finding carried forward from prior phase code review

**Scope exclusions:**
- 3 findings confirmed resolved, excluded with phase attribution
- Making any constants configurable via config file (non-goal)
- Changing any constant values (non-goal)

**Open questions deferred:**
- None — all scoping decisions resolved during spec authoring.

**Note:** This is a fresh session started to measure token usage for a single phase of brownfield remediation. This phase was executed with the Firebreak 0.3.4 workflow update.

**Process failure:** After the gate passed, the skill instruction to write the Stage 1 retrospective was not followed. The retrospective was only created after the user explicitly pointed out the omission. The skill prompt states this step clearly under "## Retrospective" — it was not an ambiguous instruction. Root cause is unclear: the gate result and the semantic criteria summary may have consumed enough attention that the transition steps were not re-read before presenting to the user. This should be flagged for Firebreak pipeline improvement.

## Stage 2: Spec Review

**Perspectives invoked:** Guardian, Architect, Builder (discussion mode). Test reviewer (independent).

**Blocking findings:** 5 (4 from council + 1 additional from test reviewer)

| ID | Finding | Source |
|----|---------|--------|
| R-01 | Namespace prefix constant typed as domain type — wrong type; string-slice site missed | Architect + Builder |
| R-02 | Sentinel marker literal not accounted for — UV check will produce false positives | Architect |
| R-03 | Carry-forward mock injection approach contradicts concrete field type | Guardian + Architect + Builder |
| R-04 | Acceptance criteria test names non-existent function | Guardian + Test Reviewer |
| R-05 | Constant deduplication fails — two test files have different build tags | Builder |
| TSR-02 | Logging-only variant strings not covered by any proposed constant | Test Reviewer only |

**Important findings:** 3 (site count error, missing test rationale, constants placement ambiguity)

**Informational findings:** 4 (scope clarifications, line number corrections, type decisions)

**Iteration count:** 1 (no spec revision loop required — findings go to spec revision before breakdown)

**Threat model:** Not required. No trust boundaries, no data handling changes, pure internal refactor.

**Notable observation:** The test reviewer independently found TSR-02 (logging-only variant gap) which all three council agents missed despite explicitly reading the same file. The council agents verified the site count was correct for assignment sites but did not flag that logging sites use distinct string values not covered by the proposed constants. The test reviewer's UV check caught it. **This suggests council agents should be explicitly prompted to check the string values at each enumerated site, not just the site count.**

**Spec revisions required before breakdown:** 10 (type corrections, scope additions, mock path redesign, test naming, build tag handling, site count corrections, placement policy, test rationale)

## Stage 3: Breakdown

**Tasks produced:** 26 tasks across 3 waves

| Wave | Tasks | Notes |
|------|-------|-------|
| 1 | 8 tasks | Independent foundation: schema constants, package constants, numeric extractions |
| 2 | 16 tasks | Test tasks first, then schema-dependent impl tasks |
| 3 | 3 tasks | Behavioral changes: metrics population, setter method, string constant replacements |

**Models assigned:** Haiku for 24 tasks (straightforward substitution, single-file additions); Sonnet for 2 tasks (two-level mock chain; three distinct site types in one file; metrics population flow).

**Gate iterations:**

1. `task-reviewer-gate.sh` — first run failed: 14 implementation tasks had `test_tasks: []` (empty array falsy in Python gate check). Fixed by assigning appropriate test task references to each impl task. Second run passed.

2. `breakdown-gate.sh` — first run failed on two issues:
   - One task (wave 2) depended on another task (wave 2) — intra-wave dependency violation. Fixed by moving the dependent task to wave 3.
   - Test tasks listed after implementation tasks within wave 2. Fixed by reordering the manifest.
   Second run passed.

**Test reviewer (CP2):** PASS. Non-blocking flag: one task's type-assertion injection guard (`if ok`) silently skips mock injection on signature mismatch; implementor should add `t.Fatal` on `!ok`.

**New test tasks added (not in original spec):** 4 tasks — satisfy the gate's requirement that every AC has a test task. These represent real cleanup: test files contain bare strings that will be inconsistent with the Wave 2 production changes.

**Process note:** One task's wave assignment was a design error — placed in wave 2 without recognizing its dependency was also wave 2. The gate caught it; wave 3 is the correct placement.

## Stage 4: Implementation

**Firebreak version:** 0.3.4

**Baseline:** 1856 passing, 20 pre-existing failures (5 packages).

### Task execution summary

| Task | Type | Model | Status | Escalations | In-session retries |
|------|------|-------|--------|-------------|-------------------|
| task-01 | impl | Haiku | complete | 0 | 0 |
| task-02 | impl | Haiku | complete | 0 | 0 |
| task-03 | impl | Haiku | complete | 0 | 0 |
| task-04 | test | Haiku | complete | 0 | 0 |
| task-05 | test | Haiku | complete | 0 | 0 |
| task-06 | test | Haiku | complete | 0 | 0 |
| task-07 | test | Sonnet | complete | 0 | 0 |
| task-08 | impl | Haiku | complete | 0 | 0 |
| task-09 | impl | Haiku | complete | 0 | 0 |
| task-10 | impl | Haiku | complete | 0 | 0 |
| task-11 | impl | Haiku | complete | 0 | 0 |
| task-12 | impl | Haiku | complete | 0 | 0 |
| task-13 | impl | Haiku | complete | 0 | 0 |
| task-14 | impl | Haiku | complete | 0 | 0 |
| task-15 | impl | Haiku | complete | 0 | 0 |
| task-16 | impl | Haiku | complete | 0 | 0 |
| task-17 | impl | Sonnet | complete | 0 | 0 |
| task-18 | impl | Haiku | complete | 0 | 0 |
| task-19 | impl | Haiku | complete | 0 | 0 |
| task-20 | impl | Haiku | complete | 0 | 0 |
| task-21 | impl | Sonnet | complete | 0 | 0 |
| task-22 | impl | Haiku | complete | 0 | 0 |
| task-23 | test | Haiku | complete | 0 | 0 |
| task-24 | test | Haiku | complete | 0 | 0 |
| task-25 | test | Haiku | complete | 0 | 0 |
| task-26 | test | Haiku | complete | 0 | 0 |

**Total:** 26/26 complete. Zero escalations. Zero in-session hook retries (TaskCompleted hook fired but no rejections).

### Model routing accuracy

All 24 Haiku tasks succeeded without escalation. All 3 Sonnet tasks succeeded without escalation. Haiku success rate: 100%. No model routing changes warranted in retrospect.

### Task sizing accuracy

All tasks modified only their declared file scopes. No out-of-scope files were touched. One edge case: log field arguments (e.g., `F("session_id", ...)`) were correctly left unchanged — they are log labels, not property map keys. Agent honored the scope boundary without guidance.

### Per-wave verification

| Wave | New failures | Classification |
|------|-------------|----------------|
| 1 | 0 | — |
| 2 | 1 (intentional pre-implementation test) | Expected — test task's intentional pre-implementation failure |
| 3 | 0 | All tests pass including new behavioral tests |

### Behavioral observations

**task-07 deviation:** A test was expected to fail before a later task added a setter method (type assertion returns `ok=false`, mock not injected). Instead it passed immediately after unskipping. Root cause: the existing wired component already fails to parse the mock's response as valid JSON, triggering a warning log on the real error path. This is correct behavior — just not from the mock injection path. Classification: spec gap (the task instructions correctly described the expected failure mode but the existing code state made it impossible to achieve).

**Teammate reporting pattern:** Approximately 60% of agents went idle without sending a completion report, requiring status check messages from the team lead. File verification (grep/read) was used in parallel to confirm work rather than waiting for responses. No tasks required re-assignment as a result.

### UV verification (final)

All 7 spec UV checks passed at final state:
- UV-1: New behavioral test ✓ PASS
- UV-2: Mock injection test ✓ PASS
- UV-3: Zero bare namespace prefix in target package production code ✓
- UV-4: Zero bare identifier key in target package production code ✓
- UV-5: Zero bare domain strings in target package ✓
- UV-6: Zero bare match-source assignments in target package ✓
- UV-7: `go build ./...` clean ✓

### Documentation impact

Spec stated: none. Confirmed — no documentation files modified.

### Upstream traceability

- Stage 2 blocking findings before advancing: 6 (5 council + 1 test reviewer)
- Spec revisions required: 10
- Stage 3 gate iterations: task-reviewer-gate 2 runs; breakdown-gate 2 runs
- Stage 4 escalations: 0

## Stage 5: Code Review

**Detector:** code-review-detector (behavioral comparison)
**Challenger:** not invoked (findings were minor/informational only)

### Findings

| ID | Type | Severity | Description | Resolution |
|----|------|----------|-------------|------------|
| S-01 | structural | minor | Numeric constant declared inside a typed `iota` block — misleading to readers; not the same type as surrounding constants | Fixed: moved to separate `const` block |
| S-02 | fragile | minor | Log argument uses bare literal `10` instead of the constant it's adjacent to; diverges silently if constant changes | Fixed: replaced with constant reference |
| S-03 | test-integrity | minor | Mock input fields used bare strings while assertions used constants; inputs are dead (overwritten by function under test) but inconsistency was confusing | Fixed: replaced with constants |
| S-04 | test-integrity | info | Bare string key in test while production uses typed constant; out of scope for this phase | Carry-forward: deferred to future phase |
| S-05 | behavioral | info | Metrics timing is correct; `> 0` assertion in new test is technically fragile on zero-latency mock but adequate for CI | No action — informational only |

**Findings resolved this stage:** 3 (S-01, S-02, S-03)
**Carry-forward findings:** 1 (S-04 — out-of-scope test bare literal)

### Verification after fixes

All 7 UV checks still pass post-review fixes. `go build ./...` clean.

## Stage 5: Final Test Suite

**Run:** post-code-review, after S-01/S-02/S-03 fixes applied.

### Results

| Package Group | Result | Notes |
|---------------|--------|-------|
| 5 packages | FAIL | Pre-existing baseline failures (unchanged) |
| 20 packages | PASS | All passing |

**Baseline comparison:** All failures match the pre-phase baseline (1856 passing, 20 pre-existing failures). Zero new failures introduced by this phase or post-review fixes.

### Build fixes applied during test run

Three files had pre-existing compile failures under tagged builds (`-tags integration`, `-tags e2e`) that prevented test execution. Fixed as part of closing out this phase:

| Issue | Classification | Fix |
|-------|----------------|-----|
| Shared constant renamed in one file but not the other (same package, different build tags) | **This phase's regression** — task-05 incomplete scope | Rename in both files |
| Constructor signature changed in prior phase; e2e tests never updated (6 call sites) | Pre-existing | Update call sites with new parameter |
| Struct fields changed from value to pointer type; test passed bare literals | Pre-existing | Add pointer helper, wrap values |
| Non-constant format string in `logf` call | Pre-existing | Wrap in `"%s"` format |

### Integration tests (`-tags integration`)

**Result: PASS** — 7/7 tests passing (90.5s).

### E2E tests (`-tags e2e`)

**Result: FAIL** — 0/6 tests passing. All failures are environment/test-setup issues, not code regressions:

| Failure Pattern | Count | Classification |
|----------------|-------|----------------|
| WebSocket connection timeout (requires running server) | 1 | Environment — server-based test |
| `"no candidate discovery strategy available"` — engine created without retrieval pipeline wired | 5 | Test setup — missing DI wiring |

These tests were compile-broken before this phase (missing constructor arg, undefined constant), so this runtime failure was never reachable. Carry-forward for a dedicated repair phase.

### Web API tests

**Result: FAIL** — Database file lock timeout at 660s. Pre-existing — same failure mode as baseline.

### Experiment harness

**Result: no test files** — build-only package. Build now clean after format string fix.

## Process Findings

### PF-01: E2E tests silently skipped across multiple remediation phases

The Firebreak workflow includes instructions to run e2e tests at the end of implementation final waves. This instruction has been skipped across at least 4 phases of two remediation cycles. The likely mechanism: the agent runs `go test ./...` (which reports `ok` with zero tests due to build tags), considers the suite "passing," and moves on. Once the tests are classified as "pre-existing failures" in one phase, subsequent phases inherit that classification without re-validating.

**Root causes:**
1. `-tags integration` and `-tags e2e` are not included in the standard `go test ./...` invocation, so tagged tests are invisible to normal verification.
2. The Firebreak workflow does not explicitly enumerate which build-tag variants must be run at phase close.
3. The pre-existing failure baseline was established without running tagged test variants, so these compile-time breaks were never recorded.

**Impact:** Three distinct breakages accumulated undetected:
- Pre-remediation commit: retrieval strategy requirement added; e2e tests never wired it. Runtime failure.
- Prior phase: constructor signature changed; e2e tests never updated. Compile failure.
- This phase: shared constant renamed in one file but not the other. Compile failure layered on top.

**Recommendation:** The Firebreak workflow needs:
1. An explicit "tagged test matrix" in the baseline snapshot: run with each relevant build tag, plus the standard `go test ./...`. Pre-existing failures in each variant must be recorded separately.
2. The final-wave verification step must enumerate all build-tag invocations, not just `go test ./...`.
3. A build-only gate (compile with all tags) should run between waves — compile failures are cheap to detect and prevent accumulation.

### PF-02: E2E test DI wiring — deferred fix with splash damage analysis

Root-cause analysis found the runtime test failure requires more than a simple fix. The e2e tests must use the production-intended retrieval strategy (hybrid vector+keyword search with fusion), not a simplified substitute.

**Why the production strategy is required, not optional:**

The project's intended design mandates hybrid search. The config default uses a legacy strategy only as a backwards-compat shim during migration. The e2e tests are the *only* test layer that validates the full retrieval stack with real LLM calls: semantic embeddings, keyword indexing, fusion ranking, incremental index updates, and psychological re-ranking. Using any other strategy makes these tests pass while validating nothing about the actual retrieval architecture.

**What the production strategy path requires:**

The factory method constructs an 11-step dependency chain including: index manager, embedding client with retry logic, persistent vector storage with connection pooling, async embedding queue with lifecycle management, keyword index, fusion searcher, and a re-ranking decorator. The factory depends on application-level state (DB connection manager, config, queue lifecycle registration).

**Splash damage of a naive fix:**

- **Duplicating the factory:** 80+ lines of production-coupled code that must track any change to the factory. Divergence risk on next refactor.
- **Import explosion:** 5 new package imports crossing boundaries tests shouldn't know about.
- **Lifecycle management:** Embedding queue and DB connections require start/stop/cleanup. Tests that skip cleanup leak goroutines and file handles.
- **Type-assertion DI pattern:** The setter method is only on the concrete type, not the interface. The code review flagged this as fragile. Adding more callers normalizes the problem.

**Decision:** Deferred to a dedicated repair phase (Phase 4.5). Scope:
1. Extract factory from application struct into standalone function — single source of truth for both production and tests.
2. Promote setter to the engine interface, eliminating the type-assertion DI pattern.
3. Wire all e2e tests to the production strategy with real embeddings.
4. Add proper lifecycle management (queue start/stop, DB cleanup) in test helpers.
5. Diagnose and fix the server-based smoke test separately.
6. Establish a tagged-build baseline snapshot for future phases.
