# Remediation Workflow: Research and Design Exploration

**Date**: 2026-03-20
**Context**: Pre-spec research for the next Firebreak iteration. Captures findings from code review product analysis, AI code review effectiveness research, tools landscape analysis, pitfall documentation, semantic drift detection techniques, permissions landscape research, Anthropic's internal skills practices, and design exploration of a remediation workflow for AI-degraded codebases.

## Motivation

Two rounds of testing (greenfield + brownfield) validated the SDL pipeline for *forward* workflows — building new features or adding to existing code. The next test targets a *remediation* workflow: diagnosing and fixing existing AI-generated code that is "technically working" but architecturally degraded.

This is motivated by a real-world pattern: AI-assisted codebases where bug fixes silently bypass core mechanisms, tests validate surface behavior without exercising intended architecture, and iterative AI changes accumulate semantic drift. The pipeline needs a front door for this class of work.

## The source of truth problem

Remediation requires knowing what "correct" looks like before you can identify what's wrong. This is fundamentally different from forward workflows, where the spec *defines* correctness.

Three distinct scenarios require different levels of human involvement:

| Scenario | Source of truth | Human role | Example |
|---|---|---|---|
| **Cleanup** | Code is the spec. Design intent is clear from reading it. | Approve/reject findings | Copy-paste duplication, magic numbers, dead code |
| **Spec-backed remediation** | Existing specs define intended behavior, but may conflict across iterations | Resolve spec conflicts, confirm which spec is current | Projects with formal specs that evolved over time |
| **Intent recovery** | No spec. "Working" is ambiguous. Core mechanisms may have been silently bypassed | Co-explore with audit agent to establish what the system *should* do | Most real-world AI-assisted codebases |

The critical distinction is between two failure classes:

1. **Cosmetic degradation** — the code works as designed but has maintainability debt. Tests pass, architecture is intact, but there's duplication, hardcoding, or style issues. An audit agent can identify these autonomously.

2. **Semantic drift** — the code "works" in that user-facing flows produce output, but has silently abandoned the design intent. Core mechanisms are bypassed, architectural layers are short-circuited, and the system is a hollow shell of what was specified. An audit agent looking at this code sees passing tests and functional user flows — it *looks correct*. The only signal that something is wrong is design intent that exists in the human's understanding or in specs that may be stale.

Automated review (including Anthropic's) checks correctness against *code behavior*, not *design intent*. It can find "this null check is wrong" but not "this module was supposed to use the caching layer and it's been bypassed." Remediation for semantic drift requires the human to establish ground truth before any audit can determine what's wrong.

### Why spec-aware review doesn't exist yet

No tool in the current landscape does spec-aware review. Two reasons:

1. **Spec maintenance is poor in practice.** Most teams don't maintain specs because there's no tooling that rewards keeping them current. If specs are just documentation, the maintenance cost is pure overhead with no automated payoff. This is a chicken-and-egg problem: spec-aware review requires maintained specs, but no one maintains specs because there's no tooling that uses them.

2. **Spec-driven development with structured artifacts is new.** The pattern of structured architecture artifacts as first-class pipeline inputs — not human documentation, but machine-readable design intent — emerged in the agentic coding space in late 2025/early 2026. GSD-2's "truths," Firebreak's specs and ACs, BMAD's PRDs, Kiro's specs, spec-kit — these all emerged from the same moment: developers realizing that unstructured prompting produces degraded output. This has high adoption in the agentic coding social media ecosystem but doesn't yet have significant adoption in enterprise codebases or legacy codebases. Enterprise is still in the "Copilot autocomplete" phase, without structured AI workflows or the artifacts they produce.

Firebreak is uniquely positioned for spec-aware review because it already produces the structured artifacts. The spec → review → breakdown pipeline generates exactly the machine-readable design intent that a review tool would check against. The exploration phase of remediation is essentially retrofitting those artifacts onto a codebase that never had them.

The spec maintenance problem is solvable within the pipeline. Anthropic's code review already does bidirectional `CLAUDE.md` enforcement — flagging when a PR makes docs stale. The same pattern applied to specs (flag when implementation drifts from spec) would close the maintenance loop.

## Anthropic's code review architecture

Anthropic offers three code review products with distinct architectures:

| Product | Type | Architecture | Cost |
|---|---|---|---|
| **Code Review for Claude Code** | Managed SaaS (Teams/Enterprise) | Multi-agent pipeline on Anthropic infrastructure | ~$15-25 per review (token-based) |
| **claude-code-action** | Open-source GitHub Action | Single agent on user's runners | API token costs |
| **claude-code-security-review** | Open-source GitHub Action | 5-step security pipeline, Opus 4.1 | API token costs |

### Premium code review: adversarial verification

The managed product runs a three-stage pipeline:

1. **Parallel bug detection**: Multiple specialized agents dispatched simultaneously, each targeting a different issue class (logic errors, boundary conditions, API misuse, authentication flaws, project convention violations).
2. **Verification and filtering**: A verification agent attempts to *disprove* each finding against actual code behavior. Only findings that survive this adversarial challenge are surfaced.
3. **Deduplication and severity ranking**: Surviving findings are deduplicated, classified, and posted as inline PR comments.

Result: <1% of posted findings are marked incorrect by engineers. Processing time: ~20 minutes per review.

### Severity taxonomy

| Marker | Level | Meaning |
|---|---|---|
| Red | Normal | Bug that should be fixed before merging |
| Yellow | Nit | Minor issue, worth fixing but not blocking |
| Purple | Pre-existing | Bug that exists in the codebase but was NOT introduced by this PR |

The "pre-existing" category is relevant to remediation — it surfaces latent bugs in adjacent code. However, it's still anchored to "code the PR touched," not a full codebase audit.

### Key design decisions

**Default to correctness, not style.** Formatting and style nits are suppressed by default. Only bugs that would break production are surfaced. Style rules are opt-in via a separate `REVIEW.md` file. This prioritizes signal-to-noise ratio.

**Non-blocking by design.** Findings never approve or block PRs. The human decides what to act on. This maps to the triage question in remediation: the audit produces findings, the human decides which ones become specs.

**Two-file configuration.** `CLAUDE.md` (shared with all Claude tools) + `REVIEW.md` (review-only guidance). Review rules don't pollute interactive instructions.

**Bidirectional enforcement.** If a PR makes a `CLAUDE.md` rule outdated, the review flags that the docs need updating. For remediation: if a fix changes behavior, the audit should flag when specs/docs become stale.

### What the code review products don't solve

All three products are *diff-triggered* — they review changes in a PR. Remediation needs to audit *existing code without a diff*. The "pre-existing" severity category is a step toward this, but the entry point is still a PR, not a codebase scan.

More critically, all three check correctness against code behavior, not design intent. They cannot detect semantic drift — code that "works" but has abandoned its architectural purpose.

### Sources

- [Code Review for Claude Code — official docs](https://code.claude.com/docs/en/code-review)
- [Code Review announcement blog post](https://claude.com/blog/code-review)
- [Claude Code GitHub Actions docs](https://code.claude.com/docs/en/github-actions)
- [anthropics/claude-code-action — GitHub](https://github.com/anthropics/claude-code-action)
- [anthropics/claude-code-security-review — GitHub](https://github.com/anthropics/claude-code-security-review)
- [TechCrunch: Anthropic launches code review tool](https://techcrunch.com/2026/03/09/anthropic-launches-code-review-tool-to-check-flood-of-ai-generated-codes/)
- [The New Stack: Multi-agent code review](https://thenewstack.io/anthropic-launches-a-multi-agent-code-review-tool-for-claude-code/)
- [DEV Community: Multi-Agent PR Reviews](https://dev.to/umesh_malik/anthropic-code-review-for-claude-code-multi-agent-pr-reviews-pricing-setup-and-limits-3o35)

## AI code review effectiveness

### Detection accuracy

**Best single-pass F1: 19%.** The SWR-Bench benchmark (1,000 manually verified GitHub PRs from 12 Python projects) found the best combination (PR-Review + Gemini-2.5-Pro) achieved F1 of 19.38%. All techniques exhibited precision below 10% on average. Functional errors (logic bugs): F1 ~26%. Style issues: F1 6-16%. Critical consistency finding: across 5 independent runs of the same model, only 27 change-points overlapped. Single-pass reviews are unreliable.
> Zeng et al. "Benchmarking and Studying the LLM-based Code Review." [arXiv:2509.01494](https://arxiv.org/html/2509.01494v1), 2025.

**Real-world bug detection: 42-48%.** Greptile's benchmark across 5 repos with 10 real bug-fix PRs each found CodeRabbit caught 46%, Cursor Bugbot 42%. Traditional static analyzers: below 20%.
> [Greptile AI Code Review Benchmarks 2025](https://www.greptile.com/benchmarks)

**Correctness classification: 68.5%.** GPT-4o classified code correctness 68.50% of the time with problem descriptions. Regression rates (suggesting wrong fixes for correct code): 10.43%.
> Cihan et al. [arXiv:2505.20206](https://arxiv.org/html/2505.20206v1), 2025.

### Multi-agent and multi-pass approaches

**Self-aggregation improves F1 by 43.67%.** Running the same LLM 10 times and aggregating results: recall improved 118.83%. Smaller models with aggregation approach larger models' single-pass performance. This is empirical justification for multi-agent architectures — the variance reduction from multiple independent passes is a measured effect.
> Zeng et al. [arXiv:2509.01494](https://arxiv.org/html/2509.01494v1), 2025.

**Anthropic verification agents: <1% error rate.** Substantive comments jumped from 16% to 54% of PRs. On large PRs (1,000+ lines), 84% get findings averaging 7.5 issues.
> [Anthropic Code Review blog](https://claude.com/blog/code-review)

**Diffray: 87% fewer false positives** (vendor-reported, not independently verified). 10+ specialized agents with cross-agent validation. False positives from 60% to under 13%.
> [Diffray Multi-Agent Code Review](https://diffray.ai/multi-agent-code-review/)

### Hybrid approaches (LLM + static analysis)

**IRIS (LLM + CodeQL): 103.7% more vulnerabilities.** Detected 55 vs CodeQL's 27 alone. Improved false discovery rate by 5 points. Discovered 4 previously unknown vulnerabilities. Architecture: LLMs infer taint specs; CodeQL performs analysis; LLM contextual analysis reduces false positives.
> "IRIS: LLM-Assisted Static Analysis." [arXiv:2405.17238](https://arxiv.org/abs/2405.17238), 2024.

**CORE proposer-ranker (Microsoft, FSE 2024): 25.8% fewer false positives.** Proposer LLM generates candidates. Static analysis filters. Ranker LLM evaluates against human acceptance criteria.
> "CORE: Resolving Code Quality Issues using LLMs." [ACM FSE 2024](https://dl.acm.org/doi/10.1145/3643762).

### Specification-aware review

**Over-correction bias is the key finding.** When asked "is this code correct?", LLMs develop a bias toward assuming defects exist. GPT-4o accuracy dropped from 52.4% to 11.0% with explain-and-fix prompts. Two strategies that work:
1. **Two-Phase Reflective Prompt** — separates requirement extraction from code auditing
2. **Behavioral Comparison Prompt** — compares spec against implemented behavior directly. GPT-4o reached 85.4%.

**Design implication**: Audit agents should be framed as *behavioral description followed by comparison*, not as *defect detection*.
> "Uncovering Systematic Failures of LLMs in Verifying Code Against NL Specifications." [arXiv:2508.12358](https://arxiv.org/html/2508.12358v1)

**ADR violation detection: 83-90%+ accuracy.** LLMs achieved 83.38% agreement judging ADR compliance. Struggled with missing context, infrastructure details, and cross-module interactions.
> [arXiv:2602.07609](https://arxiv.org/html/2602.07609v1), 2026.

**Design pattern classification: 38.81% accuracy.** LLMs are bad at recognizing design patterns. Singleton and Factory over-predicted due to training data.
> "Do Code LLMs Understand Design Patterns?" [arXiv:2501.04835](https://arxiv.org/abs/2501.04835), 2025.

### Industry deployment at scale

- **Microsoft**: AI review covers 90% of PRs, 600K+/month. Used as first-pass; critical PRs still go to humans. ([Microsoft Engineering blog](https://devblogs.microsoft.com/engineering-at-microsoft/enhancing-code-quality-at-scale-with-ai-powered-code-reviews/))
- **Cursor Bugbot**: 2M+ PRs/month. Resolution rate 52% → 76% over 6 months through 40 experiments. Largest jump from fully agentic architecture. ([Cursor blog](https://cursor.com/blog/building-bugbot))
- **Google DIDACT**: ML model resolves review comments automatically at Google scale. ([Google Research](https://research.google/pubs/resolving-code-review-comments-with-machine-learning/))

### AI-generated code quality (context for remediation)

- **DORA 2024-2025**: For every 25% increase in AI adoption, delivery stability decreased 7.2%, throughput decreased 1.5%. Root cause: "Teams with weak processes simply ship low-quality work... only faster." ([DORA 2024](https://cloud.google.com/blog/products/devops-sre/announcing-the-2024-dora-report) | [DORA 2025](https://cloud.google.com/blog/products/ai-machine-learning/announcing-the-2025-dora-report))
- **GitClear (211M lines, 2020-2024)**: Code churn 3.1% → 5.7%. Copy/paste 8.3% → 12.3% (+48%). Refactoring 24.1% → 9.5% (-60%). Duplicated blocks up eightfold. ([GitClear 2025](https://www.gitclear.com/ai_assistant_code_quality_2025_research))
- **Apiiro (Fortune 50)**: Architectural design flaws spiked 153% in AI-generated code. Privilege escalation paths jumped 322%. Trivial syntax errors dropped 76%. *The surface improves while the depth degrades.* ([Apiiro blog](https://apiiro.com/blog/4x-velocity-10x-vulnerabilities-ai-coding-assistants-are-shipping-more-risks/))

## AI code review tools landscape

### Architecture taxonomy

| Pattern | Examples | Strengths | Weaknesses |
|---|---|---|---|
| Single-pass LLM | Bito, Copilot, PR-Agent | Fast, simple, low cost | High FP, no cross-file context |
| Multi-pass LLM pipeline | CodeRabbit, Ellipsis | Better coverage, specialized passes | Slower, higher cost |
| Multi-agent adversarial | Anthropic Premium, Diffray | Lowest FP rate via verification | Highest cost, slowest (20min+) |
| Static analysis + LLM hybrid | Codacy, CodeAnt, IRIS | Deterministic base + contextual triage | Limited to known patterns |
| Full codebase indexing + RAG | Greptile | Cross-file context, convention detection | Index cost, noise trades for coverage |
| Review by testing | Qodo | Concrete evidence for findings | Only catches testable issues |
| Symbolic AI + ML | Snyk Code | Low FP for security, deep dataflow | Security-only, proprietary |

### Notable tools and their relevance

**CodeRabbit** (https://coderabbit.ai): Multi-pass pipeline with persistent knowledge graph. "Learnings" system accumulates project-specific knowledge — the closest any commercial tool gets to convention enforcement. Most talkative in benchmarks; 28% noise.

**Greptile** (https://www.greptile.com): Full codebase indexing via vector store + RAG. Can detect convention violations by comparing new code against existing patterns across the entire repo. Highest bug catch rate (82%) but also highest FP rate. Relevant to the exploration phase — codebase chat for architectural questions.

**Qodo** (https://www.qodo.ai): "Review by testing" — generates tests to prove findings. If the test passes, the concern was unfounded. Sidesteps the FP problem by requiring concrete evidence. Cannot detect semantic drift (only issues that manifest as test failures).

**Sourcery** (https://sourcery.ai): AST transformation engine + LLM. Can propose concrete, syntactically valid refactorings. Relevant to the mechanical fix track.

**Ellipsis** (https://www.ellipsis.dev): One of the few tools supporting full codebase scanning (not just PR diffs). "Standards" feature for natural language convention enforcement.

**Snyk Code** (https://snyk.io/product/snyk-code/): Proprietary symbolic AI + ML (not LLM-based). Traces tainted variables across 15+ function calls and file boundaries. Security-only but architecturally interesting.

### Open source

**Semgrep** (https://github.com/semgrep/semgrep): Pattern-based static analysis with YAML rule language. 3000+ community rules. Gold standard for deterministic pattern enforcement.

**Qodo PR-Agent** (https://github.com/Codium-ai/pr-agent): Most mature OSS LLM PR review tool. `/review`, `/describe`, `/improve`, `/test` commands.

**Aider** (https://github.com/paul-gauthier/aider): Repository map — lightweight alternative to full codebase indexing. Captures skeleton (signatures, class hierarchies) without full embedding.

**SWE-agent** (https://github.com/princeton-nlp/SWE-agent): Iterative agent with ACI — navigates, hypothesizes, edits, tests. Demonstrates that interactive exploration outperforms single-pass review for complex understanding tasks.

### Research patterns

**StaticGPT pattern** (multiple papers, 2024): Run static analysis first, use LLM to filter false positives. Inverts the typical architecture — static analysis for recall, LLM for precision. Arguably the best available hybrid architecture for production use.

**CodeReviewer** (Microsoft Research, 2022): Pre-trained transformer on 1.2M code review examples. Demonstrates that review-specific training matters — general LLMs are not optimal reviewers.

### What no tool does (as of March 2026)

1. **Spec-aware review** — no tool checks code against specs or design documents
2. **Semantic drift detection** — no tool identifies "this module was supposed to use the caching layer but it's been bypassed"
3. **Cross-module architectural review** — most tools operate at file/function level
4. **Longitudinal intent tracking** — no tool asks "is this part of a pattern of increasing degradation?"
5. **Documentation-code consistency** — no tool verifies docs/comments match code behavior

## Common pitfalls and failure modes

### Summary

| Pitfall | Severity | Mitigation maturity |
|---|---|---|
| False positive fatigue | High | Medium — tuning helps, requires ongoing investment |
| "Looks correct" trap | Critical | Low — single-digit detection for subtle logic bugs |
| Context window limits | High | Medium — repo-indexing exists but trades noise for coverage |
| Sycophancy / confirmation bias | High | Low — no production tool implements suppression |
| Security review gaps | Critical | Low — 87% of AI-built PRs contain vulnerabilities |
| Test adequacy blind spot | High | Medium — mutation testing works but rarely integrated |
| Architectural review limits | High | Low — file-level tools can't see system invariants |
| Prompt injection | Critical | Low — 75-88% success rates demonstrated |
| Over-reliance risk | High | Low — organizational, not technical |
| Noise-to-signal ratio | High | Medium — fundamental precision/recall trade-off unsolved |

### False positive fatigue

Industry FP rates: 5-15%. When 13 of 15 "critical" flags are false, engineers stop treating "critical" as urgent. Worse: consistent false-flagging of a specific pattern teaches engineers to ignore that entire category. Feedback loops reduce FP by 50%+ after tuning.
> [Graphite: Expected FPR](https://graphite.com/guides/ai-code-review-false-positives) | [DevTools Academy: State of AI Code Review 2025](https://www.devtoolsacademy.com/blog/state-of-ai-code-review-tools-2025/)

### The "looks correct" trap

LLMs hallucinate correctness — syntactically valid and internally consistent code confirmed as correct when it's semantically wrong. Detection rates on subtle bugs: ~35% for critical defects, single digits for subtle logic errors. Multi-pass catches 3-5x more than single-pass.
> [arXiv: What's Wrong with LLM-Generated Code](https://arxiv.org/html/2407.06153v1)

### Sycophancy / confirmation bias

Sycophantic behavior in 58.19% of cases. Coding assistants enthusiastically validate whatever approach is presented. Decomposable into sycophantic agreement and praise (distinct latent directions), but no production tool implements suppression.
> [AAAI/AIES: SycEval](https://ojs.aaai.org/index.php/AIES/article/view/36598)

### Test adequacy blind spot

In the worst documented case, LLM-generated tests achieved 100% line/branch coverage on a single HumanEval-Java function while scoring only 4% on mutation testing — passing all coverage checks while missing 96% of injected faults. This is a single-case extreme, not a dataset-wide average; broader studies show higher mutation scores for LLM-generated tests. But the pattern is consistent: coverage metrics alone are unreliable indicators of test quality. Meta's approach: mutation-guided LLM test generation targeting surviving mutants — engineers accepted 73%.
> [arXiv:2506.02954: Mutation-Guided Unit Test Generation](https://arxiv.org/abs/2506.02954) (100%/4% single-case finding) | [Meta: Mutation-Guided LLM Testing](https://arxiv.org/html/2501.12862v1) (73% acceptance rate)

### Security gaps

87% of AI-built PRs contain at least one security vulnerability (DryRun Security, March 2026). AI code is 2.74x more likely to add XSS, 1.91x more likely to make insecure object references (CodeRabbit). Categories systematically missed: broken access control, rate limiting (middleware defined but never connected), interprocedural taint analysis.
> [HelpNetSecurity](https://www.helpnetsecurity.com/2026/03/13/claude-code-openai-codex-google-gemini-ai-coding-agent-security/) | [CodeRabbit Report](https://www.coderabbit.ai/blog/state-of-ai-vs-human-code-generation-report)

### Prompt injection

CVE-2025-54135 (Cursor, CVSS 8.6): Hidden prompt injection in git repo comment hijacked AI on clone, exfiltrated API keys via curl — bypassing denylist. AIShellJack framework: 75-88% unauthorized command execution against agentic editors. hackerbot-claw (March 2026): RCE in 5 of 7 GitHub Actions targets across Microsoft, DataDog, CNCF.
> [HiddenLayer](https://hiddenlayer.com/innovation-hub/how-hidden-prompt-injections-can-hijack-ai-code-assistants-like-cursor/) | [arXiv: AIShellJack](https://arxiv.org/html/2509.22040v1) | [StepSecurity: hackerbot-claw](https://www.stepsecurity.io/blog/hackerbot-claw-github-actions-exploitation)

### Over-reliance risk

PRs ~18% larger with AI, incidents per PR up ~24%, change failure rates up ~30%. Microsoft/CMU RCT (52 engineers): AI-assisted participants scored 17% lower on comprehension (50% vs 67%), largest declines in debugging.
> [Addy Osmani: Code Review in the Age of AI](https://addyo.substack.com/p/code-review-in-the-age-of-ai)

### Noise-to-signal trade-off

Fundamental precision/recall trade-off unsolved. Greptile: 82% catch rate, highest FP. Graphite: sub-3% noise, 6% catch rate. AI PRs contain 10.83 issues vs 6.45 for human PRs (1.7x). 67% of developers spend more time debugging AI code.
> [Qodo: State of AI Code Quality 2025](https://www.qodo.ai/reports/state-of-ai-code-quality/) | [Greptile Benchmarks](https://www.greptile.com/benchmarks)

## Semantic drift and architectural degradation detection

### Architecture conformance checking

**ArchUnit** (production-ready): Architecture rules as executable tests. Supports layered, onion/hexagonal checks. Fails build on violation. Ports: ArchUnitTS (TypeScript), PyTestArch (Python), NetArchTest (.NET). Limitation: structural/dependency rules only — cannot express behavioral or semantic constraints.
> [ArchUnit](https://www.archunit.org/userguide/html/000_Index.html) | [GitHub](https://github.com/TNG/ArchUnit)

**Fitness Functions** (Building Evolutionary Architectures): Objective assessments of architectural properties — structural, operational, or process-based. Implemented as tests or monitoring. Only protects what you think to measure.
> Ford et al. *Building Evolutionary Architectures*, 2nd ed. O'Reilly. [nealford.com](https://nealford.com/books/buildingevolutionaryarchitectures.html)

**CALM** (FINOS, originated at Morgan Stanley): JSON Meta Schema for architectural patterns. Validates implementations against patterns in CI/CD. Early-stage.
> [CALM](https://calm.finos.org/) | [GitHub](https://github.com/finos/architecture-as-code/tree/main/calm)

### Key finding: architectural smells are independent from code smells

Study of 111 Java projects: correlation between architectural smells and code smells found "only in a very low number of occurrences." A codebase can have clean code smells while its architecture is severely eroded. Code smell detectors (SonarQube, ESLint) cannot reliably detect architectural degradation.

However, design smells *do* cause architecture smells — localized design violations propagate upward. Cyclic dependencies are "prone to becoming highly complex over time."
> Arcelli Fontana et al. [ScienceDirect](https://www.sciencedirect.com/science/article/abs/pii/S0164121219301013) | [Springer](https://link.springer.com/article/10.1007/s10664-020-09847-2)

### LLM verification against NL specs: the over-correction bias

The most important finding for our audit design. When asked "is this code correct?", LLMs develop a bias toward assuming defects exist even when the implementation is correct. GPT-4o accuracy: 52.4% with simple judgment → 11.0% with explain-and-fix prompts.

Two strategies that work:
1. **Two-Phase Reflective Prompt** — separates requirement extraction from code auditing
2. **Behavioral Comparison Prompt** — compares spec against implemented behavior directly. GPT-4o: 85.4%

**Design implication**: The audit should ask agents to *describe what the code does*, then compare that description to the ground truth document. Not "find bugs in this code."
> [arXiv:2508.12358](https://arxiv.org/html/2508.12358v1)

### AI-specific degradation patterns

**"Common > Custom" default**: LLMs default to strongest statistical patterns from training data. Project conventions are "a tiny signal compared to millions of codebases." Without active feedback: Common over Custom, Simple over Structured, Familiar over Framework-specific. This is the mechanism behind "surface-level fix that bypasses core mechanisms."

**Consistency violation**: AI-generated code violates architectural patterns *inconsistently* — correct in one file, bypassed in the next — because each generation is statistically independent without persistent architectural context.

**Security-degradation paradox**: Security degradation *accelerates in later iterations* and *counterintuitively increases during security-focused prompting*.

**Anti-pattern propagation**: AI perpetuates outdated patterns, introduces deprecated dependencies. The codebase becomes a mosaic of conflicting patterns.
> [DEV Community: AI Keeps Breaking Architectural Patterns](https://dev.to/vuong_ngo/ai-keeps-breaking-your-architectural-patterns-documentation-wont-fix-it-4dgj) | [IEEE-ISTAS 2025](https://arxiv.org/html/2506.11022)

### Drift detection tools and techniques

**Daikon** (dynamic invariant detection): Extracts specifications from observed runtime behavior. Codifies *current* behavior, not *intended* behavior. Useful for establishing a baseline and detecting *future* drift, not drift that already occurred.
> [University of Washington](https://plse.cs.washington.edu/daikon/)

**Decision Guardian**: GitHub Action that surfaces relevant ADRs on PRs when changes touch covered files. Passive surfacing, no conformance checking.
> [Decision Guardian](https://decision-guardian.decispher.com/) | [GitHub](https://github.com/DecispherHQ/decision-guardian)

**"Paths Not Taken" communication**: Record rejected alternatives and why. AI agents without this context explore the full solution space, including solutions explicitly rejected. Negative constraints directly prevent semantic drift.
> [Communicating Design Intent: Paths not Taken](https://www.neverletdown.net/2015/03/communicating-design-intent-with-the-paths-not-taken.html)

### The gap: natural language specifications

No production tool takes a natural language architectural spec and verifies code conformance. The closest approaches:
1. Two-phase LLM verification — 85% accuracy on function-level specs, untested at architectural level
2. Hybrid: translate NL specs into ArchUnit-style rules or fitness functions (manual today, natural LLM automation target)
3. Behavioral comparison prompting — compare spec against implemented behavior directly

## Anthropic's internal skills practices

Anthropic published their internal skills playbook (March 2026) documenting how they use skills across the company with hundreds in active use. Several findings directly validate and inform Firebreak's approach.

### Independent convergence on shared principles

Firebreak and Anthropic's internal practices reached similar conclusions independently:

- **Progressive disclosure**: Anthropic's three-level system (frontmatter → SKILL.md body → linked files) matches Firebreak's three-tier context architecture (router → index → leaf). Both arrived at this structure to minimize context pollution.
- **Deterministic verification over LLM self-review**: Anthropic recommends "bundling a script that performs checks programmatically rather than relying on language instructions. Code is deterministic; language interpretation isn't." This is the same principle behind Firebreak's gate scripts.
- **Context independence for quality**: Anthropic's `adversarial-review` skill "spawns a fresh-eyes subagent to critique" — the same context isolation pattern Firebreak uses for test writing, implementation, and review. No shared reasoning between the agent that wrote the code and the agent that reviews it.
- **Verification as a first-class investment**: "It can be worth having an engineer spend a week just making your verification skills excellent." Firebreak's test reviewer, gate scripts, and two-tier enforcement model reflect the same priority.

### The adversarial-review pattern

Anthropic's Category 6 (Code Quality & Review) describes a skill that is nearly identical to the proposed code review skill:

> **adversarial-review** — spawns a fresh-eyes subagent to critique, implements fixes, iterates until findings degrade to nitpicks

Key design elements:
- **Fresh-eyes subagent**: No prior context about the code — reviews cold. Context independence as a structural quality guarantee.
- **Iteration until diminishing returns**: The stopping criterion is "findings degrade to nitpicks," not "findings reach zero." This is a natural termination condition the code review skill should adopt.
- **Implements fixes in the loop**: The adversarial-review skill includes fix implementation, not just finding production. This suggests the code review skill could optionally handle mechanical fixes inline rather than routing them through a separate pipeline.

### Skill categories relevant to Firebreak

Anthropic identifies 9 skill categories from internal use. The most relevant:

| Category | Description | Firebreak mapping |
|---|---|---|
| **Product Verification** | Test/verify code is working. Programmatic assertions, video recording, multi-step state verification | Gate scripts, test reviewer, verification engine |
| **Code Quality & Review** | Enforce code quality, review code. Deterministic scripts for robustness. Run via hooks or GitHub Actions | Proposed code review skill, AI failure mode checklist |
| **Library & API Reference** | How to correctly use internal libraries/SDKs. Gotchas, edge cases, reference snippets | Context asset authoring guides |
| **Runbooks** | Take a symptom → multi-tool investigation → structured report | Corrective workflow |
| **Code Scaffolding & Templates** | Generate framework boilerplate with natural language requirements | Spec/breakdown templates |

### Practical patterns for the code review skill

**On-demand hooks**: Skills can register hooks that activate *only when the skill is called*. `/careful` blocks destructive commands, `/freeze` blocks edits outside specific directories. For the code review skill: register a freeze hook during audit to prevent review agents from accidentally modifying code while reviewing.

**Memory via data storage**: `${CLAUDE_PLUGIN_DATA}` provides a stable folder per plugin for persistent data. For the code review skill: store previous audit findings to track remediation progress across sessions. "Last time we found 14 issues. 9 were fixed. 5 remain. 2 new findings."

**Gotchas as living document**: "The highest-signal content in any skill is the Gotchas section. These should be built up from common failure points." The AI failure mode checklist should live as a gotchas section *within* the code review skill (not as a separate document), growing from each remediation run. This is the self-improvement loop applied to the skill itself.

**"Don't State the Obvious"**: "Focus on information that pushes Claude out of its normal way of thinking." The failure mode checklist isn't "check for bugs" (obvious) — it's "check for tests that test their own inline logic instead of production code" (non-obvious, specific, derived from empirical failure data).

**"Avoid Railroading Claude"**: Embed the *what to look for* (failure modes, behavioral comparison methodology) but let agents decide *how to investigate* based on the specific codebase. Don't over-specify the review process.

### Sources

- [Lessons from Building Claude Code: How We Use Skills — Anthropic engineering blog](https://www.anthropic.com/engineering/lessons-from-building-claude-code-how-we-use-skills)
- [The Complete Guide to Building Skills for Claude (PDF)](https://resources.anthropic.com/hubfs/The-Complete-Guide-to-Building-Skill-for-Claude.pdf)
- [anthropics/skills — GitHub](https://github.com/anthropics/skills)
- [Best Practices for Claude Code — official docs](https://code.claude.com/docs/en/best-practices)
- [I Applied Anthropic's Internal Skills Playbook — DEV Community](https://dev.to/billkhiz/i-applied-anthropics-internal-skills-playbook-to-my-projects-heres-what-changed-3m4h)

## Permissions landscape

### The `.claude/` directory protection

`bypassPermissions` mode skips all prompts *except* writes to protected directories: `.git/`, `.claude/`, `.vscode/`, `.idea/`. This is intentional — not a bug.

**Exempted subdirectories** (writable even in bypass mode):
- `.claude/commands/`
- `.claude/agents/`
- `.claude/skills/`

Non-exempted paths (always prompt): `.claude/docs/`, `.claude/hooks/`, `.claude/settings.json`, `.claude/CLAUDE.md`.

This explained the Phase 1.5 failure pattern: the project's template paths at `home/.claude/` triggered the `.claude/` protection because it matches on the path segment, regardless of semantic context (template directory vs actual config).

**Status: resolved.** The template directory was renamed to `home/dot-claude/` to avoid the path-segment match. This should eliminate the subagent permission blocker. Validation pending on next pipeline run with subagents targeting `home/dot-claude/` paths.

### Subagent permission inheritance

Subagents inherit the parent's permission context. The `tools` allowlist and `disallowedTools` denylist in subagent frontmatter are the most reliable restriction mechanisms.

Known issues:

| Issue | Description | Status |
|---|---|---|
| [#25000](https://github.com/anthropics/claude-code/issues/25000) | Subagents bypass deny rules entirely | Closed as duplicate, fix unconfirmed |
| [#20264](https://github.com/anthropics/claude-code/issues/20264) | Can't restrict subagents when parent uses bypass | Closed "not planned" |
| [#5465](https://github.com/anthropics/claude-code/issues/5465) | MCP mode breaks permission inheritance entirely | Closed "not planned" |
| [#27333](https://github.com/anthropics/claude-code/issues/27333) | `Edit`/`Write` allow rules don't auto-approve | Open |

### Permission strategies without yolo mode

**`acceptEdits` + Bash allowlist** is the most practical middle ground. `acceptEdits` mode auto-approves all file edits. Bash commands are allowlisted per-pattern. Destructive commands are denied explicitly.

```json
{
  "defaultMode": "acceptEdits",
  "permissions": {
    "allow": [
      "Bash(npm run *)",
      "Bash(git commit *)",
      "Bash(git diff *)",
      "Bash(git status)",
      "Bash(git log *)"
    ],
    "deny": [
      "Bash(rm -rf *)",
      "Bash(git push --force *)",
      "Bash(git reset --hard *)"
    ]
  }
}
```

**PreToolUse hooks** are the most reliable enforcement mechanism. They run before permission checks, can inspect full command arguments, and return `allow`/`deny`/`ask` per-invocation. More flexible than static allowlists, but cannot override deny rules.

### Ecosystem position

Both GSD-2 and BMAD default to `--dangerously-skip-permissions` for autonomous operation. Granular permission control without bypass mode is technically possible but is not a well-trodden path. Firebreak operating with permission safety intact is ahead of the ecosystem on this axis.

### Mitigation status

1. **Rename template directory**: **SHIPPED.** `home/.claude/` renamed to `home/dot-claude/` to avoid the `.claude/` path-segment match. Awaiting validation on next pipeline run.
2. **Use exempted subdirectories**: Available if needed. `.claude/agents/`, `.claude/skills/`, `.claude/commands/` are writable even in bypass mode.
3. **`acceptEdits` on-demand hook**: **Future feature.** The `/implement` skill could register an on-demand hook that activates `acceptEdits` for the session during implementation, returning to default mode for interactive work. Anthropic's `/careful` skill demonstrates this pattern. Claude Code supports session-scoped mode changes via hook stdout JSON with `setMode` entry. Implementation deferred until the rename's effectiveness is validated.
4. **PreToolUse hook for Bash**: Available as a future refinement. Auto-approve safe Bash patterns, deny destructive ones, with full argument inspection.
5. **Accept the constraint**: Fallback if the rename proves insufficient — execute context asset editing tasks in the main agent context rather than as subagents.

### Sources

- [Configure permissions — Claude Code docs](https://code.claude.com/docs/en/permissions)
- [Create custom subagents — Claude Code docs](https://code.claude.com/docs/en/sub-agents)
- [Hooks reference — Claude Code docs](https://code.claude.com/docs/en/hooks)
- [Example settings — anthropics/claude-code](https://github.com/anthropics/claude-code/tree/main/examples/settings)
- [GSD-2 permissions guide](https://zread.ai/gsd-build/get-shit-done/4-configuring-claude-code-permissions)
- [Claude Code permissions deep dive — stevekinney.com](https://stevekinney.com/courses/ai-development/claude-code-permissions)

## Remediation workflow: emerging design

### Key reframe: the source of truth is a spec tree

The initial design framed the source of truth as a novel "ground truth document" — an artifact with no precedent in the pipeline. Council review (6-agent independent assessment) identified this as the single biggest risk: no format, no schema, no gate, no exit criteria.

The reframe: **the source of truth is a spec tree**, the same structure used in forward workflows. A project overview spec with child feature specs, using the same 9-section template, the same AC format, the same UV steps, the same integration seam declarations. The only difference is the direction of authoring: forward workflows create specs before code, remediation creates specs *from* existing code.

This eliminates the "novel artifact" problem entirely:

| Concern | Resolution |
|---|---|
| Format | The existing 9-section spec template |
| Schema | ACs, UV steps, integration seam declarations |
| Validation gate | spec-gate.sh (already built) |
| Review process | Council review (already validated) |
| Exit criteria | Spec passes the gate |
| Injection detection | spec-gate.sh injection scanning (already present) |
| Human co-authoring model | Spec co-authoring (already tested across greenfield + brownfield) |
| Integrity verification | Hash-lock after human approval (reuse test-hash-gate.sh pattern) |

The behavioral comparison technique operates at the AC level — which is roughly function-level granularity, where the 85.4% accuracy was measured. The spec tree hierarchy provides module-level structure through the project overview → feature spec relationship.

### Pipeline shape

```
Explore ─► Audit ─► Triage ─► Remediation Spec(s) ─► [existing SDL pipeline]
  ▲           ▲        ▲
  reverse-    behavioral       human categorizes:
  author      comparison       spec-worthy vs
  spec tree   against ACs      mechanical fix
```

### Exploration phase (reverse spec authoring)

The exploration phase is spec co-authoring applied to existing code. The process differs by scenario, but the output artifact is always the same: a spec tree.

**Intent recovery (no existing specs):**
1. Agent surveys the codebase — architecture, modules, data flow, test coverage map. Produces a structural summary.
2. Agent drafts a project overview spec and child feature specs based on what the code appears to do.
3. Human reviews and refines — confirms, corrects, adds design intent: "module X is supposed to do Y but it's not." The human's role shifts from "author with agent assistance" to "reviewer of agent-proposed specs."
4. Specs pass through spec-gate.sh and council review, same as forward specs.

**Spec-backed remediation (existing but conflicting specs):**
1. Agent reads existing specs and the codebase.
2. Agent identifies conflicts between specs and between specs and code.
3. Human resolves conflicts — confirms which spec is canonical, updates or retires stale specs.
4. Reconciled specs pass through the existing review gate.

**Cleanup (cosmetic degradation only):**
1. No spec tree needed. The AI failure mode checklist is the source of truth.
2. Agent runs structural audit against the checklist (duplication, dead code, magic numbers, tests-that-test-themselves).
3. Findings enter triage directly.

A fourth scenario exists: **intentional deviation** — code that deliberately diverges from specs for practical reasons (performance optimization, external dependency workaround). The spec tree must accommodate these as documented exceptions, not flag them as drift.

### Audit phase

Informed by the behavioral comparison finding: agents should describe what the code does, then compare against the spec's ACs — not search for defects directly. This avoids the over-correction bias (52.4% → 11.0% accuracy) measured in specification verification research.

**v1 architecture (single-agent, validated first step):**
1. Single detection agent runs behavioral comparison — describes code behavior per-module, compares against corresponding spec ACs and UV steps.
2. Agent produces structured findings with location, current behavior, expected behavior (from spec), severity, and recommended track.
3. Human reviews findings. v1 is suggestion-only — findings presented, not auto-applied.

**Target architecture (multi-agent, after single-agent validation):**
1. Parallel detection agents — each targeting a different failure class (structural, test integrity, semantic drift, security).
2. Adversarial verification — a verification agent attempts to disprove each finding. Iteration continues until findings degrade to nitpicks (Anthropic's adversarial-review stopping criterion).
3. Deduplication and classification — surviving findings grouped, classified, presented as audit report.

Research data supports multi-agent as the target: single-pass reviews have catastrophic recall variance (only 27 change-points overlap across 5 runs of the same model). Self-aggregation improves F1 by 43.67%. But single-agent must be validated first before investing in orchestration complexity.

### Triage phase

The human categorizes findings into two tracks:

| Track | Characteristics | Pipeline path |
|---|---|---|
| **Spec-worthy** | Behavioral change needed, design decision involved, test strategy affected | Full SDL pipeline: spec → review → breakdown → implement |
| **Mechanical fix** | No design decision, deterministic transformation, no test impact. Must not touch security-sensitive code (auth, authz, input validation, data flow boundaries). | Lighter-weight path using corrective workflow fast-track criteria |

The mechanical fix track reuses the existing corrective workflow's fast-track eligibility criteria: known root cause, identical pattern, validated tests, no design decisions. If a mechanical fix does not resolve on first attempt, it escalates to the full spec pipeline. Triage misclassification is asymmetric — calling a spec-worthy finding "mechanical" is worse than the reverse — so the default when uncertain should be spec-worthy.

### Security model

The remediation workflow introduces a new trust boundary: the target codebase is untrusted input. In the forward workflow, all inputs originate from the trusted side (user-authored specs). In remediation, agents read arbitrary code during exploration and audit.

Mitigations (reusing existing infrastructure):
1. **Injection scanning on spec tree** — spec-gate.sh already scans for control characters, zero-width chars, embedded instructions. Apply to reverse-authored specs before they enter the pipeline.
2. **Hash-lock spec tree after human approval** — reuse SHA-256 pattern from test-hash-gate.sh. Prevents modification between human approval and audit consumption.
3. **Audit agents cannot write to spec tree** — enforce via `disallowedTools` or PreToolUse hook. Defense-in-depth against injection that tries to modify the source of truth to match drifted code.
4. **Human co-authoring is the structural mitigation** — the human reviews agent-proposed specs before they become authoritative. Same principle as forward spec review: "the pipeline optimizes for whatever the spec says."

For untrusted codebases (future scope): sanitize code context before agent ingestion, hard gate on injection detection, separate exploration agent read/write scopes.

### Success metrics

Established before building (per council review):
- **Audit precision**: <15% false positive rate on first real test
- **Audit recall**: 80%+ on known issues in the test codebase
- **Triage accuracy**: Track mechanical-fix items that later required spec-level rework
- **Time-to-resolution**: Instrument first run to establish baseline vs manual remediation

### Council review findings

A 6-agent council review (Architect, Builder, Guardian, Security, Advocate, Analyst) independently assessed this research document. Key findings incorporated above:

- The spec tree reframe eliminates the "novel artifact" problem — all existing validation infrastructure applies
- Cleanup should ship as a standalone `/audit` skill first, before the full remediation workflow
- Behavioral comparison accuracy at module-level is an untested extrapolation of function-level results — treat as hypothesis, validate with a degradation curve test (function → class → module → cross-module)
- v1 should be suggestion-only (generate findings, don't auto-apply)
- The 100%/4% mutation score citation was misattributed and overstated — corrected to cite the actual source (arXiv:2506.02954) and reframed as a single worst-case example, not a dataset-wide average.
- Multi-agent adversarial architecture is the validated target but premature for v1

### Open questions (reduced from 10 to 5 after reframe and council review)

1. **Reverse spec authoring process**: How does the agent draft specs from existing code? What does it read, in what order, and how does it present drafts to the human? This is a process design question — the artifact format is now defined.

2. **Audit scope and cost**: Per-module audits are likely necessary for larger codebases. Token consumption per stage must be instrumented from the first run to build empirical cost data.

3. **Mechanical fix workflow**: The corrective workflow fast-track criteria apply, but the test suite may be complicit in semantic drift. A verification agent confirming behavior-preservation may be needed beyond "tests still pass."

4. **Incremental remediation and dependency analysis**: Fixing module A may break module B if B depends on A's drifted behavior. Incremental remediation needs dependency analysis between findings — not yet addressed.

5. **Behavioral comparison at scale**: The degradation curve test (function → class → module → cross-module) must validate the technique before the full remediation workflow is specced. If accuracy drops below ~70% at module level, the technique needs modification.
