# Research Findings: Relevance to Context Asset Authoring Guidelines

This document evaluates research findings from 4 parallel research agents against our plan for context asset authoring meta-guidance. The goal is to determine which findings should be incorporated into the authoring guidelines (the seed crystal), and which are deferred to future content.

## Scope Filter

**In scope**: Findings that change how we teach the agent to *write and structure* context assets — principles, formatting rules, structural patterns, trigger selection.

**Out of scope for now**: Findings about runtime behavior (long-running tasks, multi-agent coordination, session bridging, memory systems). These are valid topics for future leaf documents but aren't meta-guidance about authoring.

---

## Findings to Incorporate

### 1. Instruction Ordering — "Lost in the Middle" Effect

**Sources**: Liu et al. (TACL 2024), IFScale (2025)

**Finding**: U-shaped attention curve — information at the beginning and end of context is best retained. The middle is a dead zone. GPT-3.5-Turbo's mid-context performance dropped *below its no-context baseline*.

**Relevance**: Directly affects how we tell authors to structure content within any context asset. This is a formatting/authoring concern.

**Proposed guidance**: Place critical instructions at the top and bottom of any context asset. Never bury important rules in the middle of a long list. If a document has many instructions, use explicit section headers to create navigable structure rather than relying on a flat list.

**Confidence**: High — replicated across multiple studies and models.

---

### 2. Instruction Density Ceiling (~150 constraints)

**Sources**: IFScale (arXiv:2507.11538) — 20 models, instruction densities from 10 to 500

**Finding**: Frontier reasoning models maintain near-perfect performance through ~150 instructions, then decline. Non-reasoning models decay earlier. Some models (GPT-4o, Llama-4-Scout) collapse exponentially to a 7-15% floor. Even the best model (Gemini 2.5 Pro) achieves only 68% accuracy at 500 instructions.

**Relevance**: Sets a concrete upper bound on how many rules a loaded context set should contain. Directly informs our Necessity Test — if you can only reliably get ~150 rules followed, every rule must earn its place.

**Proposed guidance**: Target well under 150 total constraints across all loaded context. Count your rules. If a leaf document has 30 rules and the index has 20 and CLAUDE.md has 10, that's 60 — leaving headroom for rules from other sources (user prompts, tool descriptions, etc.).

**Confidence**: High — large-scale controlled study across 20 models.

**Open question**: Should we cite a specific number, or keep it directional ("minimize aggressively")?

---

### 3. Positive Framing Over Negative

**Sources**: Gadlet analysis, MIT/CVPR 2025 (NegBench), prompt variation studies

**Finding**: "Don't do X" is consistently less effective than "Do Y instead." Negative sentiment reduces factual accuracy by ~8.4%. Vision-language models perform at near-chance on negated instructions. Token generation is inherently a positive selection process.

**Relevance**: Directly affects how authors write individual instructions. This is a writing style principle — same category as our existing "Write for Agents, Not Humans."

**Proposed guidance**: Always reframe negative instructions as positive ones. "Use const for immutable bindings; use let only when reassignment is needed" instead of "Don't use var." If a prohibition is truly necessary, pair it with the positive alternative.

**Confidence**: High — consistent across multiple independent studies.

---

### 4. Decomposable Verification Criteria

**Sources**: DeCRIM (EMNLP 2024), InFoBench (ACL 2024), self-correction survey (TACL 2024)

**Finding**: Decomposing instructions into individually-checkable constraints improved instruction-following by 7-8%. Intrinsic self-correction (without external feedback or decomposed criteria) is unreliable and can *degrade* output. The key insight: models can verify against specific, atomic criteria but fail at holistic "review your work" checks.

**Relevance**: Affects how authors write instructions — make each rule individually verifiable. Also relevant to how we structure checklists and validation criteria within context assets.

**Proposed guidance**: Write each instruction as a single, verifiable constraint. Avoid compound rules ("use consistent naming and handle errors properly" — split these). When including review/verification steps, decompose them into specific checkable items.

**Confidence**: Medium-high — strong experimental support, though the studies measured general instruction-following, not specifically context asset scenarios.

---

### 5. Examples vs. Rules — When to Use Each

**Sources**: Clinical NLP prompting study (PMC 2024), Anthropic best practices, LangChain tool-calling study, Few-shot Dilemma (arXiv:2509.13196)

**Finding**: Rules are more effective for clear-cut constraints. Few-shot examples are powerful for style, format, and ambiguous behaviors — but diminishing returns after 2-3 examples, and negative returns after ~5. Examples are "one of the most reliable ways to steer output format, tone, and structure" (Anthropic).

**Relevance**: Directly informs how leaf documents should be structured. Some guidance is best expressed as rules; some needs examples.

**Proposed guidance**: Use declarative rules for unambiguous constraints (naming conventions, file structure, required sections). Use 2-3 examples for style, tone, and format guidance where the desired behavior is hard to articulate as a rule. Do not exceed 5 examples — over-prompting degrades performance.

**Confidence**: Medium-high — multiple sources agree on the general pattern, though the optimal example count varies by task.

---

### 6. Vercel's Skill Discovery Problem

**Source**: Vercel engineering blog — internal evals on Next.js 16 API knowledge

**Finding**: Passive 8KB AGENTS.md achieved 100% pass rate. On-demand skills achieved only 79% — agents frequently *failed to invoke skills even when available*. Original trigger instructions had to be rewritten before agents would use skills at all.

**Relevance**: Directly challenges our progressive disclosure model. If agents don't reliably load on-demand content, the routing table in CLAUDE.md must compensate.

**Proposed guidance**: Acknowledge the discovery reliability trade-off explicitly. Routing instructions in CLAUDE.md and indexes must be clear, prominent, and use language the agent will match. Consider: for critical guidance that must always be followed, inline it or use always-loaded triggers (rules without path scoping). Reserve progressive disclosure for supplementary/reference content where missing it degrades quality but doesn't cause failures.

**Confidence**: Medium — single study, specific to one framework. But the failure mode (agents not invoking available tools) is well-documented elsewhere.

**Open question**: Does this change our trigger strategy? Should some content that we planned as on-demand instead be always-loaded via unscoped rules?

---

### 7. Aggressive Compression Works

**Sources**: Vercel (40KB → 8KB, zero loss), Upsun synthesis, AGENTbench token cost analysis

**Finding**: Dramatic compression of instruction files causes no measurable performance loss. Every token in an instruction file is a token not used for reasoning. 80% size reduction with zero accuracy loss (Vercel).

**Relevance**: Reinforces our Necessity Test but goes further — even content that passes the Necessity Test should be compressed to its minimal form. This is a writing style principle.

**Proposed guidance**: After writing any context asset, do a compression pass. Can this sentence be shorter? Can this paragraph be a single line? Can this list be reduced? The goal is minimum viable instruction — the fewest tokens that reliably produce the desired behavior.

**Confidence**: High — strong quantitative support.

---

### 8. Security: Instruction Files as Attack Vectors

**Sources**: Secure Code Warrior (2025), arXiv:2601.17548, OWASP LLM cheat sheet, Anthropic prompt injection research

**Finding**: Repository-level instruction files are a documented prompt injection vector. Adaptive injection bypasses 90%+ of published defenses. Any contributor can modify these files.

**Relevance**: Affects how we guide authors on what to include (and what never to include) in context assets. Security is a meta-concern for all asset types.

**Proposed guidance**: Add security considerations to the index (applies to all asset types): Never include instructions that grant elevated permissions. Never embed secrets or sensitive paths. Review instruction file changes in PRs with the same scrutiny as code. Do not blindly adopt third-party instruction files.

**Confidence**: High — well-documented attack vector with multiple independent sources.

---

### 9. Eval-Driven Refinement

**Sources**: SCOPE (arXiv:2512.15374), Tessl blog, Promptfoo framework

**Finding**: SCOPE's automatically-evolved prompts improved task success from 14% → 39% (HLE) and 33% → 57% (GAIA). Static, write-once instruction files are inherently limited. "Your AGENTS.md isn't the problem — your lack of evals is."

**Relevance**: Affects how we advise authors to maintain context assets over time. Authoring isn't a one-time activity.

**Proposed guidance**: Treat context assets like code — iterate based on observed failures. When the agent makes a mistake despite having relevant context, investigate whether the instruction was unclear, too vague, or positioned poorly. When the agent succeeds consistently on a topic, consider whether the instruction is still necessary or whether the model has learned the pattern.

**Confidence**: Medium — SCOPE's results are strong but the technique (automatic prompt evolution) isn't directly applicable to manual authoring. The general principle (iterate from observed failures) is sound.

**Open question**: Should we include guidance on formal evals, or keep it at "iterate from observed failures"? Formal eval infrastructure may be premature for the seed crystal.

---

### 10. MCP Server Overscoping — Context Pollution and Security Surface

**Sources**: IFScale instruction density findings, Secure Code Warrior (2025), arXiv:2601.17548, practical observation

**Finding**: This is a synthesis concern, not a single study — but it follows directly from the instruction density and security research. MCP (Model Context Protocol) servers expose tool schemas that are loaded into context for every session where the server is connected. Each tool schema is effectively an instruction: it tells the model what the tool does, what parameters it accepts, and when to use it.

**The overscoping problem**: Vendor-supported MCP servers are incentivized to expose their *entire API surface* as tools. A GitHub MCP server doesn't just expose "read file contents" — it exposes repository management, issue creation, PR workflows, organization settings, and dozens of other capabilities. A database MCP server exposes read, write, delete, schema modification, and administrative operations. This is analogous to giving full bash access when all you need is to read a specific file path.

**Two compounding costs**:

1. **Context pollution**: Every tool schema occupies context and competes for the model's instruction-following budget — even tools the current task will never use. A project that connects 3 MCP servers, each exposing 15-20 tools, has injected 45-60 tool schemas into every session. The IFScale research shows this kind of constraint density directly degrades compliance with the instructions that actually matter.

2. **Security surface expansion**: Each exposed tool is a capability the agent *can invoke*. Over-scoped tools increase the blast radius of prompt injection, hallucinated tool calls, and agent misbehavior. The prompt injection research (arXiv:2601.17548) shows 90%+ bypass rates against published defenses — meaning the agent *will* sometimes do things you didn't intend. The fewer destructive capabilities available, the less damage a misbehaving agent can do.

**The industry enthusiasm problem**: MCP adoption is accelerating, and the default vendor incentive is "expose everything." Individual projects rarely need more than a narrow slice of a vendor's API, but the MCP server ships as a monolith. There is currently no standard mechanism for scoping an MCP server's exposed tools to a project's actual needs (though some servers support configuration-based tool filtering).

**Relevance**: We cannot prevent users from registering MCP servers — that's outside our scope. But this finding is important *background* for why the authoring principles matter. Context assets don't operate in isolation; they share a budget with MCP tool schemas, skill descriptions, and everything else in context. This reinforces the stakes of the Necessity Test — the budget available for your context assets may already be partially consumed by things you don't control.

**Disposition**: Reference in documentation as environmental context. Not an actionable authoring principle — we focus on what authors *can* affect. Mention briefly in the "context as shared budget" framing to explain *why* every instruction must earn its place, without prescribing MCP behavior.

**Confidence**: High on the mechanism (instruction density research is strong, security research is strong). The specific concern about vendor MCP overscoping is observational but follows directly from the research.

---

## Findings Deferred to Future Work

These are valid and well-supported but belong in future leaf documents, not in the authoring meta-guidance:

| Finding | Why Deferred | Future Home |
|---------|-------------|-------------|
| Long-running task degradation (35 min threshold) | Runtime strategy, not authoring guidance | New leaf: `long-running-tasks.md` |
| Session bridging artifacts (progress files, checklists) | Runtime pattern, not asset structure | New leaf: `long-running-tasks.md` |
| System prompt drift / periodic re-injection | Runtime mitigation, not authoring choice | Hooks leaf or long-running leaf |
| Multi-agent coordination limits (3-4 optimal) | Agent orchestration, not authoring | Agents leaf (future expansion) |
| Memory systems (Mem0, A-MEM, Zettelkasten) | Memory architecture, not asset authoring | New leaf: `memory-patterns.md` |
| Guardrails ROI (3x productivity with hooks) | Motivational framing — we don't include "why" | Could strengthen hooks leaf |
| Observation masking vs. summarization | Context management strategy, not authoring | Infrastructure concern |
| Pre-execution vs. post-execution guardrails | Hook design pattern, not meta-guidance | Hooks leaf (future expansion) |

---

## Open Questions for Discussion

### 1. Instruction density: what can we actually control?

The IFScale finding (~150 instruction ceiling for frontier models) is real, but the context asset author **cannot control total instruction count**. The agent's loaded context includes:

- The system prompt (large, not user-controlled)
- CLAUDE.md and any loaded rules/docs (user-controlled)
- All skill descriptions (loaded every session, one per skill)
- All MCP server tool schemas (loaded every session, one per tool)
- User messages, tool results, and conversation history
- Any hooks or agent definitions

This means:
- A user with 20 skills and 3 MCP servers (each exposing 10-15 tools) has already consumed a significant chunk of the model's instruction-following budget before any context assets load.
- The degradation isn't just about context window size — it's about **constraint density**. Each skill description, each tool schema, each rule is implicitly a constraint the model tries to satisfy.
- We can't tell users "keep your total rules under 150" because we don't control most of the budget. But we *can* inform them that every addition has a cost, and that cost is non-linear at high densities.

**Implications for our guidance**:
- Frame the Necessity Test partly in terms of this budget. Every instruction competes with every other instruction for the model's attention. Unnecessary instructions don't just waste tokens — they actively degrade compliance with *other* instructions.
- Warn about the hidden cost of skill proliferation. Each skill's description is loaded every session, even when irrelevant. 30 skills = 30 descriptions always in context, each one a potential distractor. The same applies to MCP tool schemas.
- Don't cite a specific number. Instead, convey the principle: **context is a shared, finite budget, and everything loaded into it competes for attention**. Authors should treat instruction count as a cost, not just a style concern.
- This also strengthens the case for `user-invocable: false` skills with narrow descriptions — a vague description that matches too broadly will load content unnecessarily, consuming budget.

**Resolution**: Don't add a "max rules" guideline. Instead, add a principle about context as a finite shared budget, and frame the Necessity Test as budget discipline. Mention skill descriptions and MCP tool schemas as significant, often-overlooked contributors to instruction density.

### 2. Skill discovery reliability

Vercel found agents failed to invoke skills 21% of the time even when available. Does this change our trigger architecture? Should critical authoring principles be in an always-loaded rule rather than an on-demand doc?

Our current design already mitigates this: the *routing table* is always-loaded (in CLAUDE.md or the index), while only the *detailed content* is on-demand. The agent doesn't need to "discover" a skill — it follows an explicit instruction to read a specific file path.

But the finding does reinforce: routing instructions must be clear, prominent, and use language the agent will reliably match. If the routing table says "For context asset authoring guidance, see `.claude/docs/context-assets.md`" and the agent is editing a rule file, the connection needs to be obvious.

**Resolution**: Keep the current architecture. Strengthen the guidance on writing clear routing instructions. Acknowledge the trade-off explicitly in the referenced-docs leaf.

### 3. Eval guidance scope

Include in seed crystal (lightweight: "iterate from observed failures") or defer formal eval guidance to a future leaf?

**Resolution**: Include lightweight guidance in the index principles. "Treat context assets as living documents — iterate based on observed agent failures. When the agent makes a mistake despite relevant context, investigate whether the instruction was unclear, poorly positioned, or too vague." Defer formal eval tooling (Promptfoo, CI integration) to a future leaf.

### 4. Instruction ordering

How prescriptive should we be about where to place critical instructions? A general principle ("top and bottom") vs. a structural template?

**Resolution**: General principle in the index, with a note in leaf documents about section ordering for that specific asset type. Avoid a rigid template that becomes one more constraint for authors to satisfy.
