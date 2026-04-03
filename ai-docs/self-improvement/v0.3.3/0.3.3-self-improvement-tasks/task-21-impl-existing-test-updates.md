---
id: task-21
type: implementation
wave: 5
covers: [AC-09, AC-36, AC-38, AC-55, AC-56, AC-57]
files_to_modify:
  - tests/sdl-workflow/test-code-review-structural.sh
test_tasks: [task-09]
completion_gate: "all tests in test-code-review-structural.sh pass against implemented files"
---

## Objective

Ensures all tests in `test-code-review-structural.sh` pass after 0.3.3 implementation: verifies task-09's 4 test updates are correct and fixes 2 additional regression-causing tests (Tests 16 and 18) that the spec's impact analysis missed.

## Context

Task-09 (Wave 1) updated 4 tests to fail-before-implementation. By Wave 5, all implementation tasks have landed. This task ensures those updated tests pass, and also fixes 2 additional tests that break due to the category-to-type migration:

**Tests updated by task-09 (verify they pass):**
- **Test 5**: Asserts Detector tools = `Read, Grep, Glob` without Bash (AC-09).
- **Test 17**: Asserts type values `behavioral`, `structural`, `test-integrity`, `fragile` (AC-57).
- **Test 23**: Floor threshold raised to `>= 12` for checklist items.
- **Test 24**: Checks for `bare literal` (AC-36) and `non-enforcing` (AC-38) keywords.

**Tests NOT updated by task-09 that will regress (fix in this task):**
- **Test 16** (line 168-181): Checks finding format has 8 fields, including `category`. After migration (AC-56), `Category:` is replaced by `Type:` + `Severity:`. The `category=$(grep -ci 'category' "$GUIDE")` check will return 0, failing the test. Fix: replace the `category` check with a `type` check (the word "type" will appear in the finding format's `Type:` field).
- **Test 18** (line 194-205): Checks sighting format has 6 fields, including `sighting_category`. After migration (AC-55), `Category:` is replaced by `Type:` + `Severity:`. Fix: replace the `sighting_category` check with a `sighting_type` check.

Current test file state for Test 16 (line 172): `category=$(grep -ci 'category' "$GUIDE" 2>/dev/null || true)`
Current test file state for Test 18 (line 197): `sighting_category=$(grep -ci 'category' "$GUIDE" 2>/dev/null || true)`

## Instructions

1. Read the test file and verify task-09's updates to Tests 5, 17, 23, 24 are in place.

2. **Update Test 16** (finding format fields):
   - Replace `category=$(grep -ci 'category' "$GUIDE" 2>/dev/null || true)` with `type_field=$(grep -ci 'Type:' "$GUIDE" 2>/dev/null || true)`.
   - In the condition, replace `[ "$category" -gt 0 ]` with `[ "$type_field" -gt 0 ]`.
   - In the `not_ok` diagnostic string, replace `category=$category` with `type_field=$type_field`.

3. **Update Test 18** (sighting format fields):
   - Replace `sighting_category=$(grep -ci 'category' "$GUIDE" 2>/dev/null || true)` with `sighting_type=$(grep -ci 'Type:' "$GUIDE" 2>/dev/null || true)`.
   - In the condition, replace `[ "$sighting_category" -gt 0 ]` with `[ "$sighting_type" -gt 0 ]`.
   - In the `not_ok` diagnostic string, replace `sighting_category=$sighting_category` with `sighting_type=$sighting_type`.

4. Run the full test file. All 24 tests must pass. If any test fails due to wording mismatches between grep patterns and actual implementation text, adjust the grep pattern to match the implementation (implementation is authoritative).

## Files to create/modify

- `tests/sdl-workflow/test-code-review-structural.sh` (modify)

## Test requirements

All 24 tests in the file must pass against the implemented target files. The 6 directly updated tests (5, 16, 17, 18, 23, 24) verify the 0.3.3 changes. The remaining 18 tests must not regress.

## Acceptance criteria

- AC-09: Test 5 passes — Detector tools list contains Read, Grep, Glob without Bash.
- AC-55: Test 18 passes — sighting format uses Type field (not Category).
- AC-56: Test 16 passes — finding format uses Type field (not Category).
- AC-57: Test 17 passes — guide documents type values behavioral, structural, test-integrity, fragile.
- AC-36: Test 24 passes — checklist contains "bare literal" keyword.
- AC-38: Test 24 passes — checklist contains "non-enforcing" keyword.
- No regressions in any other tests in the file.

## Model

Sonnet

## Wave

Wave 5
