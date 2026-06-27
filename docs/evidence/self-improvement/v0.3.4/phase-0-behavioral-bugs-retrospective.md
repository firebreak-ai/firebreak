# Phase 0: Behavioral Bugs — Retrospective

## Factual Data

### Task Results

| Task | Type | Wave | Model | Status | Escalations | Notes |
|------|------|------|-------|--------|-------------|-------|
| task-01 | test | 1 | Sonnet | complete | 0 | ContentIndex incremental indexing test |
| task-02 | test | 1 | Sonnet | complete | 0 | Generation parameter from config test |
| task-04 | test | 1 | Haiku | complete | 0 | Keyword relevance interaction test |
| task-05 | test | 1 | Haiku | complete | 0 | Message schema role constants test |
| task-07 | test | 1 | Haiku | complete | 0 | Internal annotation budget filtering test |
| task-09 | test | 1 | Haiku | complete | 0 | SessionMetadata field names test |
| task-10 | test | 1 | Haiku | complete | 0 | Scoring reranker entity bypass test |
| task-12 | test | 1 | Sonnet | complete | 0 | Debug endpoint property keys test |
| task-13 | test | 1 | Haiku | complete | 0 | Internal annotation label test |
| task-14 | test | 1 | Haiku | complete | 0 | ProcessingMode concurrent race test |
| task-34 | test | 1 | Haiku | complete | 0 | Delete zero-value parameter settings test |
| task-06 | test | 2 | Haiku | complete | 0 | Update existing role string literals |
| task-11 | test | 2 | Haiku | complete | 0 | Update scoring reranker tests with NodeKind |
| task-15 | test | 2 | Haiku | complete | 0 | Update theme significance test assertions |
| task-35 | test | 2 | Haiku | complete | 0 | Update heartbeat tests to use accessors |
| task-16 | impl | 3 | Sonnet | complete | 0 | IndexEntry map writes + RWMutex |
| task-17 | impl | 3 | Sonnet | complete | 0 | Remove generation parameter from Session structs |
| task-21 | impl | 3 | Haiku | complete | 0 | Fix record content property key |
| task-22 | impl | 3 | Haiku | complete | 0 | Fix keyword relevance precedence |
| task-23 | impl | 3 | Haiku | complete | 0 | Fix role string mismatch |
| task-24 | impl | 3 | Haiku | complete | 0 | Internal annotation budget filter |
| task-25 | impl | 3 | Haiku | complete | 0 | Recency decay guard |
| task-28 | impl | 3 | Haiku | complete | 0 | Scoring reranker node kind gate |
| task-29 | impl | 3 | Haiku | complete | 0 | Debug endpoint property fix |
| task-30 | impl | 3 | Haiku | complete | 0 | Internal annotation label in content analysis |
| task-18 | impl | 4 | Haiku | **superseded** | 0 | Engine parameter — already done by task-17 |
| task-19 | impl | 6 | Haiku | **superseded** | 0 | Handler parameter — already done by task-17 |
| task-20 | impl | 6 | Haiku | **superseded** | 0 | API+frontend parameter — already done by task-17 |
| task-26 | impl | 4 | Haiku | complete | 0 | SessionMetadata field rename (struct + session module) |
| task-27 | impl | 4* | Haiku | complete | 0 | SessionMetadata API site rename (pulled forward from Wave 7) |
| task-33 | impl | 4 | Haiku | complete | 0 | Theme significance cap |
| task-31 | impl | 5 | Sonnet | complete | 0 | ProcessingMode atomic + accessors |
| task-32 | impl | 6 | Haiku | **superseded** | 0 | Engine ProcessingMode read — already done by task-31 |

**Totals:** 33 tasks. 28 complete, 4 superseded (task-18, -19, -20, -32), 1 uncreated test gap (AC-03, AC-06 — accepted by design). 0 escalations. 0 parked.

### Superseded Task Analysis

Four implementation tasks were superseded because earlier agents fixed more than their declared scope:

**task-17 (Parameter struct removal) superseded tasks 18, 19, 20:**
The task-17 agent (Sonnet) was assigned to remove the generation parameter field from session-related structs in the interface and session modules. The agent also fixed all downstream compile errors in the engine, handler, session manager, frontend config, and test files — work that was split across tasks 18 (engine), 19 (handler), and 20 (API+frontend) in Waves 4-6. The agent treated the struct removal as requiring all references to be fixed in one pass to achieve a clean compile.

**task-31 (ProcessingMode atomic) superseded task-32:**
The task-31 agent (Sonnet) was assigned to convert `ProcessingMode` to `atomic.Int32` in the interfaces module and update the handler. When the field became unexported (`processingMode`), the engine module also failed to compile, so the agent fixed the engine read site — work assigned to task-32 in Wave 6.

**Root cause:** Both supersessions happened because Go's compiler forces all references to be fixed when a struct field is removed or made unexported. The task breakdown split these across waves to respect file-scope constraints, but the agents correctly fixed all compile errors in their scope to produce a clean build. This is the right behavior — agents should not leave the codebase in a non-compiling state.

**Observation for future breakdowns:** When a task removes or renames a struct field, downstream caller-migration tasks will be superseded if the primary agent needs to fix them for compilation. Consider either: (a) keeping caller migration in the same task (accepting the larger file scope), or (b) accepting that supersession will happen and planning for it. Option (a) is more honest about the actual unit of work.

### In-Session Retry Count

0 TaskCompleted hook rejections across all tasks. No in-session retries needed.

### Task Sizing Accuracy

| Task | Declared files | Actual files modified | Over-scope? |
|------|---------------|----------------------|-------------|
| task-14 | heartbeat_test.go | heartbeat_test.go, interfaces.go | Yes — added accessor scaffolding |
| task-17 | interfaces.go, session.go | interfaces.go, session.go, engine.go, handler.go, session_manager.go, config.js, 5 test files | Yes — fixed all parameter references |
| task-31 | interfaces.go, handler.go | interfaces.go, handler.go, engine.go | Yes — fixed engine compile error |
| All others | As declared | As declared | No |

### Model Routing Accuracy

- **Haiku tasks:** 24 assigned, 24 succeeded. 0 required escalation. 100% success rate.
- **Sonnet tasks:** 9 assigned, 9 succeeded. 0 required escalation. 100% success rate.
- The 3 tasks that exceeded their file scope (task-14, -17, -31) were all Sonnet. Sonnet's broader judgment led it to fix compile errors outside declared scope rather than leaving the build broken — correct behavior, but it caused task supersession.

### Verification Gate Pass Rates

- Wave 1 (11 test tasks): all passed on first attempt
- Wave 2 (4 test tasks): all passed on first attempt
- Wave 3 (10 impl tasks): all passed on first attempt; compile check clean
- Wave 4 (3 impl tasks): initial compile failure — session manager referenced old renamed fields. task-27 (originally Wave 7) was pulled forward to fix. Clean after.
- Wave 5 (1 impl task): passed on first attempt
- Final verification: 0 new test failures, 2 pre-existing failures incidentally fixed

### Test Results

**New tests passing:** All tests for AC-01, AC-04, AC-05, AC-07, AC-09, AC-10, AC-11, AC-12, AC-13
**AC-02 test:** Passes (engine reads parameter from config)
**AC-03, AC-06:** No test — debug-only code paths, verified by code review

**Pre-existing failures incidentally fixed (2):**
- Concurrent sessions test — likely fixed by parameter removal simplifying session initialization
- Session persistence test — same root cause

**Pre-existing timeout resolved (1):**
- Session retrieval API test — no longer times out at 600s

**Pre-existing failures unchanged (16):** All from the baseline, no regressions introduced.

## Upstream Traceability

- **Stage 2 review iterations:** 2 (initial review found 13 findings; re-review found 4 important, 0 blocking)
- **Blocking findings leading to spec revisions:** 7 from initial review (R-01 through R-13), all resolved
- **Key spec changes from review:**
  - N-04 dropped as false positive (domain context is correctly handled via RAG, not static prompt)
  - F-33 removal scope expanded to cover all compile sites
  - N-07 scope expanded to cover entity extraction function (second identical bug)
  - N-08 changed from RWMutex to atomic.Int32
  - N-07 updated to use schema constants instead of bare string literals
  - AC-12 test strategy strengthened to require concurrent test
- **Stage 3 compilation attempts:** 3 (AC-08 coverage, file scope conflicts, then accepted AC-03/AC-06 exceptions)

## Failure Attribution

No task failures occurred. No escalations needed.

### Accepted Gaps

**AC-03 (F-34) — no test task:**
- Classification: **spec gap** — the spec prescribed testing a record transformation function's content preview, but the function logs debug output via the logger with no return path. A behavioral test is impractical without logger interception. The fix is a 1-line string literal change in debug-only code.

**AC-06 (N-02) — no test task:**
- Classification: **spec gap** — the spec prescribed testing the inline recency calculation, but it only affects logging output. The actual scoring path already has the guard via the default scorer. A test on scored results passes before and after the fix. The fix is a 3-line guard addition.

### Observations

1. **Sonnet agents handle broader scope naturally.** When given a struct field removal task, Sonnet agents fix all downstream compile errors rather than leaving the build broken. This is correct engineering behavior but causes task supersession when downstream fixes were split into separate tasks. Future breakdowns should account for this.

2. **Wave structure was over-segmented for this change set.** The 7-wave plan was driven by file-scope conflict avoidance, but 3 of 7 waves were effectively emptied by supersession. A 4-wave plan (tests, independent impl, dependent impl, final cleanup) would have been sufficient.

3. **Task-14 added production code scaffolding.** The concurrent race test task added non-atomic `GetProcessingMode`/`SetProcessingMode` methods to the interfaces module so the test would compile. This is a valid approach (the methods exist but aren't atomic, so the race test catches the issue), but it modified production code in a test task — technically out of scope.

4. **Wave 4 compile failure was predictable.** The SessionMetadata rename (task-26) broke the session manager which was scheduled for Wave 7 (task-27). The breakdown should have placed task-27 immediately after task-26 or in the same wave with a different file scope. The wave structure created an artificial compile-broken intermediate state.

## Post-Implementation Code Review

**Rounds:** 3 (converged on Round 3 — no sightings above info)
**Total sightings:** 10 across all rounds
**Verified findings:** 7 (5 from Round 1, 2 from Round 2)
**Rejections:** 1 (concurrent race test exists but detector missed it)
**Nits:** 1 (zero-value NodeKind style issue)
**False positive rate:** 10% (1 rejection out of 10 sightings)

### Findings fixed during review (5)

| Finding | Type | Severity | Fix |
|---------|------|----------|-----|
| Dead parameter sentinel in instrumented response generator | structural | minor | Removed dead `if parameter < 0` guard |
| Scoring reranker test fixture: store NodeKindEntity vs candidate NodeKindRecord | test-integrity | major | Aligned store node kinds to NodeKindRecord |
| Recent context assembly skipped_count conflates filtered and budget-excluded | structural | minor | Added filteredCount, separated in log |
| Graceful degradation test: store NodeKindEntity vs candidate NodeKindRecord | test-integrity | major | Aligned store node kinds to NodeKindRecord |
| Entity score preservation test: zero-value NodeKind instead of explicit NodeKindEntity | test-integrity | minor | Set explicit NodeKind on both candidates |

### Findings accepted (not fixed)

| Finding | Type | Severity | Rationale |
|---------|------|----------|-----------|
| Parameter test covers ProcessMessage only, not streaming | test-integrity | minor | Streaming path reads config inline with no guard — no correctness risk |
| Rebuild lock is per-node not per-operation | structural | info | Pre-existing design, not a regression |
| No Rebuild test coverage | test-integrity | minor | Spec gap — Rebuild was not in AC-01's test requirements |

### Failure attribution

All 5 fixed findings were test-integrity issues — production code was correct across all 12 fixes. Root causes:

- **Test task agents produced inconsistent fixtures (3 findings).** The Wave 1/2 test agents created scoring reranker test fixtures where store nodes used `NodeKindEntity` but candidate structs used `NodeKindRecord`. The mock store doesn't validate node kind on lookup, so the tests passed but the scenarios were internally contradictory. This is a **compilation gap** — the test task instructions said "set `NodeKind: schema.NodeKindRecord` on candidates" but didn't specify that store node kinds should match. The agents followed instructions literally without noticing the inconsistency.

- **Orchestrator missed second instance of same pattern (1 finding).** Round 1 fixed one reranking test's store types but missed the graceful degradation test in the same file with the identical mismatch. This was caught in Round 2. The fix-review-fix loop worked as designed, but the Round 1 fix should have been applied to all instances in the file, not just the one cited in the finding.

- **Dead sentinel code left behind (1 finding).** Task-17 (parameter removal) cleaned up all session parameter references but left an unreachable guard in the instrumented response generator. This is an **implementation oversight** — the agent focused on the struct field and its direct references, not on downstream guards that became dead code.

### Detection source breakdown

| Source | Sightings | Verified |
|--------|-----------|----------|
| spec-ac | 7 | 6 |
| checklist | 1 | 1 |
| structural-target | 2 | 2 |
| linter | 0 | 0 |
