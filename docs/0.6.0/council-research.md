# Council research: model recency and applicability

Focused research delegated at the operator's request, 2026-09-07. This supplements the initial 0.6.0 plan; it does not establish the replacement single-reviewer default as superior.

## Finding

No controlled, equal-budget comparison was found that validates Firebreak's council or its replacement on current Opus 5.x. Recently published papers often evaluate older models; recent Claude models sometimes appear only as judges. Experiment execution dates were not disclosed in the inspected papers. Submission and publication dates below are not experiment dates.

The council combines domain perspectives, semi-adversarial critique, initial alignment, and discussion toward consensus. Its main discussion already permits one round, with a second only for critical dissent. Quick mode skips alignment. Relevant open questions concern cumulative context across phases, surrounding repair loops, and the value of each component, rather than an assumption that the council has unlimited discussion rounds.

## Closest software-review evidence

[Adversarial Review](https://arxiv.org/html/2608.18167v1), submitted August 16, 2026. [Primary metadata](https://arxiv.org/abs/2608.18167) reports acceptance to the ICML 2026 DL4C workshop, not the main conference.

- All agents use Claude Sonnet 4.5 Medium Reasoning, pinned `claude-sonnet-4-5-20250929`. GPT-5.2 judges review-comment matching.
- On 100 SWE-PRBench pull requests, reported F1 is .495 for one reviewer, .503 for two independent reviewers, .457 for naive reviewer–critic, and .533 for explicitly constrained reviewer–critic.
- On 500 SWE-bench Verified tasks, reviewer–critic achieves 75.2% versus 71.6% for baseline, using approximately 4.5 times the tokens.
- The useful intervention distinguishes code-cited counterevidence from an uncited concern. A concern requires the reviewer to find confirming or refuting code before retaining or dropping the finding.
- Limits: older Claude, unequal expenditure, automated matching to human review comments, and prompt adaptation on the evaluated benchmark. These results do not prove current-model superiority or maintainability gains.

## Other relevant evidence and screened limitations

| Source and status | Models and comparison | What it can support |
| --- | --- | --- |
| [Multi-Agent Reasoning Improves Compute Efficiency](https://aclanthology.org/2026.acl-srw.1/), ACL Student Research Workshop, July 2026; [methods](https://arxiv.org/html/2605.01566v1) | Llama 3.1 70B and 8B; MMLU-Pro/BBH; debate, mixture-of-agents, self-consistency, and self-refinement. Comparable compute estimated using FLOPs and memory transfers. | Debate and mixture-of-agents report 1.3/2.7 percentage-point gains over self-consistency. A counterweight to assuming one agent is always best, but uses 2024 models, multiple-choice tasks, and estimated compute. |
| [LLM Consortium for Software Design Refinement](https://arxiv.org/html/2606.01490v1), May 31, 2026 preprint | Generation uses `gemini-2.5-pro`; cross-model review uses `openai/gpt-oss-120b-maas`. `claude-opus-4-6` and `claude-sonnet-4-6` are evaluators. Compares review/refinement structures across eight architecture tasks. | Exploratory design evidence only. Unequal costs, automated rubric outcomes, no human or behavioral endpoint, and reporting inconsistencies including 12×8×5 described as 520 runs. Mentioning recent Claude judges does not establish current-Claude authoring results. |
| [Anthropic Code Review](https://code.claude.com/docs/en/code-review), current vendor documentation | Exact deployed model not disclosed. Parallel agents inspect defect classes, followed by verification of candidates against code behavior. | Direct industry relevance for specialized detection followed by verification. No controlled comparison establishing reviewer count or debate as optimal. |
| [REFINE](https://arxiv.org/html/2608.23611v1), August 2026 preprint | GPT-5.5, Gemini 3.1 Pro Preview, Claude Opus 4.8; file-level Java refactoring candidates assessed with static preservation/smell proxies. | Recent-model software work, but does not evaluate council efficacy, review accuracy, or behavioral equivalence. It cannot answer this protocol question. |

## The existing round-limit rationale needs qualification

The likely source behind the council's generic claim that ACL 2025 shows additional rounds decrease quality is [Voting or Consensus? Decision-Making in Multi-Agent Debate](https://aclanthology.org/2025.findings-acl.606.pdf), section 4.2. Its experiment uses three agents from the paper's Llama 3 setup on StrategyQA across one to ten rounds. It reports a slight downward trend with a conspicuous improvement at round ten. This does not establish a universal stopping law for modern Claude. A bounded round count can remain an engineering choice without overstating the research.

## Evaluation questions for Firebreak

1. Does separate-context review find additional valid defects compared with one reviewer given comparable resources?
2. Do domain-specific responsibilities improve coverage over identical independent review prompts?
3. Does initial alignment resolve ambiguity without suppressing useful differences?
4. Does evidence-focused challenge improve precision while retaining supported minority findings?
5. Does carrying the full discussion help compared with a frozen artifact and concise unresolved-claim record?
6. What does each extra round add in defects caught, false positives, unnecessary changes, latency, and cost?

Compare the current council, independent reviewers plus verification, and one fresh reviewer. Record exact deployed model/version and effort; use repeated runs, matched observed resource budgets, clean cases alongside known defects, and blinded human adjudication. Findings on historical models are hypotheses for this comparison, not its results. No code or protocol change is made by this research note.
