# Results

Firebreak's pipeline catches quality issues invisible to CI and static analysis, and its structured remediation process resolves them without introducing significant new debt. This document presents the evidence, the caveats, and the raw data.

Results are from the author's projects and have not been independently replicated — the author runs the pipeline, judges the findings, and writes the retrospectives. Different codebases, languages, team structures, and evaluators may produce different outcomes. If you run Firebreak on your own codebase, [share what you find](https://github.com/firebreak-ai/firebreak/issues).

## At a glance

| Metric | Value |
|--------|-------|
| Test scenarios | Greenfield (13 features), brownfield addition (1 feature), brownfield remediation (12 phases across 2 rounds) |
| Remediation tasks | ~290 across both rounds |
| First-attempt pass rate | 95–98% per round |
| Escalations to higher model | 0 |
| Regressions introduced | 0 |
| Remediation introduction rate | 10% (6 of 60 post-Round-1 findings caused by the pipeline itself; 4 were test-integrity, not production bugs) |
| Linter vs. code review overlap | 0% across all measurement points |

**Terminology:** A *phase* is a unit of remediation scoped to a category of defects (e.g., "security," "dead infrastructure"). A *wave* is an ordering within a phase — test tasks run in early waves, implementation tasks in later waves, with verification between each. The *Detector/Challenger loop* is the adversarial code review: a Detector agent scans code and identifies potential issues; a Challenger agent demands concrete code-path evidence before promoting any issue to a verified finding.

## Testing history

Firebreak has been tested across three scenarios, each building on the lessons of the previous one.

**Greenfield development** (13 features, ~80 tasks, 137 tests) — The first pipeline run passed all tests but didn't work correctly for a real user. The retrospective identified the root cause: every end-to-end test was a smoke test. The pipeline was revised with [user verification steps](assets/fbk-docs/fbk-sdl-workflow/feature-spec-guide.md), a [test reviewer](assets/agents/fbk-test-reviewer.md) that fails on missing behavioral coverage, and human interventions tracked as a first-class metric. This was the pipeline's first self-improvement cycle.

**Brownfield feature addition** (19 tasks, 43 new tests) — The revised pipeline delivered the feature with zero corrective cycles and zero human interventions. The feature worked on first human test. Council review caught 22 findings before code was written. The test reviewer caught 8 defects across 2 checkpoints. [Full greenfield/brownfield comparison](ai-docs/research/harness-patterns-analysis.md).

**Brownfield remediation** (12 phases, ~290 tasks across 2 rounds) — The primary validation test. A private Go project chosen for its high density of AI code failure modes: security vulnerabilities, concurrency crashes, disconnected interfaces, and core systems that were not wired in. The project was effectively non-functional before remediation despite passing CI. Round 1 (7 phases, ~170 tasks) used Firebreak v0.3.0–v0.3.2. Round 2 (5 phases, 120 tasks; still in progress) uses v0.3.3–v0.3.4, incorporating [43 self-improvement proposals](ai-docs/research/quality-quantification.md) from Round 1's retrospectives and [26 additional proposals](ai-docs/self-improvement/v0.3.4/0.3.4-self-improvement-report.md) from Round 2's cross-phase retrospectives. The remediation data makes up the bulk of this document.

## What the code review catches

The adversarial code review catches issues that require reasoning across call graphs and intent alignment — a class of issue that linters, CI, and single-pass review do not detect.

Examples from the brownfield remediation:

- **False-passing tests through mock wiring.** [7 tests](ai-docs/dispatch/phase-1.6-code-review-remediation/brownfield-validation/phase-1-test-infrastructure-retrospective.md) were exercising mock responses instead of actual behavior. A deprecated mock function was wired but never called by production code. CI reported green. The tests provided zero regression protection.
- **Permanently inert features.** A nil parameter was passed to the scoring function, making entity-proximity boost silently non-functional. This survived one full remediation round and was caught by the code review during Round 2 — each phase makes remaining issues more visible.
- **Thread-safety in name only.** A config wrapper [returned collections by reference without deep-copying](ai-docs/dispatch/phase-1.6-code-review-remediation/brownfield-validation/phase-0-security-retrospective.md). The wrapper compiled, the tests passed, the race condition was invisible without call-graph reasoning.
- **Tests proving nothing.** Scoring test fixtures had store nodes set to one kind while candidates used another. The mock didn't validate, so the tests passed with internally contradictory scenarios. Separately, an entity score preservation test used zero-value node kind — passing by accident, not by design.
- **Disconnected lifecycle plumbing.** A task implemented `context.Background()` as a placeholder where the spec said "pass graceful shutdown context." The structural plumbing was present but disconnected from the app lifecycle.
- **Dead infrastructure.** Worker pools constructed, initialized, and configured but never used. Interfaces defined but never implemented. Config fields declared but ignored by the code that should read them.

### Linters and code review find entirely different things

Across all measured phases in both rounds, linter findings and code review findings have [zero overlap](ai-docs/research/quality-quantification.md) (measured at two phase boundaries — a small sample, but consistent). The tools operate in different layers:

| Concern | Linters | Adversarial code review |
|---------|---------|------------------------|
| Unused variables, unchecked errors, dead code (by reference) | Catches | Doesn't target |
| Behavioral bugs (silent data loss, disconnected lifecycle) | No signal | Primary target |
| Test integrity (wrong fixtures, vacuous assertions, phantom strings) | No signal | Primary target |
| Dead infrastructure (constructed but never called) | Partial (unused exports) | Catches call-graph-level |
| Cross-package consistency (constants defined but not adopted) | No signal | Catches |
| Semantic drift (names/comments don't match behavior) | No signal | Catches |

### Adversarial review vs. single-pass review

During the post-remediation full-codebase review, detector agents got stuck on 4 of 8 review units due to an invisible permission prompt. The supervisor agent performed its own independent scan and reported those units clean (0 findings). When relaunched with proper Detector/Challenger coverage, those same units produced **32 additional findings** — including a behavioral bug that made the project's core feature silently non-functional for incremental operations.

The single-pass scan missed 53% of all findings (32 of 60), including all behavioral bugs. This comparison is between adversarial review working as intended and a single-pass fallback performed under degraded conditions — evidence that adversarial review outperforms a hasty workaround, which is a [weaker statement](ai-docs/research/quality-quantification.md) than "adversarial review catches 53% more than any single-pass review." A deliberately designed single-pass comparison would be needed to make the stronger claim.

## What remediation fixes

After 7 phases of Round 1 remediation, the project works. Manual testing confirmed systems that were disconnected now function end-to-end. This is the ground truth that linter metrics and finding counts are proxies for — "does it actually work for a real user" changed from no to yes.

| Category | Pre-remediation | Post-Round-1 |
|----------|----------------|-----------------|
| Security vulnerabilities | 5 (2 critical: arbitrary file read/write) | 0 |
| Concurrency crashes | 4 (race conditions, double-close, unsynchronized writes) | 0 |
| Disconnected interfaces | 6 (core feature non-functional) | 0 |
| Behavioral bugs | ~5 (core features non-functional) | 3 (non-crash, non-security) |
| Test integrity issues | ~50 (test suite provided no regression protection) | 9 (stale comments, empty gate tests) |

Round 2 targets the remaining 60 findings — the "needs cleanup" tier. Five phases completed:

| Phase | Scope | Tasks | Pass rate | Key code review finding |
|-------|-------|-------|-----------|------------------------|
| 0: Behavioral bugs | Race conditions, dead sentinels, type safety | 33 | 85% (28 complete, 4 superseded) | 7 test-integrity issues — wrong fixture node kinds, dead parameter sentinels |
| 1: Dead infrastructure | Orphaned interfaces, worker pool config, dead test helpers | 21 | 100% | 1 critical — wiring test outside any task's file scope |
| 2: Error handling | Context propagation, error wrapping, shutdown lifecycle | 26 | 100% | 1 major — placeholder context not replaced with shutdown context |
| 3: Deduplication | Duplicated scoring formulas, pipeline preparation, data loading | 14 | 100% | Prior-phase miss — nil parameter making feature permanently inert |
| 4: Bare literals | Replace bare string/numeric literals with named constants | 26 | 100% | 3 minor fixes (misplaced constant, bare literal in log, inconsistent mock inputs) |

## What the pipeline introduces

Of the 60 findings in the post-Round-1 review, [6 were caused by the remediation itself](ai-docs/research/quality-quantification.md) (10% introduction rate). 4 of those 6 were test-integrity issues (stale comments on now-fixed bugs, empty gate tests, placeholder tests never filled in) — not production behavioral bugs. Production lint: 1 issue introduced across ~50K lines of changes.

The pipeline has a specific blind spot: agents fix production code and leave test metadata stale. This pattern is consistent across phases. Stale "currently fails" comments on now-passing tests, empty gate tests with zero assertions, and unconditionally skipped tests with behavioral names all survived multiple review cycles.

Round 2's post-implementation code review caught 16 additional findings across 5 phases — issues introduced by the remediation agents themselves. 1 critical (wiring test referencing deleted field, outside any task's file scope), 2 major (disconnected shutdown context, permanently inert feature). The code review layer catches issues that the process layer introduces.

## Pipeline execution

### Task execution

| Metric | Round 1 (v0.3.0–0.3.2) | Round 2 (v0.3.3–0.3.4) |
|--------|------------------------|-------------------|
| Tasks | ~170 | 120 |
| First-attempt pass rate | 98.2% (first 4 phases measured) | 96% (115 complete, 4 superseded, 1 post-wave fix) |
| Escalations | 0 | 0 |
| Regressions introduced | 0 | 0 |
| Post-implementation review findings | ~14 per phase (measured phases) | ~6 per phase |

The post-implementation review findings per phase roughly halved between rounds. This is directionally encouraging but not a controlled comparison — Round 2 targets structural debt (simpler to implement correctly) while Round 1 targeted critical defects (harder). The pipeline may simply be working on easier problems.

### Model routing

| Model | Round 2 tasks | Success rate | Escalations |
|-------|---------------|-------------|-------------|
| Haiku | 64 | 100% | 0 |
| Sonnet | 30 | 100% | 0 |

Haiku handles mechanical, instruction-following work (test signature updates, single-file deletions, bounded implementations). Sonnet handles multi-file changes requiring judgment (struct removal with downstream compile fixes, context threading across modules, shared extraction with caller migration). Zero escalations across both rounds (~260 tasks total), though this could also reflect tasks being scoped narrowly enough that routing choices are less consequential than task definition.

Two predictable model behaviors shape the breakdown process: Haiku agents follow instructions literally without questioning semantic consistency (produces fixture mismatches like wrong node kinds). Sonnet agents fix compile errors outside declared scope rather than leaving the build broken (produces task supersession — 4 of 94 Round 2 tasks were superseded this way).

### Verification gates

Gates caught issues before they became implementation failures:

- **Council review** saved a live production feature from being deleted as "dead code" (Round 2, Phase 1) — the highest-leverage single gate event.
- **Test reviewer CP2** caught 13 uncounted test helper callers that would have caused a guaranteed build failure (Round 2, Phase 1).
- **Spec review** expanded 3 findings that would have been incomplete fixes (Round 2, Phase 0).
- **Test reviewer CP1/CP2** caught 6 defects across two checkpoints before implementation (Round 2, Phase 2).

### Recurring process gaps

**The orchestrator skips final e2e verification.** Documented as a corrective action in Phase 1, repeated in Phase 2. A documented corrective action is insufficient — this needs a hard gate. Build commands don't compile test files in many languages, so test-only compilation failures are invisible until the test runner executes. **Addressed in v0.3.4**: "full test suite" is now defined by output requirement (per-test pass/fail results), making build-check substitution logically impossible. Enforcement added at 6 pipeline stages.

**Wave over-segmentation.** Phase 0's 7-wave plan had 3 waves emptied by Sonnet agents fixing all downstream compile errors. Phase 3's 6-wave plan could logically have been 3. The strict wave-dependency gate rule produces correct results but adds overhead that could be reduced by recognizing struct field changes as atomic units. **Addressed in v0.3.4**: task compilation now includes struct field removal supersession guidance — combine callers into one task or mark downstream tasks as expected-superseded.

**Compilation gaps are the dominant failure mode.** Every phase had at least one instance where the task breakdown didn't grep broadly enough for all references to a changed symbol — second-order effects that require reasoning about what the codebase will do *after* the change. This is the [most recurring pattern](ai-docs/dispatch/phase-1.6-code-review-remediation/brownfield-validation/analysis.md) across both rounds. **Addressed in v0.3.4**: call-site grep requirements added at 5 pipeline stages — spec authoring, spec gate, spec review council, task compilation, and task breakdown.

## How the pipeline improves

The pipeline revises itself from structured retrospective data. Each cycle is human-approved — the pipeline produces actionable proposals, the human decides what to act on. Four cycles have shipped: [v0.3.1](CHANGELOG.md) fixed terminology that obscured friction, [v0.3.2](CHANGELOG.md) caught a routing dead-end in the code review skill, [v0.3.3](CHANGELOG.md) expanded detection scope from AI-specific failure modes to standard engineering concerns, and [v0.3.4](CHANGELOG.md) hardened verification gates, added call-site completeness checks across 5 pipeline stages, and introduced rolling retrospectives that accumulate across all stages instead of being written only at implementation end. See the [CHANGELOG](CHANGELOG.md) for details.

## Token usage and cost

Firebreak spawns multiple agents per workflow — detector/challenger pairs for code review, council agents for spec review, parallel implementation agents for task execution. Token usage scales with the number of agent calls and the size of the codebase context.

### Measured data: full SDL pipeline run

Measured from an isolated fresh session — remediation Phase 4 (bare literals replacement), a relatively mechanical phase. More complex phases (behavioral bugs, architectural remediation) would likely be more Sonnet/Opus-heavy and more expensive.

**Scope:** 26 tasks across 3 waves. 14 production files, 12 test files. Spec → council review (3 + supervisor) → breakdown → implementation → code review. Wall clock: 3 hours 13 minutes, continuous (no idle gaps — near-optimal caching).

**Token usage by model:**

| | Haiku | Sonnet | Opus |
|--|-------|--------|------|
| Input | 51K | 6K | 0K |
| Output | 174K | 435K | 21K |
| Cache write | 3.1M | 7.3M | 278K |
| Cache read | 46.1M | 138.9M | 9M |

**Estimated API cost** (at May 2025 published rates — verify at [anthropic.com/pricing](https://www.anthropic.com/pricing)):

| Model | Cost | % of total | Primary driver |
|-------|------|-----------|----------------|
| Haiku | ~$1 | 1% | 23 tasks for under a dollar |
| Sonnet | ~$76 | 78% | Cache reads ($42) + cache writes ($27) |
| Opus | ~$20 | 21% | Orchestration cache reads ($14) |
| **Total** | **~$97** | | **91% is cache costs, not output** |

**What this tells us:**

- **Model routing works.** Haiku handled 23 of 26 implementation tasks for ~$1. The routing heuristic (Haiku for mechanical/single-file, Sonnet for judgment/multi-file) produces real cost savings.
- **Cache dominates cost.** Output tokens across all models cost ~$8. Cache read/write cost ~$89. Session continuity (no idle gaps > 5 minutes) is the single biggest cost lever on API billing.
- **Subagent cache is the main expense.** Each spawned subagent (implementation tasks, council members, detector/challenger pairs) starts its own cache. 26 tasks means 26 independent cache lifecycles.
- **The orchestrator is an optimization target.** Sonnet handled orchestration in this session, contributing $76 — primarily from cache. Orchestrator model selection and context management are the highest-leverage areas for future cost reduction.
- **On a Max plan, this is included.** Cache behavior is invisible on flat-rate billing. The $97 API estimate is the cost of *not* having a Max plan for heavy pipeline usage.

### Measured data: standalone code review

Measured from an isolated fresh session — a full-repo code review scoped to test files only. This is the "just point it at your code" entry point that requires no spec, no pipeline, no task breakdown.

**Wall clock: ~30 minutes,** continuous.

**Token usage by model:**

| | Opus | Sonnet |
|--|------|--------|
| Input | 28K | 43K |
| Output | 50K | 74K |
| Cache write | 2.3M | 1.2M |
| Cache read | 8.4M | 11.3M |

**Estimated API cost:**

| Model | Cost | % of total | Primary driver |
|-------|------|-----------|----------------|
| Opus | ~$60 | 87% | Cache write ($43) + cache read ($13) |
| Sonnet | ~$9 | 13% | Cache write ($5) + cache read ($3) |
| **Total** | **~$69** | | **92% is cache costs** |

**What this tells us:**
- **The review automatically escalated to Opus** for complex analysis tasks. This was a full-repo scan of all test files — significantly larger scope than a typical PR review. The model routing chose Opus for the review work and Sonnet for supporting tasks, without manual configuration.
- **Cache is 92% of total cost.** Cache overhead, not model choice or output volume, sets the cost floor.
- **Scope drives cost.** This session reviewed an entire project's test suite — significantly larger scope than a typical PR diff. The adversarial Detector/Challenger architecture and automatic Opus escalation for complex findings contribute to the cost but also to the detection quality.

### Measured data: PR-scope code review

Measured from a code review against one remediation phase's changes (Phase 4 — bare literals, 26 files). PR-scope review with report output only — no Detector/Challenger loop, no multi-agent orchestration. Equivalent in scope to reviewing a single PR's diff.

**Token usage by model:**

| | Sonnet |
|--|--------|
| Input | ~0K |
| Output | 27K |
| Cache write | 399K |
| Cache read | 4.6M |

**Estimated API cost:**

| Model | Cost | % of total | Primary driver |
|-------|------|-----------|----------------|
| Sonnet | ~$3.29 | 100% | Cache read ($1.38) + cache write ($1.50) |

**What this tells us:**
- **PR-scope review is cheap.** Reviewing one phase's changes costs ~$3.29 — useful for quick post-implementation sanity checks or lightweight PR review where the full adversarial pipeline isn't warranted.
- **Cache still dominates.** Even at this small scale, cache read/write is 88% of the total cost. Output tokens cost $0.41.

All three measurements are from one Go project. Different codebases, languages, and session patterns will produce different numbers.

### Cost optimization: match effort to finding complexity

Not every finding needs the full pipeline. The code review can classify findings by remediation effort (currently on request; automatic classification is planned for the next release):

- **Trivial findings** (bare literal replacement, stale comments, missing constants) → fix immediately in the code review session. No spec, no pipeline, no additional cost. This is the same pattern used for post-implementation code review fixes.
- **Complex findings** (architectural wiring, cross-module refactoring, behavioral bugs with test implications) → feed into the SDL pipeline as a remediation spec. The structured process prevents creating new debt while fixing old debt.

This means the practical cost pattern is: run a code review (~$69 for full-repo, less for a module), fix trivial findings on the spot, and only invoke the full pipeline (~$97) for the complex findings that need structured remediation. Most codebases will have a mix of both.

### Industry context

We were unable to find comparative cost or usage estimates from similar projects in this space. Firebreak's three measured data points span a range of scopes: a PR-scope review (~$3.29), a full-repo adversarial review (~$69), and a full SDL pipeline run including spec, review, breakdown, 26 implementation tasks, and post-implementation code review (~$97, or ~$3.73/task).

**These numbers are from a very small sample size of specific test runs on one Go project.** Your costs will vary based on codebase size, language, phase complexity (behavioral bugs cost more than bare literal replacement), session continuity (idle gaps force cache rebuilds), and model routing decisions. Treat these as directional reference points, not predictions.

### How caching affects cost

On API billing, the dominant cost factor is not output tokens — it's **cache writes**. Anthropic's API caches conversation prefixes server-side, so repeated turns in an active session serve most input from cache (cheap) rather than reprocessing (expensive). But cache entries expire after 5 minutes of inactivity.

This means:

- **An uninterrupted session** pays for cache writes once at the start, then benefits from cheap cache reads for every subsequent turn. The longer you work without breaks, the more cost-efficient the session becomes.
- **A session with gaps** (lunch break, context switch, even a 5-minute pause) forces a full cache rebuild when you resume. A single mid-session break can roughly double the cache write cost.
- **`/clear` forces fresh cache writes** on the next turn because it changes the conversation prefix, invalidating existing cache entries even if they haven't expired.
- **Subagents pay their own cache costs.** Each spawned agent starts a new conversation with its own cache lifecycle. A code review that spawns 4 detector/challenger pairs has 4 independent cache write events.

On a **Max plan** (flat-rate), cache behavior is invisible — you pay the same regardless of usage pattern. On **API billing**, session continuity is a significant cost lever.

### Per-model rate differences

Different models have different per-token rates. Firebreak uses model routing (Opus for orchestration and judgment-heavy work, Sonnet for mechanical subagent tasks), so the model mix affects total cost. The status line script at `~/.claude/scripts/token-status.sh` tracks per-model token usage with cache breakdown in real time.

For current API rates, see [Anthropic's pricing page](https://www.anthropic.com/pricing).

## Caveats and limitations

**Single author, single evaluator, single test project.** All brownfield remediation data comes from one Go project tested by the project author. Every "verified finding" was verified by the author. Every "false positive" was judged by the author. There is no inter-rater reliability. Different codebases, languages, team structures, and evaluators may produce different outcomes. Independent reviewers are actively sought.

**Go-specific advantages may not generalize.** Go's compiler catches unused variables, enforces interface implementations, and fails on type mismatches — giving the pipeline a structural advantage that dynamically typed languages would not provide. The same issues might be silent in Python or JavaScript codebases.

**The pre-remediation review drove the remediation plan.** The two reviews are not fully independent. The post-remediation review was conducted by the same pipeline that drove the remediation, looking at code it had already seen. A blind re-assessment by a different team or tool would be a stronger comparison.

**Duplication increased during remediation.** From ~10 to ~15 instances across a codebase that grew 44%. Each agent generates correct code independently without extracting shared logic — the [GitClear "collapse in refactoring activity" pattern](https://www.gitclear.com/ai_assistant_code_quality_2025_research). The pipeline didn't reduce this; Round 2 Phase 3 targets it explicitly.

**Cost data is from one measured session.** A single full-pipeline run on a mechanical phase cost ~$97 on API billing, with 91% driven by cache costs. More complex phases and different usage patterns (idle gaps, shorter sessions) will produce different numbers. See [Token usage and cost](#token-usage-and-cost) for the full breakdown and how caching patterns affect cost.

**No false negative measurement.** The document measures what the pipeline finds. It cannot measure what the pipeline misses, because there is no ground truth for "all issues that exist." The post-remediation review found 60 issues; how many remain undiscovered is unknown.

**No industry benchmark comparison.** The closest public benchmark ([Martian Code Review Bench](ai-docs/research/benchmark-research.md)) measures PR-scoped review — a fundamentally different task from full-codebase review against a failure mode taxonomy. Direct comparison is not currently possible.

**Pre-existing test failures create noise.** The brownfield project had 19 pre-existing test failures that complicate every verification step. Snapshot-based regression detection can't distinguish "newly broken" from "flaky and unlucky." The remediation reduced this count by ~4 incidentally but didn't target it as a primary objective.

## Source data

All retrospectives, quality measurements, and analysis are published.

### Cross-cutting analysis

| Document | What it covers |
|----------|---------------|
| [Harness patterns analysis](ai-docs/research/harness-patterns-analysis.md) | Greenfield and brownfield feature addition: pipeline design validation, comparison with Anthropic's agent harness patterns |
| [Quality quantification](ai-docs/research/quality-quantification.md) | Measurement methodology, per-phase lint data, cognitive complexity, linter vs. code review overlap, post-remediation full-codebase review with finding classification |
| [Brownfield validation (Round 1)](ai-docs/dispatch/phase-1.6-code-review-remediation/brownfield-validation/analysis.md) | Round 1 aggregate data across 4 measured phases, compilation gap patterns, agent scope enforcement incident |
| [AI failure taxonomy](ai-docs/research/failure-modes.md) | 39 catalogued failure modes from 25+ empirical sources (ICSE, OWASP, Microsoft AI Red Team, arXiv), mapped to pipeline mitigations |

### Per-phase retrospectives (Round 2)

| Document | What it covers |
|----------|---------------|
| [Phase 0: Behavioral bugs](ai-docs/self-improvement/v0.3.4/phase-0-behavioral-bugs-retrospective.md) | 12 behavioral fixes; superseded task analysis showing Sonnet agents fix downstream compile errors |
| [Phase 1: Dead infrastructure](ai-docs/self-improvement/v0.3.4/remediation-2-phase-1-dead-infrastructure-retrospective.md) | 2,906 lines deleted; critical finding of wiring test outside task file scope |
| [Phase 2: Error handling](ai-docs/self-improvement/v0.3.4/remediation-2-phase-2-error-handling-retrospective.md) | Context propagation across module boundaries; disconnected shutdown context finding |
| [Phase 3: Deduplication](ai-docs/self-improvement/v0.3.4/remediation-2-phase-3-deduplication-retrospective.md) | Shared extraction; prior-phase miss discovery (nil parameter making feature inert) |
| [Phase 4: Bare literals](ai-docs/self-improvement/v0.3.5/remediation-2-phase-4-bare-literals-retrospective.md) | Constant extraction across 26 files; token usage measurement; e2e test gap discovery (PF-01); first phase run under v0.3.4 improvements |
| [Intermediate retrospective](ai-docs/self-improvement/v0.3.4/remediation-2-intermediate-retrospective.md) | Cross-phase synthesis: compilation gaps as dominant failure mode, test-integrity patterns, model routing observations |
| [v0.3.4 self-improvement report](ai-docs/self-improvement/v0.3.4/0.3.4-self-improvement-report.md) | 97 proposals from 34 parallel analysts; 26 applied, 4 invalidated; verification gates, call-site completeness, rolling retrospectives |
