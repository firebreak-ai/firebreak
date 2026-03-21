Perspectives: Architecture, Pragmatism, Quality, Security, User Impact, Measurability

# Phase 1.6: Code Review and Remediation — Spec Review

## Architectural Soundness

**Finding 1** (blocking)
**Category**: Architectural soundness — integration point contradiction
The Dependencies section states "Existing infrastructure (no modifications needed)" but integration seam 8 declares `/implement` skill → `/code-review` post-impl path: "automatic invocation after verification passes." This requires modifying the existing `/implement` skill, which contradicts the dependencies claim. The spec must resolve whether post-implementation review is (a) an automatic stage requiring `/implement` modification or (b) a manual invocation requiring no modification. The choice has ripple effects on an artifact that is load-bearing for the existing pipeline.

**Finding 2** (important)
**Category**: Architectural soundness — pattern divergence
The spec proposes a `references/` subdirectory within the skill for progressive disclosure. No existing skill uses this pattern — all existing skills (`/spec`, `/spec-review`, `/breakdown`, `/implement`) load reference docs from `home/dot-claude/docs/sdl-workflow/`. The spec does not justify the divergence. Either follow the existing pattern (docs in `sdl-workflow/`) or explain why the new pattern is better and whether existing skills should eventually migrate.

**Finding 3** (important)
**Category**: Architectural soundness — misleading framing
The spec repeatedly references "council-pattern orchestration" and states the orchestrator "facilitates without contributing opinions — same principle as the council orchestrator." But the code review skill does not use `/council`. It spawns two agents in an iterative adversarial loop — structurally different from the council's fan-out-and-synthesize pattern. Calling it "council pattern" risks confusing implementers. Describe the actual pattern: iterative adversarial verification loop with an orchestrating skill.

**Finding 4** (important)
**Category**: Architectural soundness — post-impl session context
The post-implementation path "automatically runs" after `/implement`. The implement skill's context window at final verification is already loaded with wave summaries, task statuses, and retrospective data. Nesting an additional agent team for code review inside that same session creates context pressure. The spec should address whether the post-impl path runs in the same session (context risk) or as a separate invocation (requires a hand-off mechanism not described).

**Finding 5** (important)
**Category**: Architectural soundness — missing integration seam
The testing strategy requires the code review skill to produce specs conforming to the 9-section format in `feature-spec-guide.md`. This is an undeclared integration seam. The code review skill's spec output must pass spec-gate.sh, which validates the feature spec guide's structure. This constraint should be declared so breakdown tasks reference the feature spec guide.

**Finding 6** (important)
**Category**: Architectural soundness — agent tool scoping
The spec uses `disallowedTools: Edit, Write` (denylist) but the project's own agent design guidance recommends `tools: Read, Grep, Glob` (allowlist) for analysis-only agents. The denylist approach leaves Bash available — intentionally, per AC-13 (lint/AST tool usage). But this should be explicitly acknowledged as a deliberate divergence from the project's own guidance, not left as an apparent oversight. The Security review also flagged this.

## Over-engineering / Pragmatism

**Finding 7** (important)
**Category**: Over-engineering / pragmatism — terminology overhead
The sighting/finding/verified-finding/rejection terminology introduces four formal terms with structured schemas and sequential ID formats (`S-NN`, `F-NN`) for what is a two-state outcome: confirmed or not. The "sighting" intermediate state has a formal name, a schema, and cross-referencing requirements. The orchestrator's control flow is the actual filter — it simply does not present Detector output until after the Challenger runs. Consider simplifying: the Detector produces observations, the Challenger confirms or rejects them. IDs and cross-referencing can be added later if retrospective data shows traceability is needed.

**Finding 8** (important)
**Category**: Over-engineering / pragmatism — retrospective scope
AC-12 requires six categories of retrospective data (sighting counts, verification rounds, scope assessment, context health, tool usage, finding quality) for a skill that has zero runs. The existing pipeline's retrospective grew organically from actual problems. Scope the v1 retrospective to: files reviewed, findings count (confirmed vs rejected), verification rounds, and user-dismissed findings. Add categories after real reviews show what data is needed.

**Finding 9** (important)
**Category**: Over-engineering / pragmatism — lint integration
AC-13 (Detector uses project-native lint/AST/static analysis tools when available) adds a tool discovery and integration problem orthogonal to the core value proposition (behavioral comparison against specs). The README already calls out lint integration as a future exploration item. This pulls a future concern into v1. Consider deferring AC-13 — the Detector uses grep/glob/read for v1; if the user wants lint output, they paste it into the conversation.

**Finding 10** (important)
**Category**: Over-engineering / pragmatism — source-of-truth matrix
The four-row source-of-truth scenario matrix (lines 187-203) describes scenarios with minimal implementation differences. The actual branching logic is: "if specs exist, compare against ACs; otherwise, compare against the checklist." The "auto-discovered spec tree" scenario is just "there are specs" with a file lookup. Simplify to two modes: spec-backed and checklist-based.

## Testing Strategy and Impact

**Finding 11** (blocking)
**Category**: Testing strategy and impact — coverage gaps
Seven of thirteen ACs (AC-07 through AC-13) have zero test coverage in the testing strategy. Several are structurally testable using patterns already established in the test suite:
- AC-07 (dual-mode): structural test verifying routing logic and reference file existence
- AC-08 (read-only agents): grep agent definition for `disallowedTools` or `tools` frontmatter (pattern from `test-test-reviewer-agent.sh`)
- AC-09 (termination): requires a definition before it can be tested (see Finding 14)
- AC-12 (retrospective): schema validation on retrospective output (pattern from `test-spec-validator.sh`)
- AC-13 (tool fallback): structural test verifying agent definition includes tool detection instructions

AC-10 (spec conflict detection) and AC-11 (module scoping) are Tier 2 — validated through pipeline operation. The spec should explicitly classify them as Tier 2 rather than leaving them uncovered without explanation.

**Finding 12** (important)
**Category**: Testing strategy and impact — test fixture underspecified
The test fixture (5 files, 4 planted issues) cannot validate multi-round convergence. The first detection round will likely find all planted issues, leaving no signal for subsequent rounds. To validate the adversarial loop, the fixture needs: (a) issues of varying subtlety requiring multiple passes, (b) at least one nit-level issue to validate termination, (c) enough volume that the Challenger's filtering is meaningful.

**Finding 13** (important)
**Category**: Testing strategy and impact — post-implementation path untested
UV-7 (post-implementation review) has no corresponding test at any level. The post-implementation path is the more mechanically testable of the two paths (no conversation, deterministic trigger, structured output) — it is a better candidate for automated testing than the conversational path. Either add a test or explicitly classify as Tier 2.

## Stopping Criterion (cross-cutting — Architecture, Testing, Measurability)

**Finding 14** (blocking)
**Category**: Cross-cutting — termination definition
The adversarial loop's stopping criterion — "new sightings degrade to nit-level severity" — has no measurable definition. The severity enum defines exactly three values: `semantic-drift`, `structural`, `test-integrity`. None is "nit." The term is borrowed from Anthropic's severity taxonomy but the spec provides no equivalent classifier.

Three edge cases are unaddressed:
1. **Infinite loop**: Detector never produces nits — loop has no convergence signal
2. **Premature termination**: Detector starts with nits — loop terminates immediately, missing real issues
3. **Oscillation**: Real findings in round 1, nits in round 2, but more real findings would emerge in round 3

Resolution options:
- (a) Add `nit` as a fourth severity value with a concrete definition
- (b) Define a hard iteration cap (e.g., max 3 rounds) as a safety net, independent of the nit criterion
- (c) Reframe: "stop after one round produces no new confirmed findings, or after N rounds, whichever comes first"

The council recommends option (b) + (c): a hard cap plus a "no new confirmed findings" criterion. This is simpler, more predictable, and testable.

## Threat Modeling

**Finding 15** (important)
**Category**: Threat modeling — `disallowedTools` reliability
The research document catalogues four Claude Code issues where subagent permission restrictions fail or are bypassed (Issues #25000, #20264, #5465). The spec relies on `disallowedTools` for AC-08 (read-only agents) without assessing whether these known issues apply. Use `tools: Read, Grep, Glob, Bash` (allowlist) rather than `disallowedTools: Edit, Write` (denylist) — this is the more defensive posture recommended by the project's own agent design guidance.

**Finding 16** (important)
**Category**: Threat modeling — post-impl findings bypass injection scanning
Post-implementation review produces findings (not specs), so they bypass spec-gate injection scanning. If finding text contains embedded instruction payloads, these could flow into corrective workflow agents. Apply the same injection scanning to finding text before presenting it to the user. This reuses existing spec-gate logic.

## User Impact / Scope Creep

**Finding 17** (important)
**Category**: User impact — feature bundling
Thirteen ACs span at least three distinct capabilities: (1) adversarial detection/verification, (2) conversational spec co-authoring from findings, (3) post-implementation automated review. These share internal infrastructure but have different interaction models, outputs, and user expectations. Bundling creates implementation risk (one failing capability blocks all three) and user complexity (one command that behaves three different ways). Consider whether the post-implementation path should be a separate pipeline stage rather than a mode of `/code-review`.

**Finding 18** (important)
**Category**: User impact — cold-start user journey
The spec assumes users who know where to look ("focus on session handling"). The target audience — developers with AI-degraded codebases — may not know where problems are. The spec provides no "just review everything" entry point or guided triage for users who cannot steer. Options: agent proposes starting points from file change frequency or test coverage gaps, or a quick checklist sweep surfaces a starting agenda.

**Finding 19** (important)
**Category**: User impact — cleanup submode value
The cleanup submode's relationship to the corrective workflow fast-track is unclear. Most cleanup findings (e.g., "duplicated logic in two files") require design decisions about how to deduplicate — they don't meet the fast-track's "no design decisions" precondition. The cleanup submode either needs clearer eligibility criteria or should simply produce remediation specs like the main conversational flow.

**Finding 20** (important)
**Category**: User impact — conversation checkpoints
The conversational model interleaves three cognitive tasks: reviewing findings, providing design intent, and co-authoring spec sections. The spec does not describe checkpoints where the agent summarizes what it has captured and the user confirms before moving on. Without checkpoints, the user has no mechanism to verify the emerging spec reflects their intent mid-conversation.

## Measurability

**Finding 21** (important)
**Category**: Measurability — research number framing
The 85.4% accuracy from arXiv:2508.12358 is cited as justification but the spec does not clarify its role. This number was measured on function-level NL specs with GPT-4o. The spec applies it at AC-level with Claude, in a multi-agent loop, against real-world code. The 85.4% justifies the *framing choice* (behavioral comparison over defect detection), not a performance target for this system. The spec should state this explicitly.

**Finding 22** (important)
**Category**: Measurability — AC-11 undefined term
AC-11 says "scopes the review conversation module-by-module." The word "module" has no definition in the spec. The actual behavior is user-directed scoping — the user decides what to review next. Rewrite AC-11 to match reality: "supports user-directed scoping to manage context limits."

**Finding 23** (important)
**Category**: Measurability — "context health" is subjective
The retrospective metric "context health" is defined as "whether the agent team appeared to manage the task adequately." This is a subjective human assessment disguised as a metric. Replace with measurable proxies: total tokens consumed vs context window size, rejection rate per round (increasing rejection rate suggests context degradation), or whether later-round sightings reference early-round code accurately.

## Threat Model Determination

The spec explicitly introduces a new trust boundary: agents read the target codebase, which is treated as untrusted input. The v1 assumption ("user owns the codebase") makes this boundary low-risk — the user is not attacking themselves. Mitigations are proportional: read-only agents, spec-gate scanning on output, human co-authoring. No structured threat model artifact needed for v1.

**Decision**: No threat model required. Rationale: No new external trust boundaries for v1 (user's own codebase, user's own machine, existing permission model). Security findings above are defense-in-depth improvements, not responses to exploitable threats. If the skill is later extended to untrusted codebases, a threat model should be created at that time.

## Testing Strategy Coverage

| Category | Status |
|---|---|
| New tests needed | 6 tests covering AC-01 through AC-06; 7 ACs uncovered |
| Existing tests impacted | None — confirmed by test suite search |
| Test infrastructure changes | Test fixture and synthetic spec defined but underspecified for multi-round validation |

## Test Strategy Review

**Result: FAIL** — 6 blocking defects identified by the independent test reviewer at CP1.

**Defect 1**: AC-07 through AC-13 have zero test coverage. AC-07, AC-08, AC-12, AC-13 are structurally testable using existing patterns (`test-test-reviewer-agent.sh` for frontmatter checks, `test-spec-validator.sh` for schema validation). AC-10 and AC-11 should be explicitly classified as Tier 2. AC-09 requires the stopping criterion to be defined before a test can be written.

**Defect 2**: UV-2 (design intent incorporated into Problem section) is insufficiently covered — spec-gate.sh validates structure not content. UV-3 (structural finding routing) has no test. UV-7 (post-implementation path) has no test at any level.

**Defect 3**: AC-09 stopping criterion is untestable as written. The severity enum has no "nit" value. No test can verify loop termination against an undefined condition.

**Defect 4**: Integration seams 1, 2 (path routing to reference files) and 8 (`/implement` → post-impl trigger) have no test coverage. Seam 8 also has an architectural contradiction (Dependencies says no modifications, but the seam requires modifying `/implement`).

**Defect 5**: Retrospective cross-module interaction (AC-12 output must conform to existing retrospective pattern) is not declared as an integration seam.

**Defect 6**: E2e test description is insufficiently specific — "passes the gate" is the only assertion, but spec-gate.sh does not inspect content. The test cannot verify UV-2's behavioral outcome.

### Test Strategy Re-Review (after revisions)

**Result: PASS** — all prior defects addressed. Re-check found 3 remaining gaps (UV-3 assertion specificity, UV-7 behavioral test, `/implement` trigger-point test). Resolved by: adding structural finding assertion to e2e test, adding structural test for `/implement` stage-transition prompt, classifying post-impl behavioral test as Tier 2.

## Summary

**Blocking findings (3 from council review + 6 from test reviewer = 9 total, with significant overlap):**
1. Dependencies section contradicts integration seam requiring `/implement` modification (Finding 1)
2. Seven ACs have zero test coverage (Finding 11)
3. Stopping criterion "nit-level" has no measurable definition and creates edge-case risks (Finding 14)

**Important findings (20):**
Cluster around four themes: terminology/framing overhead (Findings 7, 3, 10), test coverage gaps (Findings 12, 13), measurability gaps (Findings 21, 22, 23), and scope bundling (Findings 17, 18, 19, 20). All are addressable through spec revision.

**Informational findings (0 surfaced in synthesis — 8 from individual agents were absorbed into the important findings or deemed redundant)**

The core design — adversarial Detector/Challenger with behavioral comparison, producing specs through conversational co-authoring — is architecturally sound and well-motivated. The blocking findings are resolvable: clarify the `/implement` modification, add test plans for uncovered ACs, and define the stopping criterion concretely. The important findings mostly recommend simplification, which would reduce the spec's size while preserving its substance.
