---
id: task-05
type: test
wave: 1
covers: [AC-02, AC-03, AC-04, AC-05, AC-08]
files_to_modify:
  - tests/sdl-workflow/test-code-review-structural.sh
  - tests/sdl-workflow/test-instruction-hygiene-agents.sh
completion_gate: "bash tests/sdl-workflow/test-code-review-structural.sh exits 0 && bash tests/sdl-workflow/test-instruction-hygiene-agents.sh exits 0"
---

## Objective

Update two existing test files that will break due to the Detector/Challenger persona rewrite and guide format changes. These are high-confidence breakages identified during spec review.

## Context

The Detector agent is being rewritten from a procedural definition to a persona-driven definition. The Challenger agent is being rewritten similarly. The code review guide is replacing markdown format templates with JSON schema references. These changes break specific tests that grep for old wording.

## Instructions

### File 1: `tests/sdl-workflow/test-code-review-structural.sh`

**Test 7 (line ~90)**: Currently greps the Detector description for `analysis|analyz|detect|code review|pattern`. The new Detector description is `"Senior engineer reviewing code for bugs. Reads code closely, constructs failing inputs, traces caller contracts. Produces JSON sightings."` Update the grep pattern to match the new description. Replace the pattern with `reviewing code|bug|sighting|JSON` (case-insensitive). Update the test name to `"Detector description contains code review language"`.

**Test 16 (line ~169-181)**: Currently checks the guide for `current behavior` and `expected behavior` as required finding format fields. The new guide uses `mechanism`, `consequence`, and `evidence` instead. Replace the check for `current` (which matched `current behavior`) with a check for `mechanism`. Replace the check for `expected` (which matched `expected behavior`) with a check for `consequence`. Keep `finding_id`, `sighting`, `location`, `type_field`, `source`, and `evidence` checks. Update the field count in the test name from "8 required fields" to "8 required fields" (count stays the same, names change). The specific variable assignments to update:
- Replace `current=$(grep -ci 'current behavior' "$GUIDE" 2>/dev/null || true)` with `mechanism=$(grep -ci 'mechanism' "$GUIDE" 2>/dev/null || true)`
- Replace `expected=$(grep -ci 'expected behavior' "$GUIDE" 2>/dev/null || true)` with `consequence=$(grep -ci 'consequence' "$GUIDE" 2>/dev/null || true)`
- Update the if-condition to use `$mechanism` and `$consequence` instead of `$current` and `$expected`
- Update the diagnostic string in the `not_ok` call to use `mechanism=` and `consequence=` instead of `current=` and `expected=`

**Test 18 (line ~194-205)**: Currently checks the guide sighting format for `observation` and `expected`. The new guide sighting format uses JSON fields: `mechanism`, `consequence`, `evidence`. Replace `observation=$(grep -ci 'observation' "$GUIDE" 2>/dev/null || true)` with `mechanism_s=$(grep -ci 'mechanism' "$GUIDE" 2>/dev/null || true)`. Replace `sighting_expected=$(grep -ci 'expected' "$GUIDE" 2>/dev/null || true)` with `consequence_s=$(grep -ci 'consequence' "$GUIDE" 2>/dev/null || true)`. Update the if-condition and diagnostic string to use the new variable names. Update the test name to `"Guide documents sighting format with required fields"` (name stays the same).

### File 2: `tests/sdl-workflow/test-instruction-hygiene-agents.sh`

**Tests 1-2 (lines ~17-32)**: Test 1 checks Detector for `exclude nits`. The new Detector still contains `Exclude nits.` at the end of the body. This test should still pass. **No change needed for Test 1.** Test 2 checks that the nit instruction is in a `## Scope discipline` section. The new Detector does NOT have a `## Scope discipline` heading — `Exclude nits.` appears as the last sentence of the body, not under a section heading. Update Test 2 to check that `Exclude nits` appears in the Detector body without requiring it to be in a specific section. Replace `sed -n '/## Scope discipline/,/^## /p' "$DETECTOR" 2>/dev/null | grep -qi 'nit'` with `grep -qi 'exclude nits' "$DETECTOR" 2>/dev/null`. Update the test name to `"Nit exclusion instruction present in Detector"`.

**Tests 3-4 (lines ~34-48)**: Test 3 checks Challenger for `pattern label`. The new Challenger uses `pattern` as a JSON field name but does not use the exact phrase `pattern label` — the Challenger's body references reclassification and the orchestrator-provided schema. Update to grep for `pattern` instead of `pattern label`. Update test name to `"Challenger contains pattern reference"`. Test 4 checks Challenger for `label correction|independent issues`. The new Challenger does not use these phrases. It references reclassification via `reclassified_from` and the type-severity matrix. Update to grep for `reclassif` (case-insensitive). Update test name to `"Challenger contains reclassification instruction"`.

**Tests 5-6 (lines ~52-67)**: Test 5 checks the guide Sighting Format section for `pattern label`. The new guide replaces the markdown sighting template with JSON schema references. The JSON schema has a `pattern` field. Update to grep the Sighting Format section (or the full guide if the section name changes) for `pattern` instead of `pattern label`. Update test name to `"Sighting format references pattern field"`. Test 6 checks the guide Finding Format section for `pattern label`. Same change — grep for `pattern` in the Finding Format section (or full guide). Update test name to `"Finding format references pattern field"`.

## Files to create/modify

Modify: `tests/sdl-workflow/test-code-review-structural.sh`
Modify: `tests/sdl-workflow/test-instruction-hygiene-agents.sh`

## Test requirements

Both files must remain executable, exit 0 on all pass / 1 on any fail, and follow TAP conventions.

## Acceptance criteria

- `test-code-review-structural.sh` tests 7, 16, 18 updated to match new Detector description, guide finding format fields (mechanism/consequence instead of current behavior/expected behavior), and guide sighting format fields
- `test-instruction-hygiene-agents.sh` tests 2, 3, 4, 5, 6 updated to match new Detector/Challenger structure and guide JSON format
- No changes to tests that do not break
- Both test files pass after implementation of the corresponding asset changes

## Model

sonnet

## Wave

1
