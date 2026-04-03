# Spec-Driven Development Workflow — Council Research Findings

Council session research on coding agent workflow automation, analyzing how spec-driven pipelines compare to industry patterns. These findings informed the design of the SDL workflow in this repo.

---

## Unanimous Findings

### Spec-driven development is validated

GitHub Spec Kit, JetBrains Junie, QuantumBlack (McKinsey), EPAM all endorse the pattern. SWE-bench Pro: removing human specifications drops GPT-5 from 25.9% to 8.4%. ICSE 2026: measurable gains in functional correctness, architectural conformance, and code modularity when architectural documentation guides LLM code generation. EPAM reports up to 80% of structured tasks can be automated when guided by specs.

### Effective agent teams cap at 3-4

Google scaling study (arXiv:2512.08296): communication overhead grows super-linearly beyond 3-4 agents (exponent 1.724). Tool-heavy tasks suffer 2-6x efficiency penalties.

### Task decomposition to bounded units is correct

SWE-bench Pro: performance drops catastrophically on long-horizon tasks (70%+ to ~23%). Long-running agents degrade after 35 minutes of human time (Anthropic). 57% of organizations now deploy multi-step agent workflows with decomposed stages (Anthropic 2026 Agentic Coding Trends).

### AI self-review without external grounding is unreliable

Huang et al. (ICLR 2024): LLMs cannot self-correct reasoning without external feedback — performance sometimes degrades after self-correction. Kamoi et al. (TACL 2024): works only with reliable external feedback (test results, linter output). VerifiAgent (2025): separate LLM for verification outperforms same-model self-review. Verdent: AI review adds ~0.5% lift per attempt. DeCRIM (EMNLP 2024): decomposed verification adds 7-8% — value comes from specificity of criteria, not from running the same check twice.

### Model routing economics are sound but need empirical validation

Haiku 4.5: 73.3% vs. Sonnet's 77.2% on SWE-bench Verified (within 5pp) at ~3x less cost. Qodo 400-PR: Haiku won 55.19% vs. Sonnet's 44.81% on code review quality at one-third cost. 80/20 split theoretically saves 65-70%. But measure cost-per-completed-task, not cost-per-attempt — if Haiku rework exceeds 15% of attempts, savings evaporate.

### E2E testing gates are strongly justified

AI-generated code averages 1.77 quality issues per "passing" task (arXiv:2407.06153). 40-45% of AI-generated code contains security vulnerabilities (Veracode 2025, CrowdStrike). LLMs frequently hallucinate library APIs; only integration/E2E tests against real dependencies catch these.

### Parallel speedup is sub-linear

M1-Parallel (arXiv:2507.08944): 1.8-2.2x speedup with 5 parallel agents, not 5x. Practical concurrency cap at 4-6 parallel tasks before diminishing returns and rate limits.

### Hard handoffs are defensible but should be lightweight

METR study (July 2025, peer-reviewed, 16 developers, 246 issues): AI tools made developers 19% slower. Stack Overflow 2025: trust in AI accuracy at 29%. Phase-gated review prevents compound errors. But handoffs must be near-zero-friction for routine work.

### No baseline measurement exists

Without measuring single-pass performance first, the pipeline's ROI cannot be validated. This is the single most important gap.

---

## Architecture Recommendations

### 1. Keep runtime agents minimal

Prefer a small number of focused agents (Spec Agent, Implement Agent, deterministic Verify Gate) over large agent teams. Research shows diminishing returns beyond 3-4 agents.

### 2. Use append-only stage outputs over shared mutable state

Each stage writes an immutable output file. Eliminates write-contention, makes recovery trivial, provides full audit trail. Shared mutable state (e.g., `state.json`) is prone to corruption in concurrent agent scenarios (documented in Claude Code issues #28847, #28922, #29036).

### 3. Replace AI-reviewing-AI with deterministic verification gates

| Gate | What it checks | How |
|------|---------------|-----|
| Spec → Implement | Spec has required sections, acceptance criteria present | JSON Schema validation |
| Implement → Verify | Code compiles, no new lint errors, files within declared scope | Build + lint + scope-boundary check |
| Verify → Done | Tests pass, coverage thresholds met, acceptance criteria satisfied | Test runner + criteria matcher |

Zero AI-reviewing-AI passes. Verification value comes from running tests, linters, and schema validation — not AI re-reading AI output.

### 4. Add a single feedback loop: Verify → Re-plan

On verification failure, feed a structured error report back to the planning stage (not the implementation stage). Capped at 2 re-plans per task, then escalate to human. The feedback crosses an agent boundary with external signal (test failure) — the only scenario where correction reliably works.

### 5. Measure before optimizing

40 representative tasks, stratified by complexity. 20 through the pipeline, 20 single-pass-with-review. Minimum detectable effect at n=20 per arm is ~25pp — directional, not precise.

Track 4 metrics from day 1:
1. Task completion rate by stage (% passing without human intervention)
2. Cost per completed task (total tokens / tasks reaching done)
3. Cycle time distribution (wall-clock minutes: queue, execution, rework)
4. Human intervention rate (at which stage, why)

The pipeline earns its keep only when single-pass failure rate exceeds 40-50%.

### 6. Validate model routing empirically

Run same 30 tasks through Sonnet-only and through Haiku/Sonnet mix. Compare cost-per-completed-task, not cost-per-attempt. If Haiku rework exceeds 15% of attempts, routing savings evaporate.

### 7. Anti-over-engineering: move from rules to examples

Evidence that prompt-based "do not over-engineer" constraints work is weak. Stronger approach: curate 2-3 canonical examples of right-sized implementations. Pair with eval-driven iteration.

---

## Unresolved Questions

**5-30 minute task granularity has no empirical basis.** No study validates this specific range. Instrument first 20-30 tasks and adjust empirically.

**Routing classifier accuracy is undefined.** Misrouting complex tasks to Haiku could create costly rework. Needs explicit routing policy with fallback/escalation.

**100% traceability may be over-specified.** Strongest evidence is in safety-critical domains (healthcare, finance, automotive). In agile environments, lightweight traceability (story-to-test mapping) provides most of the value. No peer-reviewed research demonstrates 100% traceability in AI-assisted pipelines improves outcomes over lighter alternatives.

---

## Key Quotes

> "This pipeline is over-engineered. Every agent boundary is a serialization point, a prompt to maintain, and a failure mode." — Builder

> "Do not measure token savings or theoretical throughput — measure 'how long until I have working, tested code I trust.'" — Builder

> "Builder's bypass path for simple tasks is the right instinct, but 'simple' cannot be a manual classification the user makes before every task. That is its own form of user burden." — Advocate

> "I am not going to burn instruction budget on threats that require an attacker with commit access to a solo developer's local machine." — Security

> "Without measuring single-pass performance first, the pipeline's ROI cannot be validated. This is the single most important gap." — Analyst

---

## Industry Context

**Two camps emerging:** (a) Autonomous/parallel orchestration (Cursor 2.0, Devin) and (b) spec-driven sequential pipelines with human checkpoints (GitHub Spec Kit, JetBrains Junie). This pipeline sits firmly in camp (b).

**Orchestration patterns:** Sequential, DAG-based, Managerial (supervisor-directed), Hybrid. Wave-based execution maps to scatter-gather. DAGs offer 10-30% better throughput but add dependency specification complexity.

**MAST taxonomy (arXiv:2503.13657):** 14 failure modes from 1,600+ traces across 7 frameworks. Coordination failures: 36.94%. Verification gaps: 21.30%. Accuracy saturates beyond 4 agents.

**Atlassian HULA (ICSE 2025, 663 work items):** Generated coding plans for 79% of items; 82% approved by engineers; 87% of approved plans produced code; only 25% reached PR stage.

**Analyst's cost model:** Pipeline is worth it only when `(single_pass_rework_rate * rework_cost) > overhead + (pipeline_rework_rate * rework_cost)`. For tasks under 50 lines of change, overhead likely exceeds benefit.

---

## References

| Short name | Citation | Used for |
|---|---|---|
| Google Scaling | arXiv:2512.08296 | 3-4 agent ceiling, super-linear overhead |
| SWE-bench Pro | SWE-bench Pro benchmark | Long-horizon task degradation |
| METR | July 2025, 16 developers, 246 issues | 19% slowdown with AI tools |
| QuantumBlack | McKinsey, February 2026 | Deterministic orchestration + bounded execution |
| EPAM / GitHub Spec Kit | EPAM analysis | 80% automation with specs |
| ICSE 2026 | Architectural docs + LLM generation | Functional correctness gains |
| Huang et al. | ICLR 2024 | Self-correction failure |
| Kamoi et al. | TACL 2024 | External feedback requirement |
| VerifiAgent | 2025 | Separate verifier outperforms self-review |
| DeCRIM | EMNLP 2024 | Decomposed verification 7-8% lift |
| Verdent | 2025 | AI review ~0.5% lift |
| M1-Parallel | arXiv:2507.08944 | Sub-linear parallel speedup |
| MAST | arXiv:2503.13657 | Multi-agent failure taxonomy |
| HULA | ICSE 2025 | Multi-stage approval pattern |
| Veracode | 2025 | 45% AI code contains flaws |
| CrowdStrike | 2025 | AI-specific vulnerability patterns |
| arXiv:2407.06153 | 2024 | 1.77 quality issues per passing task |
| Stack Overflow | 2025 survey | 29% trust in AI accuracy |
| Anthropic Agentic Trends | 2026 | 57% multi-step agent workflows |
| arXiv:2601.17548 | 2025 | Prompt injection in agentic coding |
| OWASP Agentic Top 10 | 2026 | Agent-specific threat taxonomy |
| Qodo 400-PR | Qodo benchmark, 400 PRs | Haiku vs Sonnet code review quality |
| Azure Multi-Agent Guidance | Microsoft Azure documentation | Single-agent preference when sufficient |
| Anthropic Multi-Agent Research | Anthropic internal system | File-based context isolation pattern |
| SAGA | 2025 | Dual-pronged verification +9.55% detection rate |
| GeneAgent | Nature Methods, 2025 | Self-verification against external databases |
| Osmani / O'Reilly | "Conductors to Orchestrators" | Conductor-vs-orchestrator spectrum |
| Gloria Mark | Context switching research | 23 min 15 sec to regain focus after interruption |
| arXiv:2505.18286 | 2025 | Verification overhead grows exponentially with depth |
| arXiv:2506.23260 | 2025 | Unified threat model, 30+ attack techniques |
| Agent Security Bench | ICLR 2025 | Attack surfaces: inputs, profiles, inter-agent messages |
| AGENTbench (ETH Zurich) | 2025 | Context files increase inference costs up to 159% |
| Claude Code Issues | GitHub #28847, #28922, #29036 | `state.json` concurrent write corruption |
