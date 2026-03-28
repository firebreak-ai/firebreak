# Corrective Phase: Config Wiring, Pipeline Correctness & Error Handling — Retrospective

This retrospective covers a corrective phase in a Go project using the Firebreak SDL workflow. The phase wired dead config fields to their consumers, fixed pipeline correctness bugs, replaced hardcoded values with config-driven lookups, and fixed error-swallowing patterns across multiple packages. Project-specific identifiers have been replaced with generic descriptions.

## Implementation results

### Factual data

| Metric | Value |
|--------|-------|
| Total tasks | 31 (15 test + 16 implementation) |
| Waves | 8 |
| Re-plans | 0 formal (1 team-lead intervention) |
| Tasks passed on first attempt | 30/31 |
| Files changed | 41 |
| Lines changed | +2278 / -309 net |

### Per-task results

| Task | Type | Model | Status | Notes |
|------|------|-------|--------|-------|
| T-01 | test | Haiku | pass | Config loader defaults + epsilon tests |
| T-02 | test | Haiku | pass | Capturing logger infrastructure |
| T-03 | test | Sonnet | pass | Service config constructor tests |
| T-04 | test | Haiku | pass | Validator strict/permissive + response-cleanup tests |
| T-05 | test | Haiku | pass | Priority ordering + field propagation tests |
| T-06 | test | Sonnet | pass | Pipeline context cancellation test (rewrote existing) |
| T-07 | test | Sonnet | pass | Config wiring tests (orchestrator + engine) |
| T-08 | test | Sonnet | pass | Hardcoded model replacement tests (3 files, justified) |
| T-09 | test | Haiku | pass | Domain service logger wiring tests |
| T-10 | test | Sonnet | pass | Entity processor error logging tests |
| T-11 | test | Sonnet | pass | Data importer error logging tests |
| T-12 | test | Sonnet | pass | Model fallback + stop-word + continue-on-error tests |
| T-13 | test | Sonnet | pass | Goroutine ordering + mutation persistence tests |
| T-14 | test | Sonnet | pass | Async worker context test |
| T-15 | test | Haiku | pass | No-new-failures gate verification |
| T-16 | impl | Haiku | pass | Remove redundant loader defaults, epsilon validation |
| T-17 | impl | Sonnet | pass | Service config constructor, stdout->logger, remove legacy constructor, migrate 13 test callers (~40min) |
| T-18 | impl | Haiku | pass | Strict mode + response-cleanup in validator |
| T-19 | impl | Haiku | pass | Priority ordering fix |
| T-20 | impl | Haiku | pass | Field propagation in chunk splitter |
| T-21 | impl | Sonnet | pass | Pipeline context cancellation check |
| T-22 | impl | Sonnet | pass | Wire timeout, retry, model config in orchestrator/engine |
| T-23 | impl | Sonnet | pass | Replace hardcoded models, add context window config (4 files, justified) |
| T-24 | impl | Haiku | pass | Data importer logger wiring + all caller updates |
| T-25 | impl | Sonnet | pass | Entity processor error logging + propagation |
| T-26 | impl | Sonnet | pass | Data importer error logging + verification error |
| T-27 | impl | Haiku | pass | Relationship extractor model fallback |
| T-28 | impl | Haiku | pass | Continue-on-error + stop-word filter |
| T-29 | impl | Haiku | INTERVENTION | Team lead handled directly — agent unresponsive |
| T-30 | impl | Haiku | pass | Entity attribute mutation persistence via store update |
| T-31 | impl | Sonnet | pass | Async worker cancellable context |

### Model routing accuracy

- 13 Haiku tasks: 12 succeeded, 1 required team lead intervention (T-29)
- 18 Sonnet tasks: all succeeded
- T-29 failure was agent responsiveness, not model capability — the change was a 1-block code move

### Agent issues

1. **Agent stuck on T-29**: Agent became unresponsive after being assigned a goroutine ordering task. Did not respond to status check message. Team lead implemented the change directly (move metadata save before goroutine launch). Agent eventually responded ~20 minutes later during shutdown. Root cause unknown — possibly stuck in TaskCompleted hook test suite run or context exhaustion.

2. **T-17 duration**: Constructor refactor + 13 test caller migration took ~40 minutes — significantly longer than other tasks. This task was at the sizing limit (2 files, ~50 lines changed across many call sites). Consider splitting large migration tasks.

3. **Agent auto-commits**: The TaskCompleted hook caused agents to commit changes as they completed tasks, resulting in intermediate commits rather than the team-lead-controlled per-wave commits used in the prior phase. The final state is correct but the commit history is less clean.

### Cascade fixes (team lead)

- An async shutdown test needed updating — the cancellable context implementation (T-31) causes shutdown to succeed (cancels in-flight requests) instead of timing out. Updated test assertion.
- T-15 (gate task) updated stop-word test expectations to match T-28's implementation.

### Upstream traceability

- Spec review: 1 council session (Architect, Builder, Guardian), 9 blocking findings resolved + 4 test reviewer defects
- Spec revisions: one config field already existed (closed an open question), one new config field noted, one AC dropped (deferred to subsequent phase), two ACs clarified
- Breakdown: 2 agent invocations (test + impl compilers), multiple gate iterations for wave ordering and file scope conflicts
- Task file naming mishap required re-generation (agents used `T-NN` prefix instead of `task-NN`, rename attempt destroyed files)

### Workflow context

- Firebreak quick-win adjustments (5 changes) applied between the prior phase and this phase's breakdown
- Firebreak 0.3.0 full release applied between breakdown and implementation
- Skill names changed (e.g., `implement` to `fbk-implement`, `spec-review` to `fbk-spec-review`)
- No observable impact on wave execution from workflow changes

### Code review results

Post-implementation review (Detector/Challenger, 1 round):

| Metric | Value |
|--------|-------|
| Sightings | 5 |
| Verified findings | 3 |
| Rejections | 2 |
| Nits | 0 |
| Rounds | 1 |
| False positive rate | 40% (2/5) |

**F-01 (semantic-drift, AC-03):** Config constructor accepted a validation-mode flag but ignored it — always constructed the permissive validator. Fixed: wired flag to validator constructor.

**F-02 (semantic-drift, AC-02/AC-03 adjacent):** The orchestrator's pipeline service used a legacy constructor that dropped two config fields (entity cap and validation mode). Fixed: upgraded to the full-config constructor.

**F-03 (test-integrity, AC-26):** Two tests for mutation persistence had stale `t.Skip()` despite production code being implemented. Fixed: removed skips, added structural assertions.

**Rejected:** S-03 (pre-existing partial epsilon scope — AC only covers sub-weight validation, not primary weights), S-05 (stdout in test code — AC scoped to production file).

### Process failures

1. **Code review results not auto-appended to retrospective.** The orchestrator should have added code review findings to the retrospective automatically after the detection-verification loop completed, without requiring user prompting.

2. **Self-improvement skill transition not offered.** After code review completion, the orchestrator should have asked: "Would you like to run `/fbk-improve` to analyze this retrospective for workflow improvements?" This transition was missed entirely.

3. **Root cause:** The code review skill's post-impl path says "Produce findings only" but doesn't specify retrospective integration or next-stage transition. The orchestrator failed to follow the broader workflow pattern established in prior phases (each stage transitions to the next with a prompt). These are process gaps in the skill definition and in the orchestrator's adherence to the workflow lifecycle.

### Improvement proposals from `/fbk-improve`

12 proposals generated by 4 improvement analysts. Grouped by target asset:

**Post-Implementation Review (`post-impl-review.md`)**
1. Add `## Post-Output Steps` — auto-append code review results to retrospective + offer `/fbk-improve` transition
2. Add `## Inputs Required` — confirm retrospective path before non-interactive loop starts

**Code Review Guide (`code-review-guide.md`)**
3. Add pre-existing sighting treatment guidance — rejection requires counter-evidence, not just "out of scope"
4. Add post-review process instruction — auto-append + `/fbk-improve` transition (redundant with #1, in guide)
5. Add origin breakdown requirement to Finding quality retrospective field

**Implementation Guide (`implementation-guide.md`)**
6. Add 10-minute unresponsive agent timeout to Re-Plan Protocol
7. Add migration task size cap (80 lines, 4-5 files max per call-site task)
8. Add commit prohibition for agents — all commits controlled by team lead at wave checkpoints
9. Add task file rename warning — never rename task files, content loss is non-obvious

**Task Compilation Guide (`task-compilation.md`)**
10. Disambiguate `task-NN` filename format from `T-NN` task ID format with explicit prohibition
11. Add call-site migration split rule — split definition change from caller migration when 10+ callers
12. Add cascade fix responsibility — create explicit update tasks for tests whose assertions change, don't leave to team lead
