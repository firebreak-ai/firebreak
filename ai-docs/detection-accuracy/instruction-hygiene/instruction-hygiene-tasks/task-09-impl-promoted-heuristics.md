---
id: task-09
type: implementation
wave: 2
covers: [AC-04, AC-10, AC-11]
files_to_modify:
  - assets/fbk-docs/fbk-design-guidelines/quality-detection.md
test_tasks: [task-03, task-04, task-07]
completion_gate: "task-03, task-04, task-07 tests pass"
---

## Objective

Splits the "Silent error and context discard" section in `quality-detection.md` into two separate sections, and adds three promoted detection heuristics from `existing-code-review.md` in the standard structural target format.

## Context

`quality-detection.md` currently has a combined section "Silent error and context discard" (lines 43-45) that addresses two distinct concerns. This must be split into "Silent error discard" and "Context discard" as separate `## ` sections. Additionally, three heuristics currently trapped in `existing-code-review.md` (which agents never see in the spawn prompt) must be promoted into `quality-detection.md` using the established format: imperative statement + "Detect this when..." heuristic. The file currently has 8 occurrences of "Detect this when" — after changes it must have at least 11.

## Instructions

1. Replace the section heading `## Silent error and context discard` (line 43) and its body (lines 44-45) with two separate sections:

   ```
   ## Silent error discard

   Flag code that discards errors without logging or propagating them. Detect this when an error return is assigned to `_` or ignored without a comment justifying the discard.

   ## Context discard

   Flag code that replaces a caller-provided context with a fresh background context, discarding cancellation signals, deadlines, or trace propagation. Detect this when a function that receives a context parameter constructs a new context instead of forwarding the caller's.
   ```

   Completion: `grep -q '## Silent error discard' quality-detection.md` AND `grep -q '## Context discard' quality-detection.md` both succeed. The old combined heading `## Silent error and context discard` must not appear.

2. After the existing `## String-based type discrimination` section (the last current section), add three new sections:

   ```
   ## Dual-path verification

   Flag operations that have both a bulk path and an incremental path for the same state. Detect this when the bulk path (initial load, full sync) sets fields that the incremental path (event-driven update, delta sync) ignores, or vice versa — this creates state divergence that manifests only under specific execution sequences.

   ## Test-production string alignment

   Flag test assertions that match on string values absent from the production code being tested. Detect this when a test asserts on an error message, status string, or format pattern that does not appear in the production module's source — these are phantom assertions that pass trivially because the production code never produces the matched string.

   ## Dead code after field or function removal

   Flag guards, conditionals, and logging branches that reference values from a removed field or changed function signature. Detect this when a field removal or parameter change leaves downstream checks on the removed value — the check is reachable code that can never evaluate to true.
   ```

   Completion: `grep -q '## Dual-path verification' quality-detection.md` AND `grep -q '## Test-production string alignment' quality-detection.md` AND `grep -q '## Dead code after field' quality-detection.md` all succeed. Each new section must contain "Detect this when".

3. Verify the total "Detect this when" count is >= 11: `grep -c 'Detect this when' quality-detection.md` returns 11 or more.

## Files to create/modify

- `assets/fbk-docs/fbk-design-guidelines/quality-detection.md` (modify)

## Test requirements

Tests from task-03 (AC-11 section split: "Silent error discard" and "Context discard" as separate headings), task-04 (AC-04: three promoted heuristic headings present with "Detect this when" format, count >= 11), and task-07 (coverage: silent error discard, context discard, dual-path verification, test-production string, dead code after field in agent-facing docs) must pass after this task.

## Acceptance criteria

- AC-11: "Silent error and context discard" is split into "Silent error discard" and "Context discard" as separate `## ` sections
- AC-04: `quality-detection.md` contains "Dual-path verification", "Test-production string alignment", and "Dead code after field or function removal" sections in standard format (imperative + "Detect this when...")

## Model

Haiku

## Wave

Wave 2
