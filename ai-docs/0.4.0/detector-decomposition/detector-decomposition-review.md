Perspectives: Architecture, Builder, Guardian, Analyst

# detector-decomposition — Spec Review (Round 2)

## Architectural Soundness

### B-1: Test Reviewer naming collision destroys the SDL checkpoint agent (blocking)

**Agents:** Architect, Builder, Guardian (unanimous)

The spec proposes creating `assets/agents/fbk-test-reviewer.md` as a code-review sighting detector. That file already exists as a 172-line SDL checkpoint-based test validator used by `/fbk-spec-review` (CP1), `/fbk-breakdown` (CP2), and implementation stages (CP3-CP5). The existing agent has pipeline-blocking authority, 5 distinct checkpoints, mutation testing capability, and brownfield support. The spec's "New documentation to create" lists `fbk-test-reviewer.md` without acknowledging the existing file. The "Existing tests impacted" section lists `test-test-reviewer-agent.sh` and `test-test-reviewer-extensions.sh` as needing format updates, but those tests validate the SDL checkpoint agent which should continue to exist unchanged.

**Action:** Rename the new detection agent to `fbk-cr-test-reviewer.md` (matching the `fbk-cr-*` or `fbk-t1-*` naming convention). Preserve the existing SDL checkpoint agent untouched. Update AC-05, the sighting ID prefix table (TR prefix is fine), SKILL.md references, preset mappings, shell tests, and the installer manifest. Add a non-goal: "No changes to the checkpoint-based Test Reviewer used by `/fbk-spec-review` and `/fbk-breakdown`." Remove the two SDL test-reviewer tests from the "Existing tests impacted" list.

### I-1: Orchestrator cognitive load is not measured (important)

**Agents:** Architect, Builder (independent convergence)

The spec meticulously counts per-detector instructions (17-19 active per group) but does not apply the same discipline to the orchestrator. Post-decomposition, the orchestrator must: resolve presets to groups, identify entry points, construct spawn prompts with randomized target ordering, ensure identical code payloads, selectively inject Mermaid diagrams, spawn parallel agents, collect sightings, conditionally spawn a Deduplicator, collect deduplicated results, batch Challengers by detection category, collect verified findings, evaluate per-agent respawn eligibility including merge-credit tracking, and repeat for sequential preset waves. The IFScale compliance research that motivates the detector decomposition applies equally to the orchestrator.

**Action:** The spec should acknowledge orchestrator instruction load as a risk. Identify which orchestrator behaviors are essential (core spawn-collect-challenge loop) vs aspirational (randomized ordering, merge-credit tracking, per-group toggle overrides). AC-02's runtime instruction traces will provide data; the risk should be documented.

### I-2: Sighting format non-goal contradiction (important)

**Agent:** Architect

The non-goals state "New finding types, severity levels, or sighting format fields." Instruction #9 adds `detection_phase` (`enumeration` or `cross-instance`) as a new sighting tag. This is a sighting format addition.

**Action:** Update the non-goal to: "New finding types, severity levels, or sighting format fields (except `detection_phase` for observability)."

### I-3: Cross-preset finding dedup is underspecified at the integration seam level (important)

**Agent:** Architect

Cross-preset dedup runs "inline" (orchestrator-level) after all preset waves complete in `full` runs. The integration seam declaration has no entry for this step. The mechanism operates on verified findings (not sightings), but the resolution rules for finding-level conflicts are not specified.

**Action:** Add an integration seam: "Cross-preset finding dedup ↔ report assembly: orchestrator compares verified findings across waves for same-location overlaps; higher-severity finding retained." Specify that this operates on findings, not sightings.

### I-4: Prompt cache optimization claim is unverified (important)

**Agents:** Architect, Analyst (independent convergence)

AC-03 and UV-11 frame identical code payload ordering as "prompt cache optimization." Prompt caching in Claude requires prefix matching. Each agent receives a different agent definition before the code payload — if the definition comes before the code (which it does per "instructions last" from v0.3.5 content-first ordering), the code is at the same position and caching should work. However, no mechanism exists to measure cache hit rates (`cache_creation_input_tokens` / `cache_read_input_tokens` from API responses). The optimization is plausible but unverified.

**Action:** Keep the identical ordering requirement (it costs nothing). Reframe AC-03: "Tier 1 spawn prompts contain identical code payloads in identical order" — drop the "for prompt cache optimization" framing unless cache metrics are instrumented.

## Over-engineering / Pragmatism

### I-5: Preset UX contradicts "no change to invocation syntax" (important)

**Agent:** Builder

The spec states "No change to invocation syntax" (User-facing behavior section) but also "Users select a preset via the `/fbk-code-review` invocation." These contradict. Either preset selection is a new invocation parameter (which changes the syntax) or it happens conversationally (which changes the observable behavior).

**Action:** Either add preset selection to the invocation syntax and remove the "no change" claim, or specify that preset selection is conversational (the user says "run a full review" and the orchestrator interprets).

### I-6: Respawn gating merge-credit tracking adds subtle orchestrator state (important)

**Agent:** Builder

The merge-credit clause ("when a merged sighting survives Challenger verification, all originating agents are credited for respawn eligibility") requires the orchestrator to parse the Deduplicator's merge log and maintain per-agent credit state. This is stateful multi-step reasoning for a feature whose benefit is "save one agent spawn in round 2" in the rare case of cross-agent sighting merges.

**Action:** Simplify respawn gating to: if an agent produced zero sightings, do not respawn. Drop the merge-credit clause. If evaluation shows agents being unfairly pruned because their sightings got merged, add it back with data.

## Measurability

### I-7: UV-8c has no predefined success threshold (important)

**Agent:** Analyst

UV-8c says "validates whether the behavioral-only projection holds as an actual score" but does not define what constitutes success. Without a threshold, any result can be rationalized post-hoc.

**Action:** Add: "UV-8c success = actual behavioral-only F1 >= 46% (the projected score). UV-8c confirms the filter projection. Decomposition-specific success is measured by UV-8b, not UV-8c."

### I-8: UV-8b has no predefined success threshold (important)

**Agent:** Analyst

UV-8b compares execution-gap catches (decomposed vs v0.3.5's 0/14) but does not define a success threshold.

**Action:** Add: "UV-8b success = decomposed pipeline catches >= 4 of the 14 execution-gap issues (>= 28%), demonstrating narrower mandates improve systematic application."

### I-9: AC-02 instruction trace may not be computable from the agent's perspective (important)

**Agent:** Analyst

AC-02 requires "instruction tokens vs payload tokens" in the retrospective. The hook-based approach (PreToolUse logging) is flagged as uncertain. The fallback ("structured agent output") is unclear — agents cannot self-report their own prompt composition. The orchestrator knows what it injected but not what the agent subsequently loaded via tool calls.

**Action:** Clarify the fallback: the orchestrator logs what it injected (instruction file paths + payload size); agents log which additional files they Read via a structured output section. Combined, these approximate the full instruction chain. Accept this is approximate until hook infrastructure is validated.

### I-10: AC-15 enumeration compliance denominator undefined (important)

**Agents:** Analyst, Guardian

`files_in_scope` for enumeration compliance (files_reported / files_in_scope) is not explicitly defined. The orchestrator knows this (it constructs the code payload), but the spec does not state that the orchestrator records the count.

**Action:** Define: "`files_in_scope` = count of code files injected into the agent's spawn prompt (for Tier 1 detectors) or test files provided (for Test Reviewer). The orchestrator records this count at spawn time."

## Testing Strategy and Impact

### I-11: AC-02, AC-16, AC-17, AC-18 have no shell tests (important)

**Agent:** Guardian

Four ACs have no structural shell test:
- AC-02 (instruction trace in retrospective)
- AC-16 (preset definitions in SKILL.md)
- AC-17 (per-group toggle overrides)
- AC-18 (sequential preset execution for `full` runs)

**Action:** Add shell tests: AC-16 (grep SKILL.md for all four preset names + "default" adjacent to "behavioral-only"), AC-17 (grep for "toggle" or "override"), AC-18 (grep for sequential ordering language + cross-preset dedup). AC-02 is primarily a runtime concern; add a shell test verifying code-review-guide.md references "instruction trace" or "prompt composition" in retrospective fields.

### I-12: AC-19 shell test weaker than AC requires (important)

**Agent:** Guardian

The shell test checks "at least one agent-facing document" but AC-19 requires "exactly one per-group agent definition." The test catches missing targets but not cross-group duplication.

**Action:** Update the shell test description to match AC-19: verify each target name appears in exactly one per-group agent definition or the Test Reviewer (not just "at least one agent-facing document").

### I-13: Missing impacted tests (important)

**Agent:** Guardian

Two test files are not listed in the "Existing tests impacted" section:
- `tests/sdl-workflow/test-code-review-skill.sh` — references `quality-detection.md` with `>= 11` count assertion; needs updating to `>= 15`
- `tests/sdl-workflow/test-code-review-guide-extensions.sh` — references `code-review-guide.md` and `quality-detection.md`; needs review for impact from AC-14 changes

**Action:** Add both to the "Existing tests impacted" section with specific update plans.

## Test Strategy Review

**Result: FAIL** — 15 defects identified by independent test reviewer.

### Critical (blocking per test reviewer)

- **Defect 1 (AC-02):** No test coverage for hook-based runtime instruction trace pipeline.
- **Defect 3 (AC-16):** No shell test for preset definitions (all four preset names + default).
- **Defect 4 (AC-17):** No test for per-group toggle override syntax.
- **Defect 5 (AC-18):** No test for sequential full-preset execution order or cross-preset inline dedup.
- **Defect 11 (AC-08/AC-18):** Dedup bypass for single-agent preset waves has no test.

### Significant

- **Defect 2 (AC-08/AC-14):** Retrospective merge-count metric and merge policy coverage absent from shell tests.
- **Defect 6 (AC-20):** Respawn gating shell test does not cover the 5-repetition cap.
- **Defect 7 (AC-03):** "Identical payload ordering" grep pattern too vague.
- **Defect 8 (AC-03):** Agent-name presence check does not verify agents appear in spawn context.
- **Defect 12 (AC-20):** Merged-sighting respawn credit rule has no test.

### Gaps

- **Defect 9 (AC-06/AC-07):** test-code-review-skill.sh threshold update not identified.
- **Defect 10 (AC-13/fbk-improve):** test-improvement-skill.sh and test-improvement-integration.sh not listed as impacted.
- **Defect 13:** No test verifies new detection targets assigned to correct group (Group 7 specifically).
- **Defect 14:** No test verifies dedup-to-Challenger handoff (deduplicated list, not raw).
- **Defect 15:** fbk-improve ↔ retrospective metrics is an undeclared integration seam.

## Threat Model Determination

**Security-relevant characteristics:** This feature changes how code review agents are spawned and orchestrated. It does not introduce new trust boundaries, handle user data, add external API calls, or modify auth/access control. The pipeline reviews code but does not execute it. Detection targets are static text, not executable. The preset system adds user-facing selection but no new data flows.

**Decision:** No threat model needed. No new trust boundaries, no data handling changes, no external API interaction. Pipeline reviews code but does not execute it.

## Testing Strategy Summary

| Category | Status |
|----------|--------|
| New tests needed | 20 shell tests in spec; 5+ additional needed (AC-02, AC-16, AC-17, AC-18, dedup bypass) |
| Existing tests impacted | 18 identified in spec; 2+ additional (test-code-review-skill.sh, test-code-review-guide-extensions.sh) |
| Test infrastructure changes | None needed |
