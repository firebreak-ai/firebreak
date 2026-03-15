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

### 2. Per-task changelogs in the task manifest

**Finding**: The article's `claude-progress.txt` pattern solves context-window exhaustion: agents write a self-briefing document updated after each meaningful step, so the next session (or a resumed session) can pick up where it left off.

**Gap**: Dispatch's audit log (F3) captures events from the dispatcher's perspective, not from inside the agent's reasoning. The task manifest tracks per-task status but not what happened within a task. The ralph-loop handles error recovery within a session, but there's no structured handoff mechanism if an agent exhausts its context window or needs to be restarted.

**Recommendation**: Extend the task manifest (`task.json`) with per-task fields:

- `changelog`: ordered array of brief entries summarizing each meaningful agent action (file and line references, not full code). Updated by the agent after each step.
- `worktree`: path to the git worktree used for the task.
- `last_commit`: SHA of the agent's most recent commit.

This serves three purposes: (1) resume after failure — the next attempt knows what was already done, (2) debugging — when a wave fails verification, trace what each agent did without reconstructing from diffs, (3) audit fidelity — agent-level events complement dispatcher-level events from F3.

The agent instruction is: "after each meaningful step, append a changelog entry summarizing what you changed and why." The schema change is minimal. The changelogs also serve as a prerequisite for future inter-agent coordination (see Future Exploration below).

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
