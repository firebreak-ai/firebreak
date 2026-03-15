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

## Scope

Global agents (`~/.claude/agents/`) apply to all projects for that user. Place project-specific agents at project level (`.claude/agents/`). Apply the Necessity Test more strictly at global scope — the agent definition must be correct across every project.

## Security

Use `permissionMode: dontAsk` to auto-deny permission prompts rather than granting broad permissions with `bypassPermissions`.

Use `PreToolUse` hooks to validate specific operations when you need finer control than tool-level allow/deny lists provide.

Place project-level agents in `.claude/agents/` and commit them to version control so changes are visible in code review. User-level agents in `~/.claude/agents/` bypass team review -- use project-level agents for shared workflows.
