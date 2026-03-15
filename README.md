# Firebreak

**AI coding agents produce worse code than humans.** AI-generated PRs contain 1.7x more issues and 1.57x more security vulnerabilities than human-written PRs. AI-assisted development correlates with doubled code churn, ~8x growth in duplicated code blocks, and a 60% collapse in refactoring activity. The most dangerous failure mode — code that runs but produces wrong results — is increasing.

Most teams try to fix this with post-implementation gates: tests, linting, code review. Firebreak takes a different approach: **front-load human judgment into structured artifacts before agents write any code**, then constrain agents to implement against well-defined criteria with deterministic verification gates. Prevention is less costly than repair.

```
Spec ─► Review ─► Breakdown ─► Test Creation ─► Test Review ─► Implementation ─► Verification ─► PR
         ▲                          ▲                ▲                                  ▲
     council +               context-independent   pipeline-         deterministic checks +
     agentic review          test-writing agents   blocking          mutation testing +
                                                   gate              test immutability
```

A core design principle is **context and persona isolation between agents**. When the same agent designs tests and writes the implementation, its tests tend to validate its own reasoning rather than the spec's intent. By using separate agents with independent context for test authoring, implementation, and review, correlated failures are structurally reduced. Each agent can only see what it needs, and no agent reviews its own work.

**Many pipeline stages does not mean many user interactions.** The developer collaborates during spec authoring — that's where human judgment has the highest leverage. After that, the pipeline advances autonomously: council review runs without prompting, breakdown compiles and gates check automatically, test creation and implementation proceed through agent teams. The developer's next interaction is reviewing the results. The goal is rigorous code quality with minimal user friction — the pipeline does the work, not the developer.

The current friction point is permissions prompts, which are being iteratively reduced through data-driven tuning of tool access allowlists. As the Dispatch pipeline matures toward full autonomy, the vision is an autonomous developer that works on approved specifications to completion around the clock — combining structured quality gates with hands-off execution.

## Status

| Layer | Status | Description |
|-------|--------|-------------|
| Context Asset Framework | **Working** | Authoring guidelines, progressive disclosure, skills, hooks, docs |
| SDL Workflow | **Working** | `/spec`, `/spec-review`, `/breakdown`, `/implement` with deterministic gates |
| Dispatch Pipeline | **In testing** | Phase 1 (pipeline core) under active testing against real projects |

The project has three layers, each built using the one before it. The authoring framework produced the SDL workflow. The SDL workflow produced Dispatch's first phase. As Dispatch matures, future phases will be implemented using the updated pipeline — the process bootstraps itself up the complexity ladder.

## Quick Start

Copy the context assets to your Claude Code configuration:

```bash
cp -r home/.claude/* ~/.claude/
```

### Context Asset Authoring (works in any project)

Even without the SDL workflow, Firebreak includes a research-based prompt engineering framework for writing better context assets — CLAUDE.md files, agent definitions, skills, hooks, and rules. It applies findings from empirical research on instruction density, context pollution, and progressive disclosure to help you write context assets that produce measurably better agent behavior.

Invoke it with `/context-asset-authoring`, or just start talking about creating or improving context assets — "help me write a CLAUDE.md", "create a new skill", "improve my agent definition." The skill loads detailed, research-backed guidelines automatically.

### SDL Workflow

The spec-driven development lifecycle applies to any code change where correctness and maintainability matter — new features, bug fixes, refactoring. A bug fix is a spec with a root cause analysis, a test plan review asking "were the tests wrong or missing?", and a constrained implementation. The stages are the same; the scope at each stage is smaller.

Four slash commands, each advancing through a verification gate before the next stage can begin:

| Command | What it does | What it produces |
|---------|-------------|-----------------|
| `/spec` | Co-author a specification with structured sections, acceptance criteria, and a testing strategy | A spec document in `ai-docs/` |
| `/spec-review` | Run council review (architect, security, guardian, advocate, analyst perspectives) | Review findings with pass/fail determination |
| `/breakdown` | Compile the reviewed spec into sized, wave-assigned implementation tasks | Individual task files and a task manifest |
| `/implement` | Execute tasks with parallel agent teams, wave-based sequencing, and per-wave verification | Implemented code with passing tests |

You can invoke these directly with the slash commands, or use natural language — talking about designing a new feature, fixing a bug, writing a specification, reviewing a spec, breaking down tasks, or implementing a change will trigger the appropriate skill automatically.

If you find that a natural language phrase you expected to trigger a skill didn't, [please report it](https://github.com/teknoll/firebreak/issues) — we're actively tuning trigger coverage based on how different users talk to Claude Code.

## How It Works

### 1. Context Asset Authoring Framework

Guidelines that teach agents how to write well-structured context assets, following their own principles — progressive disclosure, minimal instruction density, and separation of concerns.

**The problem:** Developers put all instructions into a single monolithic file. Research shows this hurts agent performance. Irrelevant instructions degrade output quality even when the context window has plenty of room — a phenomenon called **context pollution**. Every instruction competes for the model's attention, so unnecessary ones actively interfere with the instructions that matter.

The guidelines live in `home/.claude/docs/context-assets/` as leaf documents (one per asset type), with an index at `home/.claude/docs/context-assets.md` that routes to the right leaf based on the current task.

### 2. SDL Workflow: Spec-Driven Development Lifecycle

A 4-stage interactive pipeline: **Spec → Review → Breakdown → Implement**. Each stage has a dedicated skill, deterministic verification gates (shell scripts), and structured artifact output.

Key design decisions, informed by [research](research.md):
- **Deterministic gates over AI self-review** — verification value comes from tests, linters, and schema checks, not from an AI re-reading its own output
- **External feedback at every iteration** — human judgment, test results, lint output, or council agents with distinct perspectives
- **Wave-based parallel implementation** — tasks decomposed into dependency waves, executed by agent teams with per-wave verification
- **Capped retry loops** — 2 re-plans per task, then escalate to human

The workflow assets live in `home/.claude/skills/` (skills), `home/.claude/hooks/sdl-workflow/` (gates), and `home/.claude/docs/sdl-workflow/` (stage guides).

### 3. Dispatch: Autonomous Pipeline Orchestration

The next evolution — an autonomous pipeline that drives specs from queue to PR without human intervention at intermediate stages. The developer's last judgment call is spec review; after that, the pipeline handles breakdown, test creation, test review, implementation, verification, and PR creation autonomously.

Dispatch extends the SDL workflow with:
- **10-stage pipeline** with deterministic and agentic gates at every transition
- **Container isolation** — each implementation agent runs in an ephemeral Docker container with bubblewrap sandboxing
- **Five-checkpoint test validation** — test strategy, test tasks, test code, test integrity, and mutation testing
- **Context-independent agents** — test writers and implementers never share reasoning, reducing correlated failures
- **Test file immutability** — SHA-256 hash verification prevents implementation agents from weakening tests

See [ai-docs/dispatch/dispatch-overview.md](ai-docs/dispatch/dispatch-overview.md) for the full design.

## Process Artifacts (`ai-docs/`)

The `ai-docs/` directory contains the plans, specs, task breakdowns, research, and analysis that produced this project — left in place as examples of the SDL workflow in action and as documentation of design decisions.

| Directory | Contents |
|-----------|----------|
| `ai-docs/mvp-000/` | Plan and task breakdown for the context asset authoring guidelines — the "seed crystal" that bootstrapped the project |
| `ai-docs/sdl-workflow/` | Full spec and task breakdown for the SDL workflow itself |
| `ai-docs/dispatch/` | Dispatch pipeline design: overview spec, phase specs, task breakdowns, review artifacts, failure mode analysis, and external research analysis |
| `ai-docs/spec-workflow.md` | Council research session analyzing spec-driven development patterns against industry findings |

## Repository Structure

The `home/` directory mirrors what gets installed to `~/.claude/` — it represents a user's global Claude Code configuration.

```
home/
├── .claude/
│   ├── settings.json              # Hook registrations
│   ├── agents/                    # Agent definitions (test-reviewer)
│   ├── docs/
│   │   ├── context-assets.md      # Index: authoring guidelines
│   │   ├── context-assets/        # Leaves: one per asset type
│   │   ├── sdl-workflow.md        # Index: pipeline principles
│   │   └── sdl-workflow/          # Leaves: stage guides, schemas
│   ├── skills/
│   │   ├── context-asset-authoring/  # Triggers authoring guidelines
│   │   ├── spec/                     # /spec — feature specification
│   │   ├── spec-review/              # /spec-review — council review
│   │   ├── breakdown/                # /breakdown — task compilation
│   │   └── implement/                # /implement — wave execution
│   └── hooks/
│       └── sdl-workflow/          # Verification gate scripts

ai-docs/                           # Process artifacts and specs
tests/                             # Test suites and fixtures
research.md                        # Research basis with citations
```

## Progressive Disclosure

Instead of loading everything upfront, context is structured as a hierarchy where agents load only what they need:

```
CLAUDE.md (auto-loaded, minimal router)
 └─ references → .claude/docs/<topic>.md (index with routing table)
      └─ references → .claude/docs/<topic>/<subtopic>.md (leaf with detailed instructions)
```

| Tier | Role | Loaded |
|------|------|--------|
| **Router** (CLAUDE.md) | Lists topics with file references. No detailed instructions. | Always (auto-loaded) |
| **Index** (.claude/docs/topic.md) | Maps tasks/conditions to leaf file paths. Includes principles that apply across subtopics. | On demand, when the topic is relevant |
| **Leaf** (.claude/docs/topic/subtopic.md) | Detailed, self-contained instructions for one concern. | On demand, when the specific subtopic is needed |

The agent starts with the lightweight router, follows a reference when a topic is relevant, then loads only the specific leaf it needs. Most context never enters the window at all.

## Research Basis

The design is grounded in empirical research on how LLMs handle instructions and context:

- **Context pollution is measurable.** LLM-generated context files reduce task success by 0.5-2% while increasing costs 20-23%. Even a single irrelevant distractor degrades performance (AGENTbench, 2025; Chroma Context Rot, 2025).
- **Compression helps.** Vercel found that 40KB of context compressed to 8KB with zero accuracy loss. Longer inputs independently degrade performance even with perfect retrieval (EMNLP Findings, 2025).
- **Progressive disclosure is the recommended approach.** Anthropic's own guidance advocates progressive context discovery over upfront loading (Codified Context, 2026).
- **Scoped, relevant context helps.** Focused context files improved efficiency by ~28.6% for small, targeted tasks (AGENTbench, 2025).
- **Structured artifacts constrain agent behavior.** Independent research from Anthropic confirms that structured external state and constrained interfaces are the most effective interventions for long-running agent quality ([Effective Harnesses for Long-Running Agents](https://www.anthropic.com/engineering/effective-harnesses-for-long-running-agents), 2025).

See [research.md](research.md) for the full analysis with citations and methodology.

## Security

The `.claude/` directory and `CLAUDE.md` files are instruction files — they influence agent behavior. Treat them the same way you treat code: review `.claude/` contents in repositories you didn't author, and scrutinize `.claude/` changes in pull requests just as carefully as code changes. These files are a documented prompt injection vector.

## Feedback

This project is under active development and testing. If you try it out, find issues, or have ideas:

- [Open an issue](https://github.com/teknoll/firebreak/issues) with bug reports, feature suggestions, or questions
- If you run the SDL workflow on your own project, I'd like to hear how it went — what worked, what didn't, and where the friction was

## License

MIT — see [LICENSE](LICENSE).
