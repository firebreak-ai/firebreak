---
id: task-01
type: test
wave: 1
covers: [AC-01, AC-04, AC-09]
files_to_modify:
  - tests/sdl-workflow/test-detection-scope.sh
completion_gate: "tests updated; removed tests gone; redirected and threshold tests compile and fail pre-implementation (expected); severity ordering test passes"
---

## Objective

Updates 6 existing tests in `test-detection-scope.sh` to reflect instruction hygiene changes: redirected assertions, removed tests, and updated thresholds.

## Context

The instruction hygiene spec moves detection heuristics from `existing-code-review.md` to `quality-detection.md`, removes duplicates, and splits checklist item 12 into two items (raising the item count from 13 to 14). Six tests in `test-detection-scope.sh` assert on the pre-change state and must be updated.

The test file uses TAP format with `ok`/`not_ok` helper functions, sequential test numbering, and `grep` assertions against file paths stored in shell variables (`$CHECKLIST`, `$QUALITY`, `$EXISTING`).

## Instructions

1. In `test-detection-scope.sh`, update Test 1 (line ~30): change the threshold from `>= 11` to `>= 14` in both the condition and the test description. Completion: `grep -q '>= 14' tests/sdl-workflow/test-detection-scope.sh` succeeds.

2. Update Test 15 (line ~129): change the assertion target from `$EXISTING` to `$QUALITY`. Update the test description from `existing-code-review.md contains "dual-path" keyword` to `quality-detection.md contains "dual-path" keyword`. Completion: Test 15 greps `$QUALITY` for `dual.path`.

3. Remove three tests entirely, identified by their assertion content (not by number, since numbers shift during editing):
   - The test asserting `sentinel value` against `$EXISTING` — superseded by existing test asserting `sentinel` against `$CHECKLIST`
   - The test asserting `string-based error` against `$EXISTING` — superseded by existing test asserting on `$CHECKLIST`
   - The test asserting `dead infrastructure` against `$EXISTING` — superseded by existing test asserting on `$QUALITY`
   Completion: `grep -c 'EXISTING' tests/sdl-workflow/test-detection-scope.sh` returns 0 for these three assertion patterns.

4. Update the test asserting `string alignment|test.production` against `$EXISTING`: change target from `$EXISTING` to `$QUALITY`. Update description to reference `quality-detection.md`. Completion: the assertion targets `$QUALITY`.

5. Renumber all remaining tests sequentially. The severity ordering test (formerly last) becomes the final test. Update `$TOTAL` to match the new count.

6. Update the summary comment and test count. After changes, the file should have 17 tests (was 20, removed 3). Verify the final test number matches `$TOTAL`. Completion: run `bash tests/sdl-workflow/test-detection-scope.sh` and confirm all tests pass against current file state (the `>= 14` threshold will fail pre-implementation, which is expected).

## Files to create/modify

- `tests/sdl-workflow/test-detection-scope.sh` (modify)

## Test requirements

This is a test task. Tests being updated:
- Test 1: threshold `>= 14` (was `>= 11`) — will fail pre-implementation (current file has 13 items), passes post-implementation (14 items)
- Test 15: redirected to `$QUALITY` for `dual-path` — will fail pre-implementation (quality-detection.md lacks this section), passes post-implementation
- Test 16 (was 17): redirected to `$QUALITY` for `test-production` — will fail pre-implementation, passes post-implementation
- Tests 16, 18, 19 removed (sentinel, string-based error, dead infrastructure on `$EXISTING`) — no longer relevant
- Test 17 (was 20): unchanged severity ordering test — passes now and post-implementation

## Acceptance criteria

- AC-01, AC-09: Test 1 threshold reflects 14-item checklist
- AC-04: Tests 15-16 redirect promoted heuristic assertions to `quality-detection.md`; removed tests no longer assert on `existing-code-review.md` for canonicalized targets

## Model

Haiku

## Wave

Wave 1
