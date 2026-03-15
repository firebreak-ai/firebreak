# Agent Harness Patterns: Insights for Dispatch

Source: [Effective Harnesses for Long-Running Agents](https://www.anthropic.com/engineering/effective-harnesses-for-long-running-agents) — Anthropic Engineering, 2025.

## Context

Anthropic's engineering team studied how to make AI agents effective across long-running, multi-session tasks. Their core finding: agents need structured external state to maintain coherence and constrained interfaces to prevent common failure modes. They built a two-agent architecture (initializer + coding agent) with a startup checklist, a structured feature list, progress files, and git-based checkpointing.

This analysis compares their empirical findings against Dispatch's design and identifies actionable improvements.

## Validated design bets

These Dispatch design decisions are independently supported by the article's empirical results.

### Structured artifacts as the primary quality lever

The article's most effective intervention was a structured JSON feature list that agents could only modify by flipping a `passes` field — not editing descriptions or steps. This constrains the agent's role from "figure out what to build" to "implement this well-defined thing." Dispatch's spec-driven approach codifies this architecturally; the article arrived at it empirically.

### Immutable boundaries

The article's "only edit the `passes` field" constraint prevented feature scope creep and documentation loss. Dispatch generalizes this with test file immutability (SHA-256 hash manifests after Stage 7). The underlying insight: agents silently modify artifacts that should be fixed reference points unless modification is mechanically impossible.

### Context-independent specialized agents

The article raises "specialized multi-agent architectures" as a future direction. Dispatch has already committed to this — separate agents for test writing, implementation, and review, each context-independent. The article's experience with a single general-purpose agent struggling with breadth of concerns suggests this is the right call.

### Git as checkpoint infrastructure

Both systems use git commits as recovery points. The article's coding agent commits after each feature to enable reverting problematic code. Dispatch's wave-based implementation with per-wave verification serves the same purpose at finer granularity.

### Testing as the critical gate

The article found agents would mark features done without proper testing and needed explicit prompting for end-to-end verification. Dispatch's five-checkpoint test validation model is an aggressive response to exactly this failure mode. The article validates that the concern is real, not theoretical.

## Actionable improvements for Dispatch

### 1. Agent-side startup verification

**Finding**: The article's most practical pattern is a deterministic startup sequence per agent session — read progress, verify the environment still works, *then* begin new work.

**Gap**: Dispatch's implementation agents receive a task file and a repo clone, but the overview doesn't describe a per-agent startup verification step. The inter-wave file reference check (Stage 8) is a dispatcher-side check, not an agent-side one.

**Recommendation**: Add to implementation agent instructions: before writing code, verify prerequisites compile/run and existing tests pass. This catches environment issues the dispatcher's structural checks miss (e.g., a dependency that installs but fails at runtime, a prior wave's output that compiles but doesn't behave as expected).

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

**Gap**: Dispatch's testing philosophy addresses test quality (behavioral assertions, mutation testing) but doesn't explicitly address the unit-vs-integration test spectrum. LLMs naturally produce unit tests. Unit tests can pass without the feature working in context.

**Recommendation**: The spec template's testing strategy section should require explicit decisions about test granularity — pushing toward integration/behavioral tests over isolated unit tests. The test reviewer checkpoints (Stages 3, 5, 7) should evaluate whether test granularity matches the acceptance criteria's scope. An AC about user-visible behavior needs an integration test, not a unit test on an internal function.

### 4. "Verify before you build" at every level

**Finding**: The article's startup checklist begins with "verify fundamental features still function" before starting new work. This applies verification at session start, not just pipeline end.

**Gap**: Dispatch's fresh-verification protocol runs at Stage 9. The inter-wave check validates file existence but not behavioral correctness.

**Recommendation**: After Wave N completes and before Wave N+1 agents start, run the full existing test suite (not just Wave N's new tests) to confirm the repo is in a working state. If Wave N broke something, catch it before Wave N+1 agents start building on a broken foundation. This is a dispatcher-side check that strengthens the inter-wave boundary.

### 5. Premature completion in agentic stages

**Finding**: The article's #1 failure mode was agents declaring they were done when they weren't.

**Gap**: Dispatch mitigates this in implementation (deterministic completion gates — referenced tests must pass), but the failure mode can still manifest in agentic stages: a review agent declaring a spec "good enough," a breakdown agent producing incomplete task coverage, or an implementation agent reporting DONE when tests pass but end-to-end behavior is broken.

**Recommendation**: Treat AC coverage checks as load-bearing infrastructure, not ceremony. For agentic stages without deterministic gates (review, breakdown), consider adding a deterministic "completeness check" layer that validates structural coverage independent of the agent's self-assessment.

## Structural divergence

The article optimizes for a single agent working incrementally across many sessions on one codebase. Dispatch optimizes for many specialized agents working in parallel on one feature. These are different coordination problems:

- **Article's challenge**: Temporal continuity (memory across sessions).
- **Dispatch's challenge**: Spatial coordination (multiple agents touching the same codebase simultaneously).

The article doesn't address the spatial problem. Dispatch's wave structure and file-boundary constraints solve a problem the article hasn't encountered. The coordination patterns don't transfer directly, but the failure-mode thinking does: wherever agents have autonomy, they find ways to silently fail, and mitigations need to be mechanically enforced, not instruction-based.

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

Applying this pattern to Dispatch is harder because the pipeline's ultimate output is code, and code quality (bugs, maintainability, design adherence) is notoriously difficult to measure without sustained human effort. But the pipeline generates rich structured data about its own operations that is measurable and actionable.

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

## Early retrospective evidence

The SDL workflow is being tested against real projects. Each feature implementation produces a structured retrospective that captures per-task results (model, status, re-plans, declared vs. actual files), upstream traceability (which review stage caught which issues), failure attribution, and notes on unexpected behavior.

### What the retrospectives show so far

Even in early testing, the retrospectives are generating actionable self-improvement data:

- **Repeated gate failure patterns**: Breakdown gates consistently fail for the same categories of structural issues across features. This identifies specific areas where skill instructions need reinforcement — a direct input for Layer 1's feedback loop.
- **Test-level adequacy gaps**: The test reviewer validated AC coverage at the unit level but did not flag cases where the test *level* (unit vs. integration vs. e2e) was insufficient for the feature's runtime environment. This was identified as a systemic gap — not a single-feature oversight — and led to a specific improvement to the test reviewer's evaluation criteria. This is the "tests pass but the feature doesn't work" failure mode identified in the Anthropic harness article, caught by the retrospective process.
- **Undeclared file creation**: Implementation agents occasionally produce files not declared in the task breakdown. The retrospectives capture these deviations with root cause analysis, feeding knowledge gaps back into task planning for future runs.
- **Agent autonomy observations**: Implementation agents sometimes proactively execute later-wave tasks when dependency analysis permits. The retrospectives track whether these optimizations succeed or cause problems — data that will inform the lead agent design if pursued.
- **Zero re-plans across initial features**: All tasks passed on first attempt after upstream gates (spec review, breakdown review, test review) completed their work. This is early evidence that front-loading quality into structured artifacts before implementation reduces the need for corrective iteration during implementation.

### Planned testing progression

Testing is structured to progressively increase difficulty:

1. **Greenfield implementation** (in progress): Build a project from scratch using the full SDL workflow. Validates the basic pipeline under ideal conditions — clear specs, no existing code to conflict with.
2. **Brownfield change to a disciplined codebase**: Introduce a post-implementation feature change to the greenfield project. The change is not revealed to implementation agents during initial development — the codebase must genuinely be treated as existing code, not code pre-optimized for modification. Tests whether the brownfield mitigations (codebase survey, existing pattern identification, partial replacement detection) work when modifying pipeline-produced code.
3. **Brownfield improvement of an undisciplined codebase**: Apply the pipeline to an existing project that was built outside the SDL workflow and suffers from known agentic coding failure modes — dead subsystems, parallel pathways, tests that pass but don't validate behavior. This is the hardest and most realistic scenario: can the pipeline produce specs that correctly identify what's broken, break down fixes that reference and consolidate existing code rather than adding more sprawl, and produce PRs that improve rather than perpetuate the mess?

Each scenario produces retrospectives that feed the self-improvement loop. Results across all three will indicate where the pipeline's quality interventions hold up and where they need refinement.
