# Agent Instruction Alignment Research Summary

**Date**: 2026-04-04
**Analyst**: Opus agent (isolated context)
**Purpose**: Identify best practices for improving agent instruction-following in the Firebreak code review pipeline

## Key Research Findings

### 1. Instruction Capacity (IFScale, Jaroslawicz et al. 2025)
- Standard Claude Sonnet: **linear decay** from instruction 1 onward, ~53% at 500 instructions
- Reasoning models: near-perfect through ~150, then threshold decay
- Practical limit for reliable compliance: **~20 instructions per agent**
- Instruction COUNT, not token count, is the primary driver of degradation

### 2. Context Rot (Chroma 2025, Liu et al. 2024)
- **Every model degrades at every context length increment** — no exceptions
- U-shaped attention: high at beginning/end, 30%+ drop in middle
- Even with perfect retrieval, performance degrades with input length
- Three compounding mechanisms: lost-in-the-middle, attention dilution, distractor interference

### 3. Instruction-to-Content Ratio (Jaroslawicz et al. 2025)
- Performance decline is **linear**: beta = -0.003 per percentage point of extraneous content
- Effect is **additive** — instruction count and content volume degrade independently
- Minimizing context per agent is one of the highest-leverage interventions

### 4. Instruction Position (Anthropic best practices)
- Anthropic explicitly recommends: data at top, instructions/queries at bottom
- Measured **30% improvement** from this ordering
- Consistent with U-shaped attention curve

### 5. Sub-Agent Decomposition (Multiple sources)
- Anthropic recommends sub-agent architectures for complex tasks
- AgentGroupChat-V2: focused agent teams outperform single large-context agents
- Long-context divide-and-conquer research provides theoretical framework

## Top 10 Recommendations (ordered by impact and evidence level)

| # | Recommendation | Evidence | Impact |
|---|---------------|----------|--------|
| R1 | Decompose: 1-3 checklist items per agent, not all 24 | IFScale + context rot + Anthropic | Highest — directly attacks instruction saturation |
| R2 | Force explicit per-file, per-item enumeration | Anthropic best practices | High — prevents satisficing after first match |
| R3 | Data at top, instructions at bottom | Anthropic (30% measured improvement) | High — exploits U-shaped attention |
| R4 | Grounding quotes before analysis | Anthropic documentation | High — forces re-attendance to actual code |
| R5 | Minimize context per agent invocation | Context rot research | High — every token removed improves compliance |
| R6 | Self-verification pass | Anthropic prompt chaining | Medium-high — catches silent omissions |
| R7 | Randomize checklist order across runs | Implied by position research | Medium — prevents consistent middle-position disadvantage |
| R8 | Use reasoning/thinking mode | IFScale (reasoning models ~3x better) | Medium-high — dramatic improvement on instruction density |
| R9 | Hierarchical instruction grouping | IFScale (count > tokens) | Medium — balance against "right altitude" principle |
| R10 | Coverage matrix aggregator | Engineering pattern | Medium — system-level gap detection |

## Source References
- IFScale (Jaroslawicz et al. 2025): https://arxiv.org/html/2507.11538v1
- Lost in the Middle (Liu et al. 2024): https://aclanthology.org/2024.tacl-1.9/
- Context Rot (Chroma 2025): https://research.trychroma.com/context-rot
- Cognitive Load Limits (Jaroslawicz et al. 2025): https://arxiv.org/html/2509.19517v2
- Anthropic Best Practices: https://platform.claude.com/docs/en/docs/build-with-claude/prompt-engineering/claude-4-best-practices
- Anthropic Context Engineering: https://www.anthropic.com/engineering/effective-context-engineering-for-ai-agents
- AgentGroupChat-V2: https://arxiv.org/html/2506.15451v1
