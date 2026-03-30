---
id: task-02
type: test
wave: 1
covers: [AC-55, AC-56, AC-57, AC-58, AC-59]
files_to_create:
  - tests/sdl-workflow/test-category-migration.sh
completion_gate: "tests compile and fail before implementation"
---

## Objective

Creates `tests/sdl-workflow/test-category-migration.sh` — a structural test suite validating the category-to-type migration across code-review-guide.md, the Detector agent, and the Challenger agent.

## Context

The existing system uses a single `Category` field with values `semantic-drift`, `structural`, `test-integrity`, `nit`. This is replaced by two orthogonal axes: `Type` (behavioral, structural, test-integrity, fragile) and `Severity` (critical, major, minor, info). The migration touches three files:

- `code-review-guide.md`: sighting format template replaces `Category:` with `Type:` + `Severity:`, finding format template does the same, and the "Category Values" section is replaced with canonical two-axis definitions.
- `fbk-code-review-detector.md`: output instruction replaces `category` with `type` + `severity`.
- `fbk-code-review-challenger.md`: "downgrade to nit" behavior replaced with "reject as nit" (exclude from findings, count separately).

Current state of target files:
- `code-review-guide.md` sighting format line 18: `Category: [semantic-drift | structural | test-integrity | nit]`
- `code-review-guide.md` finding format line 44: `Category: [semantic-drift | structural | test-integrity | nit]`
- `code-review-guide.md` line 53: `## Category Values` section heading
- `fbk-code-review-detector.md` line 16: `Assign a category to each sighting: \`semantic-drift\`, \`structural\`, \`test-integrity\`, or \`nit\`.`
- `fbk-code-review-challenger.md` line 18: `**Downgrade to nit:**`

Follow the TAP format and helper patterns from `tests/sdl-workflow/test-code-review-structural.sh`.

## Instructions

1. Create `tests/sdl-workflow/test-category-migration.sh` with shebang and `set -uo pipefail`.

2. Add standard boilerplate (counters, PROJECT_ROOT, ok/not_ok helpers, TAP header). Define path variables:
   - `GUIDE="$PROJECT_ROOT/assets/fbk-docs/fbk-sdl-workflow/code-review-guide.md"`
   - `DETECTOR="$PROJECT_ROOT/assets/agents/fbk-code-review-detector.md"`
   - `CHALLENGER="$PROJECT_ROOT/assets/agents/fbk-code-review-challenger.md"`

3. Add the following tests:

   **Test 1: Sighting format contains Type field (AC-55)**
   Grep for a line containing `Type:` within the sighting format block in `$GUIDE`. Use: Search for `Type:` appearing in the file. `grep -q 'Type:' "$GUIDE"`. Test name: "Guide sighting format contains Type field".

   **Test 2: Sighting format contains Severity field (AC-55)**
   Grep for `Severity:` in `$GUIDE`. Use: `grep -q 'Severity:' "$GUIDE"`. Test name: "Guide sighting format contains Severity field".

   **Test 3: Sighting format does not contain Category field (AC-55)**
   Grep the sighting format block for `Category:`. Extract lines between `^Sighting ID:` and the next blank line or closing triple-backtick. Assert `Category:` does NOT appear in that range. Simpler approach: count occurrences of the exact string `Category:` preceded by a line starting with `Sighting ID:` or `Finding ID:` — but since this is fragile, use a broader check: assert that `Category:` does not appear as a field line in any code block. Simplest reliable approach:
   ```bash
   # Count Category: lines in code blocks (between ``` markers)
   category_in_blocks=$(sed -n '/^```/,/^```/p' "$GUIDE" | grep -c 'Category:' 2>/dev/null || true)
   ```
   Assert `category_in_blocks` equals 0. Test name: "Guide format templates do not contain Category field".

   **Test 4: Finding format contains Type and Severity fields (AC-56)**
   Already covered by Tests 1-3 (both format blocks are in the same file and both must use Type/Severity). Add an explicit check: grep for `Finding ID:` in the file, then verify `Type:` and `Severity:` also appear. This is covered by Tests 1-2 existing. Skip — Tests 1-3 cover AC-55 and AC-56 together since both templates are in the same file and the "no Category in code blocks" check covers both.

   **Test 5: Guide does not contain "Category Values" section heading (AC-57)**
   Grep for `## Category Values` in `$GUIDE`. Assert it does NOT appear. Use:
   ```bash
   if grep -q '## Category Values' "$GUIDE"; then not_ok "..."; else ok "..."; fi
   ```
   Test name: "Guide does not contain Category Values section heading".

   **Test 6: Guide contains canonical type axis definitions (AC-57)**
   Grep for all four type values: `behavioral`, `structural`, `test-integrity`, `fragile`. All four must appear. Use four separate grep checks combined with `&&`. Test name: "Guide contains all four type axis values".

   **Test 7: Guide contains canonical severity axis definitions (AC-57)**
   Grep for all four severity values: `critical`, `major`, `minor`, `info`. All four must appear. Test name: "Guide contains all four severity axis values".

   **Test 8: Guide contains type disambiguation rule (AC-57)**
   Grep case-insensitively for `disambiguation` in `$GUIDE`. Use: `grep -qi 'disambigu' "$GUIDE"`. Test name: "Guide contains type disambiguation rule".

   **Test 9: Detector output instruction uses type and severity, not category (AC-58)**
   Check that `$DETECTOR` body (after frontmatter) does not contain the word `category` as a field assignment. Grep the body for `category` (case-insensitive). Use:
   ```bash
   # Extract body after frontmatter
   body=$(sed -n '/^---$/,/^---$/!p' "$DETECTOR" | tail -n +2)
   cat_count=$(echo "$body" | grep -ci 'category' 2>/dev/null || true)
   ```
   Assert `cat_count` equals 0. Additionally verify `type` and `severity` appear in the body:
   ```bash
   has_type=$(echo "$body" | grep -ci 'type' 2>/dev/null || true)
   has_sev=$(echo "$body" | grep -ci 'severity' 2>/dev/null || true)
   ```
   Assert both > 0. Test name: "Detector output uses type and severity, not category".

   **Test 10: Challenger contains "reject as nit" and not "downgrade to nit" (AC-59)**
   Grep `$CHALLENGER` for "reject as nit" (or "reject.*nit" to be flexible). Assert present. Then grep for "downgrade to nit" or "Downgrade to nit". Assert absent. Use:
   ```bash
   has_reject_nit=$(grep -ciE 'reject.*(as )?nit' "$CHALLENGER" 2>/dev/null || true)
   has_downgrade_nit=$(grep -ci 'downgrade.*nit\|downgrade to nit' "$CHALLENGER" 2>/dev/null || true)
   ```
   Assert `has_reject_nit > 0` AND `has_downgrade_nit == 0`. Test name: "Challenger rejects nits instead of downgrading".

4. Add standard summary footer.

5. Make the file executable.

## Files to create/modify

- `tests/sdl-workflow/test-category-migration.sh` (create)

## Test requirements

10 structural tests covering AC-55 through AC-59. Tests check that the old `Category` system is replaced by the new `Type` + `Severity` two-axis system. All tests must fail before implementation.

## Acceptance criteria

- AC-55, AC-56: Tests verify Type and Severity fields present, Category field absent in format templates.
- AC-57: Tests verify canonical definitions (4 type values, 4 severity values, disambiguation rule) and absence of old "Category Values" heading.
- AC-58: Test verifies Detector body uses type/severity, not category.
- AC-59: Test verifies Challenger uses nit-rejection, not nit-downgrade.

## Model

Haiku

## Wave

Wave 1
