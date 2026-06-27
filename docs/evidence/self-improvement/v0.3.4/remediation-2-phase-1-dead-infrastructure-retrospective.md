# Phase 1: Dead Infrastructure Cleanup — Retrospective

## Factual Data

### Per-Task Results

| Task | Type | Wave | Model | Status | Escalations | In-Session Retries |
|------|------|------|-------|--------|-------------|-------------------|
| task-01 | test | 0 | Haiku | complete | 0 | 0 |
| task-02 | test | 0 | Haiku | complete | 0 | 0 |
| task-03 | test | 0 | Sonnet | complete | 0 | 0 |
| task-04 | test | 0 | Haiku | complete | 0 | 0 |
| task-21 | test | 0 | Haiku | complete | 0 | 0 |
| task-05 | impl | 1 | Haiku | complete | 0 | 0 |
| task-06 | impl | 1 | Haiku | complete | 0 | 0 |
| task-07 | impl | 1 | Haiku | complete | 0 | 0 |
| task-08 | impl | 1 | Haiku | complete | 0 | 0 |
| task-09 | impl | 1 | Haiku | complete | 0 | 0 |
| task-10 | impl | 1 | Haiku | complete | 0 | 0 |
| task-11 | impl | 1 | Sonnet | complete | 0 | 0 |
| task-12 | impl | 1 | Haiku | complete | 0 | 0 |
| task-13 | impl | 2 | Haiku | complete | 0 | 0 |
| task-14 | impl | 1 | Haiku | complete | 0 | 0 |
| task-15 | impl | 2 | Sonnet | complete | 0 | 0 |
| task-16 | impl | 1 | Haiku | complete | 0 | 0 |
| task-17 | impl | 1 | Haiku | complete | 0 | 0 |
| task-18 | impl | 1 | Haiku | complete | 0 | 0 |
| task-19 | impl | 1 | Haiku | complete | 0 | 0 |
| task-20 | impl | 2 | Haiku | complete | 0 | 0 |

### Summary Statistics

- **Total tasks**: 21 (5 test, 16 implementation)
- **Waves**: 3 (wave 0: test cleanup, wave 1: main deletions, wave 2: cross-module cleanup)
- **Pass rate**: 21/21 (100%)
- **Escalations**: 0
- **Total lines changed**: 31 files, 26 insertions, 2,906 deletions
- **Regressions introduced**: 0
- **Model routing**: 18 Haiku, 3 Sonnet — all succeeded at assigned tier

### Task Sizing Accuracy

| Task | Declared Files | Actual Files | Over/Under |
|------|---------------|-------------|------------|
| task-03 | 1 | 1 | match |
| task-05 | 2 | 2 | match |
| task-08 | 2 | 2 | match |
| task-11 | 2 | 2 | match |
| task-15 | 1 | 1 | match |

All tasks stayed within declared file scope. No scope violations detected.

### Model Routing Accuracy

All 18 Haiku tasks succeeded without escalation. All 3 Sonnet tasks succeeded. No evidence of under-routing. For a deletion-only phase, Haiku was sufficient for all single/two-file bounded deletions. Sonnet was appropriate for:
- task-03: 14 function deletions with import cleanup (780+ lines)
- task-11: multi-site WorkerPool removal with safety check
- task-15: App struct modification with side-effect verification

### Verification Gate Pass Rates

| Gate | Attempts | Passes |
|------|----------|--------|
| Spec gate | 1 | 1 |
| Review gate | 2 | 2 (re-run after AC consolidation) |
| Task reviewer gate | 2 | 1 fail, 1 pass (fixed missing test_tasks + wave conflict) |
| Breakdown gate | 2 | 1 fail, 1 pass (fixed wave ordering + missing AC-03 test task) |
| Per-wave build verification | 3 | 3 |
| Final verification | 1 | 1 |

## Upstream Traceability

### Stage 1 (Spec)
- Original spec reshaped into Firebreak template format for gate compatibility
- Spec gate passed on first attempt after reshaping

### Stage 2 (Review)
- 1 council invocation (Quick Council: Architect, Builder, Guardian)
- 1 blocking finding: AC-05 scope ambiguity on recency entity scoring — resolved with user input after research revealed the feature is alive in production via the entity-aware retriever
- 5 important findings: F-44 simplified to deletion, F-49 simplified to deletion, N-16 resolved as Option B, N-11 path corrected, 4 missing test files added
- 4 informational findings
- 1 test reviewer invocation (CP1): FAIL — 2 mechanical defects from AC renumbering, fixed
- ACs consolidated from 13 to 5 per Builder recommendation
- Spec revised once to incorporate all findings

### Stage 3 (Breakdown)
- 2 compilation attempts before gate passed
- First attempt: 11 impl tasks missing `test_tasks` frontmatter, 1 file scope conflict (context_test.go), missing AC-03 test task, wave ordering violations
- Fixes: added test_tasks to all impl tasks, moved task-13/15 to wave 2, created task-21 (AC-03 verification), moved test tasks to wave 0
- 1 test reviewer invocation (CP2): FAIL — task-03 had dangling test helper references (13 additional test functions not accounted for). Expanded task-03 from 2 deletions to 14+2 deletions.

## Failure Attribution

No task failures occurred during implementation. All 21 tasks passed on first attempt.

### Breakdown-Phase Issues (pre-implementation)

1. **task-03 scope underestimation** — Root cause: **Spec gap**. The spec's testing strategy only identified the test helper function and one integration test for deletion, but the helper was called by 13 other test functions. The test reviewer (CP2) caught this before implementation. The spec should have enumerated all callers, not just the helper definition.

2. **Wave ordering violations** — Root cause: **Compilation gap**. Test tasks and their dependent impl tasks were placed in the same wave, but the gate requires strict wave precedence for dependencies. The task compilation guide states this rule but the compiler didn't apply it initially.

3. **Missing AC-03 test task** — Root cause: **Compilation gap**. The breakdown gate requires every AC to have a test task. AC-03 genuinely needed no test changes, but a verification-only task was required to satisfy the gate invariant.

## Post-Implementation Code Review

### Summary
- **Rounds**: 3 (converged on round 3)
- **Total sightings**: 7 (4 round 1, 3 round 2)
- **Verified findings**: 5 (F-01 through F-05)
- **Rejections**: 1 (S-04, nit — pre-existing guard test)
- **Info-only**: 1 (S-03 round 2, explicit nil in struct literal)
- **False positive rate**: 0% (no user dismissals)
- **Detection sources**: 1 linter, 4 structural-target, 1 spec-ac

### Verified Findings

| ID | Severity | Type | Description | Resolution |
|----|----------|------|-------------|------------|
| F-01 | critical | test-integrity | App wiring test referenced deleted `App.DomainContext` | Test replaced with dependency wiring verification test |
| F-02 | minor | structural | Stale QueryBuilder comment in schema example file | Comment updated |
| F-03 | minor | structural | Misleading "includes recency entity scoring" comment | Comment corrected |
| F-04 | minor | structural | Stale WorkerPool comments in config module | Comments updated, then fields fully removed |
| F-05 | minor | structural | `WorkerPoolSize`/`JobQueueSize` no-op fields retained without rationale | Fields, defaults, example config entries, and e2e test references all removed |

### Failure Attribution

- **F-01** (critical): **Compilation gap**. The app wiring test file was not in any task's file scope. The spec claimed "No tests reference Loader interfaces" — true, but the test referenced `DomainContext` (a domain context manager, not a Loader), which was removed alongside them. The task compiler should have grepped for all `App` field references when planning the removal.
- **F-02–F-05**: **Spec gap / compilation gap**. Stale comments and no-op config fields are secondary cleanup that the spec's verification grep didn't cover (it checked core modules not examples or config packages).

## Final Verification

Full test suite run after all code review fixes:

- **Build**: `go build ./...` passes clean
- **go vet**: Only pre-existing experiment harness issue (unrelated)
- **Passing packages**: application entry point, embedding, graph/schema, inference, integration, profile, analysis, retrieval, scene, test utilities, web, websocket, domain, errors, logging, string utilities, tokenizer, validation
- **Failing packages (all pre-existing)**: conversation module (6 failures), extraction module (6 failures), graph module (1 failure), web API (3 failures), config (3 failures), experiment harness (build failure)
- **Regressions introduced**: 0 — all 19 failing tests match the pre-existing baseline
- **Symbol verification**: grep confirms zero remaining references to all deleted symbols

Notable: the application entry point now passes (was failing before code review fix F-01 resolved the wiring test compilation error).

## Process Gaps

### Skipped final e2e test after implementation

The implementation guide specifies running the full test suite as final verification after the last wave's checkpoint. The orchestrator did not run this step — it was only performed after the user prompted for it. The e2e run after Wave 1 tested only affected packages, not the full `go test ./...`. The application entry point test binary was broken at that point (F-01) but was not caught until the code review's `go vet` flagged it.

**Root cause**: The orchestrator treated per-wave `go build ./...` as sufficient verification and skipped the full `go test ./...` run that the implementation guide requires between waves and at final verification. For a deletion-only phase where Go's compiler catches most issues, the build check covered most risk — but it missed the test-only compilation failure because `go build` doesn't compile test files.

**Corrective action**: Final verification must include `go test ./...` (not just `go build ./...`), and the orchestrator should not skip this step even when the user asks to proceed without inter-wave commits.

## Observations

- Pure deletion phases are exceptionally well-suited to parallel agent execution. All 13 Wave 1 agents completed within ~60 seconds with zero conflicts.
- Go's compiler is the primary safety net for deletion work, but `go build` does not compile test files. `go test ./...` is required to catch test-only compilation failures like F-01.
- The recency entity scoring scope investigation was the most valuable review finding. Without it, the implementation might have deleted production-active scoring logic.
- The test reviewer CP2 catch (test helper callers) prevented a guaranteed build failure. This validates the checkpoint pattern for catching spec-level gaps before they become implementation failures.
- A retrieval test was confirmed as a pre-existing flaky test (fails on original code). It appeared as a regression because it happened to pass during baseline capture. This is a known limitation of snapshot-based regression detection.
- Backward-compatibility retention of config fields was questioned during code review. For a personal project with no strict YAML mode, keeping no-op fields is unnecessary overhead. The fields were removed entirely after user confirmation.
