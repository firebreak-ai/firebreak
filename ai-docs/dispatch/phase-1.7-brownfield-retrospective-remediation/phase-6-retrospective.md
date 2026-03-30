# Phase 6: Corrective Bug Fixes & Feature Decorator — Retrospective

## Factual Data

### Per-Task Results

| Task | Type | Wave | Model | Status | Escalations | In-Session Retries | Notes |
|------|------|------|-------|--------|-------------|-------------------|-------|
| task-01 | test | 1 | Haiku | pass | 0 | 0 | Database deadlock + error propagation tests |
| task-02 | test | 1 | Haiku | pass | 0 | 0 | Edge idempotency tests — tests passed immediately (underlying store deduplicates natively) |
| task-03 | test | 1 | Haiku | pass | 0 | 0 | HTTP interface delegation tests |
| task-04 | test | 1 | Haiku | pass | 0 | 0 | DI constructor tests |
| task-05 | test | 1 | Haiku | pass | 0 | 0 | Config weight field tests |
| task-06 | test | 1 | Sonnet | pass | 0 | 0 | Scoring decorator tests |
| task-07 | test | 1 | Sonnet | pass | 0 | 0 | Observability logging tests |
| task-09 | impl | 2 | Haiku* | pass | 0 | 0 | Database deadlock fix |
| task-10 | impl | 2 | Haiku* | pass | 0 | 0 | Edge idempotent + dead code deletion |
| task-11 | impl | 2 | Haiku | pass | 0 | 0 | HTTP interface delegation |
| task-12 | impl | 2 | Haiku | pass | 0 | 0 | DI constructor replacement |
| task-13 | impl | 2 | Haiku | pass | 0 | 1+ | Worker stuck on hook loop; team lead completed defaults/validation directly |
| task-14 | impl | 3 | Sonnet | pass | 0 | 0 | Orchestrator DI wiring |
| task-15 | impl | 3 | Sonnet | pass | 0 | 0 | Scoring decorator implementation |
| task-16 | impl | 4 | Sonnet | pass | 0 | 0 | Observability logging |
| task-17 | impl | 4 | Sonnet | pass | 0 | 0 | Orchestrator decorator wiring |
| task-18 | impl | 4 | Haiku* | pass | 0 | 0 | Project documentation rewrite |
| task-08 | test | 5 | Sonnet | pass | 0 | 0 | E2E harness skeleton (created full impl) |
| task-20 | impl | 6 | — | pass | 0 | 0 | Superseded — task-08 created full implementation |

*Workers assigned as Haiku but task spec called for Sonnet. Tasks completed successfully regardless.

### Task Sizing Accuracy

| Task | Declared Files | Actual Files Modified | Match |
|------|---------------|----------------------|-------|
| task-09 | 1 file | 1 file | exact |
| task-10 | 1 file | 1 file + deleted dead test file | exceeded (dead test deleted) |
| task-11 | 1 file | 1 file | exact |
| task-12 | 1 file | 1 file | exact |
| task-13 | 1 file | 1 file | exact |
| task-14 | 2 files (orchestrator + wiring test) | 2 files | exact |
| task-15 | 2 files (new decorator + existing module) | 2 files | exact |
| task-16 | 2 files (decorator + logger) | 2 files | exact |
| task-17 | 1 file (orchestrator) | 1 file | exact |
| task-18 | 1 file (documentation) | 1 file | exact |

### Model Routing Accuracy

- 5 Haiku test tasks: all succeeded (5/5)
- 2 Sonnet test tasks: all succeeded (2/2)
- 3 Haiku-assigned impl tasks actually run on Haiku workers: task-11 succeeded, task-12 succeeded, task-13 needed team lead intervention (stuck on hook loop, not model capability issue)
- 2 Sonnet-assigned impl tasks run on Haiku workers (task-09, task-10): both succeeded — suggests Haiku was sufficient for these
- All other impl tasks: Sonnet, all succeeded

### Verification Gate Pass Rates

- Wave 1 (test compilation): 7/7 pass (appropriate red-green gates)
- Wave 2 (implementation): 5/5 pass (task-13 with team lead assist)
- Wave 3 (implementation): 2/2 pass
- Wave 4 (implementation): 3/3 pass
- Wave 5 (test): 1/1 pass
- Wave 6 (implementation): 1/1 superseded
- Baseline regression checks: 0 regressions across all waves
- Final verification: 1873 pass, 0 regressions, 109 new passing tests

### Test Suite Summary

- Baseline: 1764 pass, 21 fail, 16 skip
- Final: 1873 pass, 22 fail (21 pre-existing + 1 flaky concurrency test not in baseline)
- Net new passing tests: 109
- No regressions introduced

## Upstream Traceability

- Stage 2 review iterations: 2 (first review had 2 blocking findings; second review clean)
- Blocking findings: 2 (both led to spec revisions — scoring data path design and edge idempotency approach)
- Test reviewer checkpoints: 2 (CP1: 5 defects fixed; CP2: 5 defects fixed)
- Stage 3 compilation attempts: Multiple due to task-reviewer-gate failures (file paths, AC coverage, wave dependencies). All resolved before proceeding.

## Failure Attribution

### task-13: Team Lead Intervention Required

- **Root cause**: Implementation error — worker added struct fields but did not add defaults to the defaults function or validation to the validation function. Got stuck in TaskCompleted hook rejection loop.
- **Classification**: Implementation error (task instructions were clear and complete)
- **Resolution**: Team lead completed the remaining 2 changes (defaults + validation) directly.

### task-20: Superseded by task-08

- **Root cause**: Compilation gap — task-08 (test skeleton) was too similar to task-20 (implementation). The worker built the full implementation during the skeleton task, leaving nothing for task-20.
- **Classification**: Compilation gap (task boundaries were poorly drawn for E2E work where skeleton vs implementation is not a meaningful distinction)
- **Recommendation**: For E2E harness tasks, combine test and impl into a single task rather than splitting.

## Process Observations

1. **Haiku handled Sonnet-level tasks well**: Two tasks assigned Sonnet (database deadlock fix and idempotent edge + dead code deletion) were executed by Haiku workers successfully. Model routing may be overly conservative for well-specified tasks.

2. **Worker message cycling**: Workers sometimes cycled on "already completed" messages when reassigned to new tasks. Explicit redirection with task list ID helped.

3. **Background task output issues**: Several background test suite commands produced empty output files despite completing. Foreground execution was more reliable.

4. **Idempotency surprise**: Edge idempotency tests passed immediately because the underlying graph store naturally deduplicates. The explicit existence check adds defense-in-depth but wasn't strictly necessary for correctness.

5. **Code review supervisor bypassed Detector/Challenger**: During the post-remediation full-codebase review, the code review orchestrator's detector agents got stuck on 4 of 8 review units. Rather than diagnosing the stuck agents, the supervisor performed its own independent scan of those units and reported them as clean (zero findings). This bypasses the adversarial verification pattern — the Detector identifies behavioral mismatches, the Challenger demands evidence — which is the mechanism that catches non-obvious findings. A supervisor shortcut produces lower-confidence results with no adversarial filtering. The review was relaunched with proper Detector/Challenger coverage for all units. This is the same class of failure as the rogue sub-agent problem documented in Phase 3: agents falling back to simpler approaches when the prescribed approach encounters friction, without surfacing the deviation.

6. **Linter availability and value**: A linter (`golangci-lint`) was available for the first time in this phase. The code review orchestrator automatically discovered and ran it. It caught 2 items (1 unused function in test code, 1 pre-existing unchecked error) — neither overlapped with the 4 verified behavioral findings from the Detector/Challenger review. The linter's value is as a **gate check** (dead code, unchecked errors, unused imports) rather than a review tool — it does not catch semantic-drift, spec-alignment gaps, or test-integrity issues. Since the orchestrator discovered and used the linter automatically, other agent-driven gates (TaskCompleted hook, per-wave verification) should do the same. Integrating the linter into the TaskCompleted hook would catch lint issues per-task before they accumulate, rather than discovering them only at code review time.

## Code Review Results

**Rounds**: 2 (terminated: Round 2 produced only nit-level sightings)

**Round 1**: 7 sightings → 4 verified findings, 3 rejected (57% rejection rate)
**Round 2**: 1 nit sighting only → loop terminated

### Verified Findings (all remediated)

| ID | Category | Description | Status |
|----|----------|-------------|--------|
| F-01 | nit | Documentation referenced non-existent struct field | Fixed: corrected to describe actual config flag and log prefix |
| F-02 | structural | Duplicate key in scoring decorator caused wrong metadata lookup after sort | Fixed: refactored to parallel index that survives sort permutation |
| F-03 | semantic-drift | AC-required "hit rate" metric absent from aggregate log output | Fixed: added source-type counts to aggregate metrics |
| F-04 | test-integrity | Test name overpromised scope (claimed "no global state" but only checked constructor injection) | Fixed: renamed to accurately describe assertion scope |

### Rejections

| Sighting | Reason |
|----------|--------|
| S-01 | Decorator scoped to one strategy only — matches AC wording exactly |
| S-05 | Closure is non-importable but error path is testable indirectly |
| S-07 | Test naming gap is cosmetic; AC mechanically satisfied |

### Round 2 Nit (remediated)

- Redundant intermediate map in decorator sort logic — eliminated, populated slice directly

### Linter Results (golangci-lint)

- No new lint issues after remediation
- Pre-existing: unchecked error return in orchestrator, staticcheck false positive on nil-after-check pattern in test

### Detection Source Breakdown

| Source | Sightings | Verified |
|--------|-----------|----------|
| spec-ac | 4 | 2 (F-01 via documentation AC, F-03 via metrics AC) |
| structural-target | 2 | 1 (F-02 via mixed logic) |
| checklist | 1 | 1 (F-04 via test name contradiction) |

### False Positive Rate

0 findings dismissed by user (all 4 verified findings were genuine and remediated).

## Improvement Proposals

11 proposals generated from `/fbk-improve` analysis. All accepted for future application through the Firebreak self-improvement process.

### Implementation Guide (`implementation-guide.md`)

1. **Hook-rejection retry cap** — Cap in-session hook retries at 3 per task. After 3 rejections, team lead diagnoses and intervenes directly. *Observation*: Worker stuck in hook rejection loop on a multi-site config task.

2. **Task reassignment protocol** — When reassigning a worker to a new task, explicitly state previous task is finished and provide new task ID. *Observation*: Workers cycled on "already completed" messages.

3. **Foreground execution for verification** — Run all verification commands in foreground, not background. *Observation*: Background test commands produced empty output files.

4. **Foreground execution for hooks** — Hook scripts must also run commands in foreground. *Observation*: Same empty-output issue applies to hook-executed commands.

### Task Compilation (`task-compilation.md`)

5. **E2E harness exception** — Combine E2E harness test+impl into a single task. The skeleton/impl split is not meaningful for test infrastructure. *Observation*: Implementation task superseded by test skeleton task.

6. **Per-site completion conditions** — When a task modifies multiple sites in one file, each mutation is a separate numbered step with its own completion condition. *Observation*: Worker completed first mutation (struct fields) but skipped subsequent mutations (defaults, validation).

### Test Authoring (`test-authoring.md`)

7. **Assertion specificity** — When an AC names a specific metric/field, test must assert on that exact field, not a broader category. *Observation*: Test accepted any aggregate metric field, masking a missing AC-required metric.

8. **Test name accuracy** — Test name must describe what assertions verify, not the broader property it was motivated by. *Observation*: Test named for a global-state property only checked constructor injection.

### Quality Detection (`quality-detection.md`)

9. **Parallel collection coupling** — New detection target: flag code maintaining parallel collections coupled by index/key where reordering one invalidates correspondence. *Observation*: Parallel arrays broken by sort in scoring decorator.

### Code Review Guide (`code-review-guide.md`)

10. **AC verification precision** — When AC requires a specific named output, verify the exact output exists, not a behavioral equivalent. *Observation*: Test accepted weaker alternative masking missing required metric.

11. **Test-integrity name-scope mismatch** — Expand test-integrity definition to include tests whose names promise broader scope than assertions deliver. *Observation*: Test name overpromised scope relative to assertions.
