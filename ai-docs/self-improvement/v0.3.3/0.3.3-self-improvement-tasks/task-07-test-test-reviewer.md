---
id: task-07
type: test
wave: 1
covers: [AC-49, AC-50, AC-51, AC-52, AC-53, AC-54]
files_to_create:
  - tests/sdl-workflow/test-test-reviewer-extensions.sh
completion_gate: "tests compile and fail before implementation"
---

## Objective

Creates `tests/sdl-workflow/test-test-reviewer-extensions.sh` — a structural test suite validating the 6 new test reviewer criteria in fbk-test-reviewer.md: three Tier 1 additions and three checkpoint additions.

## Context

The test reviewer agent (`assets/agents/fbk-test-reviewer.md`) currently has Tier 1 (1 criterion: silent failure detection) and Tier 2 (4 criteria). Six new items are added:

Tier 1 additions (non-overridable, mechanical checks):
- AC-49: Stale failure annotations on passing tests — a test marked as expected-to-fail that now passes.
- AC-50: Empty gate tests with zero assertions — a test that exists but contains no assertion calls.
- AC-51: Advisory assertions (non-failing output for behavioral checks) — a test that logs or prints a behavioral check result but does not assert on it.

Checkpoint additions (applied at specific checkpoints):
- AC-52: Unconditionally skipped tests with behavioral names — tests that are `skip`ped unconditionally but have names suggesting behavioral verification.
- AC-53: Phantom assertion strings — test assertions referencing string values that do not appear in the production code being tested.
- AC-54: Build-tag consistency for infrastructure-dependent tests — tests requiring specific build tags or environments match the project's actual build configuration.

Current state: The file's Tier 1 section (lines 18-25) has only Criterion 1 (silent failure detection). The checkpoint sections (CP1-CP5) do not mention any of these new items.

Follow the TAP format from existing test files.

## Instructions

1. Create `tests/sdl-workflow/test-test-reviewer-extensions.sh` with shebang and `set -uo pipefail`.

2. Add standard boilerplate. Define:
   - `REVIEWER="$PROJECT_ROOT/assets/agents/fbk-test-reviewer.md"`

3. Add the following tests:

   **Test 1: Test reviewer Tier 1 contains stale failure annotation criterion (AC-49)**
   Grep the Tier 1 section for `stale.*fail\|fail.*annotation\|expected.to.fail.*pass` in `$REVIEWER`. Extract the Tier 1 section:
   ```bash
   tier1=$(sed -n '/### Tier 1/,/### Tier 2/p' "$REVIEWER" | head -n -1)
   has_stale=$(echo "$tier1" | grep -ciE 'stale.*fail|fail.*annotation|expected.to.fail' 2>/dev/null || true)
   ```
   Assert `has_stale > 0`. Test name: "Test reviewer Tier 1 contains stale failure annotation criterion".

   **Test 2: Test reviewer Tier 1 contains empty gate test criterion (AC-50)**
   Grep the Tier 1 section for `empty.*gate\|zero.*assert\|no.*assert`. Use:
   ```bash
   has_empty=$(echo "$tier1" | grep -ciE 'empty.*gate|zero.*assert|no.*assert' 2>/dev/null || true)
   ```
   Assert `has_empty > 0`. Test name: "Test reviewer Tier 1 contains empty gate test criterion".

   **Test 3: Test reviewer Tier 1 contains advisory assertion criterion (AC-51)**
   Grep the Tier 1 section for `advisory.*assert\|non.failing.*output\|advisory`. Use:
   ```bash
   has_advisory=$(echo "$tier1" | grep -ciE 'advisory|non.failing.*output' 2>/dev/null || true)
   ```
   Assert `has_advisory > 0`. Test name: "Test reviewer Tier 1 contains advisory assertion criterion".

   **Test 4: Test reviewer checkpoints contain unconditionally skipped test criterion (AC-52)**
   Grep the full file for `unconditionally.*skip\|skip.*unconditional\|always.*skip`. Use: `grep -qiE 'unconditionally.*skip|skip.*unconditional' "$REVIEWER"`. Test name: "Test reviewer contains unconditionally skipped test criterion".

   **Test 5: Test reviewer checkpoints contain phantom assertion string criterion (AC-53)**
   Grep for `phantom.*assert\|phantom.*string\|assert.*string.*absent\|absent.*production`. Use: `grep -qiE 'phantom|assert.*absent.*production|string.*not.*production' "$REVIEWER"`. Test name: "Test reviewer contains phantom assertion string criterion".

   **Test 6: Test reviewer checkpoints contain build-tag consistency criterion (AC-54)**
   Grep for `build.tag\|build tag\|infrastructure.dependent`. Use: `grep -qiE 'build.tag|infrastructure.dependent' "$REVIEWER"`. Test name: "Test reviewer contains build-tag consistency criterion".

4. Add standard summary footer.

5. Make the file executable.

## Files to create/modify

- `tests/sdl-workflow/test-test-reviewer-extensions.sh` (create)

## Test requirements

6 structural tests covering AC-49 through AC-54. Tests 1-3 verify Tier 1 section placement. Tests 4-6 verify checkpoint-level criteria presence. Tests must fail before implementation.

## Acceptance criteria

- AC-49: Test 1 verifies stale failure annotation in Tier 1 section.
- AC-50: Test 2 verifies empty gate test in Tier 1 section.
- AC-51: Test 3 verifies advisory assertion in Tier 1 section.
- AC-52: Test 4 verifies unconditionally skipped test criterion.
- AC-53: Test 5 verifies phantom assertion string criterion.
- AC-54: Test 6 verifies build-tag consistency criterion.

## Model

Haiku

## Wave

Wave 1
