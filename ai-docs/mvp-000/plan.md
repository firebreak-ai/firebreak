# Plan: Context Assets — Bootstrap / Seed Crystal

## Problem

Developers using Claude Code commonly overload CLAUDE.md with all possible instructions, causing **context pollution** — irrelevant instructions degrade output quality even when the context window isn't full. The agent must filter signal from noise, increasing non-determinism and hallucination rates.

### Empirical evidence

**AGENTbench** — ["Evaluating AGENTS.md"](https://arxiv.org/html/2602.11988v1) (2025, 138 tasks across 12 Python repositories):

- **LLM-generated context files reduce task success by 0.5-2%** while increasing inference costs by 20-23%.
- **Developer-written context files provide marginal improvement** (~4% on average) and still increase costs up to 19%.
- **Redundancy is the core problem**, not context itself. When existing documentation was removed, LLM-generated context files *improved* performance by 2.7% — context helps when it's not duplicating what's already available.
- Context files cause agents to **spend more reasoning tokens** (2-22% increase depending on model and context source) without proportional quality gains.
- **Specific tooling instructions work.** Tools mentioned in context files were used 1.6x more frequently; repository-specific tools increased 2.5x. Targeted, actionable instructions produce measurable behavioral change.
- Broad "overview" sections **fail to help agents discover relevant files** effectively.
- The paper recommends: **include only minimal, essential requirements** — specific tooling instructions and necessary constraints.

**Complementary findings:**

- ["On the Impact of AGENTS.md Files"](https://arxiv.org/html/2601.20404v1) (2025, single agent, 10 repositories) found context files *improved* efficiency by ~28.6% in wall-clock time for small, focused pull requests. Note: this measured speed, not correctness. Consistent with the idea that **scoped context can help for constrained tasks**.
- [Chroma: "Context Rot"](https://research.trychroma.com/context-rot) (2025, 18 LLMs) confirmed that even a single irrelevant distractor degrades performance, and degradation is non-linear — independently validating the context pollution concern.
- [Anthropic's own guidance](https://www.anthropic.com/engineering/effective-context-engineering-for-ai-agents) advocates progressive context discovery over upfront loading, describing CLAUDE.md as "naively dropped into context up front."

**Additional research (from parallel research agents — see `research.md` for full analysis):**

- [IFScale: "How Many Instructions Can LLMs Follow at Once?"](https://arxiv.org/abs/2507.11538) (2025, 20 models, densities from 10 to 500): Frontier reasoning models maintain near-perfect instruction-following through ~150 simultaneous constraints, then decline. Non-reasoning models decay earlier — some collapse exponentially to a 7-15% accuracy floor. Even the best model (Gemini 2.5 Pro) achieved only 68% accuracy at 500 instructions. Instructions later in the list are more likely to be ignored (primacy effect).
- [Liu et al.: "Lost in the Middle"](https://aclanthology.org/2024.tacl-1.9/) (TACL 2024): U-shaped attention curve — information at the beginning and end of context is best retained. Mid-context performance dropped *below the no-context baseline* for some models.
- [Gadlet: positive vs. negative framing](https://gadlet.com/posts/negative-prompting/); [MIT/NegBench](https://news.mit.edu/2025/study-shows-vision-language-models-cant-handle-negation-words-queries-0514) (CVPR 2025): Negative instructions ("don't do X") are measurably less effective than positive reframings ("do Y instead"). Token generation is inherently a positive selection process.
- [DeCRIM](https://aclanthology.org/2024.findings-emnlp.458/) (EMNLP 2024); [InFoBench](https://aclanthology.org/2024.findings-acl.772/) (ACL 2024): Decomposing instructions into individually-checkable constraints improved instruction-following by 7-8%. Intrinsic self-correction without decomposed criteria is unreliable and can degrade output.
- [Vercel: "AGENTS.md Outperforms Skills"](https://vercel.com/blog/agents-md-outperforms-skills-in-our-agent-evals): Passive 8KB AGENTS.md achieved 100% pass rate vs. on-demand skills at 79% — agents frequently failed to invoke skills even when available. 40KB compressed to 8KB with zero accuracy loss.
- ["Codified Context"](https://arxiv.org/abs/2602.20478) (2026, 108K-line C# system, 283 sessions): Single-file manifests do not scale. Uses three-tier architecture: hot-memory constitution + domain-expert agents + on-demand knowledge base — independently validating the progressive disclosure pattern.
- [Prompt injection in agentic coding](https://arxiv.org/html/2601.17548) (2025); [OWASP LLM cheat sheet](https://cheatsheetseries.owasp.org/cheatsheets/LLM_Prompt_Injection_Prevention_Cheat_Sheet.html): Repository-level instruction files are a documented prompt injection vector. Adaptive injection bypasses 90%+ of published defenses. Real defense is architectural (capability restriction, human review), not instructional.
- [SCOPE: Prompt Evolution](https://arxiv.org/abs/2512.15374) (2025): Automatically-evolved prompts improved task success from 14% → 39% (HLE) and 33% → 57% (GAIA). Static, write-once instruction files are inherently limited — iterative refinement from observed failures produces measurably better outcomes.
- [Context length alone hurts](https://arxiv.org/abs/2510.05381) (EMNLP Findings 2025): Even with perfect retrieval, longer inputs independently degrade performance. There is no safe "just in case" extra context.

**Key takeaway**: Monolithic, always-loaded context files hurt performance. Scoped, relevant context helps. Progressive disclosure is a reasonable approach to deliver scoped context, though the specific routing hierarchy proposed here has not been empirically tested — it is an application of these validated principles, not a validated technique itself.

## Core Principles

### 1. The Necessity Test

For every instruction in a context asset, ask: **"If this instruction were removed, is the coding agent more likely to make a mistake?"**

- **Yes** → keep it.
- **No** → remove it.

Only include instructions that are necessary to guide behavior and prevent mistakes. This filters out:
- Things the agent already does correctly by default
- Descriptions or explanations that don't change behavior
- Aspirational guidelines the agent can't act on
- Redundant restatements of what the codebase already makes obvious

**Context is a shared, finite budget.** Every instruction competes for model attention with system prompts, tool schemas, skill descriptions, and conversation history — sources the context asset author doesn't control. Unnecessary instructions actively degrade compliance with instructions that matter. Treat instruction count as a cost, not a style concern.

This test applies recursively — the meta-assets themselves must pass it. Every sentence in every leaf document should earn its place by preventing a concrete mistake.

Note: this is a heuristic judgment call, not a binary filter. What the agent "does correctly by default" changes across model versions — re-evaluate context assets when the underlying model changes significantly. Security-defensive instructions may pass the test even when they seem unnecessary under normal conditions, because they guard against adversarial scenarios. This security carve-out should appear in the authored index, not just this plan — so agents applying the test aggressively don't strip security constraints.

**Authored index version**: The index should compress this to the imperative core — the test question, the filter list, and the budget framing — without citing specific research papers. Citations belong in this plan (human reference); the agent needs the rule, not the provenance.

### 2. Progressive Disclosure

Load context in layers: CLAUDE.md routes to topic indexes, which route to leaf documents. Load only what's relevant to the current task.

- **Router (CLAUDE.md)**: list topics with file references. Include no detailed instructions.
- **Index (.claude/docs/\<topic>.md)**: map tasks/conditions to leaf file paths. Include principles that apply to all subtopics.
- **Leaf (.claude/docs/\<topic>/\<subtopic>.md)**: detailed, self-contained instructions for one concern.

**Authored index version**: This principle is thin by design — the three-tier hierarchy section below carries the structural detail, and the routing table demonstrates the pattern in action.

### 3. Separation of Concerns

- **Separate triggers from content.** Triggers (CLAUDE.md, rules, skills, hooks, agents) determine *when* context loads. Content (instructions, reference docs) is *what* gets loaded. These are independent decisions.
- **One file, one concern.** A doc covering both Go coding standards and Git workflow should be split. Mixed concerns force the agent to ingest irrelevant context when loading one topic.
- **Inline when sole consumer, extract when shared.** If only one skill uses certain instructions, keep them in the skill. Extract to a shared file (e.g., `.claude/docs/`) only when multiple assets need the same content.
- **Treat conflicts as structural bugs.** If two files can plausibly give contradictory instructions, partition the concerns so this is unlikely.

**Authored index version**: These four bullets stand as-is — they're already imperative and agent-targeted. Drop the original "Context assets are a software system" preamble.

### 4. Trust the Agent's Native Capabilities

Provide **direction**, not **description**. The agent can search files, read code, and trace dependencies on its own.

- **Good:** "If working on topic X, read context asset Y" — routing the agent can't infer.
- **Bad:** "Library A contains functions for B; file X handles Y" — the agent discovers this itself, and the description drifts out of sync.

Include only what the agent can't figure out alone: project-specific rules, non-obvious conventions, architectural decisions that aren't self-evident from the code, and routing to the right context at the right time. Codebase catalogs, file listings, and module summaries fail the Necessity Test and go stale.

**Authored index version**: The good/bad examples are useful — keep them. The closing sentence is already imperative.

### 5. Write for Agents, Not Humans

Context assets are consumed by coding agents, not human readers. Write accordingly.

- **Start with the first instruction.** Skip "This document describes..." preambles — the agent just loaded the file and can see what it contains.
- **State rules directly.** Skip "It's important to..." or "Best practice is to..." — motivational framing adds no behavioral guidance.
- **Default to imperatives.** The agent needs *what to do*. Include background context only when it's necessary to prevent a mistake.
- **Use direct address.** Write as if speaking to the agent: "Use X when Y" not "Developers should use X when Y."
- **Frame positively.** "Use const for immutable bindings" not "Don't use var." Negated instructions are measurably less effective (Gadlet; MIT/NegBench CVPR 2025). If a prohibition is necessary, pair it with the positive alternative.
- **One instruction, one verifiable constraint.** Split compound rules. "Use consistent naming and handle errors properly" should be two instructions (DeCRIM, EMNLP 2024).

Review heuristic: **"Is this sentence written for the agent that will load it, or for a human browsing the repo?"** Agents (including the one writing the context asset) default to human-readable prose because that's what their training data looks like.

### 6. Choose the Right Trigger and Content Strategy

Context assets have two layers: **triggers** (mechanisms that determine *when* context loads) and **content** (the actual instructions). Choose the right trigger for the activation condition, then decide whether content belongs inline or in a referenced file.

#### Trigger types

| Trigger | Activation | Example |
|---------|-----------|---------|
| **CLAUDE.md** | Every session, automatically | Universal routing references, critical one-liner rules |
| **Rules** (.claude/rules/*.md) | Auto-loaded; `paths:` frontmatter scopes to file patterns | Go coding standards triggered only when touching `**/*.go` |
| **Skills** (.claude/skills/) | User invokes a slash command, or agent loads via description match (`user-invocable: false`) | User-initiated workflows; reference knowledge loaded on relevance |
| **Hooks** (.claude/settings.json) | Specific tool events (pre/post) | Automated checks, enforcement on agent actions |
| **Agents** (.claude/agents/) | Spawned as a subagent | Specialized personas or delegated workflows |

#### Content strategies

| Strategy | When to use |
|----------|------------|
| **Inline** (content inside the trigger) | The trigger is the sole consumer. A skill that owns its own instructions. |
| **Referenced** (trigger points to a `.claude/docs/` file) | Multiple triggers need the same content, or content is detailed enough to warrant separation. |
| **Routing table** (trigger points to an index, index points to leaves) | A topic has multiple subtopics; the agent should load only the relevant one. |

#### Key considerations

- **~/.claude/CLAUDE.md applies to every project for that user.** Only instructions that are universally correct across all projects belong here. The higher the hierarchy, the stricter this filter.
- **Match trigger to activation condition.** Ask: "What should cause this context to load?" Every session → CLAUDE.md. When touching specific file types → rule with `paths:`. When the user asks → skill. When the agent does X → hook. When working on topic Y → doc referenced from a routing table.
- **Avoid over-triggering.** Loading context when it's not needed is the same problem as putting everything in CLAUDE.md. A rule without `paths:` scoping loads on every session, just like CLAUDE.md — use scoping when the content is conditional.
- **`.claude/docs/` is a content convention, not an auto-loading mechanism.** Files here load when the agent reads them in response to a routing instruction, not automatically. This is by design — it enables progressive disclosure through agent judgment.

---

These six principles govern the entire framework:
- **Necessity Test** → controls *what* goes into context
- **Progressive Disclosure** → controls *when* it gets loaded
- **Separation of Concerns** → controls *where* it lives — triggers vs. content, inline vs. referenced
- **Trust Native Capabilities** → controls *what not to include* — don't describe what the agent can discover
- **Write for Agents** → controls *how* content is written — instructions, not prose
- **Right Trigger & Content Strategy** → controls *which mechanism* activates and *how content is delivered*

**Principle ordering in the index document**: Research on positional attention (Liu et al., TACL 2024) shows a U-shaped recall curve — information at the beginning and end of a document gets the most attention; the middle is a dead zone. In the authored index, order principles to exploit this: Necessity Test first (most important gate), Write for Agents last among the principles (most commonly violated, benefits from end-position attention). Structural principles (Separation of Concerns, Trust Native Capabilities) occupy middle positions where they're less likely to be subtly violated — if you violate them, the result is structurally obvious.

## Progressive Disclosure Pattern

```
CLAUDE.md (auto-loaded, minimal router)
 └─ references → .claude/docs/<topic>.md (index with routing table)
      └─ references → .claude/docs/<topic>/<subtopic>.md (leaf with detailed instructions)
```

### Three-tier hierarchy

| Tier | Role | Loaded | Example |
|------|------|--------|---------|
| **Router** (CLAUDE.md) | Lists topics with file references. No detailed instructions. | Always (auto-loaded) | "For context asset authoring guidance, see `.claude/docs/context-assets.md`" |
| **Index** (.claude/docs/\<topic>.md) | Routing table — maps task/condition to leaf file paths | On demand, when topic is relevant | Table mapping "writing a CLAUDE.md" → claude-md.md |
| **Leaf** (.claude/docs/\<topic>/\<subtopic>.md) | Detailed, self-contained instructions for one concern | On demand, when specific subtopic is needed | Full guide on writing CLAUDE.md as a router |

### Multi-level application

The pattern applies at every level where `.claude/` exists:
- `~/.claude/docs/` — global/user-level context (applies to all projects)
- `<project>/.claude/docs/` — project-scoped context (applies to one project)

## A note on plan prose vs. authored content

This plan is a human-facing design document. It explains, motivates, cites research, and discusses trade-offs — all appropriate for humans planning a project. The **authored context assets** must be dramatically different: agent-compressed, imperative, citation-free, with no explanatory prose. When translating a principle from this plan to the authored index, strip everything that doesn't pass the Necessity Test for an agent reader. The plan says "Research shows X (IFScale, 2025)"; the index says "X." The plan says "Context assets are a software system. Apply the same design principles:"; the index skips straight to the bullets.

Every principle description above includes a note where the authored version should differ from the plan version.

## This Session's Deliverables

This first session creates the **seed crystal** — context assets that teach the coding agent how to create and maintain all types of context assets following the framework's principles. The project bootstraps itself: these assets will guide all future development of the project.

### Design: ~~Two triggers~~ One trigger, shared content

> **Post-implementation update**: The rule trigger was removed after discovering `paths:` frontmatter in `~/.claude/rules/` is silently ignored (GitHub #21858). The rule loaded unconditionally, adding noise to every session. Path resolution is project-root-relative, so it cannot match `~/.claude/` files even if fixed. The skill trigger alone provides the correct activation. See task 002 for details.

~~The authoring guidelines must engage automatically in two distinct scenarios:~~

~~1. **Editing an existing context asset** — the agent is modifying a file in a known context asset directory. A **rule with `paths:` scoping** catches this via platform-enforced file-pattern matching.~~

~~2. **Creating a new context asset or discussing context strategy** — no file path exists yet. A **skill with `user-invocable: false`** catches this via description-based matching.~~

~~Both triggers need the same authoring guidelines → content lives in shared `.claude/docs/` files, referenced by both triggers (Principle 3: extract when shared).~~

The authoring guidelines engage via a single **skill with `user-invocable: false`**, description-matched for all context asset scenarios: creation, modification, strategy discussion, and quality evaluation. Content lives in shared `.claude/docs/` files referenced by the skill trigger (Principle 3: extract when shared).

The **index** carries the six core principles (always relevant when authoring any asset) plus a routing table to asset-type-specific leaves. Each **leaf** covers one asset type. This prevents loading hook guidance when writing a skill.

### Files to create

```
context-assets/
├── CLAUDE.md                                           # Project router
├── .claude/
│   ├── rules/
│   │   └── context-asset-authoring.md                  # Trigger: paths-scoped to context asset dirs
│   ├── skills/
│   │   └── context-asset-authoring/
│   │       └── SKILL.md                                # Trigger: description-matched for creation/discussion
│   └── docs/
│       ├── context-assets.md                           # Index: core principles + routing table
│       └── context-assets/
│           ├── claude-md.md                            # Leaf: writing CLAUDE.md files
│           ├── rules.md                                # Leaf: writing rules
│           ├── skills.md                               # Leaf: writing skills
│           ├── hooks.md                                # Leaf: writing hooks
│           ├── agents.md                               # Leaf: writing agents
│           └── referenced-docs.md                      # Leaf: writing docs/ files (index + leaf pattern)
└── README.md                                           # Project overview (human-facing)
```

### File descriptions

#### Triggers

**1. `.claude/rules/context-asset-authoring.md`** — Rule trigger

Thin trigger with `paths:` frontmatter scoped to context asset directories:
- `.claude/skills/**/*.md`
- `.claude/docs/**/*.md`
- `.claude/rules/**/*.md`
- `.claude/agents/**/*.md`
- `**/CLAUDE.md`

Body: a concise instruction to read the authoring guidelines index at `.claude/docs/context-assets.md`.

Does NOT scope to `.claude/settings.json` (shared config file — would over-trigger for non-hook edits) or to all of `.claude/` (would catch unrelated config).

**2. `.claude/skills/context-asset-authoring/SKILL.md`** — Skill trigger

`user-invocable: false` skill. Description-matched for scenarios where no file path exists yet: creating new context assets, discussing context strategy, planning context structure.

Body: same concise instruction to read the authoring guidelines index.

#### Content

**3. `CLAUDE.md`** — Project router

This project's own root context. Terse router that references the context-assets index for authoring guidance. Demonstrates the pattern it describes. Also includes any project-specific routing (e.g., contribution guidelines if/when they exist).

Note: this is appropriate for the project-level CLAUDE.md because this project IS about context assets. A user's `~/.claude/CLAUDE.md` would NOT include this — it fails the Necessity Test for most projects.

**4. `.claude/docs/context-assets.md`** — Index

Structure (ordered for positional attention — critical content at top and bottom):

1. **Six core principles** (concise, agent-targeted — always relevant when authoring). Ordered: Necessity Test (position 1, most important) → Progressive Disclosure → Separation of Concerns → Trust Native Capabilities → Right Trigger & Content Strategy → Write for Agents (position 6, near bottom for high-attention end position).

2. **Routing table** mapping authoring task → leaf document:

| When you are... | Read |
|-----------------|------|
| Writing or modifying a CLAUDE.md file | `context-assets/claude-md.md` |
| Writing or modifying a rule | `context-assets/rules.md` |
| Writing or modifying a skill | `context-assets/skills.md` |
| Writing or modifying a hook | `context-assets/hooks.md` |
| Writing or modifying an agent | `context-assets/agents.md` |
| Writing or modifying a docs/ file (index or leaf) | `context-assets/referenced-docs.md` |

3. **Instruction writing checklist** (at document bottom, exploiting U-shaped attention curve — second-highest recall position). This is a scannable summary, not redundancy — Principle 5 explains the rules; the checklist is a quick-reference reminder at a high-attention position. The authored versions must be phrased differently to avoid literal repetition:
   - **Compress**: fewest tokens that reliably produce the desired behavior
   - **Positive**: state what to do, not what to avoid
   - **Atomic**: each instruction is independently verifiable
   - **Show when telling fails**: 2-3 examples for style/format/tone; declarative rules for unambiguous constraints

Estimated instruction count after incorporating research: ~35-42 discrete instructions. Well within the budget ceiling established by IFScale, with headroom for instructions from other sources the agent is simultaneously following.

**5-10. Leaf documents** (one per asset type)

Each leaf covers the specific guidance for authoring that asset type:

- **`claude-md.md`** — CLAUDE.md as a router (not a monolith). What belongs there (routing references, critical universal rules), what doesn't (detailed instructions). Hierarchy considerations (~/.claude/ vs project-level). Security: never embed secrets, credentials, or permission-escalating instructions.
- **`rules.md`** — Writing rules with `paths:` frontmatter. When to use path scoping vs. unconditional rules. Keeping rules focused on one concern. Structural advice: place critical constraints at the top of the rule file (Lost in the Middle).
- **`skills.md`** — Writing skills. YAML frontmatter options (`user-invocable`, `allowed-tools`, etc.). When to use `user-invocable: false` for reference knowledge. Description writing for discovery — agents sometimes fail to invoke available skills (Vercel, 2025), so descriptions must use clear, matchable language. Security: use `allowed-tools` to restrict capability surface to what the skill actually needs.
- **`hooks.md`** — Writing hooks in `.claude/settings.json`. Trigger events (pre/post tool use). Keeping hooks scoped and auditable. Security: hooks execute shell commands — every hook must be auditable; a reviewer should be able to determine exactly what it will execute by reading the configuration.
- **`agents.md`** — Writing agent definitions. When to use a specialized agent vs. inline instructions. Security: constrain agent definitions to minimum required capabilities using `allowed-tools`.
- **`referenced-docs.md`** — Writing docs/ files. The index + leaf pattern. When to use an index vs. a standalone doc. Naming conventions. The `.claude/docs/` content convention. Content strategy guidance: when to use rules vs. examples (rules for unambiguous constraints, 2-3 examples for style/format/tone; cap at 5 examples per Few-shot Dilemma, arXiv:2509.13196). Routing instruction clarity — agents sometimes fail to load on-demand content, so routing language must be prominent and matchable.

**11. `README.md`** — Human-facing project overview

What this project is, the progressive disclosure concept, how to use it. Target audience statement. Graduated adoption path (apply Necessity Test → split by concern → add routing when needed). Brief security note about reviewing `.claude/` in repos you didn't author.

### Seed crystal validation

After creating the files, validate the seed crystal by testing for the specific failure modes the research identifies. Generic compliance checks ("does this look right?") are unreliable — models fail at holistic review (DeCRIM, EMNLP 2024). Instead, use targeted tests:

1. **Negative framing test**: Ask the agent to write a context asset for a topic that naturally invites prohibitions (e.g., "common mistakes in error handling"). Verify the output uses positive framing ("wrap errors with context" not "don't return bare errors").
2. **Atomicity test**: Ask for a topic complex enough to generate compound instructions (e.g., "Go coding standards"). Verify each instruction covers a single verifiable constraint.
3. **Compression test**: Check that the output contains no introductions, preambles, motivational framing, or explanatory prose that fails the Necessity Test.
4. **Structural test**: For a topic with enough rules to create a long document, verify critical constraints appear at the top, not buried in the middle.

If any test fails, the seed has a bug — the guidance isn't effectively shaping agent behavior for that failure mode.

## Open Questions

All open questions resolved.


### Resolved questions

**From open questions:**
- [x] **Naming conventions**: kebab-case, all lowercase with hyphens. Files: `claude-md.md`, `rules.md`, `skills.md`, `hooks.md`, `agents.md`, `referenced-docs.md`. Headings: use markdown headers (`##`, `###`), not custom conventions.
- [x] **Leaf templates**: No rigid template. Single structural rule: put the most critical constraints in the first 3 lines. Use section headers only when a document is long enough to benefit from them.
- [x] **Detail level for hooks/skills/agents**: Full comprehensive authoring guidance based on current Claude Code documentation and research findings.

**From research + council analysis:**

- [x] **Instruction count guidance**: Do not cite a specific number. The ~150 ceiling (IFScale) is model-dependent and the author cannot control the total budget. Frame as "context is a shared, finite budget" in the Necessity Test. (Council: unanimous)
- [x] **Skill discovery reliability**: Keep the current architecture (routing table always loaded, detail on demand). Strengthen guidance on writing clear routing instructions in the skills leaf and referenced-docs leaf. (Council: unanimous)
- [x] **Eval guidance scope**: Cut from the index entirely. At most a one-liner in the document intro. Formal eval tooling (Promptfoo, CI integration) is a future leaf. (Council: Advocate argued "telling developers to iterate is like telling a writer to reread their draft" — carried)
- [x] **Instruction ordering**: General principle applied to our own index structure (principles ordered for attention optimization, checklist at bottom). Leaf documents include type-specific structural advice. No rigid template. (Council: unanimous)
- [x] **Security placement**: Security guidance distributed to relevant leaves (hooks, skills, agents, CLAUDE.md), not centralized in the index. The Necessity Test's existing security carve-out appears in the index. README keeps its human-facing supply-chain warning. (Council: Security conceded to Builder's argument — "putting it in the index adds instruction density without meaningfully changing agent output")
- [x] **New principles vs. enrichment**: Research enriches existing principles, does not add new ones. 6 principles remain. Principle 1 gets the shared budget framing; Principle 5 gets positive framing and atomic constraints. Instruction Writing Checklist added at document bottom. (Council: unanimous)

## NOT in scope for this session

- Install script
- Shareable asset library (coding standards, testing patterns, etc.)
- License
- Git initialization
- Long-running task patterns (future leaf: `long-running-tasks.md`)
- Memory system guidance (future leaf: `memory-patterns.md`)
- Formal eval tooling / CI integration (future leaf)
- MCP server configuration guidance (outside our scope — we focus on what authors can affect)

## References

Research citations used in this plan (full analysis in `research.md`):

| Short name | Full citation | Used for |
|---|---|---|
| AGENTbench | [Gloaguen et al., "Evaluating AGENTS.md"](https://arxiv.org/abs/2602.11988) (2026) | Problem statement, context pollution evidence |
| Efficiency study | ["On the Impact of AGENTS.md Files"](https://arxiv.org/abs/2601.20404) (2026) | Scoped context helps for constrained tasks |
| Context Rot | [Chroma Research](https://research.trychroma.com/context-rot) (2025) | Non-linear degradation from irrelevant distractors |
| Context Engineering | [Anthropic](https://www.anthropic.com/engineering/effective-context-engineering-for-ai-agents) (2025) | Progressive disclosure advocacy |
| IFScale | ["How Many Instructions Can LLMs Follow at Once?"](https://arxiv.org/abs/2507.11538) (2025) | Instruction density ceiling (~150), primacy effect |
| Lost in the Middle | [Liu et al.](https://aclanthology.org/2024.tacl-1.9/) (TACL 2024) | U-shaped attention, document ordering |
| Positive framing | [Gadlet](https://gadlet.com/posts/negative-prompting/); [MIT/NegBench](https://news.mit.edu/2025/study-shows-vision-language-models-cant-handle-negation-words-queries-0514) (CVPR 2025) | Positive > negative instructions |
| DeCRIM | [Amazon/EMNLP 2024](https://aclanthology.org/2024.findings-emnlp.458/) | Decomposed atomic constraints, 7-8% improvement |
| InFoBench | [Qian et al.](https://aclanthology.org/2024.findings-acl.772/) (ACL 2024) | Decomposed requirements, measurable compliance |
| Vercel evals | [Vercel blog](https://vercel.com/blog/agents-md-outperforms-skills-in-our-agent-evals) (2025) | Skill discovery failure, aggressive compression |
| Codified Context | [arXiv:2602.20478](https://arxiv.org/abs/2602.20478) (2026) | Three-tier architecture validation |
| Prompt injection | [arXiv:2601.17548](https://arxiv.org/abs/2601.17548) (2025); [OWASP](https://cheatsheetseries.owasp.org/cheatsheets/LLM_Prompt_Injection_Prevention_Cheat_Sheet.html) | Security: instruction files as attack vectors |
| SCOPE | [arXiv:2512.15374](https://arxiv.org/abs/2512.15374) (2025) | Iterative refinement > static prompts |
| Context length hurts | [EMNLP Findings 2025](https://arxiv.org/abs/2510.05381) | Length independently degrades performance |
| Few-shot Dilemma | [arXiv:2509.13196](https://arxiv.org/abs/2509.13196) (2025) | Diminishing/negative returns past ~5 examples |
| Cursor Rules | ["Beyond the Prompt"](https://arxiv.org/abs/2512.18925) (2025) | 28.7% of rules files are duplicated boilerplate |
| Structured Context | [arXiv:2602.05447](https://arxiv.org/abs/2602.05447) (2026) | Format (MD/YAML/JSON) barely matters; model capability dominates |
