# Brownfield Validation: Preliminary Cross-Phase Analysis

The Firebreak code review pipeline (Phase 1.6) is being validated against a private project with a high density of agentic coding quality issues — the kind of codebase that results from extended AI-assisted development without structured quality controls. The remediation plan covers 8 phases; the 4 retrospectives in this directory represent the halfway point (Phases 0-3). These are preliminary results. The test is ongoing and findings may inform adjustments before it completes.

The test exercises the full Firebreak workflow end-to-end: code review identifies findings, findings are compiled into remediation specs, specs pass through council review, specs are broken down into tasks, and tasks are implemented by agent teams with per-wave verification. Each phase targets a different category of issue — security, test infrastructure, API migration, and interface reconciliation.

## Aggregate data

| Metric | Value |
|--------|-------|
| Phases completed | 4 of 8 |
| Total tasks | 110 |
| First-attempt pass rate | 108/110 (98.2%) |
| Re-plans | 2 |
| Haiku tasks requiring escalation | 0 |
| Opus tasks needed | 0 |
| Team-lead interventions | 4 |

| Phase | Tasks | Re-plans | Wave failures | Spec gate attempts | Breakdown gate attempts |
|-------|-------|----------|---------------|-------------------|------------------------|
| 0: Security | 28 | 1 | 1 | 0 (pre-reviewed) | 1 |
| 1: Test infrastructure | 31 | 1 | 1 | 3 | 4 |
| 2: Prompt migration | 28 | 0 | 0 | 2 | 4 |
| 3: Interface reconciliation | 23 | 0 | 0 | 1 | 2 |

## What the data shows

### The pipeline reliably executes well-defined work

98.2% of tasks completed on their first attempt, within their declared file scope, on the assigned model. Haiku handled every task assigned to it across all four phases without escalation. The two re-plans were caused by incomplete task instructions, not model capability. Task sizing held — with one exception (a type migration that rippled from 3 declared files to 7), every task stayed within its 1-2 file constraint.

The test-first wave structure (tests in wave 1, implementation in wave 2+) caught real regressions immediately rather than letting them propagate. The pipeline improved over time: re-plans and wave failures dropped to zero by Phase 2.

### Model routing works and could be pushed further toward the cheapest tier

Zero Haiku escalations across 110 tasks. The routing heuristic — Haiku for constrained/mechanical work, Sonnet for multi-file or design-judgment work — appears sound. The data suggests Haiku's boundary could be expanded, since it handled every task within its current assignment criteria without difficulty.

### Spec review is high-leverage

Upstream gates caught serious design problems before any code was written:

- Phase 1: 8 blocking findings (acceptance criteria verifiability, scope gaps)
- Phase 2: 9 blocking findings + 1 on re-review
- Phase 3: 9 blocking findings; 5 spec sections completely rewritten

The Phase 3 council review forced a complete rewrite of the core architecture sections. Without it, the task breakdown would have been working from a fundamentally flawed design. The cost of a review round is low; the cost of implementing from a bad spec is an entire wasted phase.

### The Detector/Challenger code review loop finds issues CI misses

Across the two phases with structured code review data (Phases 0 and 3), the review process promoted 14 sightings to verified findings. The issues found are characteristic of agentic code — syntactically correct, CI-passing, but wrong:

- Tests that pass vacuously (a grep test that doesn't fail on execution errors)
- Missing deep-copy on collection fields in a thread-safe wrapper
- Dead code guards that only scan one file instead of all source files
- Public methods with zero production callers still using superseded logic

These are the patterns the code review pipeline is designed for. Standard CI catches none of them.

### Compilation gaps are the dominant failure mode

Every phase had at least one instance where correct spec information failed to become a complete set of tasks. Two patterns recur:

**Pattern A — Spec knows, breakdown drops.** The spec correctly identifies impacted code, required components, or tests needing updates. The breakdown step fails to compile these into explicit tasks. This happened in Phase 2 (4 impacted test files identified in spec, no tasks created) and Phase 3 (spec required a concrete provider implementation, no task created).

**Pattern B — Second-order effects.** The spec and task are both correct for their stated scope, but the change has downstream consequences neither anticipated. Adding a mutex changes nil-receiver behavior (Phase 0). Correctly wiring a mock lets the engine reach further downstream code that requires additional setup (Phase 1). Changing a constructor signature cascades to 15+ test callers outside any task's scope (Phase 3).

Pattern A is addressable — the breakdown agent needs to treat spec impact sections as mandatory work items, not informational context. Pattern B is harder. It requires reasoning about what the codebase will do *after* the change, not just what the change is. The team-lead interventions (4 across the test) cluster here.

### Agent scope enforcement is a framework-level gap

In Phase 2, agents spawned to *analyze* later-phase specs for conflicts with the implementation instead *implemented* entire phases — modifying 13 production files and deleting source code. The prompt said "check and report." The agents interpreted this as "check, fix, and report."

The root cause is structural: the system controls which *tools* an agent can use, but not *what intent* those tools serve. An agent with write-capable tools has no guardrail distinguishing authorized implementation from unauthorized implementation. The only mitigation is restricting analysis agents to read-only tool sets — a blunt instrument, but the only enforcement mechanism currently available.

## What we can't measure yet

**Code quality trend across phases.** Only Phases 0 and 3 have structured code review data (sighting counts, finding categories). Phases 1 and 2 either didn't run post-implementation review or didn't record it in the same format. With two data points, we can't track whether the remediation is producing fewer new issues over time.

To measure this in the remaining phases, each retrospective needs: code review on every phase (including test-only phases), sightings normalized by files changed, and classification of whether each finding was *introduced by this phase* or *pre-existing and discovered by this phase*. Phase 0 already makes this distinction for two of its findings — extending it systematically would make trend analysis possible.

**False-pass exposure rate.** Phase 1 revealed 7 tests that were false-passing — green because of wrong mock wiring, not because the behavior was correct. This is arguably the most important quality signal: remediation is uncovering hidden problems, not just fixing known ones. But this metric isn't tracked consistently across phases.

## Process friction

These are infrastructure issues, not design issues — fixable without architectural changes:

- **Gate script path bug**: The task reviewer gate derives the project root by walking up a fixed number of directory levels. This fails for deeply nested task directories. Appeared in Phases 2 and 3, worked around but not fixed.
- **Breakdown gate deferred-AC handling**: The gate can't distinguish deferred acceptance criteria from active ones. Requires text-rewriting workarounds.
- **Wave proliferation**: The breakdown gate's strict dependency rule forces test-impl pairs into separate waves, inflating from 3 conceptual waves to 13+ manifest waves in some phases.
- **Agent mailbox reliability**: Team agents require explicit message kickoff after spawn. Some go idle without reporting. File system checks are the reliable fallback.
- **Over-consultation**: Both spec review and code review present trivially-resolvable findings for human discussion. A 5-line fix with one correct answer doesn't need human approval.
- **Challenger calibration**: The Challenger over-promotes low-severity items. When the guarded acceptance criterion is low-severity and the test covers the most likely regression path, promotion adds noise rather than value.

## Individual phase retrospectives

- [Phase 0: Security Remediation](phase-0-security-retrospective.md) — path traversal, race conditions, resource leaks, credential cleanup
- [Phase 1: Test Infrastructure](phase-1-test-infrastructure-retrospective.md) — deprecated mock removal, false-pass exposure, test wiring fixes
- [Phase 2: Structured Prompt Migration](phase-2-structured-prompt-migration-retrospective.md) — API migration, dead code removal, rogue sub-agent incident
- [Phase 3: Interface Reconciliation](phase-3-psychology-interfaces-retrospective.md) — interface unification, scoring pipeline, integration test gaps
