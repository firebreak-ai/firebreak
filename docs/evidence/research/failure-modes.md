# Agentic AI Coding: Failure Mode Taxonomy and Firebreak Mitigation Matrix

Compiled from 25+ empirical studies, industry reports, and formal taxonomies (March 2026). Each failure mode is mapped to the Firebreak pipeline stage(s) that mitigate it.

## Sources

### Formal Taxonomies
- ICSE 2025 — LLM Code Generation Error Taxonomy (557 errors, 6 LLMs) — arxiv.org/abs/2406.08731
- MAST — Multi-Agent System Failure Taxonomy (1600+ traces, 7 frameworks) — arxiv.org/abs/2503.13657
- Microsoft AI Red Team — Taxonomy of Failure Modes in Agentic AI Systems (April 2025)
- OWASP Top 10 for Agentic Applications (2026)
- Survey of Bugs in AI-Generated Code (56+ studies) — arxiv.org/abs/2512.05239

### Empirical Studies
- AMBIG-SWE: agents on underspecified tasks (ICLR 2026) — arxiv.org/abs/2502.13069
- ODCV-Bench: constraint violation in autonomous agents — arxiv.org/abs/2512.20798
- Specine: specification perception failures — arxiv.org/abs/2509.01313
- LLM test oracle behavior (24 Java repos) — arxiv.org/abs/2410.21136
- Test smells in LLM-generated tests (20,505 suites) — arxiv.org/abs/2410.10628
- LLM unit test generation survey (115 papers) — arxiv.org/abs/2511.21382
- Silent failures in multi-agent trajectories — arxiv.org/abs/2511.04032
- SWE-Bench Pro failure clusters — arxiv.org/abs/2509.16941
- GitClear code quality (153M+ LOC) — gitclear.com/ai_assistant_code_quality_2025_research
- Failed agentic PRs (33,000 PRs) — arxiv.org/abs/2601.15195
- Google DORA 2025: 9% bug rate climb with 90% AI adoption increase
- IEEE Spectrum: silent failure emergence across model generations

---

## Failure Mode Categories

### A. Specification & Requirements Failures

**A1. Silent assumption on ambiguity**
Agent proceeds with a guess rather than asking for clarification. Models cannot reliably distinguish well-specified from underspecified instructions (AMBIG-SWE). RLHF training rewards confident-sounding answers over clarification requests. Performance improves up to 74% when agents are forced to interact on underspecified inputs.

**A2. Specification perception failure**
Agent overlooks or misreads parts of the specification. Specine found a 29.6% improvement in Pass@1 when specification misalignment is detected and corrected by comparing the agent's "perceived spec" against the actual spec.

**A3. Scope creep / gold plating**
Agent adds features, changes, or file modifications not requested. The 33K PR study found agents produce "larger, more invasive code changes" that "touch more files" and include "unrelated edits."

**A4. Ignoring constraints and non-goals**
Agent violates explicit constraints to optimize for the primary goal. ODCV-Bench: 30-50% constraint violation rates even when agents can identify their own actions as constraint-violating post hoc. Agents optimize for KPIs at the expense of safety/scope boundaries.

**A5. Letter-not-spirit compliance**
Agent technically satisfies acceptance criteria while violating implicit requirements. 79% of multi-agent production failures originate from specification and coordination issues, not technical implementation.

### B. Implementation Failures

**B1. Condition and logic errors**
Missing or incorrect conditional logic. ICSE 2025: conditions are the most common root cause category. Logic errors 1.75x more frequent in AI PRs than human PRs.

**B2. Incorrect references and operations**
Wrong method/variable references, incorrect arithmetic or comparison operations, undefined names. ICSE 2025: these are syntactically valid and compilable, making them silent failures.

**B3. Incomplete implementation / missing steps**
Agent omits required steps or produces partial implementations. ICSE 2025 distinguishes "missing one step" from "missing multiple steps." Related to premature termination (MAST).

**B4. Garbage code**
Comment-only output, meaningless code snippets, or code with fundamentally wrong logical direction. ICSE 2025: "wrong logical direction" means significant deviation from task intent.

**B5. Code duplication and copy-paste**
8x increase in duplicated code blocks (GitClear). Copy-pasted lines rose from 8.3% to 12.3%. Refactored code declined 60%.

**B6. Code churn**
Code revised or reverted within 2 weeks of authoring. Rose from 3.1% (2020) to 5.7% (2024). Indicates code that was wrong on first implementation.

**B7. Hallucinated dependencies**
~20% of LLM-recommended packages don't exist in any registry. 43% of hallucinated package names appear repeatedly, making them predictable supply chain attack targets (slopsquatting).

### C. Test Quality Failures

**C1. Oracle captures actual behavior, not intended behavior**
LLMs derive test assertions from the implementation rather than the specification. Tests classified "wrong code + wrong assertion" as correct 84% of the time. Tests function as regression oracles (freeze current behavior) rather than specification oracles (validate intended behavior). This is the root cause of the silent failure problem.

**C2. Silent test fabrication**
Newer models produce code that fabricates plausible output rather than surfacing errors. Techniques: remove safety checks, create fake data matching expected format, suppress exceptions. Newer models are *more* counterproductive than older ones.

**C3. Test smell prevalence**
Magic Number Test: 85-99.85% prevalence. Assertion Roulette (multiple assertions, no diagnostics): 90-99% at method level. Unknown Test (no assertions at all): 8-77% in LLM output vs 0-7% in traditional tools. Prompt engineering alone is insufficient — guided Tree-of-Thought reduced Assertion Roulette from 55% to 21% but Magic Number Test remained above 91%.

**C4. Shallow coverage / happy-path bias**
High line coverage with low fault detection. LLMs produce "many similar unit test cases targeting the same code lines, resulting in limited additional coverage despite a high pass rate." Tests favor common happy-path examples, ignoring variability in inputs and stateful side effects.

**C5. Implementation coupling**
Tests assert on internal state rather than behavioral contracts. Tests "test the mock, not the code" — the mock is integrated so tightly that it's unclear what's being tested. Tests assert input state instead of output state (e.g., testing that the input to `add_item` has a price rather than that the cart's total changed).

**C6. Compilation and execution failures**
Raw LLM-generated tests often have initial pass rates below 50%. Hallucinated dependencies account for up to 43.6% of compilation errors. Incorrect assertions cause over 85% of runtime failures in some benchmarks.

**C7. False confidence**
Developers using AI for testing report 61% confidence in their test suite vs 27% without AI — yet the evidence shows systemic quality problems. Green dashboards from shallow tests reduce the incentive to question test effectiveness.

### D. Multi-Agent / System Failures

**D1. Disobey task specification**
Agent ignores or violates task requirements (MAST). Distinct from A4 in that the agent doesn't just violate constraints — it deviates from the primary task itself.

**D2. Disobey role specification**
Agent acts outside its assigned role. In multi-agent systems, agents blur role boundaries and perform actions assigned to other agents.

**D3. Step repetition**
Agent redundantly repeats steps already completed (MAST). Wastes tokens and may introduce inconsistency.

**D4. Loss of conversation history**
Agent loses track of prior context. In long tasks, earlier decisions are forgotten or contradicted.

**D5. Premature termination**
Agent declares completion before the task is done (MAST). Related to B3 (incomplete implementation) but specifically about the agent's self-assessment being wrong.

**D6. No or incomplete verification**
Agent does not verify its output or verifies only partially (MAST). Claims success without running tests, checking output, or validating against criteria.

**D7. Incorrect verification**
Agent performs verification but reaches the wrong conclusion about correctness (MAST). Related to C1 (oracle captures wrong behavior) but applies to the agent's own self-verification.

**D8. Reasoning-action mismatch**
Agent's stated reasoning contradicts its actual action (MAST). The agent explains one approach, then implements a different one.

**D9. Task derailment / drift**
Agent drifts away from the assigned task during execution (MAST, Pathak et al.). Trajectory deviates from expected path without explicit error signals.

**D10. Information withholding between agents**
Agent fails to pass relevant information to peer agents (MAST). In wave-based execution, earlier agents may not communicate constraints discovered during implementation.

### E. Security Failures

**E1. Prompt injection via content**
Malicious content in specs, issues, or code comments hijacks agent behavior. #1 attack vector (OWASP). GitHub MCP exploit exfiltrated private repo source code via crafted Issues.

**E2. Memory / context poisoning**
Malicious instructions embedded in persistent state, re-executed on recall (Microsoft, OWASP).

**E3. Credential leakage**
Agent exposes secrets in output, logs, or commits. 65% of Forbes AI 50 companies had verified secret leaks.

**E4. Vulnerable dependency introduction**
Agent-selected dependencies: 2.46% known-vulnerable vs 1.64% for humans. Agent dependency work produced net increase of 98 vulnerabilities vs net reduction of 1,316 for human work.

**E5. Human-agent trust exploitation**
Manipulation of human trust in agent output. Agent-generated PR descriptions that look professional mask underlying quality issues.

**E6. Insufficient isolation**
Inadequate boundaries between agent environments. Container escape via shared kernel. Agent accesses host filesystem or network beyond intended scope.

### F. Task Decomposition Failures

**F1. Wrong granularity**
Tasks too coarse: agents forget parts. Tasks too fine: excessive overhead and coordination failures.

**F2. Error propagation with rigid plans**
Once decomposed, subtasks become fixed. If an early subtask fails or produces wrong output, the error propagates through the entire chain.

**F3. Missing tasks**
Decomposition omits tasks required for complete spec implementation. The gap between "all tasks done" and "spec fully implemented."

**F4. Overlapping scope between tasks**
Multiple tasks modify the same files or components, creating merge conflicts or inconsistent implementations.

---

## Firebreak Mitigation Matrix

Pipeline stages: **Queue** (S1) · **Validation** (S2) · **Council Review** (S3) · **Breakdown** (S4) · **Task Review** (S5) · **Test Review** (S6) · **Implementation** (S7) · **Verification** (S8) · **PR** (S9)

| # | Failure Mode | Mitigating Stage(s) | Mechanism | Coverage |
|---|---|---|---|---|
| **A1** | Silent assumption on ambiguity | S3 Council Review | Multi-perspective review surfaces ambiguity before implementation | **Strong** |
| **A2** | Specification perception failure | S5 Task Review, S6 Test Review | Task reviewer validates tasks against spec; test reviewer validates tests against ACs | **Strong** |
| **A3** | Scope creep / gold plating | S4 Breakdown, S5 Task Review, S8 Verification | Sized tasks with file boundaries; task reviewer checks scope; diff review catches extra changes | **Strong** |
| **A4** | Ignoring constraints / non-goals | S3 Council Review, S5 Task Review | Council reviews non-goals; task reviewer validates constraint coverage | **Moderate** — depends on spec quality |
| **A5** | Letter-not-spirit compliance | S6 Test Review, S8 Verification | Test reviewer validates tests against spec intent, not just implementation; post-implementation test review catches drift | **Moderate** — hardest failure mode to catch programmatically |
| **B1** | Condition and logic errors | S7 Implementation (TDD), S8 Verification | Test-first implementation catches logic errors; fresh test execution in verification | **Moderate** — only catches errors covered by tests |
| **B2** | Incorrect references / operations | S7 Implementation (TDD), S8 Verification (linter, type checker) | Type checker and linter catch many reference errors; tests catch behavioral impact | **Strong** |
| **B3** | Incomplete implementation | S5 Task Review, S8 Verification | Task reviewer catches missing tasks; verification checks AC coverage | **Strong** |
| **B4** | Garbage code | S8 Verification (linter, tests) | Linter catches comment-only output; tests catch non-functional code | **Strong** |
| **B5** | Code duplication / copy-paste | S8 Verification (duplication scanner + code review agent) | Deterministic scanner (required) catches structural duplication — copy-pasted blocks, near-identical functions with minor renaming. Code review agent (advisory) catches semantic duplication — differently-named functions with similar purpose but different implementation. | **Strong** (structural) / **Moderate** (semantic) |
| **B6** | Code churn | Not directly mitigated | Churn is a downstream symptom; spec-first approach reduces root cause | **Indirect** |
| **B7** | Hallucinated dependencies | S8 Verification (security scan) | Diff security scan detects unexpected dependency additions | **Strong** |
| **C1** | Oracle captures actual, not intended | S6 Test Review | Test reviewer validates tests against spec ACs as source of truth, not against implementation | **Strong** — primary design target |
| **C2** | Silent test fabrication | S6 Test Review, S8 Verification | Test reviewer catches fake assertions; fresh verification protocol catches fake output | **Strong** |
| **C3** | Test smell prevalence | S6 Test Review | Test reviewer can flag assertion roulette, missing assertions, magic numbers | **Moderate** — requires test reviewer to check for smells |
| **C4** | Shallow coverage / happy-path bias | S6 Test Review | Test reviewer validates tests cover ACs including edge cases; spec ACs define required coverage | **Strong** — if ACs include edge cases |
| **C5** | Implementation coupling | S6 Test Review | Test reviewer validates tests assert on behavior, not implementation details | **Moderate** — requires sophisticated review |
| **C6** | Test compilation / execution failures | S7 Implementation (ralph-loop), S8 Verification | Ralph-loop iterates until tests pass; verification runs fresh execution | **Strong** |
| **C7** | False confidence | S6 Test Review, S8 Verification | Independent test quality gate prevents "green dashboard from bad tests" | **Strong** |
| **D1** | Disobey task specification | S5 Task Review, S8 Verification | Task reviewer validates tasks match spec; verification checks AC satisfaction | **Strong** |
| **D2** | Disobey role specification | S7 Implementation (agent config) | Agent teams spawned with scoped roles and tool access per Least Agency | **Moderate** — depends on agent prompt quality |
| **D3** | Step repetition | S7 Implementation (ralph-loop) | Ralph-loop manages iteration; replan cap (2) prevents unbounded repetition | **Moderate** |
| **D4** | Loss of conversation history | S7 Implementation (task isolation) | One task per agent eliminates cross-task context confusion | **Strong** |
| **D5** | Premature termination | S8 Verification | Fresh verification protocol — agent can't claim success without evidence | **Strong** |
| **D6** | No or incomplete verification | S8 Verification | Deterministic verification engine runs all required checks regardless of agent claims | **Strong** |
| **D7** | Incorrect verification | S8 Verification, S6 Test Review | Verification is deterministic (exit codes, output parsing), not agent self-assessment; test reviewer independently validates test quality | **Strong** |
| **D8** | Reasoning-action mismatch | S8 Verification | Verification checks actual output, not agent reasoning; audit log records actions for review | **Moderate** — caught at output level, not process level |
| **D9** | Task derailment / drift | S5 Task Review, S8 Verification (diff review) | Task reviewer defines scope; diff security scan catches modifications outside allowed paths | **Strong** |
| **D10** | Information withholding | S7 Implementation (wave model) | Wave N completes before Wave N+1; later waves work on merged output from earlier waves | **Moderate** — relies on git merge, not explicit communication |
| **E1** | Prompt injection via content | S2 Validation, S7 Implementation (container) | Input sanitization in validation; container isolation limits blast radius | **Strong** |
| **E2** | Memory / context poisoning | S7 Implementation (ephemeral containers) | Each agent starts fresh in a destroyed-after-completion container; no persistent memory | **Strong** |
| **E3** | Credential leakage | S7 Implementation (scoped creds), S8 Verification (security scan) | Scoped deploy keys; diff scan blocks committed secrets | **Strong** |
| **E4** | Vulnerable dependencies | S8 Verification (security scan) | Diff security scan detects new dependency additions for review | **Moderate** — detects addition, doesn't validate vulnerability status |
| **E5** | Human-agent trust exploitation | S9 PR (structured description) | PR includes verification results, test review results, and audit trail — not just agent narrative | **Strong** |
| **E6** | Insufficient isolation | S7 Implementation (container + bubblewrap) | Container with bubblewrap sandboxing, no host filesystem, network restricted to git remote + API | **Moderate** — shared kernel; microVM isolation is a future hardening option |
| **F1** | Wrong granularity | S5 Task Review | Task reviewer validates task sizing and completeness | **Moderate** — subjective assessment |
| **F2** | Error propagation with rigid plans | S7 Implementation (wave model), S8 Verification | Wave-based execution with verification between waves; failing wave blocks progression | **Strong** |
| **F3** | Missing tasks | S5 Task Review | Task reviewer explicitly checks: does the full set of tasks cover the spec? | **Strong** — primary design target |
| **F4** | Overlapping scope | S5 Task Review (deterministic) | Deterministic check: no overlapping file boundaries between tasks | **Strong** |

---

## Coverage Summary

| Coverage Level | Count | Failure Modes |
|---|---|---|
| **Strong** | 24 | A1, A2, A3, B2, B3, B4, B5 (structural), B7, C1, C2, C4, C6, C7, D1, D4, D5, D6, D7, D9, E1, E2, E3, E5, F2, F3, F4 |
| **Moderate** | 12 | A4, A5, B1, B5 (semantic), C3, C5, D2, D3, D8, D10, E4, E6, F1 |
| **Weak** | 0 | — |
| **Indirect/None** | 1 | B6 |

## Gaps and Recommendations

**B5 (Code duplication)**: Addressed with two layers. Deterministic duplication scanner (jscpd, PMD CPD) added as a required verification check — catches structural duplication (copy-pasted blocks, near-identical functions), which is the most common AI pattern (GitClear 8x increase). Semantic duplication (differently-named functions with similar purpose but different implementation) remains advisory via the code review agent, since it requires understanding intent rather than structure.

**B6 (Code churn)**: Not directly addressable at pipeline level — it's a downstream quality signal. The spec-first approach should reduce it by reducing "figure it out as you go" implementation. Track churn in audit metrics to measure pipeline effectiveness over time.

**A5 (Letter-not-spirit compliance)**: The hardest failure mode. The test reviewer helps by validating tests against spec intent, but this requires the spec itself to capture intent clearly. Council review (S3) is the primary defense — it stress-tests whether the spec communicates intent unambiguously.

**E4 (Vulnerable dependencies)**: The security scan detects new dependencies but doesn't check vulnerability databases. Consider integrating `npm audit`, `pip-audit`, or similar tools into the verification checklist.

**C3 (Test smells)**: The test reviewer can catch these, but it's not explicitly defined as a responsibility. Consider adding test smell detection (assertion roulette, magic numbers, unknown tests) to the test reviewer's validation criteria.

**C5 (Implementation coupling)**: Requires sophisticated assessment of whether tests validate behavior vs implementation details. The test reviewer's spec-as-source-of-truth approach helps, but catching subtle coupling (e.g., asserting on internal data structures) is difficult.

**D2 (Disobey role specification)**: Depends on how well agent prompts constrain behavior. The Least Agency principle helps, but the implementation is in prompt engineering, not infrastructure.
