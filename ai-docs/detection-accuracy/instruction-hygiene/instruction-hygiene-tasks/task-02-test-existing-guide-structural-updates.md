---
id: task-02
type: test
wave: 1
covers: [AC-01, AC-09]
files_to_modify:
  - tests/sdl-workflow/test-code-review-guide-extensions.sh
  - tests/sdl-workflow/test-code-review-structural.sh
completion_gate: "Test 3 redirect passes immediately (quality-detection.md already contains 'dead infrastructure'); Test 23 threshold >= 14 fails pre-implementation (expected, current file has 13 items)"
---

## Objective

Updates 2 existing tests across 2 test files to reflect instruction hygiene changes: removed dead infrastructure subsection from `code-review-guide.md` and updated checklist item count threshold.

## Context

The instruction hygiene spec removes the "Dead and disconnected infrastructure" subsection from `code-review-guide.md` (detection targets belong in detection target documents, not the behavioral comparison methodology section). It also raises the checklist item count from 13 to 14 (split of item 12).

Both test files use the same TAP format convention with `ok`/`not_ok` helpers.

## Instructions

1. In `test-code-review-guide-extensions.sh`, update Test 3 (lines ~42-46): redirect the assertion from `$GUIDE` to `$PROJECT_ROOT/assets/fbk-docs/fbk-design-guidelines/quality-detection.md`. Add a `QUALITY` variable at the top alongside the existing `GUIDE` variable: `QUALITY="$PROJECT_ROOT/assets/fbk-docs/fbk-design-guidelines/quality-detection.md"`. Change the grep target from `$GUIDE` to `$QUALITY`. Update the test description to `quality-detection.md contains dead infrastructure check`. Completion: Test 3 greps `$QUALITY` for `dead infrastructure`.

2. In `test-code-review-structural.sh`, update Test 23 (lines ~246-251): change the threshold from `>= 11` to `>= 14` in both the condition and the test description. Completion: `grep -q '>= 14' tests/sdl-workflow/test-code-review-structural.sh` succeeds.

## Files to create/modify

- `tests/sdl-workflow/test-code-review-guide-extensions.sh` (modify)
- `tests/sdl-workflow/test-code-review-structural.sh` (modify)

## Test requirements

This is a test task. Tests being updated:
- `test-code-review-guide-extensions.sh` Test 3: redirected to `quality-detection.md` — passes now (quality-detection.md already contains "dead infrastructure"), passes post-implementation
- `test-code-review-structural.sh` Test 23: threshold `>= 14` — will fail pre-implementation (current file has 13 items), passes post-implementation (14 items)

## Acceptance criteria

- AC-01: Dead infrastructure detection target assertion redirected to its canonical location (`quality-detection.md`)
- AC-09: Checklist item count threshold updated to 14

## Model

Haiku

## Wave

Wave 1
