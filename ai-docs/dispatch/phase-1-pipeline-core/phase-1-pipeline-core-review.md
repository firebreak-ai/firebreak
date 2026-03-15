Perspectives: Architecture, Pragmatism, Quality, Security

## Architectural Soundness

### Finding 1: Sequential fallback for parallel breakdown not in spec
**Severity**: blocking — **resolved**
**Category**: Architectural soundness

The spec needed a sequential fallback when parallel breakdown reconciliation fails.

**Resolution**: Breakdown changed to sequential-only. Test task agent runs first (receives spec only), implementation task agent runs second (receives spec + test task output). Both run as Agent Teams teammates with independent context. F6, AC-07, goals, and user-facing behavior sections updated.

### Finding 2: Agentic task reviewer layer deferral not in spec
**Severity**: blocking — **resolved**
**Category**: Architectural soundness

The agentic completeness layer should be deferred to Phase 2.

**Resolution**: F7 changed to two-layer gate (deterministic + test task quality). Agentic completeness layer deferred to Phase 2. AC-08, goals, and testing strategy updated. Phase 2 spec updated to carry the deferral.

### Finding 3: Test recommendations from previous review not incorporated in test list
**Severity**: blocking — **resolved**
**Category**: Testing strategy and impact

The spec's test list didn't cover all ACs and included agentic behavior tests as if they were automated.

**Resolution**: Testing strategy completely restructured into three tiers: Tier 1 (automated tests for deterministic code), Tier 2 (context asset behaviors validated through pipeline operation), Tier 3 (longitudinal framework effectiveness). Applied across all three phase specs and the dispatch overview.

### Finding 4: State machine transitions are implicit — no explicit graph
**Severity**: important — **resolved**
**Category**: Architectural soundness

The Pipeline State Engine described states narratively without defining the valid transition graph.

**Resolution**: Added explicit state machine table with 19 states and valid transitions to the Pipeline State Engine section. Added transition validation requirement: "The state engine validates that each transition is legal before persisting; illegal transitions are rejected with an error logged to the audit log."

### Finding 5: validate_transition() specified in tests but absent from spec
**Severity**: important — **resolved**
**Category**: Architectural soundness

The testing strategy tested transition validation, but the spec never required it.

**Resolution**: Resolved by Finding 4's edit — transition validation requirement added to the Pipeline State Engine section.

### Finding 6: Agent Teams dependency has no degradation path
**Severity**: important — **accepted without change**
**Category**: Architectural soundness

Agent Teams is experimental. Three subsystems depend on it.

**Resolution**: Agent Teams is explicitly accepted as a load-bearing dependency with no fallback path. User has validated the feature through direct use. Dependencies section updated to document this decision: if the API changes, affected subsystems (F5, F6, F7) are updated to match.

### Finding 7: Spec schema is both a Phase 1 deliverable and prerequisite
**Severity**: important — **resolved**
**Category**: Architectural soundness

The Dependencies section said "must be defined as part of this phase" but the schema already exists.

**Resolution**: The spec schema is already defined by the existing `/spec` skill. Dependencies section updated to reflect this: "Spec schema (already defined by the existing `/spec` skill — F4 validates against it)."

### Finding 8: Task file format from OQ-P1-2 not referenced in technical approach
**Severity**: informational
**Category**: Architectural soundness

OQ-P1-2 defines a detailed task file format. The Breakdown Integration and Task Reviewer sections describe task contents in prose without referencing this resolution.

**Resolution**: Reference OQ-P1-2 as the canonical task file format in the F6 and F7 sections.

### Finding 9: verify.yml thresholds and spec frontmatter override interaction undefined
**Severity**: informational
**Category**: Architectural soundness

Configuration layering does not clarify whether verify.yml thresholds are overridable by spec frontmatter.

**Resolution**: State that verify.yml thresholds are project-level only and not overridable by spec frontmatter.

## Over-engineering / Pragmatism

### Finding 10: Phase scope remains large — consider sub-phases
**Severity**: important — **accepted without change**
**Category**: Over-engineering / pragmatism

Eight subsystems as a single deliverable. Sub-phases suggested.

**Resolution**: Scope is correct for MVP. Implementation sequencing will be handled by task breakdown, not spec-level sub-phasing.

### Finding 11: Brownfield intercepts need a concrete delivery mechanism
**Severity**: important — **resolved**
**Category**: Over-engineering / pragmatism

The brownfield instructions lacked a delivery mechanism.

**Resolution**: Spec updated to specify delivery as referenced docs in `.claude/docs/` (`.claude/docs/brownfield-spec.md` and `.claude/docs/brownfield-breakdown.md`), loaded by the corresponding skills. Enforcement is guidance-only for MVP.

### Finding 12: Agent Teams dependency is load-bearing but unvalidated
**Severity**: important — **resolved**
**Category**: Over-engineering / pragmatism

No spike validates Agent Teams supports the assumed invocation patterns.

**Resolution**: Resolved by Finding 6 — user has validated Agent Teams through direct use. Dependency explicitly accepted.

### Finding 13: "No human gate" claim contradicts MVP interaction model
**Severity**: informational
**Category**: Over-engineering / pragmatism

The task reviewer says "No human gate" but the developer drives all transitions manually in Phase 1.

**Resolution**: Suggested wording: "No additional human approval required beyond the developer's stage invocation."

## Testing Strategy and Impact

### Finding 14: Agentic test execution strategy undefined
**Severity**: important — **resolved**
**Category**: Testing strategy and impact

The spec didn't address cost, speed, or non-determinism for agentic tests.

**Resolution**: Resolved by Finding 3's testing strategy rewrite. The three-tier framework explicitly distinguishes automated code tests (Tier 1) from context asset behaviors validated through pipeline operation (Tier 2).

### Finding 15: Sequential fallback path has no test
**Severity**: important — **resolved (moot)**
**Category**: Testing strategy and impact

No test covered the sequential fallback path.

**Resolution**: Moot — breakdown is now sequential-only. No fallback path exists.

### Finding 16: Agent Teams context isolation has no validation test
**Severity**: important
**Category**: Testing strategy and impact

The spec trusts Agent Teams context isolation but does not verify it. One smoke test validating the isolation property is cheap insurance.

### Finding 17: Config layering edge cases untested
**Severity**: informational
**Category**: Testing strategy and impact

Untested: malformed config.yml handling and verify.yml referencing a command that does not exist.

### Finding 18: Hash gate initial-run case not explicitly tested
**Severity**: informational
**Category**: Testing strategy and impact

The hash gate has two code paths (initial run, subsequent run). The test should cover both.

## Threat Modeling

### Finding 19: "Input sanitization" is unspecified
**Severity**: important — **accepted without change**
**Category**: Threat modeling

The spec says "input sanitization" without defining what it means.

**Resolution**: Left as-is. The agent understands the intent. Over-specifying with enumerated examples would over-tune for those examples and clog context.

### Finding 20: Parallel breakdown agents share a write directory with no collision prevention
**Severity**: important — **resolved (moot)**
**Category**: Threat modeling

Two agents writing to the same directory simultaneously risked collision.

**Resolution**: Moot — breakdown is now sequential. No simultaneous writes occur.

### Finding 21: Audit log write interface not specified
**Severity**: important — **accepted without change**
**Category**: Threat modeling

The spec does not specify whether audit log writes go through a centralized interface.

**Resolution**: Left as-is for Phase 1. Components are primarily agents with file write access — the format specification (structured JSON lines, append-only) is the interface. A centralized logging script fits better in Phase 3 when the dispatcher (actual code) does the logging.

### Finding 22: Hash manifest writable by implementation agents in Phase 2
**Severity**: informational
**Category**: Threat modeling

Implementation agents in Phase 2 could overwrite the test hash manifest. Known Phase 2 concern — mitigation is that the manifest should be written by the test reviewer (separate agent context).

### Finding 23: No spec-level content size bounds
**Severity**: informational
**Category**: Threat modeling

The spec validator checks structure but specifies no size limits. A configurable maximum spec size (generous default, e.g., 50KB) would prevent resource-exhaustion.

## Documentation Impact

Deterministic check: the spec's documentation impact section lists specific documents and changes. Cross-checking against scope:
- Dispatch overview update: mentioned
- Spec-review skill documentation: mentioned
- Breakdown skill documentation: mentioned
- Spec schema definition: mentioned
- Task file schema: mentioned
- verify.yml schema: mentioned
- config.yml schema: mentioned
- Test reviewer agent definition: mentioned
- Brownfield development instruction files: mentioned
- **Missing**: Gate script migration documentation (which scripts are replaced, which are extended)
- **Missing**: Audit log event schema documentation
- **Missing**: State file schema documentation (including state transition graph)

## Testing Strategy

### New tests needed
Test recommendations from this review were incorporated directly into the spec's three-tier testing strategy during finding resolution. No additional tests beyond the spec's current list.

### Existing tests impacted
- `spec-gate.sh` — will be subsumed by F4
- `breakdown-gate.sh` — will be subsumed by F7's deterministic layer
- `review-gate.sh` — relationship to F5 must be defined

### Test infrastructure changes
- Valid spec corpus for false-positive testing (specs with legitimate HTML, unicode, external references)
- Fixture files for state engine and config loader tests

## Threat Model Determination

### Security-relevant characteristics
- **Data touched**: Spec files (developer-authored markdown), pipeline state (JSON), audit logs (structured events), task files (generated by agents), project configuration (YAML)
- **Trust boundaries crossed**: Developer-authored specs consumed by AI agents; agent-generated task files consumed by other agents and deterministic validators
- **New entry points**: `/dispatch validate`, `/dispatch verify`, `/dispatch status` commands; spec content as input to agents
- **Auth/access control changes**: None — local developer tool with no authentication
- **Agent isolation**: Context isolation between breakdown agents and test reviewer enforced by Agent Teams spawn code, not infrastructure. Shared filesystem access.

### Decision

**Threat model decision**: No — deferred to Phase 2.

### Rationale

Phase 1 risks are low because the developer drives all transitions manually. The primary threat actor (compromised AI agent via prompt injection) gains significant capability only in Phase 2 when agents execute autonomously. Phase 1 includes proportional mitigations: injection detection, transition validation, and audit logging. A structured threat model should be created for Phase 2 when agent execution introduces real trust boundary changes.
