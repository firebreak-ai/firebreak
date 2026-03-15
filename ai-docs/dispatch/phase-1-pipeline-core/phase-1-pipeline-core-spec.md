# Phase 1: Pipeline Core

## Problem

The dispatch pipeline requires foundation infrastructure (state tracking, audit logging, configuration), deterministic gates (spec validation, task review), agentic review stages (council review integration, test reviewer, breakdown), and a verification engine before any agent can execute implementation work. Without these components, the pipeline has no stages to advance through, no gates to enforce quality, and no verification to validate results. This phase builds the complete pipeline — everything except agent execution (Phase 2) and automated orchestration (Phase 3).

## Goals

**Goals**
- Implement pipeline state tracking with resume-after-interruption support
- Implement append-only audit logging with structured event recording
- Define project configuration schemas (`config.yml`, `verify.yml`) with cold-start detection
- Build the deterministic spec validator against the spec schema
- Build the test reviewer agent covering all five pipeline checkpoints
- Integrate with the existing `/spec-review` skill for council + test strategy review
- Build breakdown integration with sequential context-independent agents producing test tasks and implementation tasks
- Build the two-layer task reviewer gate (deterministic + test task quality; agentic completeness deferred to Phase 2)
- Define the `verify.yml` check interface and ship the test hash gate script (`test-hash-gate.sh`)

**Non-goals**
- Agent execution or orchestration — agents are spawned in Phase 2
- Container isolation or sandboxing — deferred post-MVP
- Automated stage transitions or queue polling — Phase 3
- PR creation or assembly — human manages git in MVP
- Full-auto mode, notification, or escalation — deferred post-MVP
- Verification engine execution — Phase 1 defines the check interface and ships the test hash gate script; the execution engine that runs all `verify.yml` checks is built in Phase 2 when implementation code exists to verify against
- Mutation testing execution infrastructure — deferred post-MVP

## User-facing behavior

The developer invokes each pipeline component directly through skills or CLI commands. There is no automated pipeline flow in this phase — the developer drives stage transitions manually.

**Spec validation**: Developer runs `/dispatch validate <spec-path>`. The validator checks the spec against the schema, reports pass/fail with specific failures. On pass, the spec is eligible for review.

**Review**: Developer runs `/spec-review <feature-name>` (existing skill, modified to include test strategy review). Council review runs as before. The test reviewer agent validates the testing strategy section. Review output includes pass/fail with feedback from both layers. On failure, feedback is attached to the spec for iteration.

**Breakdown**: Developer runs `/breakdown <feature-name>` (existing skill, modified for sequential task/impl breakdown). Two context-independent Agent Teams teammates run sequentially — the test task agent produces test tasks, then the implementation task agent produces implementation tasks informed by the test task output. Output is structured task files written to `ai-docs/<feature>/tasks/`.

**Task review**: Runs automatically after breakdown completes. Two-layer gate: deterministic checks and test task quality review. On failure, returns to breakdown with specific feedback. On pass, tasks are marked ready for execution.

**Verification (interface only)**: Phase 1 defines the `verify.yml` check interface (check name, command, required/advisory, thresholds) and ships the test hash gate script (`test-hash-gate.sh`). The execution engine that runs all checks is deferred to Phase 2.

**State and audit**: Pipeline state is visible via `/dispatch status <spec-name>`. Audit log is human-readable at `.claude/automation/logs/<spec-name>.log`.

## Technical approach

Each component is described below. All pull directly from the dispatch overview without architectural changes.

### Pipeline State Engine (F2)

JSON status file per spec in `.claude/automation/state/<spec-name>.json`. Tracks: current pipeline stage, timestamps per stage transition, agent IDs (when applicable), verification results, error history.

**Pipeline states and valid transitions:**

| State | Description | Valid transitions to |
|-------|-------------|---------------------|
| `QUEUED` | Spec added to queue, not yet started | `VALIDATING` |
| `VALIDATING` | Spec validator running (S1) | `VALIDATED`, `PARKED` |
| `VALIDATED` | Spec passed validation (S2) | `REVIEWING` |
| `REVIEWING` | Council review + test strategy review running (S3) | `REVIEWED`, `PARKED` |
| `REVIEWED` | Spec passed review | `BREAKING_DOWN` |
| `BREAKING_DOWN` | Breakdown agents producing tasks (S4) | `BROKEN_DOWN`, `PARKED` |
| `BROKEN_DOWN` | Tasks produced, pending review | `TASK_REVIEWING` |
| `TASK_REVIEWING` | Task reviewer running (S5) | `TASKS_READY`, `PARKED` |
| `TASKS_READY` | Tasks passed review, ready for execution | `TESTING` |
| `TESTING` | Test creation agents running (S6) | `TESTS_WRITTEN`, `PARKED` |
| `TESTS_WRITTEN` | Tests produced, pending review | `TEST_REVIEWING` |
| `TEST_REVIEWING` | Test code review running (S7) | `TESTS_READY`, `PARKED` |
| `TESTS_READY` | Tests reviewed and hash manifest computed | `IMPLEMENTING` |
| `IMPLEMENTING` | Implementation agents running (S8) | `IMPLEMENTED`, `PARKED` |
| `IMPLEMENTED` | Implementation complete, pending verification | `VERIFYING` |
| `VERIFYING` | Verification engine running (S9) | `COMPLETED`, `PARKED` |
| `COMPLETED` | All stages passed | _(terminal)_ |
| `PARKED` | Requires human attention — records failed stage and failure reason | `READY` |
| `READY` | Parked spec reworked and gate cleared — resumes at failed stage | _(the failed stage's active state)_ |

The state engine validates that each transition is legal before persisting; illegal transitions are rejected with an error logged to the audit log.

State is persisted after each stage transition. The dispatcher (Phase 3) reads state to determine next action; in Phase 1, the developer reads state via the status command.

### Audit Logger (F3)

Append-only log file per spec at `.claude/automation/logs/<spec-name>.log`. Records: dispatcher actions, agent events (spawn, completion, status), gate results (pass/reject with structured JSON), verification results, errors. Format: human-readable lines with embedded structured JSON for programmatic querying.

Gate scripts emit structured JSON on both pass and rejection. Each gate script calls the audit logger CLI (`audit-logger.py log <spec-name> gate_result <json>`) to record its result after producing output. Agentic components (test reviewer, breakdown agents) log via direct file writes during their operation. This data feeds the pipeline retrospective (which gates add value, where replans concentrate, cost-per-AC).

### Project Configuration (F14)

Two configuration files in the target project:

**`.claude/automation/config.yml`**: Token budget per spec (default TBD), max concurrent agents (default 1 for Phase 2), replan cap per task (default 2), model selection per pipeline stage, configuration overrides.

**`.claude/automation/verify.yml`**: Verification checklist. Each entry specifies: check name, command to run, required vs. advisory, and any configurable thresholds (duplication scanner threshold, assertion density minimums, mutation detection rate).

Configuration layering: global defaults in the dispatch harness -> project-level overrides in `config.yml` -> per-spec overrides in spec frontmatter.

Cold-start detection: warn when a project lacks prerequisites (test suite, linting config, CLAUDE.md). Does not refuse to run — warns and continues.

Optional baseline capture command: snapshots current project metrics (test pass rate, duplication score) before the first spec enters the pipeline. Stored alongside project config.

### Spec Validator (F4)

Deterministic validation before any agentic processing. Validates against the spec schema (single source of truth). Checks:
- Required sections present and non-empty
- Field patterns (AC identifier format `AC-XX`, testing strategy AC traceability)
- Section-level constraints per the schema
- Injection pattern detection — catch mechanical vectors (hidden text, control characters, embedded instructions) that could alter agent behavior. This is not comprehensive prompt injection defense; it catches the obvious and flags the suspicious. Structural validation is the sanitization: a spec that passes the gate has validated structure and content aligned with the spec template rules.

F4 is implemented by refactoring the existing `spec-gate.sh` — adding injection detection and input sanitization to the existing structural validation. The `/spec` skill keeps its existing template. Both encode spec structure independently (accepted maintenance friction for Phase 1; a future phase should migrate to a shared declarative schema).

### Test Reviewer Agent (F8)

Dedicated agent persona that validates test quality against spec requirements. Context-independent — no access to authoring or implementing agents' reasoning, only the spec artifact and code. Invoked at five pipeline checkpoints:

1. **Spec review (Stage 3)**: Validates testing strategy against ACs. Does the strategy cover every AC? Are test descriptions specific enough for concrete test tasks? Do proposed tests validate behavior, not implementation details?
2. **Task review (Stage 5)**: Validates test task descriptions against the approved testing strategy. Catches breakdown agent deviations before test-writing agents execute.
3. **Test code review (Stage 7)**: Validates actual test code. Do tests trace to ACs? Compile and fail as expected? Match approved test tasks? Catch real regressions?
4. **Verification — test integrity (Stage 9)**: Validates implementation agents did not weaken coverage through indirect means.
5. **Verification — mutation testing (Stage 9)**: Generates targeted mutations against real implementation. Context-independent: receives spec and implemented code only. Mutations run against hash-verified test suite.

Has pipeline-blocking authority at all five checkpoints. Brownfield mode: derives requirements from existing code, flags derived requirements for human confirmation.

Also invocable on-demand via `/test-review` skill independently of the dispatch pipeline. This allows developers to run test quality validation against any spec or test code outside of a pipeline run.

The test reviewer is implemented as a Claude Code agent definition (`.claude/agents/test-reviewer.md`) with the persona, checkpoint-specific instructions, and output format. Each checkpoint invocation receives only the artifacts appropriate to that checkpoint.

### Review Integration (F5)

Connects the pipeline to the existing `/spec-review` skill. Two-layer review:
1. **Council review**: Invokes `/spec-review` with council agents (architect, security, guardian, advocate, analyst). Parses review output for pass/fail.
2. **Test strategy review**: Invokes the test reviewer agent (F8, checkpoint 1) against the spec's testing strategy section.

On failure at either layer: feedback attached to spec, state set to `PARKED`. On pass: state advances to breakdown-eligible.

Modifications to existing `/spec-review` skill: add test strategy review invocation after council review passes. The skill must reference the spec schema for structural validation (replacing any hardcoded structural assumptions).

### Breakdown Integration (F6)

Spawns two breakdown agents sequentially, each as an Agent Teams teammate with independent context:
1. **Test task agent**: Receives the spec only. Produces test tasks from the spec's testing strategy and acceptance criteria. One task per AC or logical test group. Each task specifies: files to create, test framework conventions, AC identifiers covered, completion gate (tests compile and fail).
2. **Implementation task agent**: Receives the spec plus the test task files produced in step 1. Produces implementation tasks from the spec's technical approach and ACs. Each task specifies: files to create/modify (explicit paths), AC identifiers satisfied, references to specific test tasks as completion gate, constraints (file scope, no test modification). Completion gate: referenced tests pass.

Both agents run as separate Agent Teams teammates — independent context windows, no shared reasoning or conversation history. The implementation task agent receives test task output as artifacts, not the test task agent's reasoning. All tasks are structured for AI consumption — no prose descriptions. Output written to `ai-docs/<feature>/<feature>-tasks/` as individual task files.

After both agents complete, a `task.json` manifest is assembled in the task directory. The manifest contains per-task entries with: id, title, file reference, type (test/implementation), wave assignment, dependencies, AC coverage, model assignment, and a `status` field (initialized to `not_started`). The implementation stage updates task status as agents execute (`in_progress`, `complete`, `tests_fail`, `parked`, `superseded`), and records each agent's work summary. The gate script validates `task.json` structure and invariants.

Tasks are organized into implementation waves. Wave assignment is part of the implementation task agent's output. Wave N+1 tasks may reference files or behaviors produced by Wave N.

### Task Reviewer (F7)

Two-layer gate between breakdown and execution:

1. **Deterministic checks**: Required fields present in each task, file paths exist in the repository (for files to modify), no overlapping file boundaries between tasks, every spec AC covered by at least one task, implementation tasks reference valid test tasks as completion gates.
2. **Test task quality** (test reviewer, checkpoint 2): Test task descriptions faithfully translate the testing strategy.

Agentic completeness layer (task set completeness against spec, accuracy against technical approach, gap detection, cross-wave interface validation) deferred to Phase 2. The deterministic layer covers AC mapping, structural completeness, and cross-task references mechanically. The agentic layer will be added when pipeline usage data shows the deterministic layer misses real gaps.

Failing review returns to breakdown with specific feedback on what's missing or incorrect. On pass, tasks are marked execution-ready. No additional human approval required beyond the developer's stage invocation.

### Verification Engine (F9) — Interface Only

Phase 1 defines the verification check interface and ships one standalone gate script. The execution engine that runs all checks against implementation code is deferred to Phase 2.

**Check interface definition** (`verify.yml` schema): Each entry specifies check name, command to run, required vs. advisory, and configurable thresholds. This schema is documented in Phase 1 so that Phase 2's execution engine has a stable contract.

**Test hash gate script** (`test-hash-gate.sh`): Standalone script that computes SHA-256 hashes of test files, writes manifest to `ai-docs/<feature>/test-hashes.json`, and compares on subsequent runs. Ships in Phase 1 as an independent gate — does not require the execution engine.

**Deferred to Phase 2**: Fresh-verification protocol execution, all required checks (test execution, linter, type checker, duplication scanner, assertion density, regression check), advisory checks (code review agent, test integrity), mutation testing, and verification report aggregation.

## Testing strategy

Phase 1's deliverables are primarily context assets (skills, agents, docs) with a few deterministic code artifacts (gate scripts, state engine, config loader, audit logger). The testing strategy reflects this: deterministic code gets automated tests with fixtures; context asset behaviors are validated through pipeline operation.

### Tier 1: Automated tests for deterministic code

These test actual code artifacts with fixture files. They can run in CI.

**Gate scripts:**
- Spec validator (`spec-gate.sh` refactored) rejects specs missing required sections, invalid AC identifier format, missing testing strategy AC traceability — covers AC-04
- Spec validator detects injection patterns (embedded instructions in markdown) — covers AC-04
- Spec validator passes a corpus of valid specs (including specs with legitimate HTML, unicode, external references) without false rejections — covers AC-04
- Task reviewer deterministic layer rejects tasks with missing fields, overlapping file boundaries, or unmapped ACs — covers AC-08
- Test hash gate computes SHA-256 manifest on first run and detects file modifications on subsequent runs — covers AC-09

**State engine:**
- `transition()` rejects invalid state transitions (e.g., `QUEUED` -> `COMPLETED` without intermediate stages) — covers AC-01
- Persists state to JSON after each transition and resumes correctly from persisted state — covers AC-01
- PARKED-to-READY lifecycle: park on failure (records failed stage and reason), transition to READY, resume at failed stage — covers AC-01

**Audit logger:**
- Appends structured JSON lines events without corrupting existing entries — covers AC-02

**Config loader:**
- Applies layering (global -> project -> spec frontmatter) with more-specific-wins precedence — covers AC-03
- Cold-start detection identifies missing prerequisites (no test suite, no linting config, no CLAUDE.md) and warns without blocking — covers AC-03

**Status command:**
- Returns correct stage, timestamps, and error history from pre-populated state file — covers AC-10

### Tier 2: Validated through pipeline operation

These cover context asset behaviors (skills, agents) that cannot be automated because the output is natural language evaluated by other agents or humans. They are validated by running real specs through the pipeline and observing results.

- Review integration invokes council review and test strategy review in sequence, transitions state correctly on pass and failure, attaches feedback on failure — covers AC-05, AC-06
- Test reviewer agent validates test quality at checkpoints 1 (spec review) and 2 (task review) with pipeline-blocking authority; each checkpoint receives only its appropriate artifacts — covers AC-06
- Breakdown produces test tasks and implementation tasks sequentially with correct AC coverage and task-to-test references — covers AC-07
- All components write to the audit log during pipeline operation — covers AC-10

These are verified by inspection during the first real pipeline runs. Persistent failures at these points indicate the context assets (skill prompts, agent definitions) need iteration — the fix is prompt refinement, not code changes.

### Tier 3: Framework effectiveness (longitudinal)

Measured over sustained pipeline use, not per-run:
- Which gates catch real problems vs. add ceremony (gate rejection rate per stage)
- Where replans concentrate (which stages and task types)
- Cost-per-AC (pipeline cost divided by acceptance criteria satisfied)

These metrics are tracked via the audit log (JSON lines format) and reported by `/dispatch metrics` (Phase 3). Phase 1 deliverable: the audit log captures the raw data. Reporting is deferred.

### Existing tests impacted

- `spec-gate.sh` — subsumed by F4. Run compatibility fixtures through both old and new validators before cutover.
- `breakdown-gate.sh` — subsumed by F7's deterministic layer. Same compatibility approach.
- `review-gate.sh` — relationship to F5 must be defined during implementation.

### Test infrastructure

- Fixture files: valid specs, invalid specs, injection-attempt specs, false-positive-prone specs (legitimate HTML, unicode, external references)
- Fixture files: valid task files, invalid task files (missing fields, overlapping boundaries)
- Fixture files: sample `verify.yml` with mixed required/advisory checks
- Test helper: temporary `.claude/automation/` directory creation and cleanup

## Documentation impact

### Project documents to update

- `ai-docs/dispatch/dispatch-overview.md`: Add cross-reference to phase specs noting that Phase 1 covers F2, F3, F4, F5, F6, F7, F8, F9, F14
- Existing `/spec-review` skill documentation: document the added test strategy review layer
- Existing `/breakdown` skill documentation: document the parallel task/impl agent approach and structured task output format

### New documentation to create

- Spec schema definition file (single source of truth referenced by validator, skills, and breakdown)
- Task file schema (structure for test tasks and implementation tasks)
- `verify.yml` schema documentation with example configuration
- `config.yml` schema documentation with defaults
- Test reviewer agent definition (`.claude/agents/test-reviewer.md`)
- Brownfield development instructions — referenced docs loaded by the `/spec` and `/breakdown` skills at their respective intercept points (see below). Separate files if instructions diverge per intercept.

### Brownfield development intercepts

Agentic development in existing codebases produces technically correct code that doesn't align with what's already present — duplicate functions, half-replaced patterns, ignored abstractions. Two intercept points address this. Each is delivered as a referenced doc in `.claude/docs/` and loaded by the corresponding skill. Enforcement is guidance-only for MVP — an area for future exploration and improvement.

**Spec stage** (delivered as `.claude/docs/brownfield-spec.md`, loaded by `/spec` skill when writing technical approach):

- Search the codebase for existing code that overlaps with the proposed feature before writing the technical approach.
- Identify established patterns, abstractions, and conventions that the feature must follow. Reference specific files or modules.
- In the technical approach, distinguish what is new from what extends or modifies existing code.
- If the feature replaces existing functionality, include removal or migration of the old path in scope. Partial replacement — new code on the new pattern, old code left on the old pattern — is a defect, not a follow-up.
- If the feature duplicates functionality that already exists, stop and reconsider the approach. Prefer extending existing abstractions over introducing parallel ones.

**Breakdown stage** (delivered as `.claude/docs/brownfield-breakdown.md`, loaded by `/breakdown` skill when producing task files):

- Search the codebase for related functionality before producing task files. Map each task to specific existing files where possible.
- Each task that modifies existing code must reference files by path. Each task that creates a new file must state why an existing file is not the right location.
- When the codebase has an established pattern for the type of work a task describes, include a "follow the pattern in [file/function]" reference.
- Do not introduce new dependencies when the project already provides equivalent functionality. Search package manifests and existing imports before specifying new libraries.
- If a task would create a function, utility, or abstraction, search for existing equivalents first. Reference the search in the task instructions so the implementing agent inherits the context.

## Acceptance criteria

- **AC-01**: Pipeline state engine tracks spec progress through stages, persists state as JSON after each transition, and resumes correctly after interruption. PARKED and READY states function as specified.
- **AC-02**: Audit logger records all dispatcher actions, gate results (structured JSON), and errors as append-only entries per spec. Gate pass and rejection events are both captured.
- **AC-03**: Project configuration loads `config.yml` and `verify.yml` with layered precedence (global -> project -> spec). Cold-start detection warns on missing prerequisites without blocking.
- **AC-04**: Spec validator rejects specs that fail schema validation (missing sections, invalid AC format, missing testing strategy AC traceability) and detects injection patterns. Passes valid specs without false positives.
- **AC-05**: Review integration invokes council review via `/spec-review` and parses output for pass/fail. Failing reviews set state to PARKED with feedback attached.
- **AC-06**: Test reviewer agent validates test quality at checkpoints 1 (spec review), 2 (task review), and 3 (test code review) with pipeline-blocking authority. Each checkpoint receives only its appropriate artifacts (context isolation).
- **AC-07**: Breakdown produces test tasks and implementation tasks sequentially from context-independent Agent Teams teammates. Test task agent receives spec only. Implementation task agent receives spec plus test task output. Test tasks cover every AC. Implementation tasks reference specific test tasks as completion gates. Tasks are structured (no prose) and organized into waves.
- **AC-08**: Task reviewer runs two layers (deterministic checks, test task quality). Deterministic layer rejects tasks with structural defects. Failing review returns to breakdown with specific feedback. Agentic completeness layer deferred to Phase 2.
- **AC-09**: Verification check interface defined in `verify.yml` schema (check name, command, required/advisory, thresholds). Test hash gate script (`test-hash-gate.sh`) computes SHA-256 manifest and detects test file modifications. Execution engine deferred to Phase 2.
- **AC-10**: All components write to the audit log. Pipeline state is queryable via status command.

## Open questions

- **OQ-P1-1**: Resolved. F4 refactors the existing `spec-gate.sh` rather than introducing a new schema file. The refactored script adds injection detection (see Finding 17) and input sanitization to the existing structural validation. The `/spec` skill keeps its existing template. Both the gate script and skill template encode spec structure independently — this is accepted maintenance friction for Phase 1. A future phase should migrate both to reference a shared declarative schema to eliminate dual maintenance of spec and task layouts.
- **OQ-P1-2**: Resolved. Markdown files with YAML frontmatter. Frontmatter contains structured fields for deterministic parsing: `id`, `type` (test|implementation), `wave`, `covers` (AC identifiers), `files_to_create`/`files_to_modify`, `completion_gate`, and (for implementation tasks) `test_tasks` (references to test task IDs). Markdown body contains natural-language instructions for implementation agents. Task reviewer's deterministic layer parses frontmatter; agentic layers and implementation agents read the full file.
- **OQ-P1-3**: Resolved. Per-invocation freshness via Agent Teams. Each checkpoint invocation spawns the test reviewer as an Agent Teams teammate, which has independent context from the invoking agent and no memory of prior checkpoint evaluations. Each invocation receives only its checkpoint-specific artifact set (e.g., checkpoint 1: spec + schema; checkpoint 2: spec + task files). No prior failure context is passed — the reviewer evaluates current artifacts on their merits every time. Skills must explicitly reference Agent Teams to trigger this invocation mode.
- **OQ-P1-4**: Resolved. Separate reporting command (`/dispatch metrics`), not the audit logger. The logger appends structured JSON lines events; the reporting command reads and aggregates on demand. Metric definitions evolve independently of the logging format. Implementation deferred to Phase 3 — not in scope for Phase 1. Phase 1 deliverable: audit log uses JSON lines format to support future querying.

## Dependencies

- Existing `/spec-review` skill and council agents (architect, security, guardian, advocate, analyst)
- Existing `/breakdown` skill
- Spec schema (already defined by the existing `/spec` skill — F4 validates against it)
- Python 3 with PyYAML (`import yaml`) for YAML parsing in gate scripts and config loader
- Target project must have: test runner, linter (detected by cold-start check, not enforced)
- Claude Code Agent Teams capability (for breakdown agents and test reviewer invocations). Agent Teams is experimental but explicitly accepted as a load-bearing dependency — no fallback path is designed. If the API changes, affected subsystems (F5, F6, F7) are updated to match.
