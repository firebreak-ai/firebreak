## The Necessity Test

For every instruction, ask: **"If this instruction were removed, is the agent more likely to make a mistake?"**

- **Yes** — keep it.
- **No** — remove it.

Include only instructions that prevent mistakes. Filter out:

1. Behavior the agent already produces correctly by default.
2. Descriptions or explanations that do not change behavior.
3. Aspirational guidelines the agent cannot act on.
4. Redundant restatements of what the codebase already makes obvious.

Apply this test recursively — every sentence in every context asset must earn its place by preventing a concrete mistake.

Apply the test relative to the asset's scope — an instruction in `~/.claude/` must prevent mistakes across all projects.

Security-defensive instructions may pass the test even when they seem unnecessary under normal conditions.

## Progressive Disclosure

Load context in layers, not all at once.

| Tier | Role | Loaded |
|------|------|--------|
| **Always-on** (CLAUDE.md) | Concise instructions that apply every session at this scope. Must pass the Necessity Test at maximum strictness. | Always (auto-loaded) |
| **Index** (.claude/docs/\<topic>.md) | Map tasks to leaf file paths. Include principles that apply to all subtopics. | On demand, when topic is relevant |
| **Leaf** (.claude/docs/\<topic>/\<subtopic>.md) | Detailed, self-contained instructions for one concern. | On demand, when specific subtopic is needed |

Route to the narrowest relevant file. Load only what the current task requires.

## Separation of Concerns

Separate triggers from content. Choose each independently.

Keep one file to one concern. A doc covering both coding standards and Git workflow belongs as two separate files.

Inline content when a single trigger is the sole consumer and the content is small. Extract to `.claude/docs/` when multiple triggers share the content or the content is too large to inline.

Partition concerns so each constraint appears in exactly one file.

## Trust the Agent's Native Capabilities

Provide direction, not description. The agent can search files, read code, and trace dependencies on its own.

Route the agent to context it cannot infer. Omit descriptions of code structure the agent discovers through search and reading.

Include only what the agent cannot figure out alone:

- Project-specific rules
- Non-obvious conventions
- Architectural decisions not self-evident from the code
- Routing to the right context at the right time

## Choose the Right Trigger and Content Strategy

### Trigger types

| Trigger | Activation | Example |
|---------|-----------|---------|
| **CLAUDE.md** | Every session, automatically | Universal routing references, critical one-liner rules |
| **Rules** (.claude/rules/*.md) | Auto-loaded; `paths:` frontmatter scopes to file patterns | Go coding standards triggered only when touching `**/*.go` |
| **Skills** (.claude/skills/) | User invokes a slash command, or agent loads via description match (`user-invocable: false`) | User-initiated workflows; reference knowledge loaded on relevance |
| **Hooks** (.claude/settings.json) | Specific tool events (pre/post) | Automated checks, enforcement on agent actions |
| **Agents** (.claude/agents/) | Spawned as a subagent | Specialized personas or delegated workflows |

### Content strategies

| Strategy | When to use |
|----------|------------|
| **Inline** (content inside the trigger) | The trigger is the sole consumer. A skill that owns its own instructions. |
| **Referenced** (trigger points to a `.claude/docs/` file) | Multiple triggers need the same content, or content is detailed enough to warrant separation. |
| **Routing table** (trigger points to an index, index points to leaves) | A topic has multiple subtopics; the agent loads only the relevant one. |

### Key considerations

The agent merges context from global (`~/.claude/`) and project (`<project>/.claude/`) scopes into a single session. Place instructions at the narrowest scope where they apply. Check for repetition and conflicts across layers.

Match trigger to activation condition:

- Every session → CLAUDE.md
- Touching specific file types → rule with `paths:`
- User asks for a workflow → skill
- Agent performs a specific action → hook
- Working on a topic → doc referenced from a routing table

Scope rules with `paths:` at project level when the content is conditional. A rule without `paths:` loads every session, identical to CLAUDE.md.

Files in `.claude/docs/` load only when the agent reads them in response to a routing instruction.

When a retrospective documents a behavioral gap that was already addressed by a prior corrective action, escalate enforcement from a rule or doc instruction to a hook.

## Write for Agents, Not Humans

Start with the first instruction.

Default to imperatives. Include background context only when it prevents a mistake.

Use direct address. Write "Use X when Y" — not "Developers should use X when Y."

Frame every instruction positively. Write "Use `const` for immutable bindings" — not "Don't use `var`." When a prohibition is necessary, pair it with the positive alternative.

Keep each instruction to a single verifiable constraint. Split compound rules into separate statements.

Review heuristic: **"Is this sentence written for the agent that will load it, or for a human browsing the repo?"**

---

## Routing Table

| When you are... | Read |
|-----------------|------|
| Writing or modifying a CLAUDE.md file | `fbk-context-assets/claude-md.md` |
| Writing or modifying a rule | `fbk-context-assets/rules.md` |
| Writing or modifying a skill | `fbk-context-assets/skills.md` |
| Writing or modifying a hook | `fbk-context-assets/hooks.md` |
| Writing or modifying an agent | `fbk-context-assets/agents.md` |
| Writing or modifying a docs/ file (index or leaf) | `fbk-context-assets/referenced-docs.md` |

---

## Instruction Writing Checklist

- **Show when telling fails**: Use 2-3 examples for style, format, or tone. Use declarative rules for unambiguous constraints.
