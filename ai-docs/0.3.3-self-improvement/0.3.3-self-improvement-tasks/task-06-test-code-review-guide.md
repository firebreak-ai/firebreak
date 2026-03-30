---
id: task-06
type: test
wave: 1
covers: [AC-23, AC-24, AC-25, AC-26, AC-27, AC-28, AC-29]
files_to_create:
  - tests/sdl-workflow/test-code-review-guide-extensions.sh
completion_gate: "tests compile and fail before implementation"
---

## Objective

Creates `tests/sdl-workflow/test-code-review-guide-extensions.sh` — a structural test suite validating the 7 new additions to code-review-guide.md: AC verification precision, expanded test-integrity definition, dead infrastructure check, nit exclusion, structural sub-categorization, origin guidance, and quality-detection reference.

## Context

The code review guide (`assets/fbk-docs/fbk-sdl-workflow/code-review-guide.md`) currently has 94 lines and receives 8 ACs (7 tested here; AC-57 canonical definitions tested in task-02). These additions roughly double the file's size.

Current state: The guide has sections for Behavioral Comparison Methodology, Sighting Format, Finding Format, Category Values, Orchestration Protocol, Source of Truth Handling, and Retrospective Fields. None of the 7 additions in this task exist yet.

- AC-23: AC verification precision requirement — Detectors must verify each AC individually, not batch.
- AC-24: Expanded test-integrity definition to include name-scope mismatch (test name claims broader scope than assertions cover).
- AC-25: Dead/disconnected infrastructure check in Detector instructions.
- AC-26: Explicit nit exclusion instruction — nits are excluded from findings entirely, not classified with a severity.
- AC-27: Structural-target sub-categorization in retrospective fields — structural findings broken down by sub-category.
- AC-28: Origin guidance for codebase-wide reviews — default to `pre-existing` when reviewing code not tied to a specific change set.
- AC-29: quality-detection.md reference in the no-spec source-of-truth section.

Follow the TAP format from existing test files.

## Instructions

1. Create `tests/sdl-workflow/test-code-review-guide-extensions.sh` with shebang and `set -uo pipefail`.

2. Add standard boilerplate. Define:
   - `GUIDE="$PROJECT_ROOT/assets/fbk-docs/fbk-sdl-workflow/code-review-guide.md"`

3. Add the following tests:

   **Test 1: Guide contains AC verification precision requirement (AC-23)**
   Grep for `precision` or `individually` or `each AC` or `per-AC` in `$GUIDE`. Use: `grep -qiE 'precision|individual|each AC|per.AC' "$GUIDE"`. Test name: "Guide contains AC verification precision requirement".

   **Test 2: Guide test-integrity definition includes name-scope mismatch (AC-24)**
   Grep for `name.scope` or `scope mismatch` in `$GUIDE`. Use: `grep -qiE 'name.scope|scope.mismatch' "$GUIDE"`. Test name: "Guide test-integrity includes name-scope mismatch".

   **Test 3: Guide contains dead infrastructure check (AC-25)**
   Grep for `dead infrastructure\|disconnected infrastructure` in `$GUIDE`. Use: `grep -qiE 'dead infrastructure|disconnected infrastructure' "$GUIDE"`. Test name: "Guide contains dead infrastructure check".

   **Test 4: Guide contains explicit nit exclusion instruction (AC-26)**
   Grep for `nit.*exclud\|exclud.*nit\|nit.*not.*finding` in `$GUIDE`. Use: `grep -qiE 'nit.*exclud|exclud.*nit|nit.*(not|never).*finding' "$GUIDE"`. Test name: "Guide contains nit exclusion instruction".

   **Test 5: Guide contains structural sub-categorization in retrospective (AC-27)**
   Grep for `sub.categor\|structural.*breakdown\|structural.*sub` in `$GUIDE`. Use: `grep -qiE 'sub.categor|structural.*(breakdown|sub)' "$GUIDE"`. Test name: "Guide contains structural sub-categorization in retrospective".

   **Test 6: Guide contains origin guidance for codebase-wide reviews (AC-28)**
   Grep for `pre-existing\|codebase.wide\|default.*origin` in `$GUIDE`. Use: `grep -qiE 'pre.existing.*default|default.*pre.existing|codebase.wide.*origin' "$GUIDE"`. Test name: "Guide contains origin guidance for codebase-wide reviews".

   **Test 7: Guide no-spec section references quality-detection.md (AC-29)**
   Grep for `quality-detection` in `$GUIDE`. Use: `grep -q 'quality-detection' "$GUIDE"`. Note: the current file already references `quality-detection.md` on line 64 in the Orchestration Protocol. AC-29 specifically adds it to the no-spec source-of-truth section. Check that `quality-detection` appears in the Source of Truth section. Use a section-aware approach:
   ```bash
   # Extract the Source of Truth Handling section
   sot_section=$(sed -n '/## Source of Truth Handling/,/^## /p' "$GUIDE" | head -n -1)
   has_qd=$(echo "$sot_section" | grep -c 'quality-detection' 2>/dev/null || true)
   ```
   Assert `has_qd > 0`. Test name: "Guide no-spec section references quality-detection.md".

4. Add standard summary footer.

5. Make the file executable.

## Files to create/modify

- `tests/sdl-workflow/test-code-review-guide-extensions.sh` (create)

## Test requirements

7 structural tests covering AC-23 through AC-29. Tests must fail before implementation.

## Acceptance criteria

- AC-23: Test 1 verifies precision requirement keyword.
- AC-24: Test 2 verifies name-scope mismatch in test-integrity definition.
- AC-25: Test 3 verifies dead infrastructure check keyword.
- AC-26: Test 4 verifies nit exclusion instruction.
- AC-27: Test 5 verifies structural sub-categorization.
- AC-28: Test 6 verifies origin guidance for codebase-wide reviews.
- AC-29: Test 7 verifies quality-detection.md reference in no-spec section.

## Model

Haiku

## Wave

Wave 1
