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

FeatureBench + SonarQube is the best starting point. FeatureBench is public, recognized (ICLR 2026), measures feature implementation, and baseline scores are low enough (11%) that Firebreak has room to show improvement. SonarQube adds the quality dimension FeatureBench doesn't measure. Together they cover both "does it work" and "is the code good." SonarQube Community Edition is free (LGPL); FeatureBench is fully open source. The cost is API inference, not tooling.

## FeatureBench Deep Dive

Research conducted 2026-03-30. Examined the FeatureBench GitHub repo, HuggingFace dataset, and arXiv paper in detail.

### How it works

Each task gives the agent a `problem_statement` containing a task description and interface descriptions (exact function signatures, parameter contracts, behavioral notes). The agent runs inside a Docker container with the target repo pre-installed. Evaluation is fully automated: pytest runs fail-to-pass tests (must now pass) and pass-to-pass tests (must not regress). A task is resolved only when all tests pass.

**Level 1 tasks** (83% of full set): The agent works within an existing codebase. Target functions are surgically removed; the agent must reimplement them. The agent sees the surrounding code and can modify other files.

**Level 2 tasks** (17%): The original library code is deleted entirely. The agent builds from scratch in `/testbed/agent_code/` with a `setup.py`, guided only by the interface descriptions.

### Agent execution model

Agents run non-interactively. Claude Code is invoked with `-p` (single prompt, no conversation). There is no mechanism for human input during execution. The harness handles: Docker container setup, agent installation, command execution with timeout, patch extraction, test grading.

**This means Firebreak cannot participate as-is.** The pipeline has human gates (review approval, phase progression) that require interaction. Two adaptation options:

1. **Autonomous mode (preferred):** Auto-proceed through gates unless the review pipeline flags a blocking finding. This preserves the pipeline structure while removing the human dependency. Requires building an autonomous mode into Firebreak — the gate logic becomes: auto-proceed if no blocking findings; halt (and accept timeout) if something requires judgment. This is useful beyond benchmarking.

2. **CLAUDE.md injection:** Run standard Claude Code with Firebreak context assets loaded, so the pipeline principles influence behavior without requiring the full gate/phase machinery. Simpler but weaker — you're testing "Claude Code with good instructions" rather than "the Firebreak pipeline."

### Adding a custom agent

Subclass `BaseAgent` from `featurebench/infer/agents/base.py`. Implement three things:
- `name` property — agent identifier string
- `install_script` property — bash script that installs the agent inside the Docker container (Claude Code agent installs nvm + Node.js 22 + `@anthropic-ai/claude-code`)
- `get_run_command(instruction)` — shell command to execute the agent with the task prompt

Register in `featurebench/infer/agents/__init__.py` and add a config section in `config.toml`. The harness handles everything else.

### Dataset splits

| Split | Tasks | Images | Disk (compressed) | GPU required | Overlap with lite |
|-------|-------|--------|--------------------|-------------|-------------------|
| lite | 30 | 13 | ~156 GB | Yes (Liger-Kernel, transformers) | — |
| fast | 100 | 18 | ~251 GB | No | 16 of 30 lite tasks |
| full | 200 | 24 | ~350 GB (est.) | Yes | all 30 |

The lite split was **randomly selected, not stratified** (the paper says so explicitly). It is not guaranteed to be representative.

### Lite split task distribution

| Category | Count | % | Description |
|----------|-------|---|-------------|
| Simple (1-2 interfaces) | 22 | 73% | Single function or pair; interface descriptions are prescriptive |
| Moderate (3-5 interfaces) | 6 | 20% | Cross-function dependencies; decomposition starts to matter |
| Complex (6+ interfaces) | 2 | 7% | Multi-file, multi-interface; mlflow test_trace (6), test_responses_agent (15) |

Level 1: 26 tasks (87%). Level 2: 4 tasks (13%). MLflow dominates with 7 of 30 tasks.

### Where Firebreak adds value (task analysis)

Examined two tasks in detail — `pandas read_iceberg` (Level 2, 1 interface) and `mlflow test_responses_agent` (Level 1, 15 interfaces across 12 files, 8805-line gold patch).

**Simple tasks (read_iceberg):** The interface description is prescriptive enough to be a spec. It tells you the algorithm, the API calls, the default transformations. Firebreak's spec phase adds nothing; the review phase has minimal surface area to work with. Prediction: no meaningful difference between structured and unstructured approaches.

**Complex tasks (mlflow responses_agent):** Decomposition into sequenced implementation waves matters — utilities before consumers, context threading across interfaces. Cross-interface review catches integration issues a single-shot agent misses. Prediction: Firebreak has a real advantage from structure and review.

**Implication:** Results should be reported segmented by task complexity. "No difference on simple tasks, X% improvement on complex multi-interface tasks" is a more honest and more interesting claim than an aggregate number. The lite split's 73% simple tasks will dilute the signal.

### Cost estimates

Per-task token usage from the paper: 1-10M input, 10-90K output. Midpoint estimates used below.

| Configuration | Lite (30 tasks) | Fast (100 tasks) |
|---------------|-----------------|-------------------|
| Sonnet 4, single run | $290-660 | $960-2,200 |
| Sonnet 4, two runs (baseline + Firebreak) | $580-1,320 | $1,920-4,400 |
| Sonnet 4 batch (50% off), two runs | $290-660 | $960-2,200 |
| Opus 4, two runs | $2,880-6,600 | $9,600-22,000 |

These are significant investments. The batch API (50% off, 24-hour completion window) could reduce costs but may conflict with the harness's per-task timeout expectations.

**Cost reduction strategy:** Run 5-10 tasks manually first (~$50-100) to validate that the results are interesting before committing to a full split.

### Infrastructure requirements

- Python 3.12, Docker Engine, NVIDIA Container Toolkit (for GPU tasks)
- `pip install featurebench`, configure `config.toml` with API key
- Pre-pull images: `fb pull --mode lite` (or `fast`)
- Run: `fb infer --agent claude_code --split lite --timeout 3600`
- Grade: `fb eval -p runs/<timestamp>/output.jsonl --split lite`
- Each container needs its own image + RAM; concurrent tasks (`--n-concurrent`) require substantial resources

### Prerequisites before running

1. **Build Firebreak autonomous mode.** The pipeline must run without human gates for benchmark participation. Gate logic: auto-proceed if no blocking findings.
2. **Implement custom agent.** Subclass `BaseAgent` to install and invoke the Firebreak pipeline inside FeatureBench containers.
3. **Budget.** Minimum ~$300 (Sonnet batch, lite, two runs) to ~$2,000+ for meaningful results on the fast split.
4. **Disk space.** ~156 GB for lite images, ~251 GB for fast.
5. **Decide on quality metrics.** Run SonarQube on passing solutions from both pipelines to capture the quality dimension FeatureBench doesn't measure. This is the differentiating claim — nobody else publishes quality data alongside pass rates.
