# Legacy discipline audit — 2026-09-11

The current architecture preserves or strengthens most of Firebreak's review and
workflow disciplines. The strongest remaining gaps concern instructions that used
to prevent integration mistakes during authoring, and specialized guidance that no
longer reaches every relevant execution path. These are reasons to repair focused
instructions and routing. They do not establish a need for more agents, stages,
contracts or review rounds.

This audit compares the current worktree (HEAD `cfb4f6b` plus existing uncommitted
changes) with `e889a0b`, the recorded starting point of the 0.6 rewrite. It also
uses `c2a03c6`, before the earlier unified-review rewrite, to recover specialized
legacy reviewer methods. A difference from that older revision is not automatically
a 0.6 regression. Legacy files can be inspected with `git show REVISION:PATH`.

Three fresh-context research agents independently covered reviewers and review
skills, Council roles/protocol/consultation, and architect/upstream authoring and
worker instructions. The lead inspected the research sources and checked the
reported loading paths and representative legacy instructions. This was source
research, not a live model comparison. No production instructions or runtime code
were changed for this audit.

**Preserved and improved disciplines**

| Discipline | Operative current coverage | Assessment |
| --- | --- | --- |
| Independent inspection | [Council execution](../../assets/fbk-scripts/fbk/workflow/council.py#L168) launches fresh initial readers before sharing findings. [Standalone contributors](../../assets/fbk-scripts/fbk/workflow/review_contributors.py#L65) supply the bound challenger only normalized candidates and original sources. | Stronger isolation than the legacy Council's sequential transcript-based consensus. Final Council adjudication intentionally receives current challenge assessments; it is not an opinion-free stage. |
| Evidence-based findings | [Shared review prompt](../../assets/fbk-scripts/fbk/workflow/review.py#L855) requires governing obligations, reachable scenarios and material consequences. [Final adjudication](../../assets/fbk-scripts/fbk/workflow/council.py#L310) must correct exaggerated claims and remedies. | Preserves behavioral comparison and strengthens resistance to invented defects and model preferences. User-set requirements remain authoritative. |
| Minority concerns and completion | [Council disposition validation](../../assets/fbk-scripts/fbk/workflow/council.py#L126) accounts for candidates; unresolved blockers remain explicit. Required-session failures prevent completion. | Stronger mechanical protection than dissent sections or weighted agreement in prose. Semantic judgments still depend on the model. |
| Targeted code-failure searches | [Managed implementation guidance loader](../../assets/fbk-scripts/fbk/workflow/review.py#L479) embeds five shipped guides; [standalone code review](../../assets/skills/fbk-code-review/SKILL.md#L59) captures them for workers. | Concurrency, changed predicates, callers, inconsistent siblings, permissive mocks and security targets remain operative. Removed specialist agent files do not imply lost detection. |
| Early complexity challenge | [Design authoring](../../assets/fbk-docs/workflow/design.md#L8), [spec authoring](../../assets/fbk-docs/workflow/spec.md#L25), and [Council roles](../../assets/fbk-scripts/fbk/workflow/council.py#L13) require cost identification and simpler alternatives. | Present and stronger in the current worktree. The author owns the discussion even without Council. Agent agreement cannot establish operator approval. |
| Requirements and responsibility boundaries | [Spec guidance](../../assets/fbk-docs/workflow/spec.md#L1) protects observable intent; [design guidance](../../assets/fbk-docs/workflow/design.md#L6) identifies shared policy ownership and synchronized-change costs. | Preserved with more proportionate instructions. Routine private design choices need not become contractual obligations. |
| Test and implementation evidence | [Breakdown](../../assets/fbk-docs/workflow/breakdown.md#L38) requires real interfaces, discriminating fixtures and meaningful behavioral red. [Handoffs](../../assets/fbk-docs/workflow/handoffs.md#L40) independently execute required checks and revalidate evidence. | Stronger than trusting a worker's report or a green suite. The restored standalone test lens adds a compact coverage account. |
| Durable, focused handoffs | [Worker handoffs](../../assets/fbk-docs/workflow/handoffs.md#L14) carry original authority and owned work; [task packets](../../assets/fbk-scripts/fbk/workflow/handoff.py#L378) preserve outcome, inputs and exact checks. | Fresh workers and revision-bound inputs preserve the useful context-engineering discipline. They do not prove the references are semantically sufficient. |
| Executable review evidence | [Reviewer execution](../../assets/fbk-docs/workflow/reviewer-execution.md) connects native readers to bounded disposable experiments. | Improves evidence access without giving reviewers deliverable-edit authority. Copies are not an OS security boundary; external adapters need coordinator mediation. |

**Gaps worth addressing, in priority order**

1. **Repository grounding before authoring has weakened.** Legacy
   `e889a0b:assets/fbk-docs/fbk-design-guidelines/pre-authoring-investigation.md`
   explicitly required searching for existing implementations, reading distinct
   callers, verifying dependencies and checking relevant dependency behavior. The
   implementation guide's task-isolation section loaded it for workers. Legacy
   brownfield spec and task-compilation routes also required actual repository
   reads and independent caller searches when symbols changed.

   Current [design guidance](../../assets/fbk-docs/workflow/design.md#L1) asks for
   architecture investigation, while [implementation](../../assets/fbk-docs/workflow/implementation.md#L1)
   and the [worker packet](../../assets/fbk-scripts/fbk/workflow/handoff.py#L378)
   emphasize accepted inputs, behavior and checks. They do not carry the same
   concrete default investigation duties. Project-specific task references might
   supplement them; that cannot be assumed for a bare installation.

   A plausible consequence is a parallel implementation or an omitted caller or
   migration entering accepted scope. Tests for the new path can pass while an
   existing consumer remains wrong. Later duplicate/caller review helps, but it is
   the fallback the operator wants to rely on less. Restore short conditional
   reuse, caller-impact, dependency and complete-migration guidance at existing
   authoring/worker entry points. Related legacy error/result handling and
   composition duties belong here when those interfaces change; they do not merit
   another universal checklist. Confidence: high on reduced explicit guidance,
   moderate on the unmeasured behavioral effect.

2. **Shared contracts have less explicit wiring investigation.** Legacy
   `c2a03c6:assets/agents/fbk-architect.md` required tracing inherited fields to the
   mechanisms populating them. Legacy feature-spec guidance required runtime value
   sources, and `e889a0b:assets/fbk-docs/fbk-sdl-workflow/task-compilation.md`
   required checking that a needed value is reachable or assigning its producer
   as a prerequisite.

   Current [design](../../assets/fbk-docs/workflow/design.md#L1),
   [spec](../../assets/fbk-docs/workflow/spec.md#L23) and
   [breakdown](../../assets/fbk-docs/workflow/breakdown.md#L7) retain substantial
   shared-interface and integration duties. Runtime checks prove declared inputs
   exist and dependencies are completed. They cannot prove that a real entry point
   supplies the required context, field or lifecycle signal. Individually coherent
   components can therefore remain unwired. A narrow authoring obligation to
   trace consequential producer → value/signal → consumer behavior would restore
   specificity without mandatory seam inventories or private signatures.

3. **The restored test-review criteria reach standalone review more completely
   than managed review.** [Managed review](../../assets/fbk-scripts/fbk/workflow/review.py#L479)
   does not load the test lens. Its [breakdown obligations](../../assets/fbk-scripts/fbk/workflow/review.py#L775)
   already cover meaningful red, real interfaces, fixtures, wrong-behavior rejection
   and integration. Implementation also receives code catalogs that cover empty,
   advisory and skipped tests and permissive mocks. This is partial coverage,
   not absence of test-integrity review.

   The [restored test lens](../../assets/fbk-docs/fbk-review-lenses/test-lens.md#L91)
   adds more explicit stale expected-failure checks, runtime-fidelity searches and
   proactive retirement/surviving-contract comparison. The managed path does not
   receive that complete content or its coverage account. A stale non-strict xfail
   or an undeclared retired regression could evade the narrower instructions.
   Some of these checks were already lost before `e889a0b`; this is partly an
   incomplete restoration, not solely a 0.6 regression. Supply applicable criteria
   and proportionate evidence accounting through existing managed prompts, retaining
   their current result contract. No extra test-reviewer session is required.

4. **Standalone consultation has thinner role definitions.** The
   [consultation route](../../assets/skills/fbk-council/SKILL.md#L22) loads a
   [reference](../../assets/skills/fbk-council/references/consultation.md#L7) that
   names six perspectives but concretely defines only the Builder/Architect
   exchange. It does not load runtime `FOCUS`. At `e889a0b`, named Advocate and
   Analyst agents explicitly challenged added user burden and lost value, and
   required a metric, collection method and deciding evidence.

   Current general evidence standards help, but the other selected roles depend
   on what the orchestrator infers from their names. This could miss unnecessary
   user steps or an unsupported performance promise. Supply compact responsibilities
   for the selected roles on this existing route. Managed Council already receives
   its phase-specific roles and does not have this routing gap. Confidence:
   medium; no observed consultation miss was established.

5. **Affected durable-document discovery is less assured.** Both legacy baselines'
   code-review skills required a sweep of decisions, contracts, layout, changelog
   and spec. Current [code review](../../assets/skills/fbk-code-review/SKILL.md#L144)
   routes to doc reconciliation without clearly requiring completion; managed
   review checks declared documentation. [Spec authoring](../../assets/fbk-docs/workflow/spec.md#L18)
   already asks for affected durable docs, which is useful partial protection.

   An omitted architecture document can remain authoritative and wrong after a
   dependency change. Add an affected-doc discovery/comparison duty to existing
   authoring/completion guidance where needed, rather than automatically restoring
   another review pass. This is lower priority than the authoring and managed
   review coverage gaps.

An additional **inherited concern**, distinct from the rewrite, is the categorical
wording in [fresh-eyes source handling](../../assets/fbk-docs/fbk-review-lenses/fresh-eyes-lens.md#L60).
It limits proposed-change findings to internal contradictions and treats author
deferrals as settled scope unless contradicted elsewhere. These exceptions already
exist at `e889a0b` (introduced earlier in `552abb96`). A self-consistent proposal
can still violate governing compatibility, and a deferred decision can still be
necessary now. Narrow exceptions to authorized changes and valid phase deferrals;
keep ordinary planned future work out of findings. This is an instruction conflict
risk, not a demonstrated model failure.

**Research basis and its limits**

The legacy research archive (`c2a03c6:ai-docs/research/`) mixes peer-reviewed work,
preprints, practitioner reports and local experience. Its useful ideas deserve
preservation, but each citation's actual result and publication status matter.
This audit spot-checked primary sources, not every claim in that archive.

| Primary source | Supported lesson for this audit | Limit |
| --- | --- | --- |
| [Lost in the Middle, TACL 2024](https://aclanthology.org/2024.tacl-1.9/) | Placement and relevance of context affect use of evidence in the studied retrieval/QA tasks. Focused, fresh reader inputs preserve that discipline. | Does not establish that the shortest prompt or a particular Firebreak persona arrangement is best. |
| [ACE, authors' ICLR 2026 paper](https://arxiv.org/abs/2510.04618) | The paper explicitly studies loss of useful detail through brevity bias and repeated rewriting. This supports checking whether simplification removed actionable knowledge. | Does not prove that restoring every old instruction improves present coding models, or require adopting its framework. |
| [Code-generation error taxonomy, authors' ICSE 2025 paper](https://arxiv.org/abs/2406.08731) | Error analysis finds varied, sometimes multi-line semantic errors. Targeted mechanism checks remain justified candidates for evaluation. | HumanEval and the studied six models do not directly measure repository-level Firebreak outcomes. |
| [Voting or Consensus?, Findings of ACL 2025](https://aclanthology.org/2025.findings-acl.606/) | Decision protocol and task affect multi-agent results; additional discussion can hurt in the studied conditions. | Does not establish a universal optimal Council size, round count or consensus rule for current coding agents. |
| [SWE-agent, NeurIPS 2024](https://proceedings.neurips.cc/paper_files/paper/2024/hash/5a7c947568c1b1328ccc5230172e1e7c-Abstract-Conference.html) | Agent-facing interfaces and executable feedback affect software-task performance. The runtime's clear evidence/diagnostic interfaces are consistent with this direction. | Does not validate Firebreak's current implementation or longitudinal maintainability. |

The original test-oracle study's [author-hosted preprint](https://arxiv.org/abs/2410.21136)
also supports distinguishing expected behavior from observed implementation behavior;
its inspected metadata does not establish a publication venue. The legacy
“Curse of Instructions” link was browser-verification blocked during this audit,
so its acceptance status and quoted numerical claims were not independently verified.
Neither uncertainty invalidates a source-demonstrated instruction gap.

**Establishing effectiveness parity**

Static comparison establishes that duties and loading paths exist, not that models
follow them or that the current system is at least as effective overall. Preserve
the stronger controls and evaluate focused instruction repairs with matched task,
model and resource conditions. Include known defects and clean cases: duplicate
implementation, missed caller, missing runtime producer, stale expected failure,
uncovered retired contract, stale governing docs, and a valid simple solution that
must not acquire invented complexity. Existing run observations should supply
realistic examples; synthetic cases must be labeled as such.

Measure defects created during authoring separately from defects caught at review.
Also record false findings, unnecessary changes, human interventions, timeouts,
cost, and correctness of a follow-up feature change. Fewer rounds, more findings,
more detailed documents or a passing runtime test suite cannot establish parity by
themselves. The findings above support focused repairs and evaluation while retaining
the streamlined architecture; they do not yet support an empirical parity claim.
