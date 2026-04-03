# Agent Harness Patterns: Insights for Firebreak

Source: [Effective Harnesses for Long-Running Agents](https://www.anthropic.com/engineering/effective-harnesses-for-long-running-agents) — Anthropic Engineering, 2025.

## Context

Anthropic's engineering team studied how to make AI agents effective across long-running, multi-session tasks. Their core finding: agents need structured external state to maintain coherence and constrained interfaces to prevent common failure modes. They built a two-agent architecture (initializer + coding agent) with a startup checklist, a structured feature list, progress files, and git-based checkpointing.

This analysis compares their empirical findings against Firebreak's design and identifies actionable improvements.

## Validated design bets

These Firebreak design decisions are independently supported by the article's empirical results.

### Structured artifacts as the primary quality lever

The article's most effective intervention was a structured JSON feature list that agents could only modify by flipping a `passes` field — not editing descriptions or steps. This constrains the agent's role from "figure out what to build" to "implement this well-defined thing." Firebreak's spec-driven approach codifies this architecturally; the article arrived at it empirically.

### Immutable boundaries

The article's "only edit the `passes` field" constraint prevented feature scope creep and documentation loss. Firebreak generalizes this with test file immutability (SHA-256 hash manifests after Stage 7). The underlying insight: agents silently modify artifacts that should be fixed reference points unless modification is mechanically impossible.

### Context-independent specialized agents

The article raises "specialized multi-agent architectures" as a future direction. Firebreak has already committed to this — separate agents for test writing, implementation, and review, each context-independent. The article's experience with a single general-purpose agent struggling with breadth of concerns suggests this is the right call.

### Git as checkpoint infrastructure

Both systems use git commits as recovery points. The article's coding agent commits after each feature to enable reverting problematic code. Firebreak's wave-based implementation with per-wave verification serves the same purpose at finer granularity.

### Testing as the critical gate

The article found agents would mark features done without proper testing and needed explicit prompting for end-to-end verification. Firebreak's five-checkpoint test validation model is an aggressive response to exactly this failure mode. The article validates that the concern is real, not theoretical.

## Actionable improvements for Firebreak

### 1. Agent-side startup verification

**Finding**: The article's most practical pattern is a deterministic startup sequence per agent session — read progress, verify the environment still works, *then* begin new work.

**Gap**: Firebreak's implementation agents receive a task file and a repo clone, but the overview doesn't describe a per-agent startup verification step. The inter-wave file reference check (Stage 8) is a dispatcher-side check, not an agent-side one.

**Recommendation**: Add to implementation agent instructions: before writing code, verify prerequisites compile/run and existing tests pass. This catches environment issues the dispatcher's structural checks miss (e.g., a dependency that installs but fails at runtime, a prior wave's output that compiles but doesn't behave as expected).

**Implementation status**: Implemented in Phase 1.5: per-task readiness check in implementation-guide.md and codebase-grounded compilation in task-compilation.md.

### 2. Task traceability in the manifest

**Finding**: The article's `claude-progress.txt` pattern solves context-window exhaustion: agents write a self-briefing document updated after each meaningful step, so the next session (or a resumed session) can pick up where it left off.

**Revised assessment**: Early pipeline testing shows that structured retrospectives (written after feature completion) and git commit history within worktrees already cover the debugging and audit use cases the original recommendation targeted. A per-step changelog written by the agent during execution would be largely redundant with both.

**Recommendation**: Extend the task manifest (`task.json`) with lightweight traceability fields:

- `worktree`: path to the git worktree used for the task.
- `last_commit`: SHA of the agent's most recent commit.

These are cheap, useful for traceability, and sufficient for the dispatcher to manage worktree lifecycle and verify task completion.

The original recommendation also included a per-step `changelog` array for mid-task resume. Early testing (zero re-plans across initial features) suggests mid-task failure is less common than anticipated when upstream gates are working well. More importantly, the cleanest recovery from a mid-task failure is often to revert to the last commit and retry — fixing the task spec or agent instructions so the agent succeeds on the next attempt, rather than trying to resume or repair a partially-completed implementation. This "revert and improve upstream" pattern is consistent with the pipeline's core philosophy: front-load quality into structured artifacts so agents do the right thing on the first try, rather than iterating on whatever the agent does wrong. If mid-task failures become a significant problem in later testing (complex tasks, context window exhaustion), the changelog can be reconsidered — but the default recovery strategy should be revert-and-retry with improved instructions.

### 3. Explicit test granularity guidance

**Finding**: The article found agents would pass unit tests but fail end-to-end verification. Browser automation (Puppeteer) was needed to catch the gap between "tests pass" and "feature works."

**Gap**: Firebreak's testing philosophy addresses test quality (behavioral assertions, mutation testing) but doesn't explicitly address the unit-vs-integration test spectrum. LLMs naturally produce unit tests. Unit tests can pass without the feature working in context.

**Recommendation**: The spec template's testing strategy section should require explicit decisions about test granularity — pushing toward integration/behavioral tests over isolated unit tests. The test reviewer checkpoints (Stages 3, 5, 7) should evaluate whether test granularity matches the acceptance criteria's scope. An AC about user-visible behavior needs an integration test, not a unit test on an internal function.

**Implementation status**: Implemented in Phase 1.5: two-tier test reviewer enforcement model in test-reviewer.md, user verification steps and integration seam declarations in feature-spec-guide.md.

### 4. "Verify before you build" at every level

**Finding**: The article's startup checklist begins with "verify fundamental features still function" before starting new work. This applies verification at session start, not just pipeline end.

**Gap**: Firebreak's fresh-verification protocol runs at Stage 9. The inter-wave check validates file existence but not behavioral correctness.

**Recommendation**: After Wave N completes and before Wave N+1 agents start, run the full existing test suite (not just Wave N's new tests) to confirm the repo is in a working state. If Wave N broke something, catch it before Wave N+1 agents start building on a broken foundation. This is a dispatcher-side check that strengthens the inter-wave boundary.

**Implementation status**: Implemented in Phase 1.5: inter-wave baseline-snapshot regression check in implementation-guide.md.

### 5. Premature completion in agentic stages

**Finding**: The article's #1 failure mode was agents declaring they were done when they weren't.

**Gap**: Firebreak mitigates this in implementation (deterministic completion gates — referenced tests must pass), but the failure mode can still manifest in agentic stages: a review agent declaring a spec "good enough," a breakdown agent producing incomplete task coverage, or an implementation agent reporting DONE when tests pass but end-to-end behavior is broken.

**Recommendation**: Treat AC coverage checks as load-bearing infrastructure, not ceremony. For agentic stages without deterministic gates (review, breakdown), consider adding a deterministic "completeness check" layer that validates structural coverage independent of the agent's self-assessment.

**Implementation status**: Implemented in Phase 1.5: Tier 2 behavioral completeness 'show your work' requirement in test-reviewer.md.

## Structural divergence

The article optimizes for a single agent working incrementally across many sessions on one codebase. Firebreak optimizes for many specialized agents working in parallel on one feature. These are different coordination problems:

- **Article's challenge**: Temporal continuity (memory across sessions).
- **Firebreak's challenge**: Spatial coordination (multiple agents touching the same codebase simultaneously).

The article doesn't address the spatial problem. Firebreak's wave structure and file-boundary constraints solve a problem the article hasn't encountered. The coordination patterns don't transfer directly, but the failure-mode thinking does: wherever agents have autonomy, they find ways to silently fail, and mitigations need to be mechanically enforced, not instruction-based.

## Future exploration: Lead agent for cross-task coordination

**Status**: Deferred — not an MVP feature. Requires failure data from real pipeline runs to validate the need and inform the design.

### The problem

When an implementation agent's tests fail, the ralph-loop retries. This is where agents are most likely to break constraints — editing files outside their boundary, making architectural decisions beyond their scope, or thrashing without progress. The test immutability hash catches test modifications, but file boundary violations during retry are harder to gate deterministically.

The most compelling case is cross-task dependency failures within a wave: Agent A's output doesn't match what Agent B's tests expect. Neither agent has visibility into the other's work, and neither can diagnose the root cause alone.

### The pattern: advisory lead agent

Rather than peer-to-peer communication between implementation agents (which blurs the informative/instructional boundary — agents treat all context as relevant), introduce a single "lead dev" agent that runs on Opus with:

- **Read access to the full feature spec** — broader context than any task agent has.
- **Read access to all task changelogs** — cross-task visibility into what each agent has done.
- **Read access to current test output** — can see what's failing and where.
- **No write access to code** — it advises, it doesn't implement.

This mirrors how a human dev team operates: junior devs write most code, a senior/lead helps when they hit problems. The authority relationship is directed (escalation up, guidance down), not lateral, which avoids the peer communication risks.

Implementation agents would escalate to the lead agent when ralph-loop retries fail. The lead agent reads changelogs and test output, identifies cross-task conflicts or misaligned assumptions, and provides targeted guidance back to the struggling agent — which still makes its own changes within its own file scope.

### Why defer

The complexity cost is significant: a new agent role with its own prompt and authority model, a communication protocol, state management for the lead's context, and dispatcher logic for when to spawn it. More importantly, we don't yet know the failure distribution:

- How often do implementation agents fail after 2 retries?
- What fraction of failures are cross-task dependency issues (where the lead agent helps) vs. single-task bugs (where ralph-loop is sufficient) vs. spec/breakdown quality problems (where the fix is upstream)?
- How often do agents violate file boundaries during retry?

The per-task changelogs added in recommendation #2 are a prerequisite for this feature — they're what the lead agent would read. Build the data layer now, collect failure data from real pipeline runs, and revisit when the data shows whether cross-task coordination failures are a significant source of pipeline parks.

### Design constraints if implemented

- The lead agent must be advisory only — no code writes, no test modifications.
- Implementation agents retain autonomy within their file boundaries; the lead provides analysis, not patches.
- The lead agent should be spawned on-demand (when an agent escalates), not running continuously.
- Communication should be structured (not free-form chat) to limit context bleed.
- If the lead agent cannot resolve the issue, the task parks — the lead does not override pipeline gates.

## Future exploration: Pipeline self-improvement loop

**Status**: Deferred — design direction for after phase 1 results are available. The data collection infrastructure (audit log, gate events, changelogs) is being built now; the feedback loop consumes that data.

### The opportunity

The Anthropic Skill Creator guide ([The Complete Guide to Building Skills for Claude](https://resources.anthropic.com/hubfs/The-Complete-Guide-to-Building-Skill-for-Claude.pdf)) describes an iterative improvement workflow for agent skills: observe behavior, identify failures, refine prompts, re-test. Anthropic acknowledges this is currently human-driven — autonomous self-improvement is a stated future direction, not a shipped capability.

Applying this pattern to Firebreak is harder because the pipeline's ultimate output is code, and code quality (bugs, maintainability, design adherence) is notoriously difficult to measure without sustained human effort. But the pipeline generates rich structured data about its own operations that is measurable and actionable.

### Layered approach

**Layer 1 — Pipeline operations (tractable now):** The audit log and gate scripts emit structured JSON on every pass and rejection. Pattern analysis across runs can identify systematic weaknesses and drive prompt improvements to specific pipeline stages. This layer is self-validating: if a prompt change reduces the rejection rate at a specific gate, the improvement is confirmed without human judgment.

Signals available for automated analysis:

- **Gate rejection patterns**: If the spec gate consistently rejects specs for the same structural issue, the `/spec` skill's instructions need to address it more prominently. The pattern detection is automatable; the prompt fix is a targeted edit.
- **Replan concentration**: If implementation agents consistently fail on a specific task type, that's a signal about breakdown quality — the `/breakdown` skill's instructions can be refined to decompose those tasks differently.
- **First-attempt pass rate**: Tests always pass on first try → tests may be too weak. Tests never pass within the replan cap → tasks may be under-specified. Either signal points to a specific upstream stage.
- **Cost-per-AC trending**: Rising cost across runs indicates degradation. Falling cost indicates process improvements are working.
- **Permissions prompt frequency**: Unnecessary permissions prompts indicate the pipeline's tool access configuration is too restrictive. Capture every user-facing permissions prompt with the stage, tool, and path that triggered it. Use this data to iteratively tune `.claude/settings.json` allowlists so that known-safe workflow operations are pre-approved and the user is only prompted when genuine judgment is needed. This directly addresses OQ-8 from the dispatch overview — reducing interactive prompts is a prerequisite for full automation, and the path there is incremental, data-driven tuning rather than a blanket `--dangerously-skip-permissions`.

The feedback loop: run pipeline → collect gate/audit data → analyze patterns across recent runs → propose specific prompt/instruction/config changes → human approves → iterate. A retrospective agent can automate the analysis step, producing a structured report after each pipeline completion or failure.

This loop has a useful property: it converges. Improvements are measurable (rejection rate drops, cost decreases, fewer replans), so you know when to stop iterating on a specific issue.

**Layer 2 — Deterministic quality proxies (automatable, imperfect):** Metrics correlated with code quality, trackable across runs:

- Duplication score trending (are agents producing less copy-paste?)
- Mutation detection rate (are tests catching real bugs?)
- Assertion density (are tests substantive?)
- Cyclomatic complexity (are agents producing simpler code?)
- Linter violations per run

None is ground truth for code quality, but consistent movement in the wrong direction is an early warning signal.

**Layer 3 — Code quality feedback (future):** Whether the code actually does what the spec intended, whether it's maintainable over time, whether subtle bugs exist — these traditionally require post-merge human review or production-time signals (bug reports, incident rates, churn over months). The architecture doesn't foreclose on adding this layer later: structured feedback could flow into prompt refinements the same way gate rejection data does in Layer 1.

One avenue worth exploring: a context-independent code review agent that follows the same isolation pattern as the test reviewer — separate agent, separate persona, no access to the implementing agents' reasoning, reviewing only against the spec and the produced code. This would be similar to Anthropic's subscription-based code review agent but integrated into the pipeline, with its review output captured as structured quality data for the self-improvement loop. The review agent's findings (design adherence issues, convention violations, semantic problems that deterministic tools miss) would feed back into upstream prompt refinements. This doesn't fully solve the oracle problem — an AI reviewer can still share blind spots with AI implementers — but the context independence mitigates correlated failures, and the structured output is more actionable for iteration than unstructured human feedback. This is an idea to explore once Layer 1 and Layer 2 data establish a baseline, not a commitment.

### Why this ordering matters

Layer 1 delivers measurable improvements now with existing infrastructure. It reduces token spend and likely improves code quality indirectly — a pipeline that produces better-scoped tasks and stronger tests is producing better code. Layer 2 adds automated quality signals without requiring human effort. Layer 3 waits until either the methodology matures or enough pipeline runs have accumulated to make longitudinal human assessment meaningful. Each layer is independently valuable and doesn't depend on the layers above it.

## Retrospective evidence

The SDL workflow has been tested through a complete greenfield project including a corrective bug-fix cycle: 13 features (10 original + 3 corrective), ~80 tasks, 137 tests, zero formal re-plans. Each feature implementation produces a structured retrospective that captures per-task results, upstream traceability, failure attribution, and notes on unexpected behavior.

### What the retrospectives show

### Validation evidence

- **Zero formal re-plans across ~80 tasks**: Every implementation task across 13 features passed on first attempt after upstream gates completed their work. Five team-lead interventions occurred (1-line fixes for import mismatches, module type declarations, and test calibration) but none required formal re-plans. This is strong evidence that front-loading quality into structured artifacts before implementation reduces the need for corrective iteration.
- **Spec review as design improvement, not just validation**: In multiple features, the council review actively simplified designs before implementation — reducing complex subsystems to straightforward patterns by flagging over-engineered approaches, resolving ownership ambiguities, and suggesting cleaner interfaces. These simplification cascades reduced implementation complexity downstream, making agent tasks easier to execute correctly. The review is demonstrating value beyond "catching problems" — it's improving the design.
- **Forward-referencing in specs validated across features**: Early spec reviews required specific code organization patterns (e.g., keeping related logic in cohesive blocks for future extraction). Multiple features later, those patterns enabled clean refactoring — code that was designed for future modification was successfully modified without rework. This validates brownfield-aware spec design as a practical technique, not just a principle.
- **Model routing validated and cost-effective**: The "least capable model sufficient for the role" strategy is working. Well-specified single-file tasks reliably succeed at the cheapest model tier. Complex tasks (state machines, refactoring across multiple files, multi-system integration) route to higher-capability models and also succeed on first attempt. The routing correctly matches task complexity to model capability, saving cost on simple tasks without sacrificing quality on complex ones. Zero escalations were needed across the entire project.
- **Test reviewer consistently adding value**: The test reviewer checkpoint caught missing integration tests in multiple features, resulting in additional test tasks being added before implementation began. Without this checkpoint, subsystem wiring would have gone untested in at least one feature. The test reviewer is the most consistently productive quality checkpoint in the pipeline.
- **Breakdown gate stabilizing over time**: Early features required 2-3 gate attempts before passing (structural issues in task frontmatter). Later features consistently pass on first attempt, demonstrating that the workflow improves through use — either through skill instruction refinement or improved spec quality feeding better breakdowns.
- **Backward compatibility maintained automatically**: When later features modified files created by earlier features, implementation agents preserved existing interfaces by using default parameters and maintaining test compatibility. No existing tests were modified to accommodate new functionality — the regression model worked as designed.
- **E2E tests validating real behavior**: After the e2e testing infrastructure was added (see improvement findings below), subsequent features are confirmed working in real browser environments, not just mocked test environments. This closes the gap between "tests pass" and "feature works."
- **Agent autonomy producing valid optimizations**: Implementation agents sometimes proactively execute later-wave tasks when dependency analysis permits, compressing the execution timeline. These optimizations have succeeded without issues so far — data that will inform the lead agent design if pursued.

### Improvement findings

- **All bugs occurred at integration seams**: Every bug discovered in the project existed at the boundary between correctly-implemented modules — the orchestrator file that wires all modules together. Unit tests mock across these seams. The pattern is clear: the orchestrator is the highest-risk file and needs end-to-end verification, not just unit tests of individual modules.
- **Smoke tests masquerading as behavioral tests**: The original e2e tests checked "no errors" — a negative assertion pattern that passes on a completely non-functional application. The test reviewer accepted "handled without errors" as behavioral coverage, which it isn't. The spec's non-goals conflated game logic (algorithms) with observable behavior (the application works). Four new test reviewer evaluation criteria are needed: behavioral completeness, silent failure detection, integration seam coverage, and test-level adequacy. **Implemented in Phase 1.5**: two-tier test reviewer enforcement model and behavioral completeness 'show your work' requirement added to test-reviewer.md.
- **Human spec review cannot be skipped**: The e2e spec was accepted without meaningful human review as a deliberate test. The downstream pipeline executed flawlessly against a flawed spec — every gate passed, every task succeeded, every test ran green. The application didn't work. This is the strongest evidence that the pipeline's quality depends on the spec, and the spec depends on human judgment.
- **Compilation gaps between independently-compiled tasks**: A recurring pattern: tasks compiled independently make incompatible assumptions about shared interfaces — import/export conventions, module type declarations, key string conventions, and rendering path conventions. Five bugs were traced to specific tasks where a compilation gap was introduced. Improvement: task instructions should explicitly state interface contracts when a task references or creates files that other tasks depend on.
- **Gate invariant doesn't fit all feature types**: The task reviewer requires every AC to map to both a test task and an implementation task. Testing infrastructure features (where tests are the product) and bugfix features (where tests already exist) require workarounds. Improvement: add feature type flags that relax this constraint for corrective work. **Implemented in Phase 1.5**: feature type flags added to task-reviewer gate to relax this constraint for corrective work.
- **Full ceremony is overhead for mechanical fixes**: A 15-line code fix went through full spec → council review → test reviewer → breakdown → team implementation in ~2 hours. An identical-class fix applied via fast-track took 15 minutes with the same output quality. The ceremony's value for mechanical fixes is concentrated in test design review, not fix design. When the root cause is known, the fix pattern is validated, and no design decisions are involved, fast-track is appropriate. **Implemented in Phase 1.5**: corrective workflow formalized in corrective-workflow.md with explicit fast-track eligibility criteria.
- **Spec precision on technical values**: Specs occasionally use conceptual shorthand for technical values (e.g., a human-readable key name vs. the actual runtime key code). One bug was directly caused by this — the spec used a conceptual key name that didn't match the runtime convention. Improvement: spec template guidance on using precise, runtime-accurate values.
- **Undeclared file creation**: Implementation agents occasionally produce files not declared in the task breakdown when they encounter environment-specific requirements. The retrospectives capture these deviations with root cause analysis, feeding knowledge gaps back into task planning for future runs.

### Planned testing progression

Testing is structured to progressively increase difficulty:

1. **Greenfield implementation** (complete): Built a project from scratch using the full SDL workflow — 13 features (10 original + 3 corrective), ~80 tasks, 137 tests, zero formal re-plans. Includes a full bug-fix cycle that validated the bug-fix workflow pattern and produced the most actionable improvement data of any testing phase. Establishes baseline metrics for comparison with brownfield scenarios.
2. **Brownfield change to a disciplined codebase**: Introduce a post-implementation feature change to the greenfield project. The change is not revealed to implementation agents during initial development — the codebase must genuinely be treated as existing code, not code pre-optimized for modification. Tests whether the brownfield mitigations (codebase survey, existing pattern identification, partial replacement detection) work when modifying pipeline-produced code.
3. **Brownfield improvement of an undisciplined codebase**: Apply the pipeline to an existing project that was built outside the SDL workflow and suffers from known agentic coding failure modes — dead subsystems, parallel pathways, tests that pass but don't validate behavior. This is the hardest and most realistic scenario: can the pipeline produce specs that correctly identify what's broken, break down fixes that reference and consolidate existing code rather than adding more sprawl, and produce PRs that improve rather than perpetuate the mess?

Each scenario produces retrospectives that feed the self-improvement loop. Results across all three will indicate where the pipeline's quality interventions hold up and where they need refinement.

## Bug-fix workflow pattern

**Status**: First cycle complete — validated against the greenfield project with all issues resolved. The corrective workflow has been formalized in `home/dot-claude/docs/sdl-workflow/corrective-workflow.md`.

### Origin

The completed greenfield project passed all 124 tests (unit + e2e) but the application didn't work correctly for a real user. Root cause: the e2e spec explicitly scoped out behavioral testing ("testing game logic belongs to unit tests"), and the test reviewer accepted this framing. Every e2e test was a smoke test (verifies no crashes) rather than a behavior test (verifies the application works). A silent failure — no errors, no exceptions — passed every automated check.

This failure is significant because it validates the pipeline's core design principle by counterexample: **human spec review is the highest-leverage quality intervention**. The spec was accepted without meaningful human review as a deliberate test of what happens when the human step is skipped. The downstream pipeline executed flawlessly against a flawed spec — every gate passed, every task succeeded, every test ran green. The application didn't work.

### The workflow

Bug fixes enter the pipeline as a structured sequence:

1. **Write behavioral e2e tests first** — define what "working" means from the user's perspective, before any debugging begins. Tests should verify real user interactions, not just the absence of errors. Writing tests first prevents the fixing agent from writing tests that validate its own fix rather than the intended behavior.
2. **Run tests and identify failures** — the failing tests are the bug specification. Each failure is a concrete, observable deviation from intended behavior.
3. **Root cause analysis per failure** — use a separate, context-independent agent team to identify the true root cause for each failure. The root cause agent hasn't seen the implementation agent's reasoning, so it can't inherit assumptions about why the code is correct.
4. **Update the spec** — incorporate root cause findings into a fix specification with acceptance criteria.
5. **Spec review** — run the normal council review process on the fix spec.
6. **Breakdown** — compile the reviewed fix into implementation tasks.
7. **Implement** — execute tasks through the normal workflow with verification gates, iterating until the behavioral tests pass.

The key difference from a typical agent bug fix ("here's the error, fix it") is that this workflow starts with defining correct behavior (step 1), uses that definition to find what's wrong (steps 2-3), then plans the fix through quality gates (steps 4-7). The fix is constrained by a behavioral test that was written before the fix was designed — preventing the agent from "fixing" the bug by making the tests match the broken behavior.

### Results from the first bug-fix cycle

The bug-fix workflow completed successfully, resolving all issues through three iterative passes:

1. **Behavioral e2e tests written first** — 9 tests covering the primary user flow (start game, fire weapon, destroy invaders, take damage, game over, restart). 4 of 9 failed immediately, identifying two code bugs and one test geometry issue.
2. **Root cause analysis by context-independent agents** — two root causes identified: a wrong key string crossing a module boundary (spec used conceptual name, implementation used runtime value), and missing wiring in the orchestrator file (entities spawned but never updated).
3. **Fix implementation through normal workflow** — both fixes applied, 12/13 tests passed. One remaining failure diagnosed as a test design issue (player geometry unreachable by enemy fire). Resolved with test helpers that position the player without bypassing game logic.
4. **Final result**: 137 tests (112 unit + 17 e2e + 8 Python), all passing. Application fully functional.

**Key finding**: All bugs existed at the seam between correctly-implemented modules. Unit tests mock across these seams. Only real browser execution with real module wiring surfaces them. The bug-fix workflow's "write behavioral tests first" step was the critical intervention — it defined "working" before any debugging began.

**Fast-track validation**: A second bug of the same class (rendering coordinate transform) was fixed via fast-track in 15 minutes with identical output quality to the full-ceremony fix that took 2 hours. The fast-track was safe because the root cause, fix pattern, and test pattern were all validated by the prior full-ceremony cycle. This establishes clear criteria for when fast-track is appropriate versus when full ceremony is needed.

### Improvement findings from this cycle

- **Test reviewer needs four new evaluation criteria**: Behavioral completeness (user-facing behaviors need tests that fail when broken, not just no-crash tests), silent failure detection (flag "no errors" as sole assertion), integration seam coverage (flag when components share mutable state with temporal ordering but no e2e test exercises the seam), and test-level adequacy (flag when all tests for browser-rendered features are mock-only). **Implemented in Phase 1.5**: two-tier enforcement model and behavioral completeness 'show your work' requirement added to test-reviewer.md.
- **E2e test coverage needs proportional depth**: 4 smoke tests across a 10-feature application is insufficient. E2e tests should cover the primary user flow, not just verify that the page loads without console errors. **Implemented in Phase 1.5**: user verification steps and integration seam declaration requirements added to feature-spec-guide.md.
- **Human spec review cannot be skipped without risk**: The pipeline's automated gates cannot substitute for human judgment at the spec stage. The spec defines what the pipeline optimizes for — if the spec's framing is flawed, the pipeline optimizes for the wrong thing flawlessly.
- **Ceremony level should match the work**: Full ceremony for new features with design decisions. Fast-track for mechanical fixes with known root causes and validated patterns. The distinction is whether the review would change the fix or only the tests. **Implemented in Phase 1.5**: corrective workflow formalized in corrective-workflow.md with explicit fast-track criteria.

## Phase 1.5 retrospective: brownfield feature addition

**Status**: Complete. First brownfield test of the Phase 1.5 changes — a new feature added to the existing greenfield codebase.

### Test parameters

- **Scenario**: Brownfield feature addition to a disciplined codebase (testing progression step 2)
- **Scope**: 1 feature, 19 tasks across 7 waves, 43 new tests (35 unit/integration + 8 e2e)
- **Phase 1.5 changes under test**: User verification steps, integration seam declarations, UV→test mapping, two-tier test reviewer enforcement, codebase-grounded compilation, per-task readiness checks, inter-wave baseline regression, orchestrator task wiring checklists

### Comparison with Phase 1.0

| Metric | Phase 1.0 (Greenfield) | Phase 1.5 (Brownfield) |
|--------|----------------------|----------------------|
| Corrective features needed | 3 | 0 |
| Team-lead interventions | 5 | 0 |
| Application worked on first human test | No | Yes |
| Integration seam bugs | 5 (found post-implementation) | 2 (caught during implementation) |
| E2e coverage in original spec | None | 10 UV steps, 8 e2e tests |
| Test reviewer CP failures | 0 (missed everything) | 2 FAILs with 8 total defects caught |
| Formal re-plans | 0 (misleading — see below) | 1 |

Phase 1.0's "zero re-plans" was misleading — the metric hid 5 team-lead interventions and 3 entire corrective feature cycles. Phase 1.5's single re-plan represents the system working correctly: catching bugs during implementation rather than discovering them through post-implementation human testing.

### What the Phase 1.5 changes fixed

**E2e coverage gap (Phase 1.0's biggest miss) — Fixed.** Phase 1.0 produced 10 feature specs with zero behavioral e2e tests. The test reviewer passed all of them. The application didn't work when a human used it. Phase 1.5 required UV steps in the spec, enforced UV→test mapping at CP1 and CP2, and required integration seam declarations. Result: 8 e2e tests in the spec from the start, catching 2 real orchestrator bugs during implementation. The application worked on first human test.

**Test reviewer effectiveness — Significantly improved.** Phase 1.0's test reviewer accepted "handled without errors" as behavioral coverage and missed the entire e2e gap. Phase 1.5's test reviewer returned FAIL at both CP1 (4 defects) and CP2 (4 defects), forcing concrete UV→test mapping, removal of a conditional test escape clause, concrete speed assertions, and accurate e2e remediation steps. Each defect forced real improvements to the testing strategy.

**Integration seam bugs — Same pattern, earlier detection.** Both phases produced bugs at the boundary between correctly-implemented modules in the orchestrator file. Phase 1.0 discovered them through human testing and required corrective feature cycles. Phase 1.5 discovered them through e2e tests during implementation and resolved them via re-plan. The bug pattern is inherent to orchestrator files; the improvement is in detection timing.

**Orchestrator task handling — Partially improved.** Phase 1.0 gave no special treatment to orchestrator tasks. Phase 1.5 added Sonnet routing, wiring checklists, and explicit section boundaries. Wiring checklists ensured correct imports, initializations, and cleanup, but didn't prevent ordering bugs between checks in the game loop. The checklist says "what to wire" but not "in what order relative to other checks." This is a specific gap to address.

### New findings unique to Phase 1.5

Phase 1.5 included a post-implementation code review (two council agents reviewing all files against 10 AI coding failure modes), which Phase 1.0 did not. This revealed a quality dimension the pipeline doesn't address.

**Tests that test themselves** — 3 instances where tests re-implement production logic inline and assert against their own copy. These tests can never catch regressions. The most notable: a powerup drop test that manually writes the drop conditional from the orchestrator and asserts against the local result rather than exercising the actual code path.

**Copy-paste artifacts** — 2 instances where AI agents copied code blocks between similar contexts rather than extracting shared helpers. One had a quote-style inconsistency between copies (double quotes in the original, single quotes in the copy) — a telltale sign of independent generation rather than extraction.

**Hardcoded coupling** — Magic numbers duplicated across files (target positions appearing in 3 locations across 2 files, hit zone dimensions hardcoded as raw numbers instead of derived from entity dimensions).

**Dead code** — 1 variable declared and assigned but never read. The agent planned to use it, chose a different approach, and didn't clean up.

These are code quality issues, not behavioral correctness issues. All 172 tests passed. The application worked correctly. But the code has maintainability debt that compounds over time.

### Test reviewer scope gap

The tests-that-test-themselves pattern traced to a specific gap in the test reviewer's scope. At CP1, the reviewer caught the most egregious version (a constant expression `expect(0.10 < 0.15).toBe(true)`). The fix replaced it with a more elaborate version that still re-implemented production logic inline — the task instruction literally said "simulate the drop logic." The test reviewer accepted the fix because the assertion was now concrete at the expression level.

The structural problem survived because the test reviewer and code review operate at different scopes:

- **Test reviewer (CP1/CP2)**: Reads spec and task files. Validates coverage, AC traceability, and assertion concreteness.
- **Code review (post-implementation)**: Reads actual source code. Validates whether tests exercise production code vs reimplementing it.

The test reviewer validates *what* is tested and *how concretely*. It cannot validate *whether the test calls production code or its own copy* — that requires comparing implemented test code against the production code path, which only exists after both are written. Adding "tests-that-reimplement-production-logic" as an explicit check — flagging instructions that say "simulate" or include inline conditionals mirroring production code — would partially close this gap at the task compilation level.

### Implications for workflow evolution

**Code review phase justified.** The post-implementation review found 14 issues that passed all automated gates. The most impactful category — tests that test their own inline logic — is a systemic AI coding failure mode that no amount of test-passing can detect. This validates adding code review as a formal stage between implementation verification and commit/merge, positioned as the third agent in the quality layer alongside the test reviewer and the (future) troubleshooter.

**Orchestrator task ordering needs explicit specification.** Wiring checklists prevented missing-import and missing-initialization bugs but didn't prevent ordering bugs between checks in the game loop. Task instructions for orchestrator files should specify ordering constraints ("this check must run before that check") when the ordering affects correctness.

**Discretionary structuring produces duplication.** When task instructions allowed implementer discretion on helper extraction, the agents chose to copy-paste instead of extract. Prescribing shared helpers for known-duplicated blocks (or flagging the duplication risk in task instructions) would prevent this without over-constraining.

### Testing progression status

1. **Greenfield implementation** (complete): 13 features, ~80 tasks, 137 tests. Established baseline. Identified e2e gap, integration seam pattern, and ceremony calibration needs.
2. **Brownfield change to a disciplined codebase** (complete): 1 feature, 19 tasks, 43 new tests. Validated Phase 1.5 fixes for behavioral correctness. Revealed code quality dimension and test reviewer scope gap. Justified code review phase.
3. **Brownfield improvement of an undisciplined codebase**: Not yet attempted. The hardest scenario — applying the pipeline to code built outside the workflow with existing agentic failure modes.

## Future exploration: Troubleshooter and code review agents

**Status**: Design direction — not yet specified or implemented.

### Troubleshooter agent

A context-independent agent specialized in root cause analysis for existing bugs and issues. Distinct from implementation agents — the troubleshooter reads the codebase, the failing tests, and the bug description, but has no access to the original implementation agents' reasoning or the spec authoring conversation.

This maps to step 3 of the bug-fix workflow. The troubleshooter's output is a structured root cause report (what's wrong, where, why, and what needs to change) that feeds into the fix spec. It does not produce fixes — it diagnoses. Separating diagnosis from repair prevents the common agentic failure mode where an agent identifies a symptom, guesses at a fix, and iterates until the error goes away without understanding the underlying cause.

### Code review agent

A context-independent agent that reviews completed changes and PRs before final acceptance or merge. Reviews against the spec and the produced code without access to the implementing agents' reasoning.

This extends the advisory code review already present in Firebreak's Stage 9 verification. The design question is whether this agent should be advisory (output attached to PR for human review) or gate-blocking (PR cannot merge without passing review). The advisory model is safer initially — it generates quality signal data without risking false-positive blocks. If the review agent's findings consistently align with human-discovered issues over time, its authority can be elevated.

Both agents follow the established pattern: context-independent, separate persona, no shared reasoning with the agents whose work they evaluate. The troubleshooter evaluates existing code to find problems; the code reviewer evaluates new code to prevent problems. Together with the test reviewer, they form a three-agent quality layer — each operating independently, each seeing only what it needs.

## Context asset organization: shared vs skill-specific

**Finding from Phase 1.6 spec review**: Anthropic's skills guide recommends a `references/` subdirectory within each skill for skill-specific documentation, while Firebreak's existing skills place all reference docs in the shared `docs/sdl-workflow/` directory regardless of whether they are shared or skill-specific.

**Resolution for Phase 1.6**: Adopt both patterns, each where appropriate. Documents referenced by multiple skills and agents (AI failure mode checklist, code review methodology guide) live in `docs/sdl-workflow/`. Documents specific to a single skill's internal routing (path-specific instructions) live in the skill's `references/` directory. This follows Anthropic's recommended skill structure while preserving the shared `docs/` convention for cross-cutting resources.

**Deferred**: Existing skills (`/spec`, `/spec-review`, `/breakdown`, `/implement`) should be audited in a future phase to determine which of their reference docs are truly shared vs skill-specific, and realigned to match this pattern.

## Agent observability: token tracking and context health

**Finding from Phase 1.6 spec review**: The code review retrospective needs to assess whether review agents experienced context degradation during large-scope reviews. Investigation revealed significant observability gaps.

**What's observable from within a Claude Code session:**
- Structured output from agents (sightings, findings, rejections) — the orchestrator sees all of this
- Round counts, sighting-per-round trends, rejection rates — derivable from agent output
- Whether hard caps were reached — orchestrator controls the loop
- SubagentStart and SubagentStop hook events — can instrument agent lifecycle

**What's NOT observable:**
- Per-agent or per-subagent token consumption — open feature request ([Issue #22625](https://github.com/anthropics/claude-code/issues/22625))
- Context window utilization percentage within a subagent
- Whether an agent's internal context degraded during a long session
- Real-time visibility into what a running subagent is doing

**Agent SDK capabilities (API-level, not Claude Code interactive):**
- `modelUsage` in result messages provides per-model token counts and cost
- Useful when running multiple models (e.g., Haiku for subagents, Opus for main agent)
- Not exposed to the orchestrating agent in Claude Code interactive sessions

**Third-party options:**
- Bifrost (open source AI gateway) provides per-request observability by routing traffic through a compatible Anthropic API endpoint
- Various community monitoring tools exist but require external instrumentation

**Implication**: Context health assessment in pipeline retrospectives must rely on behavioral proxies (output quality trends, rejection rates, round counts) rather than direct token/context measurements. If per-subagent token tracking becomes available (Issue #22625), retrospective metrics should be updated to use direct measurements.

Sources:
- [Manage costs — Claude Code Docs](https://code.claude.com/docs/en/costs)
- [Issue #22625 — Per-Subagent Token Usage Tracking](https://github.com/anthropics/claude-code/issues/22625)
- [Agent SDK Cost Tracking](https://platform.claude.com/docs/en/agent-sdk/cost-tracking)
