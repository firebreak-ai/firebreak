# Context Engineering for LLM Coding Agents — Research Synthesis

**Date**: 2026-04-10
**Scope**: Academic papers, industry publications, and open-source projects addressing context management, instruction coherence, and attention degradation in LLM-based coding agents.

---

## Table of Contents

1. [The Problem Space](#the-problem-space)
2. [Foundational Research](#foundational-research)
3. [Instruction Following Degradation](#instruction-following-degradation)
4. [Agent Drift and Behavioral Degradation](#agent-drift-and-behavioral-degradation)
5. [Mitigation Techniques](#mitigation-techniques)
6. [Memory Architectures](#memory-architectures)
7. [Production Coding Agent Architectures](#production-coding-agent-architectures)
8. [Open-Source Projects and Tools](#open-source-projects-and-tools)
9. [Key Themes and Implications](#key-themes-and-implications)
10. [Source Index](#source-index)

---

## 1. The Problem Space

"Context engineering" emerged as a distinct discipline in mid-2025, superseding "prompt engineering" as the industry recognized that agent performance depends less on individual prompt quality and more on *designing entire information environments*.

**Andrej Karpathy** popularized the term at YC AI Startup School (June 2025): *"the delicate art and science of filling the context window with just the right information for the next step."*

**Harrison Chase** (LangChain) defined it as *"building dynamic systems to provide the right information and tools in the right format such that the LLM can plausibly accomplish the task."* Key insight: most agent failures trace to inadequate context curation, not model inadequacy.

**Phil Schmid** (Hugging Face) provided a practitioner taxonomy with four strategies: Context Offloading, Context Reduction, Context Retrieval, Context Isolation.

The core tension: every token in the context window competes for attention. More context often makes things worse, not better. The problem is not fitting information into the window — it's ensuring the model *attends to* the right information at the right time.

---

## 2. Foundational Research

### 2.1 Lost in the Middle

**Paper**: "Lost in the Middle: How Language Models Use Long Contexts"
**Authors**: Nelson F. Liu et al. (Stanford) — TACL 2024
**URL**: https://arxiv.org/abs/2307.03172

The foundational paper on positional attention bias. LLMs exhibit a **U-shaped attention curve**: performance is highest when relevant information sits at the very beginning or very end of context, and degrades significantly for middle-positioned content. Holds across model types and tasks.

**Root cause**: Rotary Position Embedding (RoPE) introduces long-term decay that systematically de-emphasizes middle tokens. Softmax attention forces weights to sum to 1, so initial tokens become "attention sinks" absorbing disproportionate weight regardless of semantic relevance.

**Follow-ups**:
- **"Found in the Middle"** (Hsieh et al., ACL 2024, [arxiv:2406.16008](https://arxiv.org/abs/2406.16008)): Calibration mechanism correcting positional bias, +15pp on RAG tasks.
- **Mitigation survey** ([arxiv:2511.13900](https://arxiv.org/abs/2511.13900)): Context compression is the most broadly effective black-box mitigation — shorter context eliminates the middle region entirely. Best methods achieve 7-15% improvement, suggesting the problem is fundamental to transformer attention.

### 2.2 Context Rot

**Research**: Chroma Research (July 2025)
**Authors**: Kelly Hong, Anton Troynikov, Jeff Huber
**URL**: https://research.trychroma.com/context-rot
**Benchmark toolkit**: https://github.com/chroma-core/context-rot (~242 stars)

Tested 18 frontier models (GPT-4.1, Claude Opus 4, Gemini 2.5). Every model degrades as input length increases — critically, this occurs **well before hitting token limits**. A 200K-window model shows significant degradation at 50K tokens.

Key findings:
- As needle-question similarity decreases, degradation amplifies with context length
- Models performed **better on shuffled haystacks than logically coherent documents** — structural coherence consistently hurt performance across all 18 models
- Claude models showed conservative behavior under uncertainty (stating inability rather than hallucinating)

### 2.3 Context Length Hurts Despite Perfect Retrieval

**Paper**: [arxiv:2510.05381](https://arxiv.org/html/2510.05381v1)

Even when a model can perfectly retrieve all evidence, performance still degrades 13.9%-85% as input length increases across math, QA, and code generation tasks. Length alone is the problem.

### 2.4 Attention Sinks / StreamingLLM

**Paper**: Xiao et al. — ICLR 2024
**URL**: https://arxiv.org/abs/2309.17453

LLMs allocate disproportionate attention to the very first few tokens regardless of semantic content — these are "attention sinks." StreamingLLM keeps the first 4 tokens as permanent anchors plus a sliding window, enabling stable generation across 4M+ tokens.

**Implication**: The first few lines of a system prompt or CLAUDE.md have outsized influence. Burying critical rules after a preamble wastes this privileged position.

---

## 3. Instruction Following Degradation

### 3.1 Curse of Instructions (ICLR 2025)

**URL**: https://openreview.net/forum?id=R6q67CDBCH

Introduces ManyIFEval benchmark with up to 10 objectively verifiable instructions. GPT-4o follows all 10 simultaneously only 15% of the time; Claude 3.5 Sonnet: 44%. Instruction adherence degrades systematically as instruction count grows.

### 3.2 IFScale — How Many Instructions Can LLMs Follow at Once?

**Paper**: [arxiv:2507.11538](https://arxiv.org/abs/2507.11538) (February 2026)
**Authors**: Daniel Jaroslawicz et al.

500 keyword-inclusion instructions; best frontier models achieve only 68% accuracy at max density. Reveals **bias towards earlier instructions** — later instructions systematically receive less attention. 20 models across 7 providers; 3 distinct performance degradation patterns correlated with model size.

### 3.3 Instruction Instability in Dialogs

**Paper**: Lam et al. — COLM 2024
**URL**: https://arxiv.org/abs/2402.10962

Demonstrated significant instruction drift within **eight conversation rounds** in LLaMA2-chat-70B and GPT-3.5. The transformer attention mechanism is the direct cause — the longer the dialog, the less weight placed on initial system prompt tokens.

### 3.4 LIFBench (ACL 2025)

**URL**: https://arxiv.org/abs/2411.07037

2,766 instructions across 11 tasks and 6 context length intervals. Evaluates instruction following *stability* (not just performance) in long-context scenarios. 20 LLMs tested.

### 3.5 Context Discipline and Performance Correlation

**Paper**: [arxiv:2601.11564](https://arxiv.org/html/2601.11564v1)

Irrelevant/distracting context imposes a severe performance "tax." Every tool call result, file read, and error log accumulates as noise that degrades instruction following — even when the context window isn't full.

---

## 4. Agent Drift and Behavioral Degradation

### 4.1 Quantifying Agent Drift

**Paper**: "Agent Drift: Quantifying Behavioral Degradation in Multi-Agent LLM Systems Over Extended Interactions"
**URL**: [arxiv:2601.04170](https://arxiv.org/abs/2601.04170) (January 2026)
**Author**: Abhishek Rath

The first formal quantification. Proposes the **Agent Stability Index (ASI)** across 12 dimensions. Three drift types:
- **Semantic drift**: Progressive deviation from original intent
- **Coordination drift**: Breakdown in multi-agent consensus
- **Behavioral drift**: Emergence of unintended strategies

Practical observations: agents forget customer names by turn 12, contradict earlier commitments by turn 18. Workflows with explicit long-term memory show **21% higher ASI retention** than conversation-history-only approaches.

### 4.2 Drift as Controllable Equilibrium

**Paper**: "Drift No More? Context Equilibria in Multi-Turn LLM Interactions"
**URL**: [arxiv:2510.07777](https://arxiv.org/html/2510.07777v1) (October 2025)
**Authors**: Vardhan Dongre, Ryan A. Rossi et al.

Counterintuitively optimistic: experiments reveal **stable, noise-limited equilibria rather than runaway degradation**. Drift stabilizes at finite levels and can be shifted downward by lightweight interventions like goal reminders. Drift is a **controllable phenomenon**, not inevitable decay.

### 4.3 Measuring Context Pollution

**Author**: Kurtis Kemple (2025)
**URL**: https://kurtiskemple.com/blog/measuring-context-pollution/

Proposes **cosine similarity between the embedding of original intent and current working context** as a drift metric. Create an anchor embedding when a plan is agreed upon; periodically compare current context against the anchor; trigger a clarification sub-loop if drift exceeds a threshold.

---

## 5. Mitigation Techniques

### 5.1 Context Compression

#### Factory.ai — Anchored Iterative Summarization
**URL**: https://factory.ai/news/compressing-context, https://factory.ai/news/evaluating-compression

Maintains a structured, persistent summary with explicit sections (session intent, file modifications, decisions made, next steps). When compression triggers, only the newly truncated span is summarized and merged — never regenerated from scratch. Tested on 36,611 production messages. Scored 3.70 vs Anthropic 3.44 vs OpenAI 3.35. Artifact tracking (file paths, error codes) survives because the summary structure explicitly preserves them.

#### JetBrains — The Complexity Trap (NeurIPS 2025, DL4Code)
**URL**: https://blog.jetbrains.com/research/2025/12/efficient-context-management/
**GitHub**: https://github.com/JetBrains-Research/the-complexity-trap

**Observation masking** (hiding old tool outputs while keeping tool calls visible) matched or beat LLM-based summarization on SWE-bench Verified while being **52% cheaper**. With Qwen3-Coder 480B: masking boosted solve rates by 2.6%. Agents need their reasoning/action history more than raw tool outputs from previous turns.

#### Microsoft LLMLingua
**URL**: https://github.com/microsoft/LLMLingua (~6k stars)

Up to 20x compression with minimal performance loss. LLMLingua-2 uses data distillation from GPT-4 for token classification. 3-6x faster than v1.

#### Contextual Memory Virtualisation ([arxiv:2602.22402](https://arxiv.org/abs/2602.22402), February 2026)

DAG-based state management. Three-pass **structurally lossless trimming**: preserves every user message and assistant response verbatim while reducing tokens by mean 20% (up to 86%). Strips mechanical bloat (raw tool outputs, base64 images, metadata) while keeping reasoning intact.

### 5.2 Instruction Reinforcement

#### Split-Softmax (Lam et al., COLM 2024)
Training-free, parameter-free method that amplifies attention to the system prompt at inference time by rescaling attention weights. More effective early in conversations; instruction repetition excels in longer sessions.

#### SCAN Protocol
**URL**: https://dev.to/nikolasi/solving-agent-system-prompt-drift-in-long-sessions-a-300-token-fix-1akh

~300 tokens. Places marker questions at the end of prompt sections (e.g., "@@SCAN_1: What data will this task affect?"). The model must read each section to answer the question, generating ~20 tokens that re-link instructions to the current task. Tiered intensity: FULL (~300 tokens) for critical tasks, MINI (~120 tokens) for medium, ANCHOR (~20 tokens) between subtasks.

#### OpenAI — Instruction Hierarchy
**URL**: https://openai.com/index/instruction-hierarchy-challenge/

Models trained via RL to follow a priority hierarchy where system-level instructions are more trusted than user-level inputs. Higher-priority instructions override lower-priority ones on conflict.

### 5.3 Hierarchical Context Architecture

#### Anthropic — Three-Tier Model
**URL**: https://www.anthropic.com/engineering/effective-context-engineering-for-ai-agents

- **System prompt**: Minimal, high-signal. Structured with XML tags or Markdown headers.
- **Just-in-time retrieval**: Lightweight identifiers (file paths, URLs) with runtime data loading via tools rather than pre-loading.
- **Sub-agent delegation**: Specialized sub-agents get clean context windows, explore extensively, return condensed 1,000-2,000 token summaries.

#### Manus — Concurrency-Inspired Isolation
**URL**: https://manus.im/blog/Context-Engineering-for-AI-Agents-Lessons-from-Building-Manus

Go-inspired principle: "Share memory by communicating, don't communicate by sharing memory." Sub-agents for context isolation; planner + knowledge manager + executor pattern.

### 5.4 Version Control Semantics for Context

#### ContextBranch ([arxiv:2512.13914](https://arxiv.org/abs/2512.13914), December 2025)

Checkpoint, branch, switch, inject primitives for LLM conversations. Addresses the 39% performance drop when instructions span multiple turns. Solves the false dichotomy of continuing in polluted context vs. starting fresh and losing everything.

#### Git Context Controller ([arxiv:2508.00031](https://arxiv.org/html/2508.00031v1))

Applies git semantics (COMMIT, BRANCH, MERGE, CONTEXT) to context management. Claims SOTA on SWE-Bench and BrowseComp.

---

## 6. Memory Architectures

### 6.1 MemGPT / Letta — OS-Inspired Memory Tiers

**Paper**: [arxiv:2310.08560](https://arxiv.org/abs/2310.08560) (2023-2024)
**GitHub**: https://github.com/letta-ai/letta (~22k stars)

Three-tier architecture inspired by OS memory management:
- **Core Memory**: Always in-context (like RAM)
- **Recall Memory**: Searchable conversation database
- **Archival Memory**: Long-term vector storage (like disk)

Agents actively manage their own memory through tool calls. New "Context Repositories" feature stores agent context in git-tracked files — agents use standard git operations to manage context divergence between subagents.

### 6.2 Mem0 — Graph-Based Memory

**Paper**: [arxiv:2504.19413](https://arxiv.org/abs/2504.19413) (April 2025)
**GitHub**: https://github.com/mem0ai/mem0 (~52k stars)

Three-tier storage: vector DB for semantic similarity, graph DB for relationships, key-value for fast facts. Self-edits when facts conflict instead of appending duplicates. 91% lower latency than full-context approaches. 90% token cost savings.

### 6.3 A-MEM — Zettelkasten-Inspired Networks

**Paper**: [arxiv:2502.12110](https://arxiv.org/abs/2502.12110) (February 2025)

Interconnected knowledge networks through dynamic indexing and linking. Atomic notes with rich contextual descriptions. Addresses the limitation of flat memory stores that lose relational structure.

### 6.4 ACE: Agentic Context Engineering (ICLR 2026)

**Paper**: [arxiv:2510.04618](https://arxiv.org/abs/2510.04618)

Three-role framework: Generator (reasoning), Reflector (distills insights from successes/errors), Curator (integrates into structured context updates). Addresses **brevity bias** (dropping insights for concise summaries) and **context collapse** (iterative rewriting eroding details). +10.6% on agent benchmarks.

---

## 7. Production Coding Agent Architectures

### 7.1 Anthropic — Claude Code

**URLs**:
- https://www.anthropic.com/engineering/effective-context-engineering-for-ai-agents
- https://www.anthropic.com/engineering/effective-harnesses-for-long-running-agents
- https://www.anthropic.com/engineering/multi-agent-research-system

Key patterns:
- CLAUDE.md files load upfront; tools enable just-in-time file retrieval
- Two-agent harness: initializer sets up environment, coding agent makes incremental progress per session
- Multi-agent with Opus lead + Sonnet subagents outperformed single-agent by >90%
- Token usage explains 80% of performance variance — multi-agent works because it allocates enough tokens
- Compact at **60% context utilization**, not 90%
- Tool result clearing — keep message structure but clear raw results

### 7.2 Cursor — Priority-Based Context + Dynamic Discovery

**URLs**:
- https://github.com/anysphere/priompt (~2.8k stars)
- https://cursor.com/blog/dynamic-context-discovery

**Priompt**: JSX-based prompt design where elements have priority scores. When context exceeds budget, lower-priority elements are dropped via binary search. Source maps for debugging cache misses.

Shifted from loading context upfront to **dynamic context discovery** — the agent pulls its own context as needed (far more token-efficient).

### 7.3 Aider — Repository Map with PageRank

**URL**: https://aider.chat/docs/repomap.html

Tree-sitter parsing extracts code definitions and references. PageRank over a file dependency graph, personalized to current chat context. Token-budgeted map (default 1k tokens, dynamically adjusts).

### 7.4 OpenAI Codex

**URL**: https://developers.openai.com/blog/run-long-horizon-tasks-with-codex

Context managed through persistent AGENTS.md files at global, project, and directory levels. GPT-5.2-Codex introduced context compaction for long-horizon work. Tested 25 hours uninterrupted, 13M tokens, 30k lines of code.

### 7.5 Google ADK — Sliding Window Compaction

**URL**: https://google.github.io/adk-docs/context/compaction/

Configurable compaction interval (every N invocations) and overlap size. Automatic event filtering, conversation summarization, lazy artifact loading. Philosophy: *"Context is a compiled view over a richer stateful system."*

---

## 8. Open-Source Projects and Tools

### Tier 1: Direct Context Engineering for Coding Agents

| Project | Stars | Key Technique | URL |
|---------|-------|---------------|-----|
| **context-mode** | ~7k | MCP server sandboxing tool outputs (98% token reduction), BM25 retrieval after compaction | https://github.com/mksglu/context-mode |
| **GSD-2** (Get Shit Done) | ~5.3k | Fresh context per task via decompose-then-dispatch, 70% compaction threshold | https://github.com/gsd-build/gsd-2 |
| **Priompt** (Cursor) | ~2.8k | JSX priority-based context compilation with binary search budget fitting | https://github.com/anysphere/priompt |
| **HumanLayer context engineering** | ~1.6k | Frequent intentional compaction at 40-60% utilization, human review at boundaries | https://github.com/humanlayer/advanced-context-engineering-for-coding-agents |
| **Headroom** | ~1.3k | 87% token reduction via AST-aware compression, reversible with on-demand retrieval | https://github.com/chopratejas/headroom |
| **Context Engineering Kit** | ~788 | Plugin-based Claude Code skills with minimal token footprint | https://github.com/NeoLabHQ/context-engineering-kit |

### Tier 2: Memory and Persistence Systems

| Project | Stars | Key Technique | URL |
|---------|-------|---------------|-----|
| **Mem0** | ~52k | Graph+vector+KV memory with self-editing on conflict | https://github.com/mem0ai/mem0 |
| **Letta** (MemGPT) | ~22k | OS-inspired 3-tier memory, git-based Context Repositories | https://github.com/letta-ai/letta |
| **Parlant** | ~17.9k | Per-turn context assembly, only relevant instructions per turn | https://github.com/emcie-co/parlant |

### Tier 3: Research and Compression Tools

| Project | Stars | Key Technique | URL |
|---------|-------|---------------|-----|
| **LLMLingua** (Microsoft) | ~6k | 20x prompt compression via token classification | https://github.com/microsoft/LLMLingua |
| **Awesome Context Engineering** | ~3k | Curated survey of papers, frameworks, and guides | https://github.com/Meirtz/Awesome-Context-Engineering |
| **Context Rot benchmark** (Chroma) | ~242 | Reproducible degradation testing across 18 models | https://github.com/chroma-core/context-rot |

### Coding-Agent-Specific Papers

| Paper | Venue | Key Contribution |
|-------|-------|-----------------|
| **The Complexity Trap** (JetBrains) | NeurIPS 2025 DL4Code | Observation masking matches summarization at 52% lower cost |
| **Codified Context** ([arxiv:2602.20478](https://arxiv.org/abs/2602.20478)) | Feb 2026 | 3-layer context infrastructure tested over 283 sessions on 108K-line C# system |
| **Context Engineering for Multi-Agent Code Assistants** ([arxiv:2508.08322](https://arxiv.org/abs/2508.08322)) | Aug 2025 | 4-component pipeline: intent translation, semantic retrieval, synthesis, multi-agent |
| **Context Engineering in OSS** ([arxiv:2510.21413](https://arxiv.org/abs/2510.21413)) | Oct 2025 | Studies CLAUDE.md/AGENTS.md adoption across 466 open-source projects |

---

## 9. Key Themes and Implications

### Theme 1: Every Token Competes — Brevity Is a Feature

Context compression research consistently shows shorter context outperforms longer context, even when the longer version contains more relevant information. Every unnecessary token actively degrades the tokens that matter.

**Implication for context assets**: The "Necessity Test" ("If removed, is the agent more likely to make a mistake?") is validated by the research. Instructions that pass this test earn their token cost; instructions that don't are actively harmful.

### Theme 2: Position Is Power

The attention sink effect (first tokens get disproportionate weight) + lost-in-the-middle (middle tokens get minimal weight) + recency bias (last tokens get high weight) create a clear priority map:

1. **First lines**: Highest-leverage position. Put the single most critical behavioral constraint here.
2. **Last section**: Second-highest leverage. Good for reinforcement of key constraints.
3. **Middle**: Lowest leverage. Put reference material and less critical guidance here.

### Theme 3: Simple Pruning Often Beats Expensive Summarization

JetBrains' observation masking matched LLM summarization at 52% lower cost. The practical implication: strip stale tool outputs rather than paying to summarize them. Agents need their own reasoning chain more than raw outputs from 10 turns ago.

### Theme 4: Drift Is Controllable, Not Inevitable

Dongre et al. show drift reaches equilibria rather than running away. Simple reminder interventions work. This validates periodic re-anchoring strategies (re-injecting key constraints at compaction boundaries, SCAN-style marker questions, "Compact Instructions" sections).

### Theme 5: Fresh Context Per Task Is the Dominant Pattern

GSD-2, HumanLayer, Anthropic's multi-agent system all converge: decompose work into tasks and dispatch each in a fresh context window with only relevant artifacts. Multi-agent outperformance is primarily a context isolation mechanism, not specialization.

### Theme 6: Lazy Loading Beats Eager Loading

Cursor's shift from upfront context loading to dynamic discovery, Anthropic's just-in-time retrieval pattern, and the context-mode MCP server all converge: load less upfront, let the agent pull what it needs. This is more token-efficient and avoids polluting context with unused information.

### Theme 7: Structured External Persistence Is Essential

Agent Drift research shows 21% better stability with explicit long-term memory. MemGPT, Mem0, Anthropic's harness patterns, and the emerging CLAUDE.md/AGENTS.md standard all converge: version-controlled markdown files as behavioral anchors that survive context boundaries.

### Theme 8: Compaction Timing Matters — Earlier Is Better

Multiple sources converge: compact at **60% utilization**, not when forced at 90%+. Context rot is measurable after 20-30 conversation turns. Proactive compaction prevents degradation; reactive compaction tries to recover from it.

---

## 10. Source Index

### Academic Papers

| Citation | URL |
|----------|-----|
| Liu et al. "Lost in the Middle" (TACL 2024) | https://arxiv.org/abs/2307.03172 |
| Hsieh et al. "Found in the Middle" (ACL 2024) | https://arxiv.org/abs/2406.16008 |
| Lost-in-middle mitigation survey | https://arxiv.org/abs/2511.13900 |
| Context length hurts despite perfect retrieval | https://arxiv.org/abs/2510.05381 |
| Xiao et al. "Attention Sinks / StreamingLLM" (ICLR 2024) | https://arxiv.org/abs/2309.17453 |
| "Curse of Instructions" (ICLR 2025) | https://openreview.net/forum?id=R6q67CDBCH |
| IFScale (Feb 2026) | https://arxiv.org/abs/2507.11538 |
| Lam et al. "Instruction Instability" (COLM 2024) | https://arxiv.org/abs/2402.10962 |
| LIFBench (ACL 2025) | https://arxiv.org/abs/2411.07037 |
| Context discipline and performance | https://arxiv.org/abs/2601.11564 |
| Agent Drift quantification (Jan 2026) | https://arxiv.org/abs/2601.04170 |
| "Drift No More?" context equilibria (Oct 2025) | https://arxiv.org/abs/2510.07777 |
| MemGPT (2023-2024) | https://arxiv.org/abs/2310.08560 |
| A-MEM Zettelkasten (Feb 2025) | https://arxiv.org/abs/2502.12110 |
| Mem0 (Apr 2025) | https://arxiv.org/abs/2504.19413 |
| Contextual Memory Virtualisation (Feb 2026) | https://arxiv.org/abs/2602.22402 |
| ACE: Agentic Context Engineering (ICLR 2026) | https://arxiv.org/abs/2510.04618 |
| The Complexity Trap (NeurIPS 2025 DL4Code) | https://github.com/JetBrains-Research/the-complexity-trap |
| Codified Context (Feb 2026) | https://arxiv.org/abs/2602.20478 |
| Context Engineering for Multi-Agent Code Assistants | https://arxiv.org/abs/2508.08322 |
| Context Engineering in OSS | https://arxiv.org/abs/2510.21413 |
| ContextBranch (Dec 2025) | https://arxiv.org/abs/2512.13914 |
| Git Context Controller | https://arxiv.org/abs/2508.00031 |
| Gemini 2.5 Technical Report | https://arxiv.org/abs/2507.06261 |

### Industry Publications

| Source | URL |
|--------|-----|
| Anthropic: Effective Context Engineering | https://www.anthropic.com/engineering/effective-context-engineering-for-ai-agents |
| Anthropic: Effective Harnesses | https://www.anthropic.com/engineering/effective-harnesses-for-long-running-agents |
| Anthropic: Multi-Agent Research System | https://www.anthropic.com/engineering/multi-agent-research-system |
| Chroma: Context Rot | https://research.trychroma.com/context-rot |
| Factory.ai: Compressing Context | https://factory.ai/news/compressing-context |
| Factory.ai: Evaluating Compression | https://factory.ai/news/evaluating-compression |
| JetBrains: Efficient Context Management | https://blog.jetbrains.com/research/2025/12/efficient-context-management/ |
| Manus: Context Engineering Lessons | https://manus.im/blog/Context-Engineering-for-AI-Agents-Lessons-from-Building-Manus |
| OpenAI: Long Horizon Tasks with Codex | https://developers.openai.com/blog/run-long-horizon-tasks-with-codex |
| Karpathy: Context Engineering (X post) | https://x.com/karpathy/status/1937902205765607626 |
| LangChain: Rise of Context Engineering | https://blog.langchain.com/the-rise-of-context-engineering/ |
| Phil Schmid: Context Engineering Part 1 | https://www.philschmid.de/context-engineering |
| Phil Schmid: Context Engineering Part 2 | https://www.philschmid.de/context-engineering-part-2 |
| Kemple: Measuring Context Pollution | https://kurtiskemple.com/blog/measuring-context-pollution/ |
| SCAN Protocol for Prompt Drift | https://dev.to/nikolasi/solving-agent-system-prompt-drift-in-long-sessions-a-300-token-fix-1akh |
| OpenAI: Instruction Hierarchy | https://openai.com/index/instruction-hierarchy-challenge/ |
| Chanl: Agent Drift | https://www.chanl.ai/blog/agent-drift-silent-degradation |
| Harness: Defeating Context Rot | https://www.harness.io/blog/defeating-context-rot-mastering-the-flow-of-ai-sessions |
| Google ADK: Context Compaction | https://google.github.io/adk-docs/context/compaction/ |
| Lance Martin: Context Engineering | https://rlancemartin.github.io/2025/06/23/context_engineering/ |
