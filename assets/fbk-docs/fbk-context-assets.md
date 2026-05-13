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

A second test — the **per-load-path Necessity Test** — applies in conjunction with this one. See Progressive Disclosure below.

## Progressive Disclosure

Progressive disclosure is the discipline of preventing context pollution by ensuring agents load only instructions relevant to the current task. Apply it aggressively when authoring or modifying any context asset.

### Declare the load condition

Every asset must have an explicit load condition. Trigger-bearing assets declare it via their trigger mechanism: CLAUDE.md (session start or subagent spawn), skills (invocation or description match), rules (`paths:` match), agents (spawn), hooks (event match). Reference assets (leaves) declare it via the routing instruction that loads them, in `when <condition> read <file>` form. Write the load condition before writing instructions, then verify each instruction against it.

### Strict relevance test

Every instruction in a loaded asset must apply every time the asset loads. An instruction that applies only sometimes belongs in a separately-routed asset gated by its sub-condition. Not 90%, not "the primary use case" — every load.

### Per-load-path Necessity Test

Given the other assets already loaded on this work path, does each instruction add new behavior? An instruction that another loaded asset already covers fails this test. Apply it alongside the per-instruction Necessity Test at the top of this document — both must pass; order does not matter.

### Trigger assets and reference assets

Assets load in two ways. **Trigger-bearing assets** load on an event; their content must apply whenever the trigger fires. **Reference assets** load only when another asset routes to them; their content must apply whenever the parent's routing condition holds — which means content must be valid under *every* parent route that leads here. A reference asset reachable from three routing conditions must contain only instructions valid under all three. Condition-specific content extracts to deeper sub-leaves.

### Routing is tree-shaped

Reference assets can route to deeper reference assets. Routing tables at any stage are *stage-local* indexes — they list the conditions available at that point in the navigation, not all assets in the system. Centralized indexes are not required and often counterproductive. Each routing decision happens at its own scope, narrowing as the agent's task narrows.

### In-asset conditional exception

Extraction to a separately-routed asset is the default. An in-asset conditional ("only do X when Y") is permitted only when extracting it would create more friction *for the agent that needs the instructions* than the conditional itself imposes — for example, a one-line domain note that does not justify a routing hop. Maintenance friction is not a justification. Testing friction (keeping routing references valid) is accepted as the cost of separation.

### Worked example

**Wrong.** A single `testing-guidelines.md` leaf contains:

> ## Writing unit tests
> [unit-test-specific instructions]
>
> ## Writing integration tests
> [integration-test-specific instructions]

Loaded by every agent writing tests. Half the content is irrelevant on any given task — unit-test authors load integration-test guidance, and vice versa.

**Right.** A `testing-guidelines.md` index routes:

> When writing unit tests, read `testing-guidelines/unit.md`.
> When writing integration tests, read `testing-guidelines/integration.md`.

Each leaf loads only when its specific condition holds. The agent's context window carries only what applies to the current task.

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

## Objectives over Procedural Steps

State the agent's objective and a measurable acceptance criterion. Enumerate procedural steps only when step order matters for correctness — runbooks, deterministic verification sequences, audit trails.

Pair every objective with a measurable acceptance criterion that operationalizes "what good looks like" in checkable terms. Without one, the agent fills the gap with a statistically likely completion, and the drift compounds across steps.

| Drift-prone | Drift-resistant |
|-------------|-----------------|
| "Be concise" | "Under 75 words; action and deadline only" |
| "Find issues" | "Find any bug that could cause incorrect behavior, a test failure, or a misleading result" |

Output-structure prescription is not procedural prescription. Constraining the deliverable shape (required sections, schema, output fields) is compatible with leaving the path to the agent's reasoning.

Workflow content — sequenced steps, deterministic protocols, runbooks — lives in skills, referenced docs, or the spawn prompt that invokes an agent. It does not live in an agent definition body. The orchestrator composes persona (from the agent definition) and workflow (from a skill, doc, or spawn prompt) at spawn time. Embedding workflow in an agent body pre-empts that composition and forces every invocation of that agent through the same workflow regardless of the orchestrator's intent. When the workflow is small and has one consumer, route it via the spawn prompt — `## Separation of Concerns` governs the inline-vs-extract decision for workflow content the same way it does for instruction content.

*Backed by `anthropic-2026-prompting-best-practices` — "Prefer general instructions over prescriptive steps." Failure-mode analysis: `cemri-2025-multi-agent-systems-fail`. Output-structure refinement: `ugare-2026-agentic-code-reasoning`.*

## Choose the Right Trigger and Content Strategy

### Trigger types

| Trigger | Activation | Example |
|---------|-----------|---------|
| **CLAUDE.md** | Every session, automatically | Universal routing references, critical one-liner rules |
| **Rules** (.claude/rules/*.md) | Auto-loaded; `paths:` frontmatter scopes to file patterns | Go coding standards triggered only when touching `**/*.go` |
| **Skills** (.claude/skills/) | User invokes a slash command, or agent loads via description match (`user-invocable: false`) | User-initiated workflows; reference knowledge loaded on relevance |
| **Hooks** (.claude/settings.json) | Specific tool events (pre/post) | Automated checks, enforcement on agent actions |
| **Agents** (.claude/agents/) | Spawned as a subagent | Specialized personas (workflow comes from skills, docs, or the spawn prompt at composition time) |

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

Remove bias-sources by restructuring the asset rather than instructing the agent to disregard them. Anchoring operates at shallow processing layers below instruction-following control, so "ignore the previous example", "be objective", and "don't be influenced by X" do not work. Restructure instead: drop the offending example, balance with diverse alternatives, or reorder so the bias-source is not in a high-attention position.

*See `huang-2026-anchoring-effect-llm`.*

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
