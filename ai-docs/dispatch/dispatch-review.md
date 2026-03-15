Perspectives: Architecture, Pragmatism, Quality, Security, UserImpact, Measurability

## Architectural Soundness

### Finding 1: Inter-wave integration relies solely on test suite — semantic interface mismatches are undetected
**Severity**: blocking → accepted with rationale
**Category**: Architectural soundness

The pipeline uses the test suite as the sole integration contract between waves. The inter-wave file reference check (Stage 8) catches file-level mismatches but not semantic interface mismatches (e.g., Wave N produces a function with a different signature than Wave N+1 expects). The pipeline-analysis document acknowledges: "If the ACs miss integration behavior, no pipeline mechanism catches it."

**Original resolution**: Add a deterministic contract check or contract chain injection.

**Decision**: Accept the gap for v1. Deterministic contract checking requires language-specific AST parsing with high false-positive risk — a feature unto itself, not a lightweight check. Contract chain injection creates a review-integrity problem: injecting post-review artifacts means the agent executes against context that was never reviewed, undermining the pipeline's quality model. The existing replan mechanism (2 per task, PARKED on exhaustion) handles the cases where Wave N+1 agents discover interface mismatches. Track inter-wave replan frequency as an operational metric from day one. If replans concentrate at wave boundaries above a threshold, invest in a contract check at that point.

**Risk owner**: Spec author.
**Tracking**: Add "inter-wave replan frequency" to the operational metrics defined in cross-cutting concerns.

### Finding 2: Context-independent breakdown is architecturally novel but unproven
**Severity**: important
**Category**: Architectural soundness

No comparable system separates test task planning from implementation task planning. Two independently-produced task sets must be compatible (file boundaries, AC coverage). The Task Review gate (Stage 5) catches structural incompatibility, but the false-failure rate (how often valid independent breakdowns get rejected because they express the same intent differently) is unknown. If high, this becomes a cost bottleneck.

**Resolution**: The spec should define a rebreakdown cap (analogous to the 2-replan cap for implementation). Track false-failure rate from first pipeline runs as an operational metric. If the rate exceeds a threshold (e.g., >30% of breakdowns require retry), consider consolidating breakdown into a single agent with explicit test-task and implementation-task output sections.

### Finding 3: Cost risk in failure-and-retry paths is unbounded at the spec level
**Severity**: important
**Category**: Architectural soundness

The circuit breaker bounds replans at 2 per task, but does not bound aggregate cost across all tasks in a spec. A spec with 10 tasks each hitting the replan cap can consume 3x the baseline token budget. The $5-15 estimate is closer to $10-25 for a realistic median accounting for retries, and worst-case can exceed this significantly.

**Resolution**: Add a per-spec token ceiling in addition to the per-task replan cap. When reached, the spec transitions to PARKED. Publish the cost model assumptions explicitly (cache hit rate, retry frequency, model tier per stage) so the estimate is auditable.

## Over-Engineering / Pragmatism

### Finding 4: v1 scope of 16 features / 5 waves is disproportionate to validation state
**Severity**: blocking → accepted with rationale
**Category**: Over-engineering / pragmatism

Sixteen features across five waves before any developer has run a single spec through the pipeline. Waves 4-5 (F13-F16: full automation, notifications) are premature without evidence the pipeline stages work. The pipeline has zero users and no published quality metrics.

**Decision**: Accept current scope. This is a project-level overview spec defining the architectural vision, not a v1 scope commitment. The 5-wave structure is a dependency-ordered roadmap. After review iteration, the spec will be broken into explicit development phases — v1 will be defined with a tight boundary, and future versions will be planned loosely/tentatively. Each feature becomes its own feature-level spec through the SDL process, providing natural scope control.

**Risk owner**: Spec author.

### Finding 5: Docker + bubblewrap is disproportionate isolation for v1 solo-developer scope
**Severity**: important
**Category**: Over-engineering / pragmatism

The Container Manager (F10) and its prerequisite infrastructure add the most implementation complexity in the entire pipeline. For a solo developer running their own specs, Claude Code's native sandbox provides sufficient isolation. Container escape CVEs (CVE-2025-9074, runc CVEs) demonstrate that Docker is not a perfect boundary anyway.

**Resolution**: Defer container isolation to a hardening phase. Use Claude Code's native sandbox with separate agent invocations (no shared conversation context) for v1. Container isolation becomes a hard requirement only when the pipeline accepts specs from untrusted sources.

### Finding 6: The dispatcher orchestrator (F13) should be v1, not Wave 4
**Severity**: blocking → deferred to phase planning
**Category**: Over-engineering / pragmatism

The developer's experience should be three interactions: write spec, review with council, invoke `/dispatch`. The current spec makes this a Wave 4 feature, meaning without it the developer must manually invoke each stage transition. Without "run-to-decision-point" as the default mode, the pipeline ships its internals as the user experience.

**Decision**: Deferred. The overview spec is a dependency-ordered roadmap. The development phases document (to be created after review iteration) will define v1 scope and will address whether the dispatcher is included in v1 or staged separately. The council's concern is noted and will inform phase planning — the pipeline's value proposition depends on automated stage transitions, and this should be reflected in how v1 is scoped.

**Risk owner**: Spec author.

### Finding 7: Five test reviewer checkpoints can be reduced to three without quality loss
**Severity**: important
**Category**: Over-engineering / pragmatism

Checkpoints 1 and 2 (test strategy at spec review, test task quality at task review) are cheap text-level reviews that can be folded into the existing council review and task review gates as sub-checks rather than independent test reviewer agent invocations. This leaves three distinct checkpoints: test code review (Stage 7), pre-implementation mutation check (new), and post-implementation verification (Stage 9).

**Resolution**: Fold checkpoint 1 into council review (test reviewer as one voice in the council at Stage 3). Fold checkpoint 2 into the deterministic task review (validate test-task-to-AC traceability structurally). Keep checkpoint 3 (test code review) as the critical independent gate. Add lightweight mutation check between Stages 7 and 8. Keep Stage 9 mutation testing and integrity check as verification layer. This reduces fresh test reviewer instances from five to three while concentrating effort on actual code and mutations.

## Testing Strategy

### Finding 8: "Tests compile and fail" is insufficient as a Stage 6 completion gate
**Severity**: important
**Category**: Testing strategy and impact

A test can compile and fail for reasons unrelated to the behavior it claims to test — wrong import, misconfigured fixture, assertion against a nonexistent method. These tests pass the gate but would pass trivially once implementation creates the referenced method, regardless of correctness. Stage 6 completion is effectively meaningless without Stage 7 test code review.

**Resolution**: Add deterministic structural checks to supplement "compile and fail": verify test files import from the modules they claim to test, verify assertion targets reference symbols in the spec's technical approach, verify no test body is empty or contains only setup without assertions. These do not replace Stage 7 but catch trivially-wrong tests before the agentic review.

### Finding 9: Test-first separation is non-negotiable — must not be deferred
**Severity**: blocking → resolved
**Category**: Testing strategy and impact

The separation between test-writing and implementation agents is the pipeline's primary defense against failure mode C1 (oracle captures actual behavior, not intended behavior). Empirical data: tests classified "wrong code + wrong assertion" were judged correct 84% of the time when the test writer shares context with the implementer. Deferring this means v1 ships without its most distinctive quality property.

**Decision**: No change needed. The spec already describes test-first separation clearly through its stage structure, context-independence discussion, and design principles ("Tests gate code, reviewers gate tests"). The council raised this as blocking to prevent it from being cut during scope reduction — the spec's existing treatment is sufficient.

### Finding 10: Mutation testing by the same test reviewer persona creates shared blind spots
**Severity**: important
**Category**: Testing strategy and impact

The test reviewer validates tests against the spec (spec-conformance checking). The mutation generator must challenge tests from a code-behavior perspective (adversarial fault injection). Using the same persona creates a monoculture in spec interpretation. A systematic blind spot in the persona propagates across checkpoints.

**Resolution**: Use a separate mutation-generation agent with a different prompt, different role framing, and access to the implementation but not the test reviewer's criteria. This provides structurally independent validation.

### Finding 11: Pre-implementation mutation testing should be added between Stages 7 and 8
**Severity**: important
**Category**: Testing strategy and impact

Placing mutation testing only at Stage 9 (post-implementation) means test detection power is only validated after all implementation work is done. If mutation testing reveals weak tests, the rework cost includes re-running Stages 6-8. A lightweight pre-implementation mutation check against stub implementations catches tests that look correct but have no detection power — before compute is spent on implementation agents.

**Resolution**: Add focused mutation check between Stages 7 and 8: inject targeted mutations into stubs, verify approved tests detect them. Keep Stage 9 mutation testing against real implementation as a second layer. Total: two mutation checkpoints with different purposes (pre-implementation detection power, post-implementation comprehensive validation).

## Threat Modeling

### Finding 12: Status reporting protocol is a narrow injection surface at the orchestration layer
**Severity**: important
**Category**: Threat modeling

The dispatcher parses agent status (DONE / DONE_WITH_CONCERNS / NEEDS_CONTEXT / BLOCKED) from agent output. If parsed by scanning stdout for keywords, a crafted status string in code comments or error messages could cause misparsing — advancing past a failed stage or masking a stuck agent.

**Resolution**: Agents must emit status as a structured JSON object on a designated channel (specific file path or last line of stdout in a defined schema). The dispatcher parses only that channel, not the full output. This closes the injection vector with minimal implementation effort.

### Finding 13: Credential scoping is underspecified and non-deferrable
**Severity**: blocking → resolved (documentation change)
**Category**: Threat modeling

The spec mentions "scoped deploy key" and "PR creation, no merge" but does not specify the required permission boundaries or document which permissions are incompatible with the security model.

**Decision**: Add to the cross-cutting concerns section: credential requirements stating that the pipeline requires minimum necessary git permissions — read/write contents and pull request creation only. Merge access, workflow dispatch, and org-level permissions are incompatible with the pipeline's security model regardless of how git access is configured (PAT, deploy key, GitHub App, SSH key, etc.). The specific credential mechanism is deferred to feature-level specs as it varies by user environment. The Anthropic API key is the developer's own key (acceptable for solo-dev scope).

### Finding 14: Hash manifest placement is within agent write scope
**Severity**: important
**Category**: Threat modeling

The spec places the test hash manifest at `ai-docs/<feature>/test-hashes.json`, inside the repository the implementation agent can write to. An agent could update the manifest alongside modified test files, bypassing the immutability check.

**Resolution**: Store the manifest at `.claude/automation/state/<spec-id>/test-hashes.json` alongside the pipeline state file. The dispatcher (running on the host) computes and writes the manifest after Stage 7. The dispatcher performs the comparison at verification. No agent has write access to the state directory. Achievable with filesystem permissions even without containers.

### Finding 15: Three injection propagation paths are bounded but real
**Severity**: informational
**Category**: Threat modeling

The pipeline-analysis document identifies three propagation paths for injection payloads: (1) spec artifact shared across all agentic stages, (2) test files from Stage 6 read by Stage 8 agents, (3) Wave N output read by Wave N+1 agents. All three are bounded by context-independence, Least Agency, and deterministic gates. For v1 (solo developer, self-authored specs), the probability of a sophisticated injection payload surviving Stage 2 is low. The architecture correctly prioritizes blast radius limitation over prevention.

**No resolution needed** — the spec's framing of Stage 2 as "catch the obvious, not injection prevention" is honest and proportional. The architectural defenses (context-independence, deterministic gates, Least Agency) are the real injection resilience. This assessment changes if the pipeline accepts specs from untrusted sources (see Finding 5).

## UserImpact / Scope Creep

### Finding 16: Cold-start detection must be Wave 1, not Wave 4
**Severity**: blocking
**Category**: User impact / scope creep

The first thing a new user encounters should not be a wall of missing prerequisites. Cold-start detection is buried in F14 (Wave 4). A developer who hits a cryptic failure at Stage 6 because they never configured a test runner will not come back.

**Resolution**: Move cold-start detection to Wave 1, either as part of F1 (queue manager prerequisite check) or as a standalone script that runs before any spec enters the queue. Check: test runner configured, linter configured, CLAUDE.md exists, context assets installed. Report clearly what the project has and what it needs. Not a sophisticated feature — a simple checklist.

### Finding 17: Value proposition vs. manual workflow is never directly articulated
**Severity**: important
**Category**: User impact / scope creep

A developer using `/spec` + `/spec-review` + `/breakdown` + `/implement` manually gets most of the spec-driven quality benefit already. The spec never answers: "What does Dispatch give me that I don't already get?" The vision discusses the problem (AI code quality) and the architecture discusses the solution (10 stages), but neither connects to the user's decision: "Is this worth the setup and ceremony cost?"

**Resolution**: Add a section to the overview that explicitly states the incremental value over the manual workflow: deterministic gate enforcement (stages cannot be skipped or shortcuts taken), test-first separation with context-independent agents (the manual workflow does not enforce this), test file immutability and mutation testing (structural quality checks the manual workflow cannot perform), structured audit trail and cost tracking, and automated stage transitions reducing developer attention cost from "invoke each stage" to "invoke once, review when needed."

## Measurability

### Finding 18: Mitigation matrix self-assessment has zero "Weak" ratings — not credible
**Severity**: important
**Category**: Measurability

The failure-modes document rates 24 mitigations as "Strong," 12 as "Moderate," and 0 as "Weak." The same document that designed the mitigations grades them. Several "Moderate" ratings are generous: D2 (role specification compliance) is "depends on agent prompt quality" — effectively no structural enforcement. F1 (wrong granularity) is "subjective assessment" — no ground truth. D10 (information withholding) mechanism is "relies on git merge" — effectively unmitigated.

**Resolution**: Re-grade the mitigation matrix with explicit criteria distinguishing Strong/Moderate/Weak. Proposed: Strong = structural/deterministic enforcement; Moderate = agentic enforcement with fallback; Weak = agentic enforcement with no fallback. Under these criteria, D2, F1, D10 should be Weak. A5 and C5 should be reconsidered. The absence of any Weak ratings undermines the matrix's credibility as an engineering assessment.

### Finding 19: Pipeline cannot measure its own effectiveness — and should define operational metrics from day one
**Severity**: important
**Category**: Measurability

The spec correctly acknowledges that code quality outcomes are external and longitudinal. But the pipeline can measure operational effectiveness immediately. Three metrics should be defined before the first spec enters the pipeline:

1. **Gate rejection rate per stage** — which stages catch problems, which are ceremony? If a stage has 0% rejection rate after 20 specs, it is either perfectly positioned upstream or not doing useful work.
2. **Cost-per-AC** — total pipeline cost divided by acceptance criteria satisfied, tracked per spec. Unit economics metric for comparing Dispatch against manual implementation.
3. **Replan concentration** — which stages and task types trigger replans? If 80% of replans concentrate in one stage, that stage needs redesign.

**Resolution**: Define these three metrics in the cross-cutting concerns section. Verify the audit log schema (F3) captures the data to compute them. Publish observed distributions after the first 5-10 specs.

### Finding 20: FeatureBench decomposition argument is weaker than presented
**Severity**: informational
**Category**: Measurability

The spec implies that decomposing feature-level work (11% solve rate) into SWE-bench-scale tasks (74.4% solve rate) will achieve the higher reliability. FeatureBench data shows a 5.2% resolve rate on SWE-bench-overlapping repositories — the gap is driven by task type (feature implementation vs. bug fixing), not purely scope. Decomposed feature sub-tasks are "implement new behavior" tasks, which may perform worse than "fix existing behavior" tasks of similar size.

**No resolution needed** — this is an intellectual honesty note. The spec should qualify the decomposition argument: decomposition improves reliability by reducing scope, but the target reliability zone is likely lower than 74.4% for implementation tasks. Track per-task success rate as an operational metric to calibrate.

### Finding 21: Mutation testing and TBD defaults need a calibration plan
**Severity**: informational
**Category**: Measurability

The minimum mutation detection rate is "default TBD based on early pipeline runs." This is appropriate, but the spec does not define what constitutes sufficient calibration data or when the default will be set.

**Resolution**: Define the calibration plan: number of specs, complexity range, and threshold for setting the default. Start with mutation testing as advisory (non-blocking) for the first N specs, collect detection rate distributions, then set the threshold at a percentile that avoids excessive false failures.

## Testing Strategy Coverage

**New tests needed**: The pipeline itself will need its own test suite. Each deterministic gate (spec validation, task review structural checks, inter-wave file reference check, test hash verification, assertion density check) should have unit tests. The dispatcher's stage transition logic, state persistence, and error handling need integration tests. The structured status parsing protocol needs tests against adversarial inputs.

**Existing tests impacted**: The existing SDL skills (`/spec-review`, `/breakdown`, `/implement`) will need to reference the spec schema for structural validation, replacing any hardcoded structural assumptions. Tests for these skills may need updates.

**Test infrastructure changes**: The verification engine (F9) introduces project-level test infrastructure requirements (verify.yml). Projects adopting Dispatch will need to configure their verification commands. The cold-start check should validate this configuration exists before any spec enters the pipeline.

## Threat Model Determination

**Security-relevant characteristics**:
- **Data touched**: Source code (read/write in implementation), spec artifacts (read across all agentic stages), credentials (deploy keys, API keys injected into agent environments)
- **Trust boundaries crossed**: Host → container (deferred to hardening), developer → agent (agents execute with developer's API credentials), agent output → dispatcher (status parsing), spec → agent (injection surface)
- **New entry points**: Spec queue directory (file-based input), pipeline state files, verification configuration (verify.yml)
- **Auth/access control changes**: Scoped credentials per stage (currently underspecified), fine-grained PAT for PR creation

**Recommendation**: This feature needs a threat model. The spec introduces multiple trust boundaries (developer-to-agent, agent-to-dispatcher, cross-agent artifact sharing) and processes untrusted-by-design inputs (specs treated as injection surfaces). The pipeline-analysis document already contains substantial security analysis. A structured threat model would consolidate this into a formal artifact with explicit threat actors, STRIDE analysis, and residual risk documentation.

**Decision**: No threat model at this time. Rationale: v1 targets a solo developer running self-authored specs with Claude Code's native sandbox. The significant trust boundary changes (container isolation, untrusted spec sources) are deferred to the hardening phase. A formal threat model should be created when container isolation (F10) is implemented, as that introduces the host-to-container trust boundary and credential injection mechanisms that warrant STRIDE analysis. Security findings from this review (Findings 12-15) still apply and should be addressed in the spec.
