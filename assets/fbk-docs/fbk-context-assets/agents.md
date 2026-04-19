Constrain every agent to the minimum required tool set using `tools` or `disallowedTools`.
Write a clear, specific `description` -- Claude uses it to decide when to delegate.
## Agent Definition Structure

Place agent files in `.claude/agents/<name>.md` (project-level) or `~/.claude/agents/<name>.md` (user-level). Use Markdown with YAML frontmatter.

### Frontmatter fields

| Field | Required | Purpose |
|-------|----------|---------|
| `name` | Yes | Unique identifier, lowercase letters and hyphens |
| `description` | Yes | When Claude should delegate to this agent |
| `tools` | No | Allowlist of tools the agent can use. Inherits all tools if omitted |
| `disallowedTools` | No | Denylist -- tools removed from inherited or specified list |
| `model` | No | `sonnet`, `opus`, `haiku`, or `inherit` (default: `inherit`) |
| `permissionMode` | No | `default`, `acceptEdits`, `dontAsk`, `bypassPermissions`, or `plan` |
| `maxTurns` | No | Maximum agentic turns before the agent stops |
| `skills` | No | Skills to preload into the agent's context at startup |
| `mcpServers` | No | MCP servers available to this agent |
| `hooks` | No | Lifecycle hooks scoped to this agent (PreToolUse, PostToolUse, Stop) |
| `memory` | No | Persistent memory scope: `user`, `project`, or `local` |
| `background` | No | `true` to always run as a background task |
| `isolation` | No | `worktree` to run in an isolated git worktree |

### Body content

The Markdown body below the frontmatter becomes the agent's system prompt.

Focus the body on what makes this agent different from the default: its role, constraints, and behavioral boundaries. Avoid duplicating general project knowledge the agent can read from CLAUDE.md or discover from the codebase.

## When to Use an Agent vs. Alternatives

### Decision guide

| Signal | Use |
|--------|-----|
| Task needs tool restrictions or a focused persona | Agent |
| Task produces verbose output that should stay out of main context | Agent |
| Task needs reusable instructions or reference knowledge | Skill |
| Behavior should activate when touching specific file types | Rule with `paths:` |
| Behavior should apply to every session unconditionally | Rule without `paths:` or CLAUDE.md |

### Key constraints

Agents cannot spawn other agents. If a workflow requires nested delegation, chain agents from the main conversation or use skills instead.

Agents do not inherit skills from the parent conversation. Preload needed skills explicitly using the `skills` frontmatter field.

## Capability Scoping

Start restrictive. Grant only the tools the agent demonstrably needs.

Give an analysis-only agent read-only tools: `tools: Read, Grep, Glob`. Omit Write, Edit, and Bash.

Use `disallowedTools` when the agent needs most tools but a few should be excluded:

```yaml
tools: Read, Edit, Bash, Grep, Glob
disallowedTools: Write
```

Use `Task(agent-type)` syntax in `tools` to restrict which subagent types a main-thread agent can spawn:

```yaml
tools: Task(worker, researcher), Read, Bash
```

Use `permissionMode: plan` for agents that should only explore and plan, with no modification capability.

For conditional tool restrictions (allow some uses of a tool but block others), use `hooks` with `PreToolUse` validators instead of blanket allowlists.

## Instruction Design

State the agent's role and scope in the first lines of the body. Place critical constraints before detailed instructions.

Tell the agent what to do when invoked -- provide a clear workflow or checklist of steps.

Write the `description` field using specific, matchable language that mirrors how users phrase relevant tasks.

Include "use proactively" in the description if the agent should be invoked automatically for relevant tasks.

Personas belong in the body; see `## Persona authoring` for activation-focused structure.

### Example structure

```markdown
---
name: test-runner
description: Runs tests and reports failures. Use proactively after code changes.
tools: Read, Bash, Grep, Glob
model: sonnet
---

Run the project test suite and report results.

1. Run the full test suite using the project's test command.
2. If tests fail, identify root causes by reading failing test files and related source.
3. Report only failing tests with error messages and suggested fixes.

Report findings only. Leave source and test files unmodified.
```

## Persona authoring

An agent's persona shapes which training distribution the model draws from when producing output. Without persona activation, agents default to the demo/tutorial distribution that dominates training data. A persona that grounds the agent in an enterprise professional role activates a smaller but higher-quality distribution — one characteristic of production codebases, professional engineering documentation, and senior-engineer code review.

### Enterprise activation as the baseline

Every agent persona grounds the agent in a professional role within an enterprise software development organization. This is the single highest-leverage persona instruction — it shifts the output distribution from demo-grade to production-grade along quality dimensions the pipeline cannot gate deterministically: maintainability, code structure, naming clarity, appropriate abstraction levels, and professional standards. The role activation line names the seniority level, the domain, and the enterprise context. Domain specialization (architecture, security, testing, implementation) layers on top of this baseline.

### Correctness vs. maintainability

Persona activation improves maintainability (reduced code smells, cyclomatic and cognitive complexity) while correctness is neutral to slightly reduced. This is the intended tradeoff for Firebreak: the pipeline's deterministic gates (spec gates, test-first development, per-wave verification, mutation testing) engineer correctness. Personas cover the gap those gates cannot reach. The detailed research rationale is documented in `ai-docs/agent-personas/agent-personas-spec.md`.

### Structure of an effective persona

An effective persona has three components:

1. **Role activation** (1-2 sentences): Ground the agent in a senior professional role within an enterprise engineering organization. Name the expertise level and domain. This is the single most impactful line — it determines which training distribution the model draws from. Example: "You are a staff engineer at an enterprise software company who writes maintainable, production code that other engineers can pick up and work with."
2. **Output quality bars** (3-6 items): State what the output must demonstrate, not how to produce it. Each bar is a falsifiable output constraint — "when the output X, Y is incomplete" — not a role grant ("you have standing authority to..."). The output either meets the bar or does not.
3. **Anti-defaults** (1-3 items, optional): Name the specific default behavior the persona counteracts. Include only when the default is both likely and harmful.

### Personas and spawn prompts

The persona defines what quality the output demonstrates. The spawn prompt defines what the task is and what format to use. Quality bars and anti-defaults belong in the persona; task details, output format, and workflow steps belong in the spawn prompt. When both address the same concern, the persona's quality bar takes precedence.

### Reference implementations

The Detector (`.claude/agents/fbk-code-review-detector.md`) and Challenger (`.claude/agents/fbk-code-review-challenger.md`) are the canonical examples of the activation-focused pattern. The Challenger is especially concise — role activation line, two quality outcomes, no section headings — demonstrating the minimal effective persona.

### What not to include

Do not include:

- Expertise lists (the model already has the knowledge; the role activation line selects the distribution)
- Communication style guidance (quality bars constrain output better than style descriptions)
- Personality descriptions (narrative, not activation)
- Generic professional advice (true of all professional communication; adds no activation signal)
- Authority grants inside quality bars (place authority grants in `## Authority`; quality bars state what output must demonstrate, not what the agent is permitted to do)

### When a persona is unnecessary

A persona adds value when the model's default distribution produces noticeably lower quality than the activated distribution. For purely mechanical tasks (sighting deduplication, format validation, file enumeration), a persona is unnecessary — the task instructions are sufficient.

## Scope

Global agents (`~/.claude/agents/`) apply to all projects for that user. Place project-specific agents at project level (`.claude/agents/`). Apply the Necessity Test more strictly at global scope — the agent definition must be correct across every project.

## Security

Use `permissionMode: dontAsk` to auto-deny permission prompts rather than granting broad permissions with `bypassPermissions`.

Use `PreToolUse` hooks to validate specific operations when you need finer control than tool-level allow/deny lists provide.

Place project-level agents in `.claude/agents/` and commit them to version control so changes are visible in code review. User-level agents in `~/.claude/agents/` bypass team review -- use project-level agents for shared workflows.
