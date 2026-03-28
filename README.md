# Firebreak

**Firebreak improves the reliability and maintainability of AI-generated code.** It's a research-backed framework for Claude Code that closes the gap between code that works and code you'd want to maintain.

You talk to it like a person — "We need to add rate limiting to the API. Let's spec it out." You co-author the spec, the system handles review, breakdown, and implementation autonomously, and you review the results. Human judgment goes where it has the highest leverage (spec authoring); everything after that runs as a pipeline with verification at every stage.

Core design decisions trace to [published research](research.md) — see [what problems this solves](#what-problems-does-this-solve) and the [full research basis, reasoning, and process](ai-docs/).

Firebreak is a research base and a reference implementation. Use the pipeline, or just take the techniques that solve your problems.

## Quick Start

**Requirements:** [Claude Code](https://docs.anthropic.com/en/docs/claude-code), python3, jq, PyYAML.

```bash
# Install globally (default: ~/.claude/)
curl -fsSL https://raw.githubusercontent.com/firebreak-ai/firebreak/main/installer/install.sh | bash

# Install to a specific project
curl -fsSL https://raw.githubusercontent.com/firebreak-ai/firebreak/main/installer/install.sh | bash -s -- --target ./my-project/.claude

# Preview what will be installed without changing anything
curl -fsSL https://raw.githubusercontent.com/firebreak-ai/firebreak/main/installer/install.sh | bash -s -- --dry-run
```

Then open any project with Claude Code and start talking:

```
"I need to add a notification system to the app. Let's design it and spec it out."
```

Firebreak picks up the intent and walks you through spec authoring. You describe what you want, it asks clarifying questions, and together you produce a structured spec. From there, the pipeline takes over.

### Improve your context assets (any project)

Context assets are anything the agent loads — CLAUDE.md files, skills, hooks, agents. Even without the full pipeline, Firebreak includes guidelines for writing these that produce measurably better agent behavior. Works in any project immediately.

```
"Help me write a CLAUDE.md for this project"
"Create a skill for running our deploy process"
"Review my agent definition — is it following best practices?"
```

### Try the software development lifecycle (SDL) workflow

```
"I need to add rate limiting to the API. Let's spec it out."
"There's a bug where sessions expire silently. Let's investigate and plan a fix."
"Let's review the auth module — I think there are quality issues from the last round of AI changes."
"Assemble the council — I want to discuss whether we should use WebSockets or SSE for real-time updates."
```

You co-author the spec, the system handles review, breakdown, and implementation autonomously, and you review the results. The council convenes 6 independent agents (architect, builder, guardian, security, analyst, advocate) that discuss the problem, challenge each other, and produce consensus recommendations.

### Slash commands

| Command | What it does |
|---------|-------------|
| `/spec` | Co-author a specification with acceptance criteria and testing strategy |
| `/spec-review` | Run council review (architect, security, guardian, advocate, analyst) |
| `/breakdown` | Compile the reviewed spec into sized, wave-assigned tasks |
| `/implement` | Execute tasks with parallel agent teams and per-wave verification |
| `/council` | Assemble 6 independent agents to discuss a problem and reach consensus |
| `/code-review` | Adversarial Detector/Challenger review of existing code |
| `/context-asset-authoring` | Guidance for writing effective context assets |

Natural language works too — talking about designing features, fixing bugs, or reviewing code triggers the appropriate skill automatically.

## Techniques you can use independently

Each of these works on its own, in any project, without the full pipeline.

- **[Progressive disclosure](assets/fbk-docs/fbk-context-assets.md)** — organize context so agents load only what they need, preventing the performance degradation that comes from irrelevant instructions
- **[Adversarial code review](assets/fbk-docs/fbk-sdl-workflow/code-review-guide.md)** — a Detector/Challenger loop where sightings require evidence to become findings, catching semantic issues invisible to CI
- **[Council review](assets/fbk-docs/fbk-sdl-workflow/review-perspectives.md)** — independent perspectives (architect, security, guardian, advocate, analyst) that challenge the user and each other, countering agent sycophancy
- **[Context-independent agents](assets/agents/)** — test writers, implementers, and reviewers never share reasoning, preventing agents from confirming their own work ([arXiv:2410.21136](https://arxiv.org/abs/2410.21136))
- **[Test-first with AI bias mitigations](assets/fbk-docs/fbk-sdl-workflow/implementation-guide.md)** — a [dedicated test reviewer](assets/agents/fbk-test-reviewer.md) gates quality before implementation, and SHA-256 hash verification ensures implementation agents cannot weaken tests
- **[Failure mode taxonomy](ai-docs/dispatch/failure-modes.md)** — 39 catalogued ways AI code fails, from 25+ empirical sources, usable as a reference regardless of pipeline
- **[Structured retrospectives](ai-docs/dispatch/harness-patterns-analysis.md)** — classified failure data (spec gap, compilation gap, implementation error) after every run, enabling the pipeline to [improve itself](ai-docs/dispatch/phase-1.6-code-review-remediation/brownfield-validation/analysis.md)
- **[Context asset authoring guidelines](assets/fbk-docs/fbk-context-assets.md)** — [empirical research](research.md) on instruction density, positive framing, and compression applied to writing skills, agents, and CLAUDE.md files

## What problems does this solve?

AI-generated code ships with [1.7x more issues and 1.5–2x more security vulnerabilities](https://www.coderabbit.ai/blog/state-of-ai-vs-human-code-generation-report) than human-written code (CodeRabbit, 2025), with doubled code churn, [~8x growth in duplicated blocks, and a 60% collapse in refactoring activity](https://www.gitclear.com/ai_assistant_code_quality_2025_research) (GitClear, 2024–2025). Existing pipelines address behavioral correctness — agents follow specs and produce code that works — but leave reliability and maintainability gaps:

| Gap | How Firebreak addresses it | Evidence | Deep dive |
|-----------|-------------|---------------|-----------|
| **Context overload degrades output** — irrelevant instructions hurt performance even when the window has room; models collapse past ~150 constraints | Three-tier context hierarchy (router/index/leaf) where agents load only what they need. Authoring framework applies the Necessity Test to every instruction. | [IFScale](https://arxiv.org/abs/2507.11538) 2025 (20 models), [Context Rot](https://research.trychroma.com/context-rot) (Chroma, 2025) | [Context assets](assets/fbk-docs/fbk-context-assets.md), [research](research.md) |
| **CI can't catch semantic quality issues** — tests that pass vacuously, missing deep-copies, dead code guards with incomplete scope | Adversarial Detector/Challenger review at project scope. Detector uses behavioral comparison against specs or failure checklist; Challenger demands evidence before promoting findings. | 14 verified findings in brownfield validation — all invisible to CI | [Code review guide](assets/fbk-docs/fbk-sdl-workflow/code-review-guide.md), [Detector](assets/agents/fbk-code-review-detector.md), [Challenger](assets/agents/fbk-code-review-challenger.md) |
| **No systematic model of how AI code fails** — teams address symptoms individually rather than mapping the failure space | 39 failure modes across 6 categories from 25+ empirical sources (ICSE, MAST, OWASP, Microsoft AI Red Team), each mapped to pipeline stages with coverage matrix and gap analysis | Grounded in published research, not experience | [Failure modes](ai-docs/dispatch/failure-modes.md) |
| **Pipelines don't learn from their own mistakes** — the same failure patterns repeat across runs | Built-in retrospectives with structured failure attribution. Every problem classified as spec gap, compilation gap, or implementation error. Human-mediated correction loop works today; the data structure supports future automated self-correction. | Re-plans and wave failures dropped to zero by Phase 2 of the brownfield test | [Harness analysis](ai-docs/dispatch/harness-patterns-analysis.md), [brownfield validation](ai-docs/dispatch/phase-1.6-code-review-remediation/brownfield-validation/analysis.md) |
| **Correlated failures between test and implementation agents** — LLMs derive test assertions from implementation behavior rather than spec intent, producing tests that freeze actual behavior as "correct" regardless of whether it matches requirements | Test writers, implementers, and reviewers never share context. No agent reviews its own work. Context isolation prevents the agent's understanding of its own implementation from contaminating test expectations. | [arXiv:2410.21136](https://arxiv.org/abs/2410.21136) | [Research](research.md) |
| **Design decisions built on intuition don't generalize** — experience-driven frameworks over-fit to the author's projects | Every structural decision cites published studies with methodology and sample sizes. Research, reasoning, and process published alongside the tools. | Full citations with confidence levels and open questions | [Research](research.md), [`ai-docs/`](ai-docs/) |

## Results

Tested through a greenfield project (13 features, ~80 tasks, 137 tests), a brownfield feature addition (19 tasks, 43 new tests), and an ongoing large-scale brownfield remediation. Results are from the author's projects and have not been independently replicated.

**Greenfield — the self-improvement loop in action:**

The first full run produced a working application across 13 features with zero formal re-plans. But the retrospective revealed that "zero re-plans" masked 5 team-lead interventions and 3 corrective feature cycles — the metric was hiding real problems. The application passed all 137 tests but [didn't work correctly for a real user](ai-docs/dispatch/harness-patterns-analysis.md). Root cause: every e2e test was a smoke test (verifies no crashes) rather than a behavior test (verifies the application works). All bugs existed at integration seams between correctly-implemented modules — exactly where unit tests mock across boundaries.

**Corrective actions:** The pipeline was revised to require [user verification steps](ai-docs/dispatch/phase-1.5-core-enhancement/phase-1.5-core-enhancement-spec.md) in every spec (action → observable outcome), enforce integration seam declarations, and add a [two-tier test reviewer](assets/agents/fbk-test-reviewer.md) that actively fails on missing behavioral coverage and silent-failure assertions. The greenfield had zero e2e tests; the brownfield tracked interventions as a first-class metric — the measurement the greenfield retrospective revealed was missing.

**Brownfield feature addition (verification):** The next test — 19 tasks, 43 new tests on a different codebase — completed with zero corrective cycles and zero team-lead interventions. The feature worked on first human test. The spec produced 8 e2e tests from the start, catching 2 integration bugs during implementation that unit tests would have missed. Council review caught 22 findings before code was written. The test reviewer caught 8 defects across 2 checkpoints. Structured failure data in, specific pipeline corrections out, measurably better results next run. See the [full comparison](ai-docs/dispatch/harness-patterns-analysis.md).

**Brownfield remediation (in progress — 4 of 8 phases complete):**
- 110 pre-decomposed tasks (1-2 file scope each), 98.2% first-attempt pass rate, zero escalations to larger models — the cheapest model tier handled every task assigned to it
- 4 team-lead interventions where the decomposition itself failed — the more interesting signal, and the [dominant remaining failure mode](ai-docs/dispatch/phase-1.6-code-review-remediation/brownfield-validation/analysis.md)
- 26 blocking spec review findings caught across 3 phases, including one that forced a complete architecture rewrite before code was written
- 14 verified code review findings (Detector/Challenger) — all invisible to CI. For example, a thread-safe config wrapper returned collection fields by reference without deep-copying; the Detector identified the behavioral mismatch, the Challenger [verified it against the call graph](ai-docs/dispatch/phase-1.6-code-review-remediation/brownfield-validation/phase-0-security-retrospective.md). Other findings included vacuously-passing tests, incomplete guards, and dead code paths that appeared covered but weren't
- Remediation exposed [7 false-passing tests](ai-docs/dispatch/phase-1.6-code-review-remediation/brownfield-validation/phase-1-test-infrastructure-retrospective.md) hidden by wrong mock wiring — a deprecated mock function was set but never called by production code, so tests exercised the mock's generic responses instead of actual behavior. Assertions were loose enough to accept either. CI reported green; the codebase's apparent test health was worse than its actual test health

See [full greenfield/brownfield analysis](ai-docs/dispatch/harness-patterns-analysis.md) and [preliminary brownfield validation](ai-docs/dispatch/phase-1.6-code-review-remediation/brownfield-validation/analysis.md).

## How it works

```
Spec ─► Review ─► Breakdown ─► Test Creation ─► Test Review ─► Implementation ─► Verification ─► Code Review ─► PR
         ▲                          ▲                ▲                                  ▲              ▲
     council +               context-independent   pipeline-         deterministic checks +    adversarial
     agentic review          test-writing agents   blocking          mutation testing +        Detector/Challenger
                                                   gate              test immutability         verification loop
```

**Context assets** use a three-tier hierarchy (router/index/leaf) to prevent context pollution — the agent starts with a lightweight router (CLAUDE.md), follows references when a topic is relevant, and loads only the specific leaf it needs. Most context never enters the window. The [authoring framework](assets/fbk-docs/fbk-context-assets.md) applies empirical research on instruction density and compression to every asset.

**The SDL pipeline** runs five stages — Spec, Review, Breakdown, Implement, Code Review — with [deterministic verification gates](assets/hooks/fbk-sdl-workflow/) at each transition. Implementation uses wave-based parallel execution with capped retry loops. Test writers, implementers, and reviewers are context-independent agents that never share reasoning. Test files are locked by SHA-256 hash after the test reviewer approves them, preventing implementation agents from weakening tests to pass.

**Retrospectives** classify every pipeline failure as a spec gap, compilation gap, or implementation error. This structured failure data drives the next revision of the pipeline itself — Firebreak was built using its own SDL workflow, and each iteration addresses the gaps the previous one revealed. See the [harness analysis](ai-docs/dispatch/harness-patterns-analysis.md) for the full bootstrapping narrative.

## Documentation

### Understanding the approach

| Topic | Document |
|-------|----------|
| Research basis — context, instructions, agent behavior | [research.md](research.md) |
| AI failure taxonomy — 39 modes, 25+ sources | [failure-modes.md](ai-docs/dispatch/failure-modes.md) |
| Harness patterns and retrospective analysis | [harness-patterns-analysis.md](ai-docs/dispatch/harness-patterns-analysis.md) |
| Brownfield remediation test results | [brownfield validation](ai-docs/dispatch/phase-1.6-code-review-remediation/brownfield-validation/analysis.md) |

### Pipeline reference

| Stage | Guide | Gate |
|-------|-------|------|
| Spec authoring | [feature-spec-guide.md](assets/fbk-docs/fbk-sdl-workflow/feature-spec-guide.md) | [spec-gate.sh](assets/hooks/fbk-sdl-workflow/spec-gate.sh) |
| Spec review | [review-perspectives.md](assets/fbk-docs/fbk-sdl-workflow/review-perspectives.md) | [review-gate.sh](assets/hooks/fbk-sdl-workflow/review-gate.sh) |
| Task breakdown | [task-compilation.md](assets/fbk-docs/fbk-sdl-workflow/task-compilation.md) | [breakdown-gate.sh](assets/hooks/fbk-sdl-workflow/breakdown-gate.sh) |
| Implementation | [implementation-guide.md](assets/fbk-docs/fbk-sdl-workflow/implementation-guide.md) | [task-completed.sh](assets/hooks/fbk-sdl-workflow/task-completed.sh) |
| Code review | [code-review-guide.md](assets/fbk-docs/fbk-sdl-workflow/code-review-guide.md) | — |
| AI failure modes | [ai-failure-modes.md](assets/fbk-docs/fbk-sdl-workflow/ai-failure-modes.md) | — |
| Brownfield work | [brownfield-breakdown.md](assets/fbk-docs/fbk-brownfield-breakdown.md) | — |

### Context asset authoring

| Asset type | Guide |
|------------|-------|
| Overview and principles | [context-assets.md](assets/fbk-docs/fbk-context-assets.md) |
| CLAUDE.md files | [claude-md.md](assets/fbk-docs/fbk-context-assets/claude-md.md) |
| Skills | [skills.md](assets/fbk-docs/fbk-context-assets/skills.md) |
| Hooks | [hooks.md](assets/fbk-docs/fbk-context-assets/hooks.md) |
| Agents | [agents.md](assets/fbk-docs/fbk-context-assets/agents.md) |

### Process artifacts

The [`ai-docs/`](ai-docs/) directory is a working artifact — the pipeline reads and writes to it. Each feature gets a subfolder with its spec, review, task breakdown, and retrospective. Firebreak is built using its own pipeline; `ai-docs/` is the audit trail.

## Security

**What runs on your machine:** The TaskCompleted hook runs your project's test suite and linter automatically after each implementation task. It auto-detects the test runner (npm test, cargo test, pytest, etc.) and executes it. Gate scripts (spec-gate, review-gate, breakdown-gate) parse markdown and JSON to validate structure — they do not execute code from those files. The spec-gate includes prompt injection detection for control characters, zero-width Unicode, and embedded override patterns.

**What does NOT happen:** No hook or gate script makes network calls. No telemetry, analytics, or data collection. No system file modifications — all writes are scoped to the project's `ai-docs/` directory and `.claude/automation/`. No permission escalation or bypass-permissions settings.

**Known limitation — agent scope enforcement:** During the brownfield remediation test, agents spawned for analysis tasks [implemented entire phases without authorization](ai-docs/dispatch/phase-1.6-code-review-remediation/brownfield-validation/analysis.md), modifying 13 production files. The root cause is a framework-level gap in Claude Code: the permission model controls which tools an agent can use, but not what intent those tools serve. Firebreak mitigates this by restricting analysis agents to read-only tool sets. The incident and root-cause analysis are documented in the [brownfield validation retrospectives](ai-docs/dispatch/phase-1.6-code-review-remediation/brownfield-validation/analysis.md).

## Feedback

This project is under active development. If you try it out, find issues, or have ideas:

- [Open an issue](https://github.com/firebreak-ai/firebreak/issues) with bug reports, feature suggestions, or questions
- If you run the SDL workflow on your own project, I'd like to hear how it went

## License

MIT — see [LICENSE](LICENSE).
