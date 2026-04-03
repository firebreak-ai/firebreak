---
id: task-03
type: test
wave: 1
covers: [AC-09, AC-10, AC-11, AC-12]
files_to_create:
  - tests/sdl-workflow/test-classification-system.sh
completion_gate: "tests compile and fail before implementation"
---

## Objective

Creates `tests/sdl-workflow/test-classification-system.sh` — a structural test suite validating the Detector schema changes (Bash removal, type/severity/pattern fields) and cross-file consistency of type and severity values between the Detector, Challenger, and code-review-guide.md.

## Context

AC-09 removes Bash from the Detector's tools list and relocates linter discovery/execution to SKILL.md. The Detector's current frontmatter tools line is `tools: Read, Grep, Glob, Bash`. After AC-09, it becomes `tools: Read, Grep, Glob` (no Bash). The linter execution instruction relocates to SKILL.md (tested in task-05).

AC-10 adds `type` (behavioral, structural, test-integrity, fragile) and `severity` (critical, major, minor, info) fields to the Detector's sighting output schema.

AC-11 adds a cross-cutting pattern label field to the Detector's sighting output schema.

AC-12 requires the Challenger to validate or adjust both type and severity on verified findings.

The canonical definitions for type and severity values live in `code-review-guide.md` (tested in task-02 AC-57). This test verifies the Detector and Challenger reference the same values.

Current state:
- Detector frontmatter line 4: `tools: Read, Grep, Glob, Bash`
- Detector sighting output section (line 16): mentions `category` only, no `type`, `severity`, or `pattern` fields
- Challenger verification protocol (lines 12-17): mentions `category` reclassification but no type/severity validation

Follow the TAP format from existing test files.

## Instructions

1. Create `tests/sdl-workflow/test-classification-system.sh` with shebang and `set -uo pipefail`.

2. Add standard boilerplate. Define path variables:
   - `DETECTOR="$PROJECT_ROOT/assets/agents/fbk-code-review-detector.md"`
   - `CHALLENGER="$PROJECT_ROOT/assets/agents/fbk-code-review-challenger.md"`
   - `GUIDE="$PROJECT_ROOT/assets/fbk-docs/fbk-sdl-workflow/code-review-guide.md"`

3. Add a `frontmatter()` helper (copy from `test-code-review-structural.sh`):
   ```bash
   frontmatter() {
     sed -n '2,/^---$/p' "$1" | sed '$d'
   }
   ```

4. Add the following tests:

   **Test 1: Detector tools list does not contain Bash (AC-09 — absence half)**
   Extract frontmatter, get the `tools:` line, check that `Bash` does not appear. Use:
   ```bash
   fm=$(frontmatter "$DETECTOR")
   tools_line=$(echo "$fm" | grep '^tools:')
   has_bash=$(echo "$tools_line" | grep -c 'Bash' 2>/dev/null || true)
   ```
   Assert `has_bash == 0`. Test name: "Detector tools list does not contain Bash".

   **Test 2: Detector tools list contains Read, Grep, Glob (AC-09 — tools preserved)**
   From the same `tools_line`, verify `Read`, `Grep`, `Glob` are all present. Use three grep checks combined with `&&`. Test name: "Detector tools list contains Read, Grep, Glob".

   **Test 3: Detector body does not contain linter discovery section (AC-09 — removal)**
   Extract the body after frontmatter. Grep for `Project-native tool discovery` or `lint configuration` or `eslintrc`. Assert none found. Use:
   ```bash
   body=$(awk '/^---$/{c++; if(c==2){found=1; next}} found' "$DETECTOR")
   has_linter_section=$(echo "$body" | grep -ciE 'project-native tool discovery|lint config|eslintrc|pylintrc' 2>/dev/null || true)
   ```
   Assert `has_linter_section == 0`. Test name: "Detector body does not contain linter discovery section".

   **Test 4: Detector sighting output mentions type field (AC-10)**
   Grep the Detector body for `type` appearing as a schema field. Use: `echo "$body" | grep -qiE '\btype\b'`. Test name: "Detector sighting output includes type field".

   **Test 5: Detector sighting output mentions severity field (AC-10)**
   Grep the Detector body for `severity`. Use: `echo "$body" | grep -qi 'severity'`. Test name: "Detector sighting output includes severity field".

   **Test 6: Detector sighting output mentions pattern label field (AC-11)**
   Grep the Detector body for `pattern` (cross-cutting pattern label). Use: `echo "$body" | grep -qiE 'pattern'`. Test name: "Detector sighting output includes pattern label field".

   **Test 7: Challenger validates type and severity (AC-12)**
   Grep the Challenger body for both `type` and `severity` in the context of validation/adjustment. Use:
   ```bash
   challenger_body=$(awk '/^---$/{c++; if(c==2){found=1; next}} found' "$CHALLENGER")
   has_type_validate=$(echo "$challenger_body" | grep -ciE '(validat|adjust|classif).*type|type.*(validat|adjust|classif)' 2>/dev/null || true)
   has_sev_validate=$(echo "$challenger_body" | grep -ciE '(validat|adjust|classif).*severity|severity.*(validat|adjust|classif)' 2>/dev/null || true)
   ```
   Assert both > 0. Test name: "Challenger validates both type and severity".

   **Test 8: Cross-file consistency — type values appear in Detector (AC-10, integration seam)**
   Grep Detector body for all four type values: `behavioral`, `structural`, `test-integrity`, `fragile`. Assert all present. Test name: "Detector references all four type values".

   **Test 9: Cross-file consistency — type values appear in Challenger (AC-12, integration seam)**
   Grep Challenger body for all four type values. Assert all present. Test name: "Challenger references all four type values".

   **Test 10: Cross-file consistency — severity values appear in Detector (AC-10, integration seam)**
   Grep Detector body for all four severity values: `critical`, `major`, `minor`, `info`. Assert all present. Test name: "Detector references all four severity values".

   **Test 11: Cross-file consistency — severity values appear in Challenger (AC-12, integration seam)**
   Grep Challenger body for all four severity values. Assert all present. Test name: "Challenger references all four severity values".

5. Add standard summary footer.

6. Make the file executable.

## Files to create/modify

- `tests/sdl-workflow/test-classification-system.sh` (create)

## Test requirements

11 structural tests covering AC-09, AC-10, AC-11, AC-12 plus the Detector-to-Challenger integration seam. Tests must fail before implementation.

## Acceptance criteria

- AC-09: Tests 1-3 verify Bash removed from tools, linter section removed from body.
- AC-10: Tests 4-5, 8, 10 verify type and severity fields and values in Detector.
- AC-11: Test 6 verifies pattern label field in Detector.
- AC-12: Tests 7, 9, 11 verify Challenger validates both axes with correct values.
- Integration seam: Tests 8-11 verify cross-file consistency of type and severity values.

## Model

Haiku

## Wave

Wave 1
