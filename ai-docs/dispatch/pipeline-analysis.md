# Dispatch Pipeline Analysis: Industry Comparison and Council Findings

Analysis conducted March 2026 by development council (6 agents, full tier). Scope: workflow design, failure mode mitigations, and industry comparison. Security isolation and full automation out of scope.

## Landscape Position

Dispatch is the most structurally rigorous spec-driven agentic coding pipeline identified in the current landscape. No comparable system implements multi-checkpoint test validation, context-independent breakdown agents, or test-first wave separation.

### Comparable Systems Evaluated

| System | Stages | Test Validation | Context Independence | Orchestration |
|--------|--------|----------------|---------------------|---------------|
| **Dispatch** | 10 (2-3 human decision points) | 4 checkpoints, test-first waves | Breakdown, test creation, implementation | Deterministic (shell script) |
| **Kiro (AWS)** | 3 (requirements, design, tasks) | Tests generated alongside code, not test-first | None documented | Agent-driven |
| **Superpowers** | ~5 (brainstorm, plan, execute, verify, merge) | Post-implementation two-stage review | Subagent-per-task at execution only | Agent-driven (SKILL.md files) |
| **CCPM** | ~6 (brainstorm, PRD, epic, tasks, execute, PRs) | No documented test validation layer | Git worktrees for parallel execution | Agent-driven |
| **TDFlow (CMU/UCSD)** | 4 sub-agents | Takes human-written tests as given (88.8% SWE-Bench Lite) | Single coherent task, shared context | Agentic loop |
| **Spec-Kit (Fred Hutch)** | 7 (constitution, specify, clarify, plan, tasks, analyze, implement) | Pre-implementation consistency check, no test code review | Independent research agents during planning | Agent-driven |
| **GitHub Copilot coding agent** | 1 trigger (assign issue) | Self-review + security scan, automated | Single agent | Automated |
| **Meta JiTTesting** | Per-diff (opposite philosophy) | Disposable tests generated at PR time, not persisted | N/A | Infrastructure-driven |
| **NxCode** | 5 agent roles | Tests generated after implementation | Separate agents but sequential handoff | Agent-driven |

### Key Differentiators

**No other pipeline separates test-writing from implementation agents.** TDFlow achieves 88.8% on SWE-Bench Lite but takes human-written tests as given — it does not address the test quality problem. Superpowers and NxCode use separate agents but as sequential handoff, not context-independent parallel execution with a review gate between them.

**No other pipeline validates test quality at multiple stages.** Most pipelines treat tests as a post-implementation verification step. Dispatch validates test quality progressively: strategy (spec review), task descriptions (task review), actual test code (test code review), and test integrity (verification). This directly addresses MAST's verification gap category (21.30% of multi-agent failures).

**Deterministic orchestration is rare.** Most pipelines use agent-driven orchestration where the agent reads skill/workflow files and decides what to do next. This makes workflow routing an injection surface (85%+ bypass rates against instruction-based defenses, arXiv:2601.17548). Dispatch's shell script dispatcher cannot be prompt-injected because it never processes natural language.

## Research Findings by Domain

### Architecture (Architect)

The pipeline's structural insight is that test quality is the load-bearing element of the entire system, and that test quality must be validated independently of the agents that write the tests or write the code. The Agentic Coding Handbook (Tweag) validates context-independence at execution time: "the test writer's detailed analysis bleeds into the implementer's thinking" in a single context window. Dispatch extends this principle back into planning (breakdown) — a novel and unproven choice.

The inter-wave integration mechanism is the test suite itself. Tests written in Wave 1 (before any implementation) define the integration contracts. If the spec's acceptance criteria include integration behavior and the test reviewer validates coverage, cross-wave integration is tested. If the ACs miss integration behavior, no pipeline mechanism catches it — this is by design, moving quality responsibility to the spec.

Fresh test reviewer instances at each checkpoint (no accumulated context) is the correct architectural choice. A persistent reviewer develops anchoring bias — if it approved the testing strategy, it has an incentive to approve the test tasks and test code. Fresh instances with the spec as the only shared source of truth make each review genuinely independent.

**Sources:**
- [Agentic Coding Handbook - TDD Workflow](https://tweag.github.io/agentic-coding-handbook/WORKFLOW_TDD/)
- [Spec-Kit Walkthrough](https://matsen.fredhutch.org/general/2026/02/10/spec-kit-walkthrough.html)
- [Kiro IDE Spec-Driven Development](https://kiro.dev/docs/specs/)
- [NxCode Agentic Engineering Guide](https://www.nxcode.io/resources/news/agentic-engineering-complete-guide-vibe-coding-ai-agents-2026)
- [Addy Osmani - How to Write a Good Spec for AI Agents](https://addyosmani.com/blog/good-spec/)
- [Mike Mason - AI Coding Agents 2026](https://mikemason.ca/writing/ai-coding-agents-jan-2026/)

### Implementation Complexity (Builder)

**Token cost estimate for a medium-complexity spec** (5 test tasks, 5 implementation tasks, 2 waves): ~1.2-1.5M tokens, approximately $5-15 depending on model mix and cache hit rates. Council review and implementation stages dominate cost (~70% of total spend). The 4 test reviewer checkpoints add meaningful but not dominant cost.

**Context-independent breakdown is unproven at planning time.** No comparable system separates test task planning from implementation task planning. The coordination cost is real: two independently-produced task sets must be compatible (file boundaries, AC coverage). The Task Review gate (Stage 5) catches structural incompatibility, but the false-failure rate is unknown.

**TDFlow comparison:** Achieves 88.8% on SWE-Bench Lite with 4 sub-agents in a test-driven loop, but does NOT separate test writing from implementation — it takes human-written tests as given. Key finding from TDFlow: "the final frontier is accurate generation of valid reproduction tests," which is exactly the problem Dispatch's test reviewer targets. TDFlow validates Dispatch's focus on test quality but highlights that nobody has proven agent-written-then-reviewed tests work as well as human-written tests at scale.

**Meta JiTTesting is the philosophical opposite:** Generate disposable tests on-the-fly per diff, tests don't live in the codebase. Works at Meta's scale with Meta's infrastructure. Interesting counterpoint — both are responses to the same problem (agent-written code has more bugs) with opposite strategies.

**Sources:**
- [TDFlow: Agentic Workflows for TDD (arXiv:2510.23761)](https://arxiv.org/abs/2510.23761)
- [Meta JiTTesting](https://engineering.fb.com/2026/02/11/developer-tools/the-death-of-traditional-testing-agentic-development-jit-testing-revival/)
- [Thoughtworks - Spec-Driven Development](https://www.thoughtworks.com/en-us/insights/blog/agile-engineering-practices/spec-driven-development-unpacking-2025-new-engineering-practices)
- [Simon Willison - Red/Green TDD for Agents](https://simonwillison.net/guides/agentic-engineering-patterns/red-green-tdd/)

### Quality and Failure Modes (Guardian)

**MAST failure taxonomy mapping** (arXiv:2503.13657, 1,600+ traces, 14 failure modes):
- Coordination failures: 36.94% — addressed by context-independence and deterministic task review
- Verification gaps: 21.30% — directly addressed by the 4-checkpoint test reviewer model
- System design issues: remaining — addressed by council review of spec architecture

**Checkpoint value is not equal across the four stages.** Checkpoints 1 (test strategy at spec review) and 2 (test tasks at task review) are cheap and high-leverage — they catch problems before any compute is spent. Checkpoint 3 (test code review) is the heaviest and most critical — it must catch C1 (oracle captures actual behavior), C2 (silent test fabrication), C3 (test smells), and C5 (implementation coupling) in actual code. Checkpoint 4 (test integrity at verification) catches a narrow but critical scenario: implementation agents weakening assertions.

**"Tests compile and fail" is necessary but insufficient.** A test can compile and fail for reasons unrelated to the behavior it claims to test — wrong import, misconfigured fixture, assertion against nonexistent method. These tests pass the gate but would pass trivially once implementation creates the referenced method, regardless of correctness. The test code review (checkpoint 3) is the mitigation, but this concentrates risk on a single agent's judgment.

**No defense-in-depth beyond the test reviewer for test quality.** The verification engine checks whether tests pass, not whether tests are good. If the reviewer approves bad tests, those bad tests become the completion gate for implementation — the pipeline will produce code that makes bad tests pass. Mutation testing as a structural supplement addresses this gap.

**Sources:**
- [MAST: Why Do Multi-Agent LLM Systems Fail? (arXiv:2503.13657)](https://arxiv.org/abs/2503.13657)
- [MAST GitHub Repository](https://github.com/multi-agent-systems-failure-taxonomy/MAST)
- [LLM Test Oracle Behavior (arXiv:2410.21136)](https://arxiv.org/abs/2410.21136)
- [Test Smells in LLM-Generated Tests (arXiv:2410.10628)](https://arxiv.org/abs/2410.10628)
- [Anthropic 2026 Agentic Coding Trends Report](https://resources.anthropic.com/hubfs/2026%20Agentic%20Coding%20Trends%20Report.pdf?hsLang=en)
- [Spec-Driven Development Map (30+ frameworks)](https://medium.com/@visrow/spec-driven-development-is-eating-software-engineering-a-map-of-30-agentic-coding-frameworks-6ac0b5e2b484)

### Security (Workflow Scope) (Security)

**Context-independence limits blast radius, not probability.** 85%+ prompt injection bypass rates (arXiv:2601.17548, 42 techniques cataloged) mean no single agent reliably resists injection. Dispatch's architecture ensures a compromised agent cannot propagate to downstream agents through shared context. An attacker would need to successfully inject into multiple independent agent contexts to achieve a coherent malicious outcome across both tests and implementation.

**Stage 2 validation is "catch the obvious," not injection prevention.** Pattern-matching against known injection templates is fragile. The pipeline's actual injection resilience comes from architectural properties: context-independence, Least Agency, deterministic gates that cannot be talked past. Stage 2 should be framed honestly as a first filter, not a defense.

**Three remaining propagation paths** (inherent to any pipeline where agents produce artifacts for other agents):
1. Spec artifact shared across every agentic stage — injection payload surviving Stage 2 reaches all agents
2. Test files written by Stage 6 agents read by Stage 8 agents — injection in comments/fixtures enters implementation context
3. Wave N output read by Wave N+1 agents — code-level injection (misleading comments, variable names) propagates

Blast radius of each path is bounded by Least Agency and deterministic gates.

**"Cannot modify tests" enforcement.** ODCV-Bench (arXiv:2512.20798) shows agents violate explicit constraints 30-50% of the time. Instruction-only enforcement will fail. SHA-based hash comparison of test files (deterministic) is the correct enforcement mechanism, with the agentic test integrity check as advisory on top.

**Sources:**
- [Prompt Injection on Agentic Coding Assistants (arXiv:2601.17548)](https://arxiv.org/html/2601.17548v1)
- [ODCV-Bench: Constraint Violation Rates (arXiv:2512.20798)](https://arxiv.org/abs/2512.20798)
- [CrowdStrike - Hidden Vulnerabilities in AI-Coded Software](https://www.crowdstrike.com/en-us/blog/crowdstrike-researchers-identify-hidden-vulnerabilities-ai-coded-software/)
- [Veracode - AI Development Security Gap](https://www.theregister.com/2026/02/26/veracode_security_ai)
- [OWASP Top 10 for Agentic Applications 2026](https://genai.owasp.org/resource/owasp-top-10-for-agentic-applications-for-2026/)
- [NVIDIA Sandboxing Guidance for Agentic Workflows](https://developer.nvidia.com/blog/practical-security-guidance-for-sandboxing-agentic-workflows-and-managing-execution-risk/)

### User Experience (Advocate)

**10 stages ≠ 10 human decision points.** Of the 10 stages, only 2 require genuine human judgment: Stage 3 (council review — the developer evaluates architectural feedback and decides whether to iterate) and Stage 5 (task review — the developer scans tasks against their mental model). Stages 1-2 are deterministic bookkeeping. Stages 4, 6, 8 are agentic execution (the human has nothing to decide unless something fails). Stages 7, 9, 10 produce pass/fail results that auto-advance on success.

**Industry comparison on ceremony:**
- Kiro (3 stages) faces "sledgehammer for a nut" criticism even at 3 stages
- GitHub Copilot coding agent (1 trigger) trades quality for simplicity
- Superpowers (~5 stages) requires human presence throughout
- CCPM (~6 stages) automates transitions

**v1 risk:** Every early adopter pays the full ceremony cost during the period when first impressions determine adoption. A "run-to-decision-point" mode (invoke once, pipeline runs until it needs human judgment) preserves every gate while reducing friction to 2-3 interactions on the happy path.

**Sources:**
- [Martin Fowler - SDD Tools](https://martinfowler.com/articles/exploring-gen-ai/sdd-3-tools.html)
- [GitHub Blog - Spec-driven development with AI](https://github.blog/ai-and-ml/generative-ai/spec-driven-development-with-ai-get-started-with-a-new-open-source-toolkit/)
- [InfoQ - AWS Kiro](https://www.infoq.com/news/2025/08/aws-kiro-spec-driven-agent/)
- [GitHub Blog - Copilot coding agent](https://github.blog/ai-and-ml/github-copilot/whats-new-with-github-copilot-coding-agent/)
- [Graphite - Adopting AI tools](https://graphite.com/guides/adopting-ai-tools-development-workflow)
- [GitHub Blog - Agentic primitives](https://github.blog/ai-and-ml/github-copilot/how-to-build-reliable-ai-workflows-with-agentic-primitives-and-context-engineering/)

### Metrics and Evidence (Analyst)

**Stat provenance for vision claims:**

| Claim in Spec | Source | Actual Finding | Population |
|--------------|--------|----------------|------------|
| 1.7x more bugs | CodeRabbit Dec 2025 | 10.83 issues/PR (AI) vs 6.45 (human) | 470 open-source PRs |
| Doubled code churn | GitClear 2024 | 3.1% → 5.7% churn rate | 153M+ LOC, 2020-2024 |
| 8x more duplication | GitClear 2024 | Duplicated code blocks grew ~8x year-over-year | Same population |
| 60% collapse in refactoring | GitClear 2024 | Refactoring dropped from ~25% to under 10% of changes | Same population |
| 1.57x security vulnerabilities | CodeRabbit Dec 2025 | Security issues 1.57x more frequent in AI PRs | 470 open-source PRs |

The CodeRabbit and GitClear studies measure different things across different populations. The spec should cite sources inline and state comparison baselines explicitly.

**FeatureBench calibration:** Claude Opus 4.5 solves 11% of feature-level tasks (790 lines, 15.7 files) vs 74.4% on SWE-bench (smaller scope). Dispatch's decomposition aims to keep each agent in the 74-80% reliability zone (1-2 files, under 55 lines per task). The pipeline's actual risk is integration failure across tasks, not per-task failure.

**No competing pipeline has published controlled quality metrics.** Superpowers has 75k+ stars but no quality data. CCPM reports ~2x shipping speed but no defect rates. Kiro has no published before/after comparison. This means Dispatch cannot benchmark against alternatives on defect rates — only on architectural features. First-mover advantage in publishing quality metrics would be significant.

**Sources:**
- [CodeRabbit AI vs Human Code Report](https://www.businesswire.com/news/home/20251217666881/en/)
- [GitClear AI Code Quality 2025](https://www.gitclear.com/ai_assistant_code_quality_2025_research)
- [FeatureBench (arXiv:2602.10975)](https://arxiv.org/abs/2602.10975)

## Council Recommendations

### 1. Make test file immutability deterministic (unanimous)

After Stage 7 approval, compute SHA hashes of all test files. At Stage 9, run deterministic comparison before the agentic test integrity check. Any modification hard-fails the pipeline. Converts the most critical constraint from agentic judgment to a checksum property. ~20 lines of shell script.

### 2. Add lightweight mutation testing between Stage 7 and Stage 8 (Guardian, supported by Analyst)

After test code is approved, inject targeted mutations into stub implementations and verify approved tests detect them. Not full mutation testing — a focused sanity check that tests have detection power. Addresses the test reviewer's single-point-of-failure risk.

### 3. Ship v1 with "run-to-decision-point" mode (Advocate, supported by Builder + Architect)

Invoke once; the pipeline runs through deterministic and successful agentic stages automatically, parking only at genuine human decision points (Stages 3 and 5) or on any failure. ~30 lines of shell. Not v2 automation — just not wasting developer attention on green checkmarks.

### 4. Add inter-wave interface verification (Guardian)

After each wave's verification pass, deterministically compare actual file signatures modified by Wave N against file references in Wave N+1's task definitions. Catches interface mismatches before downstream agents discover them.

### 5. Attribute vision statistics precisely (Analyst)

Replace conflated statistics with source-attributed claims including study population and comparison baseline.

### 6. Instrument checkpoint effectiveness from day one (Analyst)

Log every gate rejection with defect type, stage, token cost, and structured reason. Track gate pass/fail rates per stage. Required for proving the pipeline's value proposition.

### 7. Allow natural language in test task descriptions (Builder)

Pure no-prose format works for implementation tasks but loses the "why" behind a test. Test tasks should include a brief behavioral description alongside structured fields.

### Dissenting View

**Builder vs Guardian on Stage 5 test-task-quality checkpoint:** Builder argues the agentic test-task-quality sub-check could be dropped — test-writing is cheap relative to implementation, so catching bad test tasks saves less than the checkpoint costs. Guardian argues it catches breakdown agent misinterpretation before any compute is spent. Cost-benefit tradeoff for the user to decide.
