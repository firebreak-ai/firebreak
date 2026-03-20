---
id: T-07
type: implementation
wave: 2
covers: ["AC-07", "AC-09"]
files_to_modify: ["../../home/dot-claude/docs/sdl-workflow/implementation-guide.md"]
test_tasks: ["T-02"]
completion_gate: "implementation-guide.md contains per-task readiness check section (4 items with test-task skip and contract-staleness check), inter-wave baseline-snapshot regression check section (capture, check, final verification), and explicit sequencing statement"
---

## Objective

Updates the implementation guide with per-task readiness checks, inter-wave baseline-snapshot regression checks, and explicit sequencing between the two.

## Context

The current implementation guide at `home/dot-claude/docs/sdl-workflow/implementation-guide.md` has per-wave verification that runs the test suite, but no per-task readiness check and no baseline-snapshot model for regression detection. The greenfield test showed that agents can proceed on wrong assumptions about prior-wave outputs, and the corrective workflow needs a regression model that automatically excludes expected-failing diagnostic tests.

## Instructions

1. Add a "Per-task readiness check" section. Before writing code, each implementation agent verifies:
   - Item 1: Prior-wave files exist (every file in interface contracts created by a prior wave is present)
   - Item 2: Tests compile — for implementation tasks, paired test task's tests compile (should fail but compile). Test tasks skip this item.
   - Item 3: Build succeeds
   - Item 4: Contract staleness check — when interface contracts reference a file modified by a prior wave (detectable from git diff between baseline and current state), re-read the file and verify the specific conventions cited still hold. Targeted check, not a full survey.
   - On failure: report the mismatch without attempting implementation.

2. Add an "Inter-wave regression check" section using the baseline-snapshot model:
   - **Baseline capture**: Before Wave 1, run the full test suite. Capture results to `ai-docs/<feature>/baseline-snapshot.json` — test identifiers (file path + test name) with pass/fail status. Only passing tests enter the baseline.
   - **Inter-wave check**: After each wave, run the full suite and diff against baseline. Any test that was pass→fail is a regression. Wave does not advance.
   - **Final verification**: After the last wave, run the full suite. All tests (including new ones) must pass.

3. Add an explicit sequencing statement: "The inter-wave regression check runs between waves as a wave-advancement gate. The readiness check runs per-task within a wave as a pre-implementation gate. Sequence: Wave N completes → baseline regression check → Wave N+1 starts → each task in N+1 runs readiness check before coding."

4. Follow the existing document's structure and format. Place new sections where they integrate naturally with the existing wave execution flow.

## Files to create/modify

Modify:
- `home/dot-claude/docs/sdl-workflow/implementation-guide.md`

## Test requirements

Semi-manual: During brownfield testing, confirm: (a) baseline snapshot is captured before Wave 1, (b) inter-wave regression check runs between waves, (c) readiness check runs per-task.

## Acceptance criteria

- AC-07: Readiness check section present with 4 items, test-task skip, and contract-staleness check
- AC-09: Baseline-snapshot model present with capture, inter-wave check, and final verification

## Model

Sonnet

## Wave

Wave 2
