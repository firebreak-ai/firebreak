# Benchmark Research for Firebreak

Research conducted 2026-03-29. Goal: identify public benchmarks applicable to measuring Firebreak's claims about code quality, maintainability, and spec-to-implementation fidelity.

## Key Finding

Almost every benchmark measures "does it work" (tests pass). Almost none measure "is the code good." This is both a gap and an opportunity — Firebreak could publish results in a space where nobody else is measuring quality.

## Most Promising Benchmarks

### FeatureBench (ICLR 2026) — Best ROI

Measures feature-level implementation from specs across real repos. 200 tasks, 3,825 environments, 24 repos. Claude 4.5 Opus: 74.4% on SWE-bench but only 11.0% on FeatureBench — feature building is the hard problem, exactly where Firebreak claims to add value.

- **Adaptation**: Run tasks through Firebreak vs unstructured Claude Code. Compare pass rates AND quality metrics (SonarQube, mutation score) on passing solutions.
- **URLs**: [arXiv](https://arxiv.org/abs/2602.10975) | [GitHub](https://github.com/LiberCoders/FeatureBench)

### SWE-CI (March 2026) — Technical Debt Over Time

Measures long-term maintainability through simulated code evolution. 100 tasks averaging 233 days / 71 commits of evolution history. "EvoScore" penalizes technical debt accumulation — agents whose early decisions facilitate future evolution score higher.

- **Adaptation**: Directly tests Firebreak's maintainability thesis. Run evolution trajectories through both pipelines.
- **URLs**: [arXiv](https://arxiv.org/abs/2603.03823) | [GitHub](https://github.com/SKYLENAGE-AI/SWE-CI)

### SlopCodeBench (March 2026) — Quality Degradation

One of the only benchmarks explicitly measuring code quality degradation over iterative development. 20 problems, 93 checkpoints. Found agent code is 2.2x more verbose than comparable open-source projects. Tracks verbosity and structural erosion.

- **Adaptation**: Firebreak's review stages should reduce verbosity and structural erosion. Direct comparison on identical problems.
- **URLs**: [scbench.ai](https://www.scbench.ai/) | [arXiv](https://arxiv.org/abs/2603.24755)

## Code Review Benchmarks

### Martian Code Review Bench

Live leaderboard, 1.2M+ real PRs. Measures precision (are comments useful?) and recall (does it catch real issues?). Self-correcting — tracks which comments developers actually act on.

- **Adaptation**: Benchmark Firebreak's Detector/Challenger against other review tools.
- **URLs**: [Leaderboard](https://codereview.withmartian.com/) | [GitHub](https://github.com/withmartian/code-review-benchmark)

### c-CRAB (March 2026)

Evaluates review agents using executable test-based evaluation (not textual similarity). Human review feedback converted into executable tests. Agents evaluated by defect detection, not wording match.

- **URL**: [arXiv](https://arxiv.org/abs/2603.23448)

### CR-Bench (March 2026)

Focuses on defect-identifying reviews, separating objective logic errors from subjective style preferences. Measures signal-to-noise ratio.

- **URL**: [arXiv](https://arxiv.org/abs/2603.11078)

## Quality Metrics (Adaptable Frameworks)

### SonarQube / Static Analysis

Industry-standard, produces numerical metrics: bugs, vulnerabilities, code smells, cognitive complexity, technical debt ratio. Run on code from both pipelines for immediate, recognizable comparison data.

### Mutation Testing (Stryker / mutmut / PIT)

Mutation score measures whether tests actually catch behavioral changes. Directly validates Firebreak's test immutability and context isolation claims. A test suite can have 100% coverage but only 4% mutation score.

### GitClear-Style Code Churn Analysis

Measures code churn (lines revised within 2 weeks), duplication rates, refactoring ratios. Their 2025 research found AI code produces 4x growth in code clones and a collapse in refactoring activity. Firebreak should produce lower churn and duplication.

- **URL**: [GitClear 2025 Research](https://www.gitclear.com/ai_assistant_code_quality_2025_research)

## Multi-Dimensional Quality Benchmarks

### RACE Benchmark (July 2024)

Measures four dimensions: Readability, Maintainability, Correctness, Efficiency. Evaluates 28 LLMs against customized quality requirements beyond functional correctness.

- **URLs**: [arXiv](https://arxiv.org/abs/2407.11470) | [GitHub](https://github.com/jszheng21/RACE)

### RAL-Bench (February 2026)

Application-level generation with ISO/IEC 25010-inspired non-functional quality dimensions. No model exceeds 45% functional pass rate. Non-functional scores are more discriminative than functional correctness.

- **URLs**: [arXiv](https://arxiv.org/abs/2602.03462) | [GitHub](https://github.com/Wwstarry/RAL-Bench)

## Security Benchmarks

### CyberSecEval / Purple Llama (Meta)

189 patterns across 50 CWEs in 8 languages. LLMs suggested vulnerable code 30% of the time. More advanced models suggested more insecure code, not less.

- **URLs**: [arXiv](https://arxiv.org/abs/2312.04724) | [GitHub](https://github.com/meta-llama/PurpleLlama)

### Veracode GenAI Code Security Report (2025-2026)

80-task benchmark across 4 CWE types. 45% of code samples failed security tests. Java worst at 72% failure. AI code contains 2.74x more vulnerabilities than human code.

- **URLs**: [Report](https://www.veracode.com/blog/genai-code-security-report/) | [Spring 2026 Update](https://www.veracode.com/blog/spring-2026-genai-code-security/)

### SafeGenBench

558 security scenarios across 44 CWE types. Dual evaluation: SAST + LLM-as-judge. Models averaged 37.44% accuracy on secure code generation.

- **URL**: [arXiv](https://arxiv.org/abs/2506.05692)

## Industry Reports (Reference Data)

### CodeRabbit "State of AI vs Human Code Generation" (Dec 2025)

470 real PRs analyzed. AI code: 1.7x more total issues, 1.64x more maintainability errors, 1.75x more logic errors, 1.57x more security findings than human code.

- **URL**: [Report](https://www.coderabbit.ai/blog/state-of-ai-vs-human-code-generation-report)

## Evaluation Strategy

**Tier 1 — Automated, run immediately:**
- SonarQube metrics on pipeline output
- Mutation testing scores
- GitClear-style churn analysis

**Tier 2 — Structured benchmark, requires setup:**
- FeatureBench tasks (pass rate + quality metrics on passing solutions)
- SafeGenBench security scenarios
- Spec-to-implementation fidelity scoring

**Tier 3 — Gold standard, significant investment:**
- METR-style RCT with real developers ([methodology](https://metr.org/blog/2025-07-10-early-2025-ai-experienced-os-dev-study/))
- CodeRabbit-style large-scale PR analysis over time

## Recommendation

FeatureBench + SonarQube is the best starting point. FeatureBench is public, recognized (ICLR 2026), measures feature implementation, and baseline scores are low enough (11%) that Firebreak has room to show improvement. SonarQube adds the quality dimension FeatureBench doesn't measure. Together they cover both "does it work" and "is the code good."
