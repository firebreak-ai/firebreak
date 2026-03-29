# Dispatch: Spec-Driven Task Pipeline for Claude Code

## Vision

Autonomous AI coding agents produce measurably worse code than humans. AI-generated PRs contain 1.7x more issues and 1.57x more security vulnerabilities than human-written PRs (CodeRabbit, 470 open-source PRs, Dec 2025). Across a broader codebase population, AI-assisted development correlates with doubled code churn (3.1% → 5.7%), ~8x growth in duplicated code blocks, and a 60% collapse in refactoring activity (GitClear, 153M+ LOC, 2020-2024). The most dangerous failure mode — silent failures where code runs but produces wrong results — is increasing. Most teams attempt to mitigate this with post-implementation gates (tests, linting, code review). Dispatch takes a different approach: it uses a structured spec-driven lifecycle (SDL) as the primary quality intervention, front-loading human judgment into structured artifacts *before* agents write any code.

The SDL workflow — structured spec authoring, multi-perspective council review, sized task breakdown with acceptance criteria — ensures that by the time an agent begins implementation, it has explicit scope boundaries, a reviewed architecture, independently verifiable acceptance criteria, and a pre-defined testing strategy. This converts the agent's role from "figure out what to build and build it" to "implement this well-defined task against these specific criteria" — a fundamentally more constrained problem where AI agents perform better.

Dispatch does not attempt to eliminate agentic coding failures. It mitigates common pitfalls and recognized failure modes while guiding developers into an AI-friendly workflow. Prevention is less costly than repair: careful spec-driven development with context-independent AI agents and deterministic checks reduces the rate at which defects are introduced, rather than relying solely on post-implementation detection.

Dispatch is a spec-driven pipeline that moves specs from queue to PR using Claude Code's native features for implementation. In v1, the developer drives stage transitions — invoking each pipeline stage, reviewing gate results, and deciding when to advance. This is the SDL workflow with deterministic and agentic gates enforced at each stage. Full automation (loop-based polling, headless skill invocation, automatic stage transitions) is a v2 goal after the workflow proves its mitigations.

The pipeline ships as context assets (skills, agents, hooks, docs) via the context-assets repository. Target projects configure their verification commands and security constraints. Dispatch does not replace human judgment — it moves human judgment to where it has the highest leverage: the beginning of the pipeline, where one good spec produces many correct implementations.

Design principles:
- **Deterministic orchestration, agentic implementation**: The dispatcher is deterministic code. Only review, breakdown, test review, and implementation stages use AI agents.
- **Least Agency**: Each pipeline stage receives the minimum autonomy, tool access, and credential scope required.
- **Tests gate code, reviewers gate tests**: Implementation is test-driven (ralph-loop iterates until tests pass). The test reviewer independently validates that tests actually verify spec requirements — preventing the silent failure mode where agents write tests that pass but don't catch regressions.
- **Native features first**: Use Claude Code's Agent Teams, ralph-loop, hooks, and tasks rather than custom alternatives.
- **Assume untrusted input**: Specs are an injection surface. The architecture treats all input as potentially adversarial.

## Architecture

### Pipeline Stages

```
Queue ─▶ Validate ─▶ Review ─▶ Breakdown ─▶ Task Review ─▶ Test Creation ─▶ Test Code Review ─▶ Implementation ─▶ Verification ─▶ PR
(file)   (det.)      (council+  (agent      (det.+agentic) (agent teams)   (agentic)           (agent teams)    (deterministic)  (det.)
                      agentic)   teams)
```

**Stage 1: Spec Queue**
File-based queue in the target project's `.claude/automation/queue/` directory. Each spec is a markdown file following a defined schema. The dispatcher polls the queue directory for unprocessed specs.

**Stage 2: Validation**
Deterministic checks before any agentic work begins. Validates spec structure against the spec schema, required fields, and input sanitization. Rejects malformed or suspicious specs. No AI involvement.

**Stage 3: Review**
Two-layer review before breakdown begins.
- *Council review*: Invokes the existing `/spec-review` skill with council agents (architect, security, guardian, advocate, analyst). Reviews the spec for architectural soundness, security concerns, completeness, and testability.
- *Test strategy review*: The test reviewer agent (context-independent — no access to the spec authoring conversation) validates the testing strategy section against the spec's acceptance criteria. Does the testing strategy cover every AC? Are test descriptions specific enough to produce concrete test tasks during breakdown? Do the proposed tests validate intended behavior rather than implementation details? Would these tests catch regressions? This is the earliest checkpoint for test quality — a weak testing strategy produces weak test tasks, which produce weak tests, which allow silent failures.

A failing review at either layer returns the spec for iteration with specific feedback. The deterministic validation gate (spec schema check) runs before either review layer.

**Stage 4: Breakdown**
Uses agent teams to compile the spec into two artifact types in parallel, both structured for AI consumption (no prose descriptions — the structure is the instruction):
- *Test task agent*: Produces test tasks from the spec's testing strategy and acceptance criteria. One task per AC or logical test group. Each task specifies: files to create, test framework conventions, AC identifiers covered, and a completion gate (tests compile and fail — they validate behavior that doesn't exist yet).
- *Implementation task agent*: Produces implementation tasks from the spec's technical approach and acceptance criteria. Each task specifies: files to create/modify (explicit paths), AC identifiers satisfied, references to the test tasks that serve as completion gate, and constraints (e.g., do not modify files outside this list, do not alter existing test assertions). Completion gate is deterministic: the referenced tests pass.

The two breakdown agents are context-independent — they share the spec artifact but not each other's reasoning or output. This extends the context-independence principle from execution back into planning.

Breakdown output includes individual task files and a `task.json` manifest in `ai-docs/<feature>/<feature>-tasks/`. The manifest is a machine-readable index of all tasks with their dependencies, wave assignments, model routing, AC coverage, and a `status` field per task (initially `not_started`). The implementation stage updates task status as agents execute (`in_progress`, `complete`, `tests_fail`, `parked`, `superseded`), enabling resume-after-interruption at the task level and pipeline observability via `/dispatch status`.

**Stage 5: Task Review**
Three-layer automated gate validating the breakdown output before any execution begins. No human approval required — the deterministic and agentic checks enforce structural and semantic correctness. The developer's last judgment opportunity is Stage 3 (spec review), where one correction prevents many downstream errors. Task-level auditing is available but optional.
- *Deterministic checks*: required fields present in each task, file paths exist in the repository, no overlapping file boundaries between tasks, every spec AC is covered by at least one task, implementation tasks reference valid test tasks as completion gates.
- *Agentic checks*: does the full set of tasks cover the spec? Are any tasks inaccurate relative to the spec's technical approach? Are there missing tasks that would leave ACs unmet? Are there gaps that would result in incomplete implementation?
- *Test task quality* (test reviewer): do the test task descriptions faithfully translate the testing strategy into concrete test specifications? Are these the right tests to write? Would they validate behavior rather than implementation details? This catches deviations between the approved testing strategy and the breakdown agent's interpretation — before any compute is spent on test-writing agents.

A failing task review returns to the breakdown stage with specific feedback on what's missing or incorrect. On pass, the pipeline advances automatically — no human gate.

**Stage 6: Test Creation**
Spawns test-writing agents via Agent Teams, one per test task. Each agent runs inside an ephemeral Docker container with:
- A clone of the repository
- Bubblewrap sandboxing inside the container
- No internet access (git remote + Anthropic API only)
- Ralph-loop for error recovery

Each agent writes tests according to its reviewed test task. Completion gate: tests compile and fail (they validate behavior that doesn't exist yet). Test-writing agents have no knowledge of implementation tasks or technical approach — they work from the testing strategy and ACs only.

**Stage 7: Test Code Review**
The test reviewer agent validates actual test code produced by Stage 6. This is the gate between test creation and implementation:
- Do implemented tests trace to spec ACs?
- Would these tests catch real regressions, or do they assert on implementation details?
- Are there ACs with no corresponding test coverage?
- Do the tests compile and fail as expected?
- Do the tests match the approved test tasks from Stage 5?

The test reviewer has pipeline-blocking authority — implementation cannot begin until test code passes review.

**Stage 8: Implementation**
Spawns implementation agents via Agent Teams, one per implementation task, organized by waves. Each agent runs inside an ephemeral Docker container with:
- A clone of the repository (including reviewed and approved test code from Stage 7)
- Bubblewrap sandboxing inside the container
- No internet access (git remote + Anthropic API only)
- Scoped credentials (PR creation, no merge)
- Ralph-loop for error recovery within each task

Implementation agents are context-independent from test-writing agents — different agents, different containers, no shared reasoning. Each task references specific tests as its completion gate. The ralph-loop iterates until the referenced tests pass. Agents do not write new tests or modify existing test assertions — their job is to make the reviewed tests pass.

Agents work in git worktrees. Implementation wave N must complete and pass verification before wave N+1 begins. Per-wave verification includes a deterministic inter-wave file reference check: parse Wave N+1's task files for declared file references (files to modify), verify each referenced file exists in the repo after Wave N completes, and verify files Wave N+1 expects to create do not yet exist. This catches file-level mismatches before Wave N+1's agents are spawned.

Agents report structured status: DONE, DONE_WITH_CONCERNS, NEEDS_CONTEXT, or BLOCKED. NEEDS_CONTEXT and BLOCKED escalate to the dispatcher for resolution or human escalation.

**Stage 9: Verification**
Deterministic verification checklist defined by the target project. Runs after each implementation wave and before PR creation:
- Fresh test execution (required) — run the full suite, check exit code, read output, verify results. No trusting previous runs.
- Linter (required) — execute linter, verify zero errors.
- Type checker (if applicable) — execute type checker, verify zero errors.
- Duplication scanner (required) — deterministic structural duplication detection (e.g., jscpd, PMD CPD). Catches copy-pasted blocks and near-identical functions with minor renaming — the most common AI duplication pattern. Configurable threshold in `verify.yml`.
- Test file immutability check (required, deterministic) — SHA-256 hash comparison of all test files against the post-Stage-7 manifest. Any modification hard-fails the pipeline.
- Assertion density check (required, deterministic) — structural validation of test code: minimum assertion count per test, no empty test bodies, no tests that only check for existence without behavioral assertions. Configurable thresholds in `verify.yml`.
- Mutation testing (required, agentic) — the test reviewer agent, spawned as a context-independent agent with access only to the spec and the implemented code, generates targeted mutations against the real implementation (flip return values, swap conditionals, remove lines, alter boundary conditions). The mutated code is run against the approved test suite. Tests that fail to detect mutations are flagged with the specific undetected mutation. Configurable mutation sample size and timeout in `verify.yml`. Pipeline-blocking: a configurable minimum mutation detection rate must be met (default TBD based on early pipeline runs).
- Test integrity check (required, advisory) — test reviewer agent verifies that implementation agents did not weaken test coverage through indirect means (e.g., adding new weaker test files, modifying test fixtures or helpers not captured in the hash manifest). Output attached to verification report.
- Code review agent (advisory — output attached to PR body, not a gate). Covers semantic duplication (differently-named functions with similar purpose but different implementation) that deterministic scanners cannot detect.
- Diff security scan (blocks secrets, CI/CD changes, unexpected dependency additions).
- Regression check (required) — verify no existing tests were broken by new implementation. Additionally, flag any modifications to existing test assertions (added, changed, or deleted) in the PR description for human review — this is the primary indicator of both contract regressions hidden by test modification and latent defect corrections that need validation.

Each check follows the fresh-verification protocol: run the command, check exit code, read full output, verify the output confirms the claim, then record the result. No check is skipped, no previous result is trusted.

**Stage 10: PR Creation**
Deterministic PR assembly. Structured PR description includes: spec summary, implementation summary, verification results, test review results, advisory code review output, and audit trail link. PR is created as draft.

### Dispatcher Architecture

The dispatcher is a shell script (or lightweight Python script) that runs on the host machine. In v1, the developer invokes each pipeline stage explicitly (e.g., `/dispatch validate <spec>`, `/dispatch review <spec>`). The dispatcher:
1. Executes the requested pipeline stage for the specified spec
2. Enforces gate checks — the stage does not advance unless gates pass
3. Manages container lifecycle for implementation stages (create, mount repo, inject credentials, destroy)
4. Tracks pipeline state in a status file per spec
5. Writes an audit log of every action taken

v2 adds automatic stage transitions: poll the queue, drive specs through the pipeline without human invocation, integrate with `/loop` for interval-based execution. This requires resolving headless skill invocation (OQ-4) and permissions management (OQ-8).

The dispatcher never runs inside a container. It has no AI capabilities — it is pure orchestration.

### Isolation Boundary

```
Host (your machine)                    Container (per task, ephemeral)
────────────────────                   ────────────────────────────────
Dispatcher script                      Cloned repository
Spec queue (read)                      Claude Code + bubblewrap
Audit log (write)                      Scoped deploy key
Pipeline state (read/write)            Network: git remote + API only
Container lifecycle management         No host filesystem access
                                       Destroyed after task completes
```

## Technology decisions

**Dispatcher**: Shell script orchestrating the pipeline. Rationale: minimal dependencies, runs anywhere Claude Code runs, easy to audit. If complexity exceeds shell's capabilities, escalate to Python with no external dependencies beyond standard library.

**Isolation**: Docker containers with bubblewrap sandboxing inside each container. Rationale: runs on any platform with Docker Engine, minimal setup for a solo developer, bubblewrap provides filesystem and process isolation within the container. Future hardening option: microVM isolation (Docker Desktop Sandboxes, Firecracker) for separate-kernel-per-agent guarantees — currently out of scope since Docker Desktop Sandboxes are macOS/Windows only and Firecracker requires Linux + KVM.

**Task queue**: File-based (markdown files in a directory). Rationale: no external dependencies, version-controlled, human-readable, works offline. GitHub Issues integration as an optional future feature, not a launch requirement.

**State tracking**: JSON status file per spec in `.claude/automation/state/`. Tracks current pipeline stage, timestamps, agent IDs, verification results, error history.

**Audit log**: Append-only log file per spec. Records every dispatcher action, agent spawn/completion, verification result, and error. Stored alongside state files.

**Cost controls**: Token budget per spec (configurable, default TBD). Circuit breaker: abort after N consecutive failures or N replans without progress (default: 2 replans per task, matching SDL workflow). Configurable max concurrent agents.

## Feature map

Features listed in dependency order. Each becomes a separate feature-level spec.

### Wave 1: Foundation (no dependencies)

**F1: Spec Queue Manager (`/queue` skill)**
Add, list, inspect, and manage specs in the queue directory. Validate spec schema on add. Show queue status and pipeline state. Pause/resume individual specs or the entire queue.

**F2: Pipeline State Engine**
Track each spec's progress through pipeline stages. Persist state as JSON. Support resume after interruption. Record timestamps, durations, error history. Pipeline states: QUEUED → stage-specific active states → PR_CREATED. Additional states: PARKED — spec requires human attention before the pipeline can continue (e.g., replan cap exhausted, gate failure needing human judgment). PARKED specs record the failed stage, failure reason, and do not block the queue or count against concurrency limits. READY — a parked spec has been reworked (typically through the `/spec` skill's iteration process) and cleared its verification gate. The pipeline resumes at the failed stage.

**F3: Audit Logger**
Append-only per-spec audit log. Record dispatcher actions, agent events, verification results, errors. Human-readable format with structured data for programmatic querying. Gate scripts emit structured JSON on both pass and rejection; the audit logger collects these raw events. The retrospective consumes gate events rather than reconstructing them from agent memory, making its "factual data" section genuinely factual.

### Wave 2: Pipeline Stages (depends on Wave 1)

**F4: Spec Validator**
Deterministic input validation before agentic processing. Validates spec structure against the spec schema (see cross-cutting: spec schema as single source of truth). Check required sections, field patterns (AC identifiers, AC traceability in testing strategy), and section-level constraints. Detect injection patterns (embedded instructions, suspicious markdown). Sanitize spec content passed to agents. The validator is the enforcement layer for the schema — it runs before every agentic stage that consumes the spec.

**F5: Review Integration**
Connect dispatcher to existing `/spec-review` skill. Parse review output for pass/fail determination. On failure: attach review feedback to spec, return to queue. On pass: advance to breakdown.

**F6: Breakdown Integration**
Spawn two context-independent breakdown agents in parallel: one produces test tasks from the testing strategy, the other produces implementation tasks from the technical approach. Both receive the spec artifact but not each other's output. All tasks are structured for AI consumption — no prose descriptions. Breakdown produces individual task files and a `task.json` manifest containing task metadata, dependencies, wave assignments, model routing, AC coverage, and per-task status tracking. The manifest is the machine-readable contract between breakdown and implementation — the gate script validates it, the implementation stage reads and updates it. Validate: test tasks cover every AC, implementation tasks reference test tasks as completion gates, no overlapping file boundaries. Breakdown fails if test tasks are not produced or if any AC lacks test coverage.

**F7: Task Reviewer**
Three-layer gate between breakdown and execution. Deterministic checks: required fields present, file paths valid, no overlapping file boundaries, every spec AC mapped to at least one task, implementation tasks reference valid test tasks. Agentic checks: task set completeness, task accuracy against spec's technical approach, gap detection, and cross-wave interface validation — Wave N+1 tasks that reference files, functions, or behaviors produced by Wave N must make assumptions consistent with Wave N's task instructions; flag assumptions that depend on implementation details Wave N's tasks do not mandate. Test task quality (test reviewer): validates test task descriptions faithfully translate the testing strategy — catches deviations before compute is spent on test-writing agents. Failing review returns to breakdown with specific feedback.

**F8: Test Reviewer Agent**
Dedicated agent persona that validates test quality against spec requirements. Context-independent — has no access to the authoring or implementing agent's reasoning, only the spec artifact and code. Invoked at four pipeline checkpoints:
- *Spec review* (Stage 3): validates the spec's testing strategy section against acceptance criteria. Does the strategy cover every AC? Are test descriptions specific enough to produce concrete test tasks during breakdown? Do proposed tests validate behavior rather than implementation details? This is the earliest and cheapest checkpoint — a weak testing strategy propagates downstream.
- *Task review* (Stage 5): validates test task descriptions faithfully translate the approved testing strategy into concrete specifications. Are these the right tests to write? This catches breakdown agent deviations before test-writing agents execute.
- *Test code review* (Stage 7): validates actual test code written by test-writing agents. Do tests trace to spec ACs? Do they compile and fail as expected? Do they match the approved test tasks? Would they catch real regressions? This gates all implementation.
- *Verification — test integrity* (Stage 9): validates that implementation agents did not weaken test coverage through indirect means.
- *Verification — mutation testing* (Stage 9): generates targeted mutations against the real implementation to measure test detection power. The test reviewer is spawned as a context-independent agent — it receives the spec and the implemented code but has no access to the test-writing agents' reasoning, the implementation agents' reasoning, or its own prior checkpoint judgments. This prevents shared blind spots between the mutation author and the agents whose work is being validated. Mutations are run against the approved (hash-verified) test suite. Tests that fail to detect mutations are flagged for human review.
- *On-demand*: invocable via `/test-review` skill independently of the dispatch pipeline.

Has pipeline-blocking authority during dispatch at all five in-pipeline checkpoints — spec review does not pass with a weak testing strategy, task review does not pass with unfaithful test tasks, implementation cannot begin until test code passes review, verification fails if tests were modified during implementation, and verification fails if test detection power falls below the configured mutation threshold.

Brownfield mode (project without prior SDL specs): derives requirements from existing code, flags derived requirements for human confirmation before using them as test review criteria. Does not treat code-derived intent as ground truth.

**F9: Verification Engine**
Execute project-defined verification checklist (`verify.yml`). Each check follows the fresh-verification protocol: run the command, check exit code, read full output, verify the output confirms the claim. Aggregate results. Hard-fail on required checks (tests, linter, type checker, duplication scanner, test review, regression check), capture advisory output (code review). Produce verification report for PR body. The checklist supports pluggable check tools — projects configure which scanners to run in `verify.yml`. Duplication scanning is a recommended default.

### Wave 3: Execution (depends on Wave 2)

**F10: Container Manager**
Lifecycle management for ephemeral Docker containers. Create container, clone repo, inject scoped credentials, configure network restrictions (git remote + Anthropic API only), apply bubblewrap sandboxing. Destroy after task completion. Health monitoring and timeout enforcement.

**F11: Agent Orchestrator**
Spawn Claude Code Agent Teams inside containers. Manage the two execution phases: test creation (Stage 6) and implementation (Stage 8), with the test code review gate (Stage 7) between them. Test-writing agents and implementation agents are context-independent — different agents, different containers, no shared reasoning. Implementation agents receive the repo with reviewed and approved test code; their completion gate is deterministic (referenced tests pass). Implementation agents do not write new tests or modify existing test assertions. Manage implementation waves (wave N completes before wave N+1). Enforce replan cap (2 per task). Agents report structured status (DONE / DONE_WITH_CONCERNS / NEEDS_CONTEXT / BLOCKED). NEEDS_CONTEXT and BLOCKED escalate to the dispatcher. Escalate to human on repeated failure.

**F12: PR Assembler**
Create structured PRs from completed implementation. Compose PR description from spec summary, implementation notes, verification results, test review results, and code review advisory output. Create as draft PR.

### Wave 4: Orchestration — v2 (depends on Wave 3)

**F13: Dispatcher (`/dispatch` skill)**
Top-level orchestrator that runs the post-review pipeline autonomously. The developer's workflow: author a spec with `/spec`, review with `/spec-review`, iterate until satisfied, then invoke `/dispatch <feature-name>` to signal "take it from here." The dispatcher drives breakdown (S4) → task review (S5) → test creation (S6) → test code review (S7) → implementation (S8) → verification (S9) → PR (S10), enforcing all deterministic and agentic gates automatically. The pipeline parks only on gate failure or re-plan cap exhaustion — not for human approval at intermediate stages. The developer's last judgment call is spec review (S3); after `/dispatch`, the pipeline is autonomous.

v1: invoke `/dispatch` after spec review passes. The dispatcher calls existing skills (`/breakdown`, `/implement`) in sequence, advancing on gate pass and parking on failure. v2 adds: poll queue, select next spec, manage concurrency, integrate with `/loop` for interval-based execution.

**F14: Project Configuration**
Schema and validation for `.claude/automation/config.yml` and `verify.yml`. Sensible defaults. Configuration documentation. Cold-start detection: warn when a project lacks prerequisites (test suite, linting, CLAUDE.md). Optional baseline capture: a command that snapshots current project metrics (test pass rate, duplication score, churn rate from git history) before the first spec enters the pipeline. Not a gate — baseline data requires sustained use across real projects to be meaningful. Stored alongside project config for later comparison.

### Wave 5: Autonomy — v2 (depends on Wave 4)

**F15: Full-Auto Mode**
Opt-in per-project configuration for autonomous merge after verification passes. Additional safety gates: require N consecutive successful PRs before enabling, auto-disable on first regression, configurable cooldown between merges. Requires explicit per-project activation — never enabled by default.

**F16: Notification and Escalation**
Notify humans on: pipeline failures, repeated replan attempts, security scan findings, queue completion. Escalation policy: configurable channel (stdout, file, webhook). In full-auto mode: notify on every merge.

## Cross-cutting concerns

**Security model**: Least Agency applied per pipeline stage. Validation stage: no agent access. Review/breakdown stages: read-only repo access. Implementation stage: write access to repo clone in isolated container, no host access. PR stage: scoped git credentials for PR creation only. Credential requirements: the pipeline requires minimum necessary git permissions — read/write contents and pull request creation only. Merge access, workflow dispatch, and org-level permissions are incompatible with the pipeline's security model regardless of how git access is configured (deploy key, fine-grained PAT, GitHub App, SSH key, etc.). The Anthropic API key is the developer's own key (acceptable for solo-developer scope). Specific credential mechanisms are defined in feature-level specs as they vary by user environment. See `ai-docs/dispatch/research/research-findings.md` for detailed threat model and incident history.

**Error handling**: Every pipeline stage can fail. Failures are recorded in state and audit log. Deterministic stages (validation, verification) fail fast. Agentic stages (review, breakdown, implementation) use capped retries (2 replans). When retries are exhausted or a failure requires human judgment, the spec moves to PARKED with the failure reason and failed stage recorded. The user iterates on the spec (typically via `/spec`) to address the failure. When the spec passes its verification gate, it transitions to READY and the pipeline resumes at the failed stage.

**Configuration layering**: Global defaults in the dispatch harness → project-level overrides in `.claude/automation/config.yml` → per-spec overrides in spec frontmatter. More specific wins.

**Idempotency**: The dispatcher can be interrupted and resumed safely. Pipeline state is persisted after each stage transition. Re-running a failed stage does not duplicate work (agent teams are spawned with deterministic IDs tied to spec + stage + attempt).

**Cost management**: Token budget per spec. Circuit breaker on runaway loops. Configurable concurrency limit. Cost tracking in audit log (tokens consumed per stage).

**Pipeline observability**: Gate scripts emit structured JSON on every pass and rejection. The audit logger (F3) collects raw gate events; the retrospective summarizes them per run. This data serves **pipeline self-improvement** — identifying which gates add value, which are ceremony, where re-plans concentrate, and what failure types recur. It does not measure code quality. Code quality outcomes (post-merge defect rates, maintainability over time, regression frequency) are external to the pipeline and require longitudinal human assessment. The optional baseline capture in F14 provides a pre-pipeline snapshot for later comparison, but meaningful quality evidence requires sustained use across real projects — not pipeline-internal metrics. Three operational metrics are tracked from the first pipeline run: (1) gate rejection rate per stage — which stages catch problems and which are ceremony; (2) cost-per-AC — total pipeline cost divided by acceptance criteria satisfied; (3) replan concentration — which stages and task types trigger replans, including inter-wave replan frequency to detect whether wave-boundary integration failures warrant additional contract checking mechanisms.

**Regression model**: Two distinct regression types require different mitigations:
- **Contract regression**: A new change breaks existing correct code. Existing tests fail. Mitigated by CI (tests must pass before and after) and a deterministic check flagging modifications to existing test assertions — an agent that changes tests to match broken code instead of fixing the code is the primary attack vector.
- **Latent defect exposure**: Previously shipped code deviates from intended behavior but passes its own AI-written tests. A later change interacts with the incorrect code and exposes the bug. Existing tests fail, but the test itself may be wrong. Mitigated primarily through prevention: spec-driven development defines intended behavior independent of existing code, and the test reviewer validates tests against the spec rather than the implementation. Context-independent agents (the test reviewer has no access to the implementing agent's reasoning) reduce the chance of shared blind spots. The pipeline reduces the rate of latent defects but cannot eliminate them — pre-existing technical debt and specs where the oracle problem slips through remain risks.

**Spec schema as single source of truth**: A machine-readable spec schema defines the required sections, structural validation rules (e.g., AC identifier pattern, testing strategy AC traceability), and section-level constraints. This schema is the single source of truth referenced by: the `/spec` skill (to scaffold and validate specs), the deterministic validation gate (to enforce structure before council review), the `/spec-review` skill (to verify structural prerequisites before invoking agents), and the breakdown stage (to locate ACs, testing strategy, and technical approach). The schema lives in a single location; the spec authoring guide (`feature-spec-guide.md`) provides authoring instructions but does not define structure. Changes to the spec template propagate through one file — the schema — rather than requiring updates across multiple skills and gate scripts.

**Existing SDL workflow integration**: Dispatch uses the existing `/spec-review`, `/breakdown`, and `/implement` skills rather than reimplementing them. The dispatcher is orchestration glue, not a replacement. Existing SDL skills will need to reference the spec schema for structural validation, replacing any hardcoded structural assumptions.

**Brownfield awareness**: Agentic development in existing codebases produces technically correct code that doesn't align with what's already present — duplicate functions, half-replaced patterns, ignored abstractions. The pipeline intercepts this at two points: (1) **Spec stage** — the `/spec` skill loads brownfield instructions when writing the technical approach, requiring codebase survey for overlapping functionality, identification of existing patterns and conventions, and explicit distinction between new code and extensions to existing code. Partial replacement of existing patterns is treated as a defect, not a follow-up. (2) **Breakdown stage** — the `/breakdown` skill loads brownfield instructions when producing task files, requiring tasks to reference existing files by path, justify new file creation, include pattern references, and search for existing equivalents before introducing new functions or dependencies. Instructions are maintained as referenced docs, separate per intercept point if they diverge.

**Test-driven implementation**: Test quality is validated at five in-pipeline checkpoints: the testing strategy is reviewed during spec review (Stage 3), test task descriptions are validated against the strategy during task review (Stage 5), actual test code is reviewed after test creation (Stage 7), test integrity is verified after implementation (Stage 9), and mutation testing measures test detection power against the real implementation (Stage 9). This five-checkpoint model — test strategy gates the spec, test tasks gate execution, test code gates implementation, test integrity and mutation detection gate the PR — directly addresses the silent failure problem where agents write tests that pass but don't validate behavior. The mutation testing checkpoint closes the oracle gap: the test reviewer validates that tests *look correct*, mutation testing validates that tests *have detection power*. Correct tests are the primary mechanism for avoiding agentic coding failure modes; ensuring test correctness at every stage is the pipeline's highest-leverage quality intervention.

**Test file immutability**: After Stage 7 approval, a deterministic gate script (`test-hash-gate.sh`) computes SHA-256 hashes of all test files and writes a manifest (`ai-docs/<feature>/test-hashes.json`). During per-wave verification in Stage 8 and before Stage 9, the script re-computes hashes and compares against the manifest. Any modification hard-fails the pipeline — no agentic judgment involved. The agentic test integrity check at Stage 9 remains as an advisory layer that can catch semantic weakening (e.g., an agent that creates a new weaker test file rather than modifying an existing one). The deterministic hash is the hard gate; the agentic check covers edge cases the hash cannot detect.

**Testing philosophy**: The pipeline's deliverables are primarily context assets (skills, agents, docs) with deterministic code artifacts (gate scripts, state engine, config loader, dispatcher). The testing strategy reflects this distinction across all phases:

- **Tier 1 — Automated tests for deterministic code**: Gate scripts, state engine transitions, config loading, queue operations, and other code artifacts get real tests with fixture files. These can run in CI.
- **Tier 2 — Validated through pipeline operation**: Context asset behaviors (skill prompts, agent definitions) cannot be unit-tested because their output is natural language evaluated by other agents or humans. They are validated by running real specs through the pipeline and observing results. Persistent failures indicate the context assets need prompt iteration, not code changes.
- **Tier 3 — Framework effectiveness (longitudinal)**: Whether the pipeline produces better code than unstructured agentic coding, which gates catch real problems vs. add ceremony, and where replans concentrate. Measured over sustained use via audit log data and `/dispatch metrics`.

Each phase spec classifies its tests by tier. Phase specs do not list Tier 2 behaviors as automated tests — they identify the pipeline operation that validates them and the iteration mechanism (prompt refinement) that fixes them.

**Agent status protocol**: Implementation agents report structured status (DONE / DONE_WITH_CONCERNS / NEEDS_CONTEXT / BLOCKED) rather than unstructured output. DONE_WITH_CONCERNS requires the dispatcher to evaluate concerns before advancing. NEEDS_CONTEXT and BLOCKED escalate — the dispatcher provides additional context or escalates to the human. This prevents agents from silently proceeding through ambiguity.

**Model selection**: Use the least capable model sufficient for each role to control cost. Mechanical tasks (single-file changes with clear specs) use fast, cheap models. Integration tasks (multi-file coordination) use standard models. Architecture, review, and test review tasks use the most capable model. Model selection is configurable per pipeline stage in project configuration.

## Open questions

**OQ-1: Spec schema design.** What required fields should a dispatch-compatible spec contain? Minimum viable: title, description, acceptance criteria. Should it match the SDL feature spec format exactly, or use a lighter schema?

**OQ-2: Token budget defaults.** What's a reasonable per-spec token budget? Anthropic's C compiler spent ~$20K total across 2,000 sessions. A single feature PR is much smaller. Need to establish baseline costs through early testing.

**OQ-3: GitHub Issues integration scope.** Is GitHub Issues integration a launch requirement or a future feature? CCPM uses it as the primary queue. Our file-based queue is simpler but doesn't integrate with existing project management.

**OQ-4: How does the dispatcher invoke existing SDL skills?** The existing skills (`/spec-review`, `/breakdown`, `/implement`) are interactive Claude Code skills. The dispatcher needs to invoke them non-interactively. Options: (a) refactor skills to support headless invocation, (b) use `claude -p` with skill-equivalent prompts, (c) extract shared logic into scripts callable by both skills and dispatcher. Note: this gates full automation between pipeline stages. The pipeline provides value with human-triggered stage transitions; headless invocation is an optimization, not a prerequisite for the pipeline design.

**OQ-5: Cold-start requirements.** What minimum project infrastructure is required? Proposed: test suite, linting config, CLAUDE.md. Should the dispatcher detect and report missing prerequisites, or refuse to run?

**OQ-6: Diff security scan scope.** What patterns should the pre-commit security scan check? Proposed: secrets/credentials, CI/CD file modifications, new dependency additions, file modifications outside allowed paths. How strict should the default be?

**OQ-7: Notification channel for escalation (v2).** stdout? File? Desktop notification? Webhook? In v1, the developer sees gate results directly. Notifications become relevant when the pipeline runs stages automatically.

**OQ-8: Permissions management for headless execution.** Several SDL workflow steps (especially council review, which spawns multiple agents that read files, grep, and run bash) trigger interactive permission prompts. These prompts cannot be answered in headless mode, blocking the pipeline. Options: (a) run the dispatcher with `--dangerously-skip-permissions` and compensate with hooks and container isolation (Trail of Bits pattern), (b) configure allowlists in `.claude/settings.json` that pre-approve the specific tools and paths the SDL workflow uses, (c) restructure the SDL skills and their working directories so their operations fall within already-permitted scopes, (d) some combination. The goal is to eliminate interactive prompts for known-safe workflow operations without broadly disabling the permission system. This may require updates to existing context assets (skills, agents) and the directories they read/write. Note: like OQ-4, this gates full automation. Human-triggered stage transitions bypass this problem entirely.

**~~OQ-9~~ Resolved: Spec complexity vs. pipeline effort.** Single tier. The spec template and pipeline stages are fixed — they are the quality intervention, not overhead. Each stage naturally scales its effort to match the spec's complexity: council uses quick mode (3 agents) for focused fixes, breakdown produces one task instead of many, test review validates fewer tests, implementation uses a single agent. A simple fix uses the same 9-section spec template with shorter content per section. The stages don't change; the time spent at each stage does. This matches how good engineers work — they don't skip review for small changes, they spend less time on review.

## Implementation Phases

The Dispatch pipeline is being implemented in phases:

**Phase 1** establishes the pipeline core — spec validation, review integration, breakdown, task review, test creation, test code review, implementation, and verification stages with deterministic and agentic gates.

**Phase 1.5** enhances core capabilities — test quality validation with dedicated test reviewer agent, integration seam coverage improvements, and corrective workflow for remediation of failing specs and broken tasks.

**Phase 1.6** (code review and remediation) adds `/code-review` — adversarial code review with Detector/Challenger agents producing verified findings and optional remediation specs.
