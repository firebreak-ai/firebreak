Perspectives: Architecture, Pragmatism, Testing, User Impact

## Architectural Soundness

### AS-1: Automatic invocation seam not declared (blocking)

The primary invocation path — code review skill finalizes retrospective, then invokes `/fbk-improve <feature-name>` — is a cross-skill invocation with an implicit contract (retrospective persisted at expected path, feature name passed correctly). This seam is acknowledged in "Existing tests impacted" but absent from the integration seam declaration checklist.

**Resolution:** Add seam entry: `fbk-code-review → fbk-improve: automatic invocation contract (retrospective file persisted at expected path before invocation; feature name passed as argument)`.

**Status:** Resolved — seam added to spec.

### AS-2: Spawn prompt contract underspecified (important)

The integration seam declaration says "retro content, authoring rules paths, asset file list" but doesn't specify the format. Is retro content passed as file content or file path? Are authoring rules paths resolved or does the agent discover them? The implementing agent needs this boundary precise enough to build without assumptions.

**Resolution:** Specify in the seam declaration whether the skill passes file contents inline or paths for the agent to read, and whether the authoring rules index is passed or the agent reads from a known location.

**Status:** Resolved — spec updated: spawn prompt passes paths only, agent reads all files on demand. Agent operates as team lead, spawning sub-agents per asset for context independence.

### AS-3: Installation path discovery not specified (important)

Asset discovery targets "installed assets in `.claude/`" but the spec doesn't describe how the skill locates the installation. Is it `~/.claude/`? Project `.claude/`? Both? The Firebreak installer places assets in specific locations — the discovery logic needs to know which scope(s) to search.

**Resolution:** Specify the installation scope(s) the asset discovery behavior searches, or reference the installer's placement convention.

**Status:** Resolved — spec updated: Glob for `fbk-*/SKILL.md` in both `.claude/skills/` (project) and `~/.claude/skills/` (global). Project-level preferred if both exist.

## Over-engineering / Pragmatism

### PR-1: Quality review substep adds value but output is unclear (important)

The quality review substep (re-read affected assets after drafting proposals, check for bloat/redundancy) is worthwhile — it prevents accumulation. But the spec doesn't say what happens when the quality review finds issues. Does the agent self-correct its own proposals? Drop them? Add removal proposals? The behavior needs to be explicit.

**Resolution:** State that the quality review produces additional removal proposals (tagged as bloat-driven rather than retro-observation-driven), or that it modifies existing proposals in-place before presentation.

**Status:** Resolved — spec updated: both behaviors. Self-correction revises proposals in-place before presentation (invisible). Bloat findings become additional removal proposals citing authoring rules rather than retro observations.

### PR-2: Discuss flow complexity is acceptable (informational)

The discuss flow adds a conversational loop for individual proposals. This is proportionate — the alternative (accept or skip with no middle ground) would force users to either take proposals they don't fully understand or lose them entirely.

### PR-3: Discussion item escape hatch is well-scoped (informational)

The distinction between proposals (single-instruction changes) and discussion items (structural changes needing a future spec) is a clean scope boundary. No over-engineering concern.

## Testing Strategy and Impact

### TS-1: AC-08 has no test coverage (blocking)

AC-08 (cross-cutting proposals) is not referenced by any test. If the agent only considered assets in the same pipeline phase as the source observation, no test would catch it.

**Resolution:** Add an integration test where a synthetic retrospective contains an observation about implementation behavior that produces a proposal targeting a non-implementation asset (e.g., spec skill). Reference AC-08.

**Status:** Resolved — test added to spec.

### TS-2: UV-4 has no test coverage (blocking)

UV-4 (discuss flow) has no corresponding test entry. The discuss path produces different output than accept/skip and enters a conversational continuation. If broken, no test would detect it.

**Resolution:** Add an integration or e2e test that sends a "discuss" response and verifies the skill returns detailed reasoning for the named proposal. Map to UV-4.

**Status:** Resolved — test added to spec.

### TS-3: Spawn prompt isolation (seam 1) has no test coverage (important)

The integration tests exercise the agent given assumed inputs but don't verify that the skill constructs the correct prompt with excluded content (spec, implementation, review) absent. AC-02 captures the isolation requirement but the unit test only covers asset discovery enumeration.

**Resolution:** Add an integration test verifying the assembled spawn input contains retro content, authoring rules, and asset list, and does not contain spec or implementation content. Reference seam 1 and AC-02.

**Status:** Resolved — test added to spec.

### TS-4: E2e test asserting "exactly 2 proposals" may be brittle (important)

The e2e test asserts exactly 2 proposals from a synthetic retro with 2 actionable observations. Agent nondeterminism could produce additional proposals (e.g., a removal proposal from the quality review substep) or combine observations into one proposal. The assertion couples to agent judgment rather than behavior.

**Resolution:** Assert "at least 1 proposal" and validate proposal structure/traceability rather than exact count. Or tighten the synthetic fixture to make exactly 2 proposals the only reasonable output.

**Status:** Resolved — e2e test assertion softened in spec.

### TS-5: AC-05 authoring rules compliance is soft-testable (informational)

Testing that an agent self-validates output against style rules is inherently probabilistic. The integration test ("self-corrected or flagged") is the best available approach — deterministic validation of agent style compliance isn't feasible. Acceptable as-is with the understanding that this test validates the instruction to self-check, not guaranteed compliance.

## UserImpact / Scope Creep

### UI-1: Automatic invocation has no opt-out (important)

The automatic path after retrospective finalization gives the user no way to skip improvement analysis. If the user just wants to finish the review cycle and move on, they're presented with proposals they didn't ask for. The proposals require user decisions (accept/discuss/skip), so this isn't zero-cost.

**Resolution:** After confirming the retrospective path, add: "Proceed with improvement analysis, or skip?" This preserves seamlessness (the skill is already invoked and ready) while giving the user an exit.

**Status:** Resolved — opt-out prompt added to spec.

### UI-2: Proposal format serves quick decisions well (informational)

The four-field format (target, change, observation, necessity) gives users enough context to decide without reading the full asset. The observation field is the key — it lets the user recall the problem without re-reading the retro.

### UI-3: "No actionable observations" exit is clear (informational)

The empty-result message ("No improvement proposals — retrospective contains no observations that map to specific asset changes") is specific enough that the user understands why, not just that nothing happened.

## Test Strategy Review

Test strategy review: **FAIL** — 4 defects identified (TS-1, TS-2, TS-3, AS-1). All resolved in spec revision.

### New tests needed

All test gaps identified during review (AC-08, UV-4, seam 1 isolation) have been added to the spec's testing strategy. See TS-1, TS-2, TS-3 findings above.

### Existing tests impacted

`tests/sdl-workflow/test-code-review-integration.sh`: needs assertion that retrospective file is persisted at expected path. Updated in spec from conditional to specific requirement.

### Test infrastructure changes

None beyond what the spec already defines (synthetic retrospective and asset fixtures).

## Threat Model Determination

**Security-relevant characteristics:**
- Data touched: retrospective files (markdown, no secrets), context asset files (agent instructions, no secrets)
- Trust boundaries crossed: none — all operations are local file reads and writes within the user's `.claude/` directory
- New entry points: `/fbk-improve` skill invocation (user-initiated or auto-triggered from existing pipeline)
- Auth/access control changes: none

**Decision:** No threat model. No new trust boundaries, no sensitive data handling, no external API interaction, no auth changes. All operations are local file edits under user approval. User confirmed.
