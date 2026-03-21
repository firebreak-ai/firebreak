# Firebreak

**AI coding agents produce worse code than humans.** AI-generated PRs contain 1.7x more issues and 1.57x more security vulnerabilities than human-written PRs. AI-assisted development correlates with doubled code churn, ~8x growth in duplicated code blocks, and a 60% collapse in refactoring activity. The most dangerous failure mode — code that runs but produces wrong results — is increasing.

Most teams try to fix this with post-implementation gates: tests, linting, code review. Firebreak takes a different approach: **front-load human judgment into structured artifacts before agents write any code**, then constrain agents to implement against well-defined criteria with deterministic verification gates. Prevention is less costly than repair.

```
Spec ─► Review ─► Breakdown ─► Test Creation ─► Test Review ─► Implementation ─► Verification ─► Code Review ─► PR
         ▲                          ▲                ▲                                  ▲              ▲
     council +               context-independent   pipeline-         deterministic checks +    adversarial
     agentic review          test-writing agents   blocking          mutation testing +        Detector/Challenger
                                                   gate              test immutability         verification loop
```

A core design principle is **context and persona isolation between agents**. When the same agent designs tests and writes the implementation, its tests tend to validate its own reasoning rather than the spec's intent. By using separate agents with independent context for test authoring, implementation, and review, correlated failures are structurally reduced. Each agent can only see what it needs, and no agent reviews its own work.

**You talk to it like a person.** The developer interacts in natural language — sentences, questions, half-formed ideas — the same way you'd message a junior engineer on Slack. "We need to add auth to the API. Let's think about what that looks like." "That approach seems over-engineered, can we simplify?" "I also want to note that the tests need to cover the admin flow." The system progressively refines this natural conversation into highly specific artifacts: the spec compiles intent into structured sections, the breakdown compiles the spec into precise task instructions, and the implementation agents execute against those instructions. But the developer's interface stays conversational throughout — you're co-authoring, not writing prompts.

**Many pipeline stages does not mean many user interactions.** The developer collaborates during spec authoring — that's where human judgment has the highest leverage. After that, the pipeline advances autonomously: council review runs without prompting, breakdown compiles and gates check automatically, test creation and implementation proceed through agent teams. The developer's next interaction is reviewing the results. The goal is rigorous code quality with minimal user friction — the pipeline does the work, not the developer.

## Quick Start

Copy the context assets to your Claude Code configuration:

```bash
cp -r home/dot-claude/* ~/.claude/
```

### Context Asset Authoring (works in any project)

Even without the SDL workflow, Firebreak includes a research-based prompt engineering framework for writing better context assets — CLAUDE.md files, agent definitions, skills, hooks, and rules. It applies findings from empirical research on instruction density, context pollution, and progressive disclosure to help you write context assets that produce measurably better agent behavior.

Invoke it with `/context-asset-authoring`, or just start talking about creating or improving context assets — "help me write a CLAUDE.md", "create a new skill", "improve my agent definition." The skill loads detailed, research-backed guidelines automatically.

### SDL Workflow

The spec-driven development lifecycle applies to any code change where correctness and maintainability matter — new features, bug fixes, refactoring. A bug fix is a spec with a root cause analysis, a test plan review asking "were the tests wrong or missing?", and a constrained implementation. The stages are the same; the scope at each stage is smaller.

**The pipeline is scope-agnostic.** It prescribes process quality (spec must pass gate, tests must be adequate, implementation must pass verification) but is silent on scope and cadence. You choose the granularity — the pipeline ensures quality regardless:

| Project shape | How specs are scoped | Example |
|---|---|---|
| Small greenfield | One project overview → sequential feature specs, each a few tasks | A browser game: 10 features, ~80 tasks total |
| Sprint-sized work | Each feature spec fits a sprint. Multiple specs per sprint if they're small. | A new API endpoint: 1 spec, 5-8 tasks |
| Mechanical bugfix | Fast-track — skip the pipeline entirely for known-pattern fixes | Same rendering bug in a different file: 15 minutes |
| Large brownfield | Feature specs scoped to vertical slices of a broader roadmap. Each spec references existing code and tests. | Adding auth to a multi-service platform: each service gets its own spec |

Four slash commands, each advancing through a verification gate before the next stage can begin:

| Command | What it does | What it produces |
|---------|-------------|-----------------|
| `/spec` | Co-author a specification with structured sections, acceptance criteria, and a testing strategy | A spec document in `ai-docs/` |
| `/spec-review` | Run council review (architect, security, guardian, advocate, analyst perspectives) | Review findings with pass/fail determination |
| `/breakdown` | Compile the reviewed spec into sized, wave-assigned implementation tasks | Individual task files and a task manifest |
| `/implement` | Execute tasks with parallel agent teams, wave-based sequencing, and per-wave verification | Implemented code with passing tests |
| `/code-review` | Review existing code or post-implementation output using adversarial Detector/Challenger agents | Verified findings and optional remediation spec |

You can invoke these directly with the slash commands, or use natural language — talking about designing a new feature, fixing a bug, writing a specification, reviewing a spec, breaking down tasks, or implementing a change will trigger the appropriate skill automatically.

If you find that a natural language phrase you expected to trigger a skill didn't, [please report it](https://github.com/teknoll/firebreak/issues) — we're actively tuning trigger coverage based on how different users talk to Claude Code.

## How It Works

The project has three layers, each built using the one before it. The authoring framework produced the SDL workflow. The SDL workflow produced Dispatch's first phase. As Dispatch matures, future phases will be implemented using the updated pipeline — the process bootstraps itself up the complexity ladder.

| Layer | Status | Description |
|-------|--------|-------------|
| Context Asset Framework | **Working** | Authoring guidelines, progressive disclosure, skills, hooks, docs |
| SDL Workflow | **Working** | `/spec`, `/spec-review`, `/breakdown`, `/implement` with deterministic gates |
| Dispatch Pipeline | **In testing** | Phase 1 (pipeline core) complete. Phase 1.5 (test quality, integration seam coverage, corrective workflow) implemented and brownfield-validated. |

### 1. Context Asset Authoring Framework

Guidelines that teach agents how to write well-structured context assets, following their own principles — progressive disclosure, minimal instruction density, and separation of concerns.

**The problem:** Developers put all instructions into a single monolithic file. Research shows this hurts agent performance. Irrelevant instructions degrade output quality even when the context window has plenty of room — a phenomenon called **context pollution**. Every instruction competes for the model's attention, so unnecessary ones actively interfere with the instructions that matter.

Instead of loading everything upfront, context is structured as a three-tier hierarchy where agents load only what they need:

| Tier | Role | Loaded |
|------|------|--------|
| **Router** (CLAUDE.md) | Lists topics with file references. No detailed instructions. | Always (auto-loaded) |
| **Index** (.claude/docs/topic.md) | Maps tasks/conditions to leaf file paths. Includes principles that apply across subtopics. | On demand, when the topic is relevant |
| **Leaf** (.claude/docs/topic/subtopic.md) | Detailed, self-contained instructions for one concern. | On demand, when the specific subtopic is needed |

The agent starts with the lightweight router, follows a reference when a topic is relevant, then loads only the specific leaf it needs. Most context never enters the window at all.

### 2. SDL Workflow: Spec-Driven Development Lifecycle

A 5-stage interactive pipeline: **Spec → Review → Breakdown → Implement → Code Review**. Each stage has a dedicated skill, deterministic verification gates (shell scripts), and structured artifact output. Code review is available as both a standalone skill (`/code-review`) and a post-implementation pipeline stage.

Key design decisions, informed by [research](research.md):
- **Deterministic gates over AI self-review** — verification value comes from tests, linters, and schema checks, not from an AI re-reading its own output
- **External feedback at every iteration** — human judgment, test results, lint output, or council agents with distinct perspectives
- **Wave-based parallel implementation** — tasks decomposed into dependency waves, executed by agent teams with per-wave verification
- **Capped retry loops** — 2 re-plans per task, then escalate to human

### 3. Dispatch: Autonomous Pipeline Orchestration

The next evolution — an autonomous pipeline that drives specs from queue to PR without human intervention at intermediate stages. The developer's last judgment call is spec review; after that, the pipeline handles breakdown, test creation, test review, implementation, verification, and PR creation autonomously.

Dispatch extends the SDL workflow with:
- **10-stage pipeline** with deterministic and agentic gates at every transition
- **Context-independent test reviewer** — a dedicated agent that validates test quality against spec requirements at five pipeline checkpoints, with no access to the implementing agents' reasoning. Early testing confirmed this is the single most productive quality checkpoint in the pipeline.
- **Container isolation** — each implementation agent runs in an ephemeral Docker container with bubblewrap sandboxing
- **Context-independent agents** — test writers and implementers never share reasoning, reducing correlated failures
- **Test file immutability** — SHA-256 hash verification prevents implementation agents from weakening tests
- **Structured retrospectives** — each feature produces a retrospective with per-task results, upstream traceability, and failure attribution, enabling iterative improvement of pipeline skills and agent instructions

See [ai-docs/dispatch/dispatch-overview.md](ai-docs/dispatch/dispatch-overview.md) for the full design.

## Results

The SDL workflow has been tested through a complete greenfield project (13 features, ~80 tasks, 137 tests) and a subsequent brownfield feature addition (19 tasks, 43 new tests).

- **Features work on first human test.** The developer collaborates on the spec, the pipeline implements autonomously, and the result works. Zero corrective cycles, zero rounds of "go back and fix that." Compared to typical AI-assisted development — where comparable features require 2-5 rounds of human-guided iteration — the pipeline required zero.
- **Spec and review iterations prevent implementation problems.** The council review produced 22 findings on the brownfield feature, every one resolved before any code was written — including interface mismatches that would have caused broken rendering and an unspecified behavior that would have required post-implementation redesign. The review actively improves the design, not just validates it.
- **The test reviewer is the most productive quality checkpoint.** It caught 8 defects across 2 checkpoints in the brownfield feature alone — trivially-true assertions, conditionally skipped tests, inaccurate remediation steps. Each forced concrete improvements to the testing strategy before implementation began.
- **Implementation agents get it right on the first try.** Zero formal re-plans across ~80 greenfield tasks. 100% success rate on the cheapest model tier for simple tasks. Existing codebase conventions followed automatically in brownfield work. The upstream gates constrain tasks enough that agents succeed without iteration.
- **What the pipeline eliminates vs what remains.** *Absent*: hallucinated APIs, architectural incoherence, feature drift, test theater masking broken functionality. *Remaining*: copy-paste duplication, hardcoded magic numbers, dead code — the same cleanup-level issues you'd find in a human's first-pass PR, addressable in a single review pass.

See [ai-docs/dispatch/harness-patterns-analysis.md](ai-docs/dispatch/harness-patterns-analysis.md) for the full analysis including per-phase retrospectives and failure attribution data.

## Documentation Guide

This repo has extensive documentation across several layers. Here's where to find what you're looking for.

### Understanding the approach

| Topic | Where to look |
|-------|---------------|
| Why this exists — the problem with AI-generated code | This README (top) |
| Research basis — empirical findings on context, instructions, and agent behavior | [research.md](research.md) |
| Spec-driven development patterns — council research session on industry approaches | [ai-docs/spec-workflow.md](ai-docs/spec-workflow.md) |
| Anthropic's harness patterns — comparison with their engineering findings | [ai-docs/dispatch/harness-patterns-analysis.md](ai-docs/dispatch/harness-patterns-analysis.md) |

### How the pipeline works (reference docs)

| Stage | Guide | Gate script |
|-------|-------|-------------|
| Spec authoring | [home/dot-claude/docs/sdl-workflow/feature-spec-guide.md](home/dot-claude/docs/sdl-workflow/feature-spec-guide.md) | [spec-gate.sh](home/dot-claude/hooks/sdl-workflow/spec-gate.sh) |
| Spec review | [home/dot-claude/docs/sdl-workflow/review-perspectives.md](home/dot-claude/docs/sdl-workflow/review-perspectives.md) | [review-gate.sh](home/dot-claude/hooks/sdl-workflow/review-gate.sh) |
| Task breakdown | [home/dot-claude/docs/sdl-workflow/task-compilation.md](home/dot-claude/docs/sdl-workflow/task-compilation.md) | [breakdown-gate.sh](home/dot-claude/hooks/sdl-workflow/breakdown-gate.sh) |
| Implementation | [home/dot-claude/docs/sdl-workflow/implementation-guide.md](home/dot-claude/docs/sdl-workflow/implementation-guide.md) | [task-completed.sh](home/dot-claude/hooks/sdl-workflow/task-completed.sh) |
| Brownfield work | [home/dot-claude/docs/brownfield-breakdown.md](home/dot-claude/docs/brownfield-breakdown.md) | — |
| Corrective workflow | [home/dot-claude/docs/sdl-workflow/corrective-workflow.md](home/dot-claude/docs/sdl-workflow/corrective-workflow.md) | — |
| Test reviewer (agent) | [home/dot-claude/agents/test-reviewer.md](home/dot-claude/agents/test-reviewer.md) | [task-reviewer-gate.sh](home/dot-claude/hooks/sdl-workflow/task-reviewer-gate.sh) |

### Writing better context assets

| Asset type | Guide |
|------------|-------|
| Overview and principles | [home/dot-claude/docs/context-assets.md](home/dot-claude/docs/context-assets.md) |
| CLAUDE.md files | [home/dot-claude/docs/context-assets/claude-md.md](home/dot-claude/docs/context-assets/claude-md.md) |
| Skills | [home/dot-claude/docs/context-assets/skills.md](home/dot-claude/docs/context-assets/skills.md) |
| Hooks | [home/dot-claude/docs/context-assets/hooks.md](home/dot-claude/docs/context-assets/hooks.md) |
| Agents | [home/dot-claude/docs/context-assets/agents.md](home/dot-claude/docs/context-assets/agents.md) |

### Process artifacts (`ai-docs/`)

The `ai-docs/` directory is a working artifact, not just documentation. The pipeline's skills read and write to `ai-docs/<feature-name>/` — each feature gets a subfolder containing its spec, review, task breakdown, and retrospective. Browse `ai-docs/` to see what's been built, what's in progress, and what's planned.

| Directory | What happened there |
|-----------|-------------------|
| `ai-docs/mvp-000/` | The "seed crystal" — bootstrapping the context asset authoring guidelines |
| `ai-docs/sdl-workflow/` | The SDL workflow specifying and building itself |
| `ai-docs/dispatch/` | Dispatch pipeline design: overview, phase specs, research analysis, retrospectives |

**Dogfooding.** Firebreak is built using its own pipeline. The context asset framework produced the SDL workflow skills. The SDL workflow produced the Dispatch pipeline specs. Phase 1.5 improvements were themselves specified, reviewed, and broken down through the process they improved. The `ai-docs/` directory is the audit trail of this self-application. Where the pipeline can validate its own artifacts deterministically (gate scripts, schema checks, test suites), it does. Where it can't — agent instruction quality, prompt effectiveness, spec completeness — structured retrospectives after each feature capture what worked, what failed, and why, feeding improvements back into the skills and guides for the next run.

## Insights and Next Steps

Two rounds of testing (greenfield + brownfield) have produced a set of insights about where AI coding quality comes from and where it breaks down. These inform the next iteration of the pipeline.

### What we've learned

**Behavioral correctness and code quality are separate dimensions.** The pipeline now reliably produces code that works — zero corrective cycles in Phase 1.5, feature worked on first human test. But a post-implementation code review found 14 issues in code that passed all 172 tests. Passing tests validate behavior. They don't validate maintainability, duplication, or test integrity. Both dimensions need explicit quality interventions.

**Most code quality issues trace to task instructions, not agent capability.** When a task instruction says "simulate the drop logic," the agent faithfully simulates it — producing a test that re-implements production code inline. When a task carries a spec value as a literal number, the agent puts that literal in the code. The agent did what it was told. The fix is upstream: better instructions produce better code without requiring smarter agents.

**Task isolation prevents coordination failures but also prevents coordination benefits.** The file-scope constraint (one file per task per wave) eliminates merge conflicts. But when multiple tasks modify the same file across waves, each task independently implements similar patterns — producing copy-paste duplication. The later task has no visibility into what the earlier task added. This is a fundamental tension in the pipeline's design.

**The orchestrator file is always the highest-risk file.** Across both phases, every integration bug occurred in the orchestrator — the file that wires all modules together. Entity files, system files, and rendering files had zero issues. The orchestrator is where ordering matters, where concurrent events interact, and where duplication accumulates. It needs different handling than leaf-node files.

**Every existing reviewer already has the context to catch most code quality issues — they just aren't looking for them.** The spec reviewer reads the full spec and can flag values that will become magic numbers if carried as bare literals. The task reviewer reads all task files and can detect when multiple tasks describe the same logic block — the duplication signal is visible at the instruction level before any code exists. The test reviewer reads the spec and all test tasks and can detect when a test instruction describes the system's internal logic instead of its observable interface. Most of the code quality issues found in post-implementation review were detectable at the artifacts each upstream reviewer already reads.

### What we're exploring next

The pipeline's philosophy is defense in depth — each layer catches what previous layers missed. The upstream improvements reduce the volume of issues downstream reviewers see, but no layer makes the next one unnecessary.

**Failure mode awareness across existing reviewers.** Rather than concentrating failure mode detection in a single new stage, each existing reviewer gains a checklist of known failure mode patterns detectable from the artifacts it already reads:

- *Spec review*: Values that will cross file boundaries expressed as bare literals instead of named concepts. Behavioral descriptions that conflate how the system works with what to observe. Missing edge cases around concurrent events in stateful systems.
- *Task review*: Multiple tasks describing the same logic block (duplication visible at the instruction level). Implementation tasks carrying spec values as inline numbers instead of constant assignments. Later-wave tasks modifying a file without instructions to check for existing patterns from prior waves.
- *Test review*: Test instructions that describe the system's internal logic rather than its observable interface (exercising a code path vs reproducing it). Assertions that compute expected values using the same formula as production code. OR-condition assertions where one branch is trivially true. Test names that don't match what the assertion verifies.

These are framed at the archetype level — the patterns that produce the failure modes, not the specific instances we observed. Each needs careful calibration to avoid over-tuning toward individual sightings.

**Post-implementation code review stage.** The last line of defense for issues that only surface from reading implemented code — the same role code review plays on human development teams. Council agents (Architect + Guardian) reviewing against an AI failure mode checklist, positioned between final verification and commit. Upstream improvements reduce its workload; they don't eliminate its purpose. A code reviewer that consistently finds nothing is evidence the upstream layers are working, not evidence the reviewer is unnecessary.

**Lint integration.** Language-specific but high-value for catching dead code, unused variables, and style violations automatically. Exploring convention-based discovery (detect the project's existing lint setup) or CLAUDE.md-declared lint commands. Design constraint: lint failures should be feedback to the agent (retry with output), not a hard block.

See [ai-docs/dispatch/harness-patterns-analysis.md](ai-docs/dispatch/harness-patterns-analysis.md) for the detailed retrospective data behind these insights.

## Research Basis

The design is grounded in empirical research on how LLMs handle instructions and context:

- **Context pollution is measurable.** LLM-generated context files reduce task success by 0.5-2% while increasing costs 20-23%. Even a single irrelevant distractor degrades performance (AGENTbench, 2025; Chroma Context Rot, 2025).
- **Compression helps.** Vercel found that 40KB of context compressed to 8KB with zero accuracy loss. Longer inputs independently degrade performance even with perfect retrieval (EMNLP Findings, 2025).
- **Progressive disclosure is the recommended approach.** Anthropic's own guidance advocates progressive context discovery over upfront loading (Codified Context, 2026).
- **Scoped, relevant context helps.** Focused context files improved efficiency by ~28.6% for small, targeted tasks (AGENTbench, 2025).
- **Structured artifacts constrain agent behavior.** Independent research from Anthropic confirms that structured external state and constrained interfaces are the most effective interventions for long-running agent quality ([Effective Harnesses for Long-Running Agents](https://www.anthropic.com/engineering/effective-harnesses-for-long-running-agents), 2025).

See [research.md](research.md) for the full analysis with citations and methodology.


## Feedback

This project is under active development and testing. If you try it out, find issues, or have ideas:

- [Open an issue](https://github.com/teknoll/firebreak/issues) with bug reports, feature suggestions, or questions
- If you run the SDL workflow on your own project, I'd like to hear how it went — what worked, what didn't, and where the friction was

## License

MIT — see [LICENSE](LICENSE).
