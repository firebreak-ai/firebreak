# Phase 3: Dispatch Orchestration

> **Status: Pre-Review** — This spec has not yet been through council review.

## Problem

After Phase 1 (pipeline infrastructure) and Phase 2 (agent execution), the developer manually invokes each pipeline stage: validate, review, breakdown, test-create, implement, verify. This works but requires the developer to monitor completion and trigger the next stage at every transition. Phase 3 adds the dispatcher — a deterministic orchestrator that chains stages automatically after the developer's last judgment call (spec review) — and a file-based queue for managing multiple specs. The developer invokes `/dispatch <feature-name>` and the pipeline runs from breakdown through verification autonomously, parking only on gate failure or replan cap exhaustion.

## Goals

**Goals**
- Build the dispatcher that chains post-review pipeline stages automatically (breakdown -> task review -> test creation -> test code review -> implementation -> verification)
- Park the pipeline on gate failure or replan cap exhaustion, recording the failure stage and reason
- Support the PARKED -> READY transition: developer reworks the spec, clears the verification gate, pipeline resumes at the failed stage
- Build a file-based spec queue manager: add, list, inspect, and manage specs in the queue directory
- Validate spec schema on queue add
- Show queue status and pipeline state across all specs
- Support pause/resume for individual specs and the full queue

**Non-goals**
- Queue polling or automated spec pickup — developer invokes `/dispatch` explicitly per spec
- PR creation or assembly — human manages git
- Full-auto mode or automatic merge
- Notification webhooks or external escalation channels — stdout/log only
- Container isolation — agents continue to run locally
- Interval-based execution via `/loop` — v2 goal
- Headless skill invocation (OQ-4 from overview) — the dispatcher invokes pipeline stages through code, not through interactive skills

## User-facing behavior

**Queue management**:
- `/queue add <spec-path>`: Validates spec against schema, copies to `.claude/automation/queue/`, initializes pipeline state as QUEUED. Rejects invalid specs with specific validation errors.
- `/queue list`: Shows all specs in queue with current pipeline stage, state (QUEUED, active, PARKED, READY, COMPLETED), and last activity timestamp.
- `/queue inspect <spec-name>`: Shows spec details, full pipeline state, and audit log summary.
- `/queue pause <spec-name>` / `/queue resume <spec-name>`: Pause/resume individual specs. Paused specs are skipped by the dispatcher.
- `/queue pause-all` / `/queue resume-all`: Pause/resume the entire queue.

**Dispatch**:
- `/dispatch <feature-name>`: The developer's "take it from here" command. Prerequisite: spec must have passed review (Stage 3). The dispatcher chains: breakdown (S4) -> task review (S5) -> test creation (S6) -> test code review (S7) -> implementation (S8) -> verification (S9). Each gate is enforced automatically. On gate pass: advance. On gate failure or replan cap: park and report.
- `/dispatch status <feature-name>`: Current pipeline position, per-stage results, agent status if in execution. During implementation stages, reads `task.json` to show per-task status (`not_started`, `in_progress`, `complete`, `tests_fail`, `parked`, `superseded`) and agent work summaries.
- `/dispatch resume <feature-name>`: Resume a READY spec at its failed stage. Prerequisite: spec must be in READY state (reworked and gate-cleared).

**Pipeline parking**:
When the pipeline parks, the developer sees: which stage failed, what the failure was, and what needs to change. The developer iterates on the spec or tasks (via `/spec` or manual edits), then runs `/dispatch resume <feature-name>` when ready. The pipeline resumes at the failed stage, not from the beginning.

**Stage chaining behavior**:
The dispatcher is deterministic — it does not make judgment calls. It reads the current stage from pipeline state, runs the next stage, checks the gate, and either advances or parks. Agentic stages (review, breakdown, test creation, implementation) use AI agents; the dispatcher itself does not. The dispatcher logs every transition to the audit log.

## Technical approach

### Dispatcher

The dispatcher is a shell script (or lightweight Python script with no external dependencies) that runs on the host machine. Per the overview's architecture decision: shell first, escalate to Python if complexity exceeds shell's capabilities.

**Core loop** (for a single `/dispatch` invocation):
```
read current_stage from state file
while current_stage != COMPLETED and current_stage != PARKED:
  run current_stage's execution function
  run current_stage's gate check
  if gate passes:
    advance current_stage to next stage
    persist state
    log transition
  else:
    set state to PARKED with failure reason
    log parking
    report to developer
```

**Stage execution functions**: Each stage has a corresponding function that invokes the appropriate Phase 1/Phase 2 component:
- Breakdown: calls the breakdown integration (F6) programmatically
- Task review: calls the task reviewer (F7) programmatically
- Test creation: calls the agent orchestrator's test creation phase (Phase 2)
- Test code review: calls the test reviewer (F8, checkpoint 3) programmatically
- Implementation: calls the agent orchestrator's implementation phase (Phase 2)
- Verification: calls the verification engine (F9)

The dispatcher invokes these as function calls or script invocations — not as interactive Claude Code skills. This sidesteps OQ-4 (headless skill invocation) entirely. The skills (`/spec-review`, `/breakdown`, `/implement`) remain available for manual use; the dispatcher calls the underlying logic directly.

**Idempotency**: The dispatcher can be interrupted (Ctrl-C, crash, system restart) and resumed. State is persisted after each stage transition. Re-running `/dispatch <feature-name>` reads the current stage and continues from there. Agent teams are spawned with deterministic IDs tied to spec + stage + attempt, preventing duplicate spawns.

**PARKED -> READY transition**: When a spec is parked, the developer addresses the failure (edits spec, fixes tasks, resolves blockers). Running `/dispatch resume <feature-name>` re-runs the failed stage's gate check first. If the gate now passes, the state transitions to READY -> next stage. If it still fails, the spec remains PARKED with updated feedback.

### Spec Queue Manager (F1)

File-based queue in `.claude/automation/queue/`. Each spec is a markdown file following the spec schema.

**Queue operations**:
- Add: copy spec to queue directory, validate against schema (using F4 spec validator), initialize state file
- List: read all state files, format status table
- Inspect: read state file + audit log, format detailed view
- Pause/resume: set flag in state file; dispatcher skips paused specs

The queue manager is a skill (`/queue`) that wraps simple file operations and state file reads. No agentic processing.

**Queue directory structure**:
```
.claude/automation/
  queue/          # spec files
    feature-a.md
    feature-b.md
  state/          # pipeline state per spec
    feature-a.json
    feature-b.json
  logs/           # audit logs per spec
    feature-a.log
    feature-b.log
```

### Cost Controls

The dispatcher enforces cost controls from `config.yml`:
- Token budget per spec: abort if budget exceeded (tracked via audit log token counts)
- Circuit breaker: abort after N consecutive failures or N replans without progress (default: 2 replans per task)
- The dispatcher logs cost data (tokens per stage) to the audit log for operational metrics

### Integration with Phase 1 and Phase 2

- **State engine (F2)**: dispatcher reads and writes pipeline state at every transition
- **Task manifest (task.json)**: dispatcher reads `task.json` for `/dispatch status` to show per-task progress. The agent orchestrator (Phase 2) writes task status updates; the dispatcher consumes them for observability
- **Audit logger (F3)**: dispatcher logs every action (stage start, gate result, transition, parking, resume)
- **Spec validator (F4)**: invoked on `/queue add` to validate spec before queuing
- **Verification engine (F9)**: invoked by dispatcher during Stage 9
- **Agent orchestrator (Phase 2)**: invoked by dispatcher for Stages 6 and 8
- **Test reviewer (F8)**: invoked by dispatcher for Stage 7

## Testing strategy

Phase 3's deliverables are primarily deterministic code — the dispatcher script and queue manager are orchestration code, not context assets. Most tests fall into Tier 1. Testing follows the project-wide tiered approach defined in the dispatch overview.

### Tier 1: Automated tests for deterministic code

**Dispatcher:**
- Dispatcher chains stages from breakdown through verification when all gates pass (using mock stage execution functions), advancing state at each transition — covers AC-01
- Dispatcher parks on gate failure with correct failure stage and reason recorded in state — covers AC-02
- `/dispatch resume` re-runs failed stage gate, advances on pass, remains parked on continued failure — covers AC-03
- Dispatcher is idempotent — interrupting and re-running produces the same result as uninterrupted execution — covers AC-04
- Deterministic IDs for agent spawns prevent duplicate work on re-run — covers AC-04
- Cost controls abort the pipeline when token budget or replan cap is exceeded — covers AC-07
- Dispatcher logs every transition (stage start, gate result, advance/park) to audit log — covers AC-08

**Queue manager:**
- `/queue add` validates spec against schema and rejects invalid specs with specific errors — covers AC-05
- `/queue list` shows correct state for specs in various pipeline stages (QUEUED, active, PARKED, COMPLETED) — covers AC-05
- `/queue pause` and `/queue resume` toggle the paused flag; dispatcher skips paused specs — covers AC-06

### Tier 2: Validated through pipeline operation

- Full end-to-end pipeline run: a real spec goes from `/dispatch` through all stages to verification completion. This is a manual integration test run against a real project — validates that the dispatcher correctly invokes Phase 1/Phase 2 components programmatically and that stage chaining works with real agentic stages (not mocks).

### Existing tests impacted

- Phase 1 state engine tests may need new states added for dispatcher transitions
- Phase 2 orchestrator tests may need to verify they support programmatic invocation (not just skill-based)

### Test infrastructure

- Fixture files: pre-populated queue with specs in various pipeline states
- Mock stage execution functions that simulate pass/fail for dispatcher logic testing (Tier 1 tests use these instead of invoking real agentic stages)

## Documentation impact

### Project documents to update

- `ai-docs/dispatch/dispatch-overview.md`: Cross-reference Phase 3 spec for F1 and F13
- Phase 1 spec: note that Phase 1 components must support programmatic invocation (not just skill-based)
- Phase 2 spec: note that Phase 2 orchestrator must support programmatic invocation by the dispatcher

### New documentation to create

- Dispatcher usage guide: `/dispatch` and `/queue` command reference
- Pipeline flow diagram: stage transitions, gate checks, parking/resume behavior
- Troubleshooting guide: common parking reasons and resolution steps

## Acceptance criteria

- **AC-01**: `/dispatch <feature-name>` chains stages from breakdown (S4) through verification (S9) automatically. Each gate is enforced. Pipeline advances on gate pass without human intervention.
- **AC-02**: Pipeline parks on gate failure or replan cap exhaustion. State records the failed stage, failure reason, and feedback. Developer can see what failed and what needs to change.
- **AC-03**: `/dispatch resume <feature-name>` resumes a READY spec at its failed stage. The failed stage's gate is re-checked before advancing.
- **AC-04**: Dispatcher is idempotent. Interrupting and re-running `/dispatch` continues from the last persisted state. Agent spawns use deterministic IDs to prevent duplicate work.
- **AC-05**: `/queue add` validates spec on add and rejects invalid specs. `/queue list` shows all specs with current pipeline state. `/queue inspect` shows detailed state and audit summary.
- **AC-06**: `/queue pause` and `/queue resume` work for individual specs and the full queue. Paused specs are skipped by the dispatcher.
- **AC-07**: Cost controls enforce token budget per spec and circuit breaker on consecutive failures. Exceeding either aborts the pipeline and parks the spec.
- **AC-08**: Every dispatcher action (stage start, gate result, transition, parking, resume) is logged to the audit log with structured data.

## Open questions

- **OQ-P3-1**: Should the dispatcher be shell or Python? The overview says "shell first, escalate to Python." Given JSON parsing, multi-component invocation, and error routing, Python is likely the better fit — shell becomes fragile at this complexity level.
- **OQ-P3-2**: How does the dispatcher invoke Phase 1/Phase 2 components programmatically? Options: (a) CLI interface per component (most portable), (b) Python imports if dispatcher is Python (cleanest), (c) skill invocation via `claude -p` (closest to existing architecture but hits OQ-4). This affects Phase 1/2 component design — components must expose a programmatic interface regardless of which option is chosen.
- **OQ-P3-3**: Should the dispatcher stream real-time progress or report in batch? Real-time is better UX for long-running pipelines but adds output management complexity. Batch is simpler and sufficient if the developer can check status separately via `/dispatch status`.

## Dependencies

- **Phase 1**: All Phase 1 components must be implemented and support programmatic invocation
- **Phase 2**: Agent orchestrator must be implemented and support programmatic invocation
- Spec schema (defined in Phase 1) — needed for queue validation
- Claude Code skills infrastructure (for `/queue` and `/dispatch` skill registration)
