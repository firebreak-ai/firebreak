---
id: task-08
type: implementation
wave: 2
covers: [AC-01, AC-02, AC-03, AC-08, AC-09, AC-10, AC-11]
files_to_modify:
  - assets/fbk-docs/fbk-sdl-workflow/ai-failure-modes.md
test_tasks: [task-01, task-02, task-03, task-07]
completion_gate: "task-01, task-02, task-03, task-07 tests pass"
---

## Objective

Rewrites `ai-failure-modes.md` to resolve the scope contradiction, deduplicate items 7/10/11 as summaries with quality-detection.md references, and split item 12 into two separately-actionable items.

## Context

`ai-failure-modes.md` currently has 13 numbered items and a conditional scope instruction on line 1 that contradicts the orchestrator's unconditional injection. Items 7 (dead infrastructure), 10 (context bypass), and 11 (string-based error classification) duplicate definitions that exist in `quality-detection.md`. Item 12 combines two distinct detection concerns (incoherent fixtures and mock permissiveness). All changes are to a single markdown file. The file must remain self-contained — each summary item must include a detection heuristic trigger so the Detector can detect the pattern from the summary alone.

## Instructions

1. Replace the entire line 1 (the opening paragraph beginning "Use this checklist when reviewing code without specs...") with:

   ```
   Apply these detection targets to all code reviews.
   ```

   Completion: `grep -q 'Apply these detection targets to all code reviews' ai-failure-modes.md` succeeds AND `! grep -q 'When specs are available' ai-failure-modes.md` succeeds.

2. Replace item 7 (currently lines 17-18, the full "Dead infrastructure" definition) with:

   ```
   7. **Dead infrastructure** — Code constructs, initializes, or declares components never invoked in the application's runtime path. Check for constructors or factory calls whose return values are assigned but never passed to any consumer (full heuristic in quality-detection.md).
   ```

   Completion: `grep -A2 '^7\.' ai-failure-modes.md | grep -q 'quality-detection'` succeeds.

3. Replace item 10 (currently line 23, the full "Context bypass" definition) with:

   ```
   10. **Context bypass** — Functions replace a caller-provided context with a fresh background context, discarding cancellation signals, deadlines, or trace propagation. Check for background-context constructors in functions that receive a context parameter (full heuristic in quality-detection.md).
   ```

   Completion: `grep -A2 '^10\.' ai-failure-modes.md | grep -q 'quality-detection'` succeeds.

4. Replace item 11 (currently line 25, the full "String-based error classification" definition) with:

   ```
   11. **String-based error classification** — Error handling branches on string content instead of typed errors, error codes, or sentinel values. Check for string matching operations applied to error messages or type discriminator strings in conditional expressions (full heuristic in quality-detection.md).
   ```

   Completion: `grep -A2 '^11\.' ai-failure-modes.md | grep -q 'quality-detection'` succeeds.

5. Replace item 12 (currently line 26, the combined "Semantically incoherent test fixtures" definition) with two items:

   ```
   12. **Semantically incoherent test fixtures** — Test input data satisfies the type system but violates domain constraints, producing false-passing scenarios. Check for test fixtures where related fields should be consistent by domain rules but are set independently with mismatched values.
   13. **Mock permissiveness masking constraints** — Tests pass because mocks do not validate constraints the production code relies on. Check for mocks that accept any input where the production dependency enforces domain rules (e.g., type discriminators, referential integrity, value ranges).
   ```

   Completion: `grep -A1 '^12\.' ai-failure-modes.md | grep -qi 'semantically incoherent'` AND `grep -A1 '^13\.' ai-failure-modes.md | grep -qi 'mock permissiveness'` both succeed.

6. Renumber current item 13 ("Dead conditional guards") to item 14. The item content is unchanged — only the number changes.

   Completion: `grep -c '^[0-9]\+\.' ai-failure-modes.md` returns 14.

## Files to create/modify

- `assets/fbk-docs/fbk-sdl-workflow/ai-failure-modes.md` (modify)

## Test requirements

Tests from task-01 (threshold >= 14), task-02 (threshold >= 14), task-03 (scope, dedup references, item split), and task-07 (coverage: dead infrastructure, context bypass, string-based error, semantically incoherent, mock permissiveness, dead conditional in agent-facing docs) must pass after this task.

## Acceptance criteria

- AC-03: Line 1 is an unconditional imperative with no conditional scope instruction
- AC-01: Item 7 is a summary with detection trigger and quality-detection.md reference
- AC-02: Item 11 is a summary with detection trigger and quality-detection.md reference
- AC-11: Item 10 is a summary with detection trigger and quality-detection.md reference
- AC-09: File contains 14 numbered items; item 12 is "Semantically incoherent test fixtures"; item 13 is "Mock permissiveness masking constraints"; item 14 is "Dead conditional guards"

## Model

Haiku

## Wave

Wave 2
