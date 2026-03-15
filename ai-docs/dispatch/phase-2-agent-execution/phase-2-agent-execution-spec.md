# Phase 2: Agent Execution

> **Status: Pre-Review** — This spec has not yet been through council review.

## Problem

Phase 1 builds the complete pipeline infrastructure — state tracking, gates, review, breakdown, task review, verification — but no agent can execute implementation work. Test tasks and implementation tasks exist as reviewed artifacts with no execution layer. Phase 2 adds the agent orchestrator: spawning Claude Code agents locally to write tests and implement code against reviewed task files, with wave-based sequencing, ralph-loop error recovery, and the structured status protocol. This is F11 from the dispatch overview, adapted for local execution without container isolation.

## Goals

**Goals**
- Spawn test-writing agents (one per test task) that write tests according to reviewed task specifications
- Spawn implementation agents (one per implementation task) that make reviewed tests pass
- Enforce context independence: test-writing agents and implementation agents are separate agents with no shared reasoning
- Manage implementation waves: wave N completes and passes verification before wave N+1 begins
- Integrate ralph-loop for error recovery within each agent task
- Enforce the replan cap (default 2 per task, configurable via `config.yml`)
- Implement the agent status protocol (DONE / DONE_WITH_CONCERNS / NEEDS_CONTEXT / BLOCKED)
- Integrate with Phase 1's verification engine for per-wave and final verification
- Add the agentic completeness layer to the task reviewer (F7) — deferred from Phase 1. Validates task set completeness against spec, accuracy against technical approach, gap detection, and cross-wave interface validation. Added when pipeline usage data from Phase 1 confirms the deterministic layer misses real gaps
- Integrate with Phase 1's test hash gate: compute manifest after test code review (Stage 7), verify immutability during and after implementation (Stage 8/9)
- Execute mutation testing via the test reviewer agent (Stage 9, checkpoint 5) against real implementations

**Non-goals**
- Container isolation or sandboxing (F10) — agents run locally in the developer's environment
- Network restrictions — no git-remote-only networking in local mode
- Scoped credentials — agents use the developer's credentials
- Automated stage transitions — developer invokes test creation and implementation explicitly
- PR creation — human manages git

## User-facing behavior

**Test creation**: Developer runs `/dispatch test-create <feature-name>`. The orchestrator reads reviewed test tasks from `ai-docs/<feature>/tasks/`, spawns one agent per test task. Each agent writes tests in a git worktree. Completion gate: tests compile and fail (they validate behavior that doesn't exist yet). Developer sees per-agent progress and status. On completion, the test code review gate (Stage 7) runs automatically — the test reviewer agent (F8, checkpoint 3) validates the test code. If review fails, the developer sees specific feedback and can re-run test creation.

**Test hash manifest**: After test code review passes, the test hash gate computes SHA-256 hashes of all test files and writes the manifest to `ai-docs/<feature>/test-hashes.json`. This is automatic and not separately invoked.

**Implementation**: Developer runs `/dispatch implement <feature-name>`. The orchestrator reads reviewed implementation tasks, organizes by wave, and executes:
1. Spawn wave 1 agents (one per task in wave 1), each in a git worktree
2. Each agent runs ralph-loop until its referenced tests pass or replan cap is hit
3. On wave completion: run inter-wave file reference check, then per-wave verification (Phase 1's verification engine)
4. Test hash gate re-verifies test file immutability
5. Advance to wave 2, repeat
6. After final wave: run full verification (Stage 9)

Agent status is displayed as agents complete: DONE, DONE_WITH_CONCERNS (developer reviews concerns), NEEDS_CONTEXT (developer provides context or the orchestrator escalates), BLOCKED (developer intervenes).

**Mutation testing**: After final verification, the test reviewer agent (checkpoint 5) generates targeted mutations and runs them against the approved test suite. Results are included in the verification report.

**Status**: `/dispatch status <feature-name>` shows per-agent progress, wave completion status, and verification results.

## Technical approach

### Agent Orchestrator

The orchestrator is the implementation of F11 from the dispatch overview, adapted for local execution. It manages two execution phases with a review gate between them.

**Test creation phase (Stage 6)**:
- Read `task.json` from `ai-docs/<feature>/<feature>-tasks/` to identify test tasks (entries with `type: "test"`) for the current wave
- Set each task's `status` to `in_progress` in `task.json` before spawning
- Spawn one Claude Code agent per test task using Agent Teams
- Each agent works in a git worktree (Claude Code's native worktree support)
- Agent receives: the test task file, the spec's testing strategy section, AC definitions. Does not receive: implementation tasks, technical approach details
- Completion gate per agent: tests compile and fail
- Ralph-loop handles compilation errors and test framework issues
- On agent completion: set task `status` to `complete` in `task.json`, record the agent's work summary in the `summary` field
- On all agents complete: merge worktrees, trigger test code review (Stage 7)

**Test code review gate (Stage 7)**:
- Invoke test reviewer agent (F8, checkpoint 3) against the merged test code
- Pipeline-blocking: implementation cannot begin until review passes
- On pass: compute test hash manifest via `test-hash-gate.sh`
- On fail: report feedback, developer re-runs test creation

**Implementation phase (Stage 8)**:
- Read `task.json` for implementation tasks (entries with `type: "implementation"`), group by `wave_id`
- If resuming after interruption, check task statuses: skip `complete` tasks, re-evaluate `in_progress` tasks (partial work exists), treat `tests_fail` tasks as replan candidates, skip `superseded` tasks, do not resume `parked` tasks without user confirmation
- For each wave:
  1. Pre-wave check: inter-wave file reference validation (parse wave N+1 tasks for declared file references, verify referenced files exist after wave N)
  2. Spawn one agent per task in the current wave, each in a git worktree. Set each task's `status` to `in_progress` in `task.json`
  3. Each agent receives: its implementation task file, the repo with reviewed test code. Does not receive: other agents' tasks, test-writing agents' reasoning
  4. Completion gate per agent: referenced tests pass
  5. Ralph-loop iterates until tests pass or replan cap is hit
  6. Agents report structured status. On completion: set `status` to `complete` and record `summary`. On test failure: set `status` to `tests_fail`. On replan cap exhaustion: set `status` to `parked` with `note`
  7. On wave completion: merge worktrees, run test hash gate (verify immutability), run per-wave verification
  8. Advance to next wave

**Agent status protocol**:
- DONE: task completed, tests pass
- DONE_WITH_CONCERNS: tests pass but agent flags potential issues. Orchestrator logs concerns and presents to developer
- NEEDS_CONTEXT: agent cannot proceed without additional information. Orchestrator presents the context request to the developer
- BLOCKED: agent hit an unrecoverable issue. Orchestrator presents the blocker to the developer
- Replan cap exceeded: agent exhausted retries. Spec moves to PARKED with failure details

**Mutation testing (Stage 9, checkpoint 5)**:
- After final verification passes, spawn test reviewer agent as context-independent agent
- Agent receives: spec and implemented code only (no access to test-writing or implementation agents' reasoning)
- Generates targeted mutations: flip return values, swap conditionals, remove lines, alter boundary conditions
- Runs mutated code against the hash-verified test suite
- Reports: mutation detection rate, specific undetected mutations
- Pipeline-blocking: configurable minimum mutation detection rate in `verify.yml`

### Worktree Management

Agents work in git worktrees (Claude Code's native `isolation: "worktree"` parameter). The orchestrator:
- Creates worktrees before spawning agents
- Monitors agent completion
- Merges completed worktrees back to the working branch
- Handles merge conflicts by escalating to the developer (BLOCKED status)

### Integration with Phase 1

- **State engine**: orchestrator updates pipeline state on agent spawn, completion, wave transitions, and verification results
- **Task manifest (task.json)**: orchestrator reads task.json for task lists and updates per-task `status` and `summary` fields throughout execution. Task status enables resume-after-interruption at the task level
- **Audit logger**: orchestrator logs all agent events (spawn, status reports, replan attempts, completion)
- **Verification engine**: invoked per-wave and after final wave with the feature's `verify.yml` checks
- **Test hash gate**: computed after Stage 7, verified during Stage 8 (per-wave) and Stage 9
- **Config**: reads replan cap, max concurrent agents, model selection from `config.yml`

## Testing strategy

Phase 2's deliverables include orchestrator code (agent spawning, wave management, status routing, worktree management) and context asset behaviors (test-writing agents, implementation agents, mutation testing via test reviewer). Testing follows the project-wide tiered approach defined in the dispatch overview.

### Tier 1: Automated tests for deterministic code

**Orchestrator logic:**
- Inter-wave file reference check detects missing files (file expected by wave N+1 not produced by wave N) and pre-existing files (file wave N+1 expects to create already exists) — covers AC-04
- Test hash manifest is computed after Stage 7, and hash comparison detects modifications during Stage 8 — covers AC-05
- Agent status protocol correctly routes DONE, DONE_WITH_CONCERNS, NEEDS_CONTEXT, and BLOCKED to appropriate handlers — covers AC-07
- Replan cap enforcement: agent exceeding cap triggers PARKED state with failure details — covers AC-06
- Wave sequencing: wave N must complete before wave N+1 begins; verification runs between waves — covers AC-04

### Tier 2: Validated through pipeline operation

These cover agent behaviors that depend on prompt quality and Agent Teams functionality. Validated by running real specs through the pipeline.

- Test creation spawns agents that produce tests which compile and fail — covers AC-01
- Implementation agents make reviewed tests pass via ralph-loop iteration — covers AC-02
- Test code review gate blocks implementation when test reviewer rejects test code — covers AC-03
- NEEDS_CONTEXT and BLOCKED statuses escalate to developer with the agent's context request — covers AC-07
- Mutation testing generates mutations, runs against test suite, and reports detection rate — covers AC-08
- Context independence: test-writing agents and implementation agents receive only their designated artifacts — covers AC-09

Persistent failures at these points indicate the agent definitions, orchestrator prompts, or Agent Teams invocation patterns need iteration.

### Existing tests impacted

- Phase 1's state engine tests may need new transition paths for agent-related states (TESTING, IMPLEMENTING, wave states)

### Test infrastructure

- Fixture files: sample test task files and implementation task files with wave assignments
- Fixture files: minimal project repository for agents to work against (source files, test runner, linting)
- Test helper: worktree creation and cleanup
- Test helper: mock agent that produces deterministic output for orchestrator logic testing

## Documentation impact

### Project documents to update

- `ai-docs/dispatch/dispatch-overview.md`: Cross-reference to Phase 2 spec for F11 local execution adaptation
- Phase 1 spec: note that mutation testing check transitions from "registered but skipped" to active in Phase 2

### New documentation to create

- Agent orchestrator usage guide: how to invoke test creation and implementation, interpret agent status, handle escalations
- Worktree management documentation: how agents use worktrees, merge strategy, conflict resolution

## Acceptance criteria

- **AC-01**: Test creation spawns one agent per reviewed test task. Each agent works in a git worktree and produces tests that compile and fail. Agents receive only test task files and testing strategy (no implementation details).
- **AC-02**: Implementation spawns one agent per reviewed implementation task. Each agent works in a git worktree and iterates (via ralph-loop) until its referenced tests pass or the replan cap is reached.
- **AC-03**: Test code review (Stage 7) blocks implementation. Implementation cannot begin until the test reviewer agent approves test code.
- **AC-04**: Implementation waves execute in order. Wave N completes and passes per-wave verification before wave N+1 begins. Inter-wave file reference check runs before each wave.
- **AC-05**: Test file immutability is enforced. SHA-256 manifest computed after Stage 7 approval. Any test file modification during Stage 8 or 9 hard-fails the pipeline.
- **AC-06**: Ralph-loop provides error recovery within each agent task. Replan cap (configurable, default 2) is enforced. Cap exhaustion moves the spec to PARKED.
- **AC-07**: Agent status protocol functions: DONE and DONE_WITH_CONCERNS are logged. NEEDS_CONTEXT and BLOCKED escalate to the developer with the agent's request/blocker.
- **AC-08**: Mutation testing executes after final verification. Test reviewer generates mutations against real implementation, runs against hash-verified test suite, and reports detection rate. Configurable minimum detection rate in `verify.yml` is enforced.
- **AC-09**: Context independence maintained: test-writing agents and implementation agents are separate agents with no shared reasoning or artifacts beyond what each is explicitly given.
- **AC-10**: All agent events (spawn, status, replan, completion) are written to the audit log. Pipeline state reflects agent progress.

## Open questions

- **OQ-P2-1**: What is the worktree merge fallback when task review's no-overlap check fails to prevent shared-file conflicts? Options: (a) hard-fail and escalate to developer, (b) attempt sequential merge with conflict detection. Option (a) is safer since the overlap itself indicates a breakdown defect that should be fixed at the source.
- **OQ-P2-2**: What default concurrent agent count balances throughput against local resource constraints? The overview says "configurable max concurrent agents" without suggesting a default. For local execution, 2 is conservative and safe; 4 risks memory pressure on smaller machines. Resource detection adds complexity for marginal benefit.
- **OQ-P2-3**: Does DONE_WITH_CONCERNS require human review before advancing? The overview says "evaluate concerns before advancing" which is ambiguous. Pausing for human input is safer but adds friction; logging and continuing risks ignoring real issues. Recommendation: pause by default, with a config flag to auto-continue.

## Dependencies

- **Phase 1**: Pipeline state engine, audit logger, verification engine, test hash gate, test reviewer agent, project configuration — all must be implemented
- **Phase 1**: Reviewed task files (test tasks and implementation tasks) must exist for the orchestrator to consume
- Claude Code Agent Teams capability
- Claude Code worktree isolation (`isolation: "worktree"`)
- Claude Code ralph-loop for error recovery
- Target project must have: working test runner, linter, and type checker (if applicable)
