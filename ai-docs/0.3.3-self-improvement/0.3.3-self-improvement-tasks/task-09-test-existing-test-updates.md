---
id: task-09
type: test
wave: 1
covers: [AC-09, AC-36, AC-38, AC-57]
files_to_modify:
  - tests/sdl-workflow/test-code-review-structural.sh
completion_gate: "tests compile and fail before implementation"
---

## Objective

Updates three tests in `tests/sdl-workflow/test-code-review-structural.sh` to reflect the 0.3.3 changes: Test 5 (Detector tools), Test 17 (category values migration), and Test 24 (checklist keywords). Also updates the Test 23 floor threshold.

## Context

The spec identifies four existing tests that are impacted by 0.3.3 changes:

1. **Test 5** (line 69-78): Asserts Detector tools field lists `Read, Grep, Glob, Bash`. AC-09 removes Bash. After implementation, this test must assert `Read, Grep, Glob` without Bash, and must assert Bash is absent.

2. **Test 17** (line 183-192): Asserts guide documents all 4 category values including `semantic-drift` and `nit`. After migration to two-axis system (AC-57), `semantic-drift` becomes `behavioral`, `nit` is removed from findings (excluded entirely), and `fragile` is added. The test must check for the 4 type values: `behavioral`, `structural`, `test-integrity`, `fragile`.

3. **Test 23** (line 246-252): Floor threshold `>= 5` for checklist items. After additions, total is 12. Threshold should be updated to `>= 12` to match the new expected count.

4. **Test 24** (line 254-269): Greps for `magic number` and `test name` keywords. AC-36 expands "magic numbers" to "bare literals" and AC-38 expands "test name contradictions" to "non-enforcing tests." The keyword checks must be updated to match the new wording. Replace `magic number` grep with `bare literal` and replace `test name` grep with `non-enforcing`.

Current test file state:
- Test 5 (line 74): checks `has_bash` > 0
- Test 17 (line 184): checks for `semantic-drift`
- Test 23 (line 247): threshold `>= 5`
- Test 24 (line 256): greps for `magic number`, (line 262): greps for `test name`

Follow the existing test file's conventions exactly. Modify in place.

## Instructions

1. **Update Test 5** (Detector tools field):
   - Change the test name from `"Detector tools field lists Read, Grep, Glob, Bash"` to `"Detector tools field lists Read, Grep, Glob without Bash"`.
   - Remove the `has_bash=$(echo "$tools_line" | grep -c 'Bash')` check from the pass condition.
   - Change the pass condition to: `[ "$has_read" -gt 0 ] && [ "$has_grep" -gt 0 ] && [ "$has_glob" -gt 0 ] && [ "$has_bash" -eq 0 ]`.
   - Update the `not_ok` message to match the new test name.

2. **Update Test 17** (guide category/type values):
   - Change the test name from `"Guide documents all 4 allowed category values"` to `"Guide documents all 4 type values"`.
   - Replace `semantic=$(grep -c 'semantic-drift' "$GUIDE" 2>/dev/null || true)` with `behavioral=$(grep -c 'behavioral' "$GUIDE" 2>/dev/null || true)`.
   - Replace `nit=$(grep -c 'nit' "$GUIDE" 2>/dev/null || true)` with `fragile=$(grep -c 'fragile' "$GUIDE" 2>/dev/null || true)`.
   - Update the condition to: `[ "$behavioral" -gt 0 ] && [ "$structural" -gt 0 ] && [ "$test_integrity" -gt 0 ] && [ "$fragile" -gt 0 ]`.
   - Update the `not_ok` diagnostic to: `"behavioral=$behavioral structural=$structural test_integrity=$test_integrity fragile=$fragile"`.

3. **Update Test 23** (checklist item count floor):
   - Change threshold from `[ "$numbered" -ge 5 ]` to `[ "$numbered" -ge 12 ]`.
   - Update the test name from `"Checklist contains at least 5 numbered items"` to `"Checklist contains at least 12 numbered items"`.
   - Update the `not_ok` message to match.

4. **Update Test 24** (checklist keywords):
   - Replace `magic=$(grep -ci 'magic number' "$CHECKLIST" 2>/dev/null || true)` with `bare_literal=$(grep -ci 'bare literal' "$CHECKLIST" 2>/dev/null || true)`.
   - Replace `testname=$(grep -ci 'test name' "$CHECKLIST" 2>/dev/null || true)` with `nonenforcing=$(grep -ci 'non-enforcing' "$CHECKLIST" 2>/dev/null || true)`.
   - Update the `keyword_count` summation to use `bare_literal` and `nonenforcing` instead of `magic` and `testname`.
   - Update the test name to reflect the new keywords: `"Checklist contains key failure mode keywords (updated for 0.3.3)"`.

## Files to create/modify

- `tests/sdl-workflow/test-code-review-structural.sh` (modify)

## Test requirements

Updates 4 existing tests (Tests 5, 17, 23, 24) in the structural test file. After modification, Tests 5, 17, and 24 must fail before 0.3.3 implementation (the target files still have old content). Test 23 must fail (current count is 5, threshold raised to 12).

## Acceptance criteria

- AC-09: Test 5 asserts Bash absent from Detector tools.
- AC-57: Test 17 asserts new type values (behavioral, structural, test-integrity, fragile) instead of old category values (semantic-drift, nit).
- AC-36: Test 24 checks for `bare literal` instead of `magic number`.
- AC-38: Test 24 checks for `non-enforcing` instead of `test name`.
- Test 23 floor raised to 12.
- All four updated tests fail before implementation.

## Model

Haiku

## Wave

Wave 1
