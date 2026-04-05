---
id: task-04
type: test
wave: 1
covers: [AC-04]
files_to_create:
  - tests/sdl-workflow/test-instruction-hygiene-heuristics.sh
completion_gate: "tests compile and fail before implementation"
---

## Objective

Creates a new shell test file verifying the 3 promoted heuristics appear in `quality-detection.md` in standard format and all 6 detection heuristic sections are removed from `existing-code-review.md`.

## Context

The instruction hygiene spec promotes 3 heuristics from `existing-code-review.md` to `quality-detection.md` and removes all 6 detection heuristic sections from `existing-code-review.md`. The promoted heuristics must use the standard format (imperative + "Detect this when..." heuristic). The 6 removed sections are: dual-path verification, sentinel value confusion, test-production string alignment, string-based error classification, dead infrastructure detection, dead code after field or function removal.

Follow the TAP format convention from existing test files.

## Instructions

1. Create `tests/sdl-workflow/test-instruction-hygiene-heuristics.sh` with the standard boilerplate. Define variables:
   - `QUALITY="$PROJECT_ROOT/assets/fbk-docs/fbk-design-guidelines/quality-detection.md"`
   - `EXISTING="$PROJECT_ROOT/assets/skills/fbk-code-review/references/existing-code-review.md"`

2. Add Test 1 (AC-04 presence): assert `quality-detection.md` contains section heading "Dual-path verification". Use `grep -qi '## Dual-path verification' "$QUALITY"`.

3. Add Test 2 (AC-04 presence): assert `quality-detection.md` contains section heading "Test-production string alignment". Use `grep -qi '## Test-production string alignment' "$QUALITY"`.

4. Add Test 3 (AC-04 presence): assert `quality-detection.md` contains section heading matching "Dead code after field" (partial match). Use `grep -qi '## Dead code after field' "$QUALITY"`.

5. Add Test 4 (AC-04 format): assert each promoted section contains "Detect this when". Extract text between each promoted section heading and the next `## ` heading, and grep for "Detect this when". Use a loop or 3 separate checks — one per section. Simplest approach: `grep -c 'Detect this when' "$QUALITY"` and assert the count increased by 3 (current count is 8, post-change should be >= 11). Use `[ "$count" -ge 11 ]`.

6. Add Test 5 (AC-04 removal): assert `existing-code-review.md` does NOT contain "Dual-path verification" as a heading. Use `! grep -qi '## Dual-path verification' "$EXISTING"`.

7. Add Test 6 (AC-04 removal): assert `existing-code-review.md` does NOT contain "Sentinel value confusion" as a heading. Use `! grep -qi '## Sentinel value confusion' "$EXISTING"`.

8. Add Test 7 (AC-04 removal): assert `existing-code-review.md` does NOT contain "Test-production string alignment" as a heading. Use `! grep -qi '## Test-production string alignment' "$EXISTING"`.

9. Add Test 8 (AC-04 removal): assert `existing-code-review.md` does NOT contain "String-based error classification" as a heading. Use `! grep -qi '## String-based error classification' "$EXISTING"`.

10. Add Test 9 (AC-04 removal): assert `existing-code-review.md` does NOT contain "Dead infrastructure detection" as a heading. Use `! grep -qi '## Dead infrastructure detection' "$EXISTING"`.

11. Add Test 10 (AC-04 removal): assert `existing-code-review.md` does NOT contain "Dead code after field" as a heading. Use `! grep -qi '## Dead code after field' "$EXISTING"`.

12. Add the standard summary block. Make the file executable.

## Files to create/modify

- `tests/sdl-workflow/test-instruction-hygiene-heuristics.sh` (create)

## Test requirements

New shell tests (10 tests total):
- Tests 1-3: promoted heuristic section headings exist in quality-detection.md (will fail pre-implementation)
- Test 4: "Detect this when" count >= 11 in quality-detection.md (will fail pre-implementation, current count is 8)
- Tests 5-10: 6 detection heuristic section headings absent from existing-code-review.md (will fail pre-implementation, sections currently exist)

## Acceptance criteria

- AC-04: Tests verify promoted heuristics appear in standard format in quality-detection.md AND all 6 heuristic sections are removed from existing-code-review.md

## Model

Haiku

## Wave

Wave 1
