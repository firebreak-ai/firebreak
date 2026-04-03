---
id: task-01
type: test
wave: 1
covers: [AC-31, AC-32, AC-33, AC-34, AC-35, AC-36, AC-37, AC-38, AC-39, AC-40, AC-41, AC-42, AC-43, AC-44, AC-45, AC-46, AC-47, AC-48]
files_to_create:
  - tests/sdl-workflow/test-detection-scope.sh
completion_gate: "tests compile and fail before implementation"
---

## Objective

Creates `tests/sdl-workflow/test-detection-scope.sh` — a structural test suite validating that the detection scope expansion (ai-failure-modes.md items, quality-detection.md targets, existing-code-review.md instructions) contains all required content.

## Context

The 0.3.3 self-improvement cycle expands detection scope across three files:

- `ai-failure-modes.md` (5 current items, 7 additions = 12 total): AC-36 expands "magic numbers" to cover string bare literals. AC-38 expands "test name contradictions" to cover non-enforcing tests (empty gates, advisory assertions, unconditional skips). AC-37, AC-39, AC-40, AC-41, AC-42 add new checklist items.
- `quality-detection.md` (6 current targets, 5 additions = 11 total): AC-31 through AC-35 add new structural detection targets.
- `existing-code-review.md` (AC-43 through AC-48): 6 new instruction additions covering dual-path verification, sentinel value confusion, test-production string alignment, string-based error classification, dead infrastructure detection, and severity-ordered finding presentation.

Follow the TAP format and helper patterns from `tests/sdl-workflow/test-code-review-structural.sh`: `ok`/`not_ok` helpers, `$PROJECT_ROOT` resolution via `SCRIPT_DIR`, `PASS`/`FAIL`/`TOTAL` counters, `echo "TAP version 13"` header, and summary footer with exit code.

## Instructions

1. Create `tests/sdl-workflow/test-detection-scope.sh` with the shebang `#!/usr/bin/env bash` and `set -uo pipefail`.

2. Add the standard boilerplate from the existing test files:
   - `PASS=0`, `FAIL=0`, `TOTAL=0` counters.
   - `SCRIPT_DIR` and `PROJECT_ROOT` resolution.
   - File path variables:
     - `CHECKLIST="$PROJECT_ROOT/assets/fbk-docs/fbk-sdl-workflow/ai-failure-modes.md"`
     - `QUALITY="$PROJECT_ROOT/assets/fbk-docs/fbk-design-guidelines/quality-detection.md"`
     - `EXISTING="$PROJECT_ROOT/assets/skills/fbk-code-review/references/existing-code-review.md"`
   - `ok()` and `not_ok()` helper functions (copy exactly from `test-code-review-structural.sh`).
   - `echo "TAP version 13"` header.

3. Add the following tests in order:

   **Test 1: ai-failure-modes.md checklist item count >= 12 (AC-36 through AC-42)**
   Count numbered items matching `^[0-9]+\.` in `$CHECKLIST`. Assert count >= 12. The current file has 5 numbered items; after 7 additions (2 expansions of existing items + 5 new items), the total is 12. Use: `numbered=$(grep -cE '^[0-9]+\.' "$CHECKLIST" 2>/dev/null || true)` then `[ "$numbered" -ge 12 ]`.

   **Test 2: ai-failure-modes.md contains "bare literal" keyword (AC-36)**
   Grep case-insensitively for `bare literal` in `$CHECKLIST`. This verifies the "magic numbers" expansion to cover string bare literals. Use: `grep -qi 'bare literal' "$CHECKLIST"`.

   **Test 3: ai-failure-modes.md contains "dead infrastructure" keyword (AC-37)**
   Grep case-insensitively for `dead infrastructure` in `$CHECKLIST`. Use: `grep -qi 'dead infrastructure' "$CHECKLIST"`.

   **Test 4: ai-failure-modes.md contains "non-enforcing" keyword (AC-38)**
   Grep case-insensitively for `non-enforcing` in `$CHECKLIST`. This verifies the "test name contradictions" expansion. Use: `grep -qi 'non-enforcing' "$CHECKLIST"`.

   **Test 5: ai-failure-modes.md contains "comment-code drift" keyword (AC-39)**
   Grep case-insensitively for `comment.*code.*drift\|code.*comment.*drift` in `$CHECKLIST`. Use: `grep -qiE 'comment.*(code|behavior).*drift|drift.*(comment|code)' "$CHECKLIST"`.

   **Test 6: ai-failure-modes.md contains "zero-value sentinel" or "sentinel ambiguity" keyword (AC-40)**
   Grep case-insensitively for `sentinel` in `$CHECKLIST`. Use: `grep -qi 'sentinel' "$CHECKLIST"`.

   **Test 7: ai-failure-modes.md contains "context bypass" keyword (AC-41)**
   Grep case-insensitively for `context bypass` in `$CHECKLIST`. Use: `grep -qi 'context bypass' "$CHECKLIST"`.

   **Test 8: ai-failure-modes.md contains "string-based error" keyword (AC-42)**
   Grep case-insensitively for `string-based error` in `$CHECKLIST`. Use: `grep -qi 'string-based error' "$CHECKLIST"`.

   **Test 9: quality-detection.md detection target count >= 11 (AC-31 through AC-35)**
   Count level-2 headings (`^## `) in `$QUALITY`. Assert count >= 11. The current file has 6 `##` headings; after 5 additions, the total is 11. Use: `headings=$(grep -cE '^## ' "$QUALITY" 2>/dev/null || true)` then `[ "$headings" -ge 11 ]`.

   **Test 10: quality-detection.md contains "parallel collection" keyword (AC-31)**
   Grep case-insensitively for `parallel collection` in `$QUALITY`. Use: `grep -qi 'parallel collection' "$QUALITY"`.

   **Test 11: quality-detection.md contains "dead infrastructure" keyword (AC-32)**
   Grep case-insensitively for `dead infrastructure` in `$QUALITY`. Use: `grep -qi 'dead infrastructure' "$QUALITY"`.

   **Test 12: quality-detection.md contains "semantic drift" keyword (AC-33)**
   Grep case-insensitively for `semantic drift` in `$QUALITY`. Use: `grep -qi 'semantic drift' "$QUALITY"`.

   **Test 13: quality-detection.md contains "silent error" or "context discard" keyword (AC-34)**
   Grep case-insensitively for `silent error\|context discard` in `$QUALITY`. Use: `grep -qiE 'silent error|context discard' "$QUALITY"`.

   **Test 14: quality-detection.md contains "string-based type" keyword (AC-35)**
   Grep case-insensitively for `string-based type` in `$QUALITY`. Use: `grep -qi 'string-based type' "$QUALITY"`.

   **Test 15: existing-code-review.md contains "dual-path" keyword (AC-43)**
   Grep case-insensitively for `dual.path` in `$EXISTING`. Use: `grep -qiE 'dual.path' "$EXISTING"`.

   **Test 16: existing-code-review.md contains "sentinel value" keyword (AC-44)**
   Grep case-insensitively for `sentinel value` in `$EXISTING`. Use: `grep -qi 'sentinel value' "$EXISTING"`.

   **Test 17: existing-code-review.md contains "string alignment" or "test-production" keyword (AC-45)**
   Grep case-insensitively for `string alignment\|test-production\|test.*production.*string` in `$EXISTING`. Use: `grep -qiE 'string alignment|test.production' "$EXISTING"`.

   **Test 18: existing-code-review.md contains "string-based error" keyword (AC-46)**
   Grep case-insensitively for `string-based error` in `$EXISTING`. Use: `grep -qi 'string-based error' "$EXISTING"`.

   **Test 19: existing-code-review.md contains "dead infrastructure" keyword (AC-47)**
   Grep case-insensitively for `dead infrastructure` in `$EXISTING`. Use: `grep -qi 'dead infrastructure' "$EXISTING"`.

   **Test 20: existing-code-review.md contains severity ordering keyword (AC-48)**
   Grep case-insensitively for `severity\|critical first` in `$EXISTING`. Use: `grep -qiE 'severity|critical first' "$EXISTING"`.

4. Add the standard summary footer:
   ```
   echo ""
   echo "1..$TOTAL"
   echo "# $PASS/$TOTAL tests passed"
   if [ "$FAIL" -gt 0 ]; then
     echo "# FAIL $FAIL"
     exit 1
   fi
   exit 0
   ```

5. Make the file executable: the file must have `chmod +x` permissions (include a note in the file header or ensure the implementation agent sets this).

## Files to create/modify

- `tests/sdl-workflow/test-detection-scope.sh` (create)

## Test requirements

20 structural grep/count tests covering AC-31 through AC-48. All tests check markdown content in existing files. Tests must compile (bash syntax valid) and fail before implementation (the target keywords and item counts do not exist yet).

## Acceptance criteria

- AC-31 through AC-48: Each AC has at least one test asserting its keyword or count is present in the target file.
- All 20 tests produce TAP-format output.
- Running the script before implementation produces 20 "not ok" lines (all tests fail).

## Model

Haiku

## Wave

Wave 1
