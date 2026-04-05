---
id: task-03
type: test
wave: 1
covers: [AC-03, AC-01, AC-02, AC-09, AC-11]
files_to_create:
  - tests/sdl-workflow/test-instruction-hygiene-scope.sh
completion_gate: "tests compile and fail before implementation"
---

## Objective

Creates a new shell test file verifying the scope resolution, deduplication references, checklist item split, and section split changes to `ai-failure-modes.md` and `quality-detection.md`.

## Context

The instruction hygiene spec makes these changes:
- Removes the conditional scope instruction from `ai-failure-modes.md` line 1, replacing with an unconditional imperative (AC-03)
- Rewrites items 7, 10, 11 as summaries referencing `quality-detection.md` (AC-01, AC-02, AC-11)
- Splits item 12 into items 12 (semantically incoherent fixtures) and 13 (mock permissiveness), renumbers old 13 to 14 (AC-09)
- Splits "Silent error and context discard" into two separate sections in `quality-detection.md` (AC-11)

Follow the TAP format convention from existing test files: `set -uo pipefail`, `PASS`/`FAIL`/`TOTAL` counters, `ok`/`not_ok` helpers, `TAP version 13` header, numbered test comments, summary block.

## Instructions

1. Create `tests/sdl-workflow/test-instruction-hygiene-scope.sh` with the standard boilerplate (shebang, set flags, counters, PROJECT_ROOT, ok/not_ok helpers, TAP header). Define variables:
   - `CHECKLIST="$PROJECT_ROOT/assets/fbk-docs/fbk-sdl-workflow/ai-failure-modes.md"`
   - `QUALITY="$PROJECT_ROOT/assets/fbk-docs/fbk-design-guidelines/quality-detection.md"`

2. Add Test 1 (AC-03 positive): assert `ai-failure-modes.md` line 1 area contains "Apply these detection targets" using `grep -qi 'Apply these detection targets' "$CHECKLIST"`.

3. Add Test 2 (AC-03 negative): assert `ai-failure-modes.md` does NOT contain "When specs are available, use quality-detection.md instead" using `! grep -qi 'When specs are available, use quality-detection.md instead' "$CHECKLIST"`. Pass condition is absence.

4. Add Test 3 (AC-01): assert `ai-failure-modes.md` item 7 references `quality-detection.md`. Use `grep -A2 '^7\.' "$CHECKLIST" | grep -qi 'quality-detection'`.

5. Add Test 4 (AC-02): assert `ai-failure-modes.md` item 11 references `quality-detection.md`. Use `grep -A2 '^11\.' "$CHECKLIST" | grep -qi 'quality-detection'`.

6. Add Test 5 (AC-11 dedup): assert `ai-failure-modes.md` item 10 references `quality-detection.md`. Use `grep -A2 '^10\.' "$CHECKLIST" | grep -qi 'quality-detection'`.

7. Add Test 6 (AC-09 count): assert `ai-failure-modes.md` contains exactly 14 numbered items. Use `grep -cE '^[0-9]+\.' "$CHECKLIST"` and test `[ "$count" -eq 14 ]`.

8. Add Test 7 (AC-09 item 12): assert item 12 contains "Semantically incoherent". Use `grep -A1 '^12\.' "$CHECKLIST" | grep -qi 'semantically incoherent'`.

9. Add Test 8 (AC-09 item 13): assert item 13 contains "Mock permissiveness". Use `grep -A1 '^13\.' "$CHECKLIST" | grep -qi 'mock permissiveness'`.

10. Add Test 9 (AC-11 split): assert `quality-detection.md` contains "Silent error discard" as a section heading. Use `grep -qi '## Silent error discard' "$QUALITY"`.

11. Add Test 10 (AC-11 split): assert `quality-detection.md` contains "Context discard" as a section heading. Use `grep -qi '## Context discard' "$QUALITY"`.

12. Add the standard summary block (echo total, pass count, exit code). Make the file executable with `chmod +x`.

## Files to create/modify

- `tests/sdl-workflow/test-instruction-hygiene-scope.sh` (create)

## Test requirements

New shell tests (10 tests total):
- Tests 1-2: AC-03 scope resolution (positive and negative)
- Tests 3-5: AC-01, AC-02, AC-11 dedup references in items 7, 10, 11
- Tests 6-8: AC-09 item count and split verification
- Tests 9-10: AC-11 section split in quality-detection.md

All tests should fail before implementation (current state has conditional scope, no quality-detection.md references in items 7/10/11, 13 items not 14, combined silent error section).

## Acceptance criteria

- AC-03: Tests verify unconditional scope and absence of conditional instruction
- AC-01: Test verifies item 7 references quality-detection.md
- AC-02: Test verifies item 11 references quality-detection.md
- AC-09: Tests verify 14-item count and correct items 12/13 content
- AC-11: Tests verify separate section headings and item 10 dedup reference

## Model

Haiku

## Wave

Wave 1
