---
id: T-03
type: implementation
wave: 2
covers: ["AC-01", "AC-02", "AC-06", "AC-11"]
files_to_modify: ["../../home/dot-claude/agents/test-reviewer.md"]
test_tasks: ["T-02"]
completion_gate: "test-reviewer.md contains two-tier enforcement model with 5 criteria, override mechanism, corrective spec guidance, CP2 UV-step fidelity check, structured override output fields, and checkpoint applicability rules"
---

## Objective

Updates the test reviewer agent definition with the two-tier enforcement model, five evaluation criteria, override mechanism, corrective spec guidance, CP2 UV-step fidelity check, and structured output fields for metric capture.

## Context

The current test reviewer at `home/dot-claude/agents/test-reviewer.md` has 5 checkpoints but no criteria for test-level adequacy, behavioral completeness, silent failure detection, integration seam coverage, or seam declaration completeness. Phase 1.5 adds a two-tier enforcement model: Tier 1 (silent failure detection, non-overridable) and Tier 2 (test-level adequacy, behavioral completeness, integration seam coverage, seam declaration completeness — overridable with structured rationale). The reviewer must also handle corrective specs where diagnostic tests already exist.

## Instructions

1. After the existing "Context isolation" section and before "Checkpoint 1", add a new section "## Evaluation criteria" containing the two-tier model:

2. **Tier 1 — Mechanical (non-overridable)**: Add criterion 1 (silent failure detection). Flag any test whose sole assertion is error-absence. At CP1, flag test descriptions. At CP3, flag test implementations.

3. **Tier 2 — Structured judgment (overridable)**: Add criteria 2-5:
   - Criterion 2: Test-level adequacy. Flag based on runtime-dependent indicators (Canvas/WebGL, Web Audio, real DOM geometry, real network I/O, real filesystem). Reviewer cites which indicator triggered the flag.
   - Criterion 3: Behavioral completeness. For each UV step, name the test and describe the failure mode. Include corrective variants: existing failing test ("currently fails because [bug], fix will make it pass by [mechanism]") and existing passing test ("currently passes, must continue to pass after fix").
   - Criterion 4: Integration seam coverage. Verify declared seams have e2e test coverage.
   - Criterion 5: Seam declaration completeness. Evaluate whether the spec's technical approach describes module interactions missing from the seam declaration.

4. Add "## Override mechanism" section: Tier 1 has no override. Tier 2 overrides require rationale from defined categories: "Covered by existing test at [path]", "Seam not testable in current infrastructure", "Behavior verified by [other mechanism]". Freeform rejected. Reviewer validates rationale legitimacy.

5. Add "## Override output format" section: The reviewer's output includes structured fields for each finding — criterion name, severity (blocking/overridden), rationale category (if overridden), and the "show your work" mapping. This enables override frequency tracking for AC-11.

6. Update Checkpoint 1 to state: "Apply all five evaluation criteria against the testing strategy, user verification steps, and integration seam declarations."

7. Update Checkpoint 2 to add: "Verify every user verification step from the spec has at least one corresponding test task in the breakdown. This is a fidelity check — did the breakdown translate the UV-step-to-test mapping from the approved testing strategy?"

8. Update Checkpoint 3 to state: "Tier 1 criteria apply against test implementations. Tier 2 criteria are not re-evaluated at CP3."

## Files to create/modify

Modify:
- `home/dot-claude/agents/test-reviewer.md`

## Test requirements

Semi-manual: After editing, run the deficient-spec.md fixture through the updated test reviewer at CP1. Confirm Tier 1 (silent failure) and Tier 2 (test-level adequacy, seam completeness) criteria fire. Run the well-formed-spec.md and confirm it passes.

## Acceptance criteria

- AC-01: Tier 1 silent failure detection present and marked non-overridable
- AC-02: Tier 2 criteria present with "show your work" output format, including corrective variants
- AC-06: CP2 UV-step fidelity check present
- AC-11: Structured override output fields present enabling metric computation

## Model

Sonnet

## Wave

Wave 2
