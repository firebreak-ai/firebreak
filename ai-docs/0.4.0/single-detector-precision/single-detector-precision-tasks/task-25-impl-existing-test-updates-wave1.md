---
id: task-25
type: implementation
wave: 2
covers: [AC-02, AC-03, AC-04, AC-05, AC-08]
files_to_modify:
  - tests/sdl-workflow/test-code-review-structural.sh
  - tests/sdl-workflow/test-instruction-hygiene-agents.sh
test_tasks: [task-05]
completion_gate: "bash tests/sdl-workflow/test-code-review-structural.sh exits 0 && bash tests/sdl-workflow/test-instruction-hygiene-agents.sh exits 0"
---

## Objective

Update two existing test files that break due to the Detector/Challenger persona rewrite and guide format changes. These are the high-confidence breakage tests.

## Context

Task-21 rewrites the Detector agent definition. Task-22 rewrites the Challenger agent definition. Task-24 updates the code review guide. These changes break specific grep patterns in existing tests. The test updates in this task must run AFTER the asset changes in tasks 21, 22, 24 are applied.

The updated Detector description is: `"Senior engineer reviewing code for bugs. Reads code closely, constructs failing inputs, traces caller contracts. Produces JSON sightings."` The Detector body no longer has a `## Scope discipline` heading — `Exclude nits.` is the last sentence of the body. The guide replaces `current behavior`/`expected behavior` fields with `mechanism`/`consequence`/`evidence` fields. The guide replaces the markdown sighting template with JSON field documentation. The Challenger body no longer uses "pattern label" — it references reclassification via `reclassified_from`.

## Instructions

Apply every change described in test task-05. The changes are:

### File 1: `tests/sdl-workflow/test-code-review-structural.sh`

**Test 7** (~line 90): Replace the Detector description grep pattern `analysis|analyz|detect|code review|pattern` with `reviewing code|bug|sighting|JSON` (case-insensitive). Update the test name to `"Detector description contains code review language"`.

**Test 16** (~lines 169-181): Replace the finding format field checks:
- Replace `current=$(grep -ci 'current behavior' "$GUIDE" 2>/dev/null || true)` with `mechanism=$(grep -ci 'mechanism' "$GUIDE" 2>/dev/null || true)`
- Replace `expected=$(grep -ci 'expected behavior' "$GUIDE" 2>/dev/null || true)` with `consequence=$(grep -ci 'consequence' "$GUIDE" 2>/dev/null || true)`
- Update the if-condition to use `$mechanism` and `$consequence` instead of `$current` and `$expected`
- Update the diagnostic string in `not_ok` to use `mechanism=` and `consequence=` instead of `current=` and `expected=`

**Test 18** (~lines 194-205): Replace the sighting format field checks:
- Replace `observation=$(grep -ci 'observation' "$GUIDE" 2>/dev/null || true)` with `mechanism_s=$(grep -ci 'mechanism' "$GUIDE" 2>/dev/null || true)`
- Replace `sighting_expected=$(grep -ci 'expected' "$GUIDE" 2>/dev/null || true)` with `consequence_s=$(grep -ci 'consequence' "$GUIDE" 2>/dev/null || true)`
- Update the if-condition and diagnostic string to use the new variable names

### File 2: `tests/sdl-workflow/test-instruction-hygiene-agents.sh`

**Test 1**: No change needed — the new Detector still contains `Exclude nits.`

**Test 2**: Replace `sed -n '/## Scope discipline/,/^## /p' "$DETECTOR" 2>/dev/null | grep -qi 'nit'` with `grep -qi 'exclude nits' "$DETECTOR" 2>/dev/null`. Update the test name to `"Nit exclusion instruction present in Detector"`.

**Test 3**: Replace the grep pattern from `pattern label` to just `pattern`. Update the test name to `"Challenger contains pattern reference"`.

**Test 4**: Replace the grep `label correction|independent issues` with `reclassif` (case-insensitive). Update the test name to `"Challenger contains reclassification instruction"`.

**Test 5**: Replace the grep for `Pattern label:` in the Sighting Format section with a grep for `pattern` in the full guide (or sighting format section). Update test name to `"Sighting format references pattern field"`.

**Test 6**: Replace the grep for `Pattern label:` in the Finding Format section with a grep for `pattern` in the full guide (or finding format section). Update test name to `"Finding format references pattern field"`.

## Files to create/modify

Modify: `tests/sdl-workflow/test-code-review-structural.sh`
Modify: `tests/sdl-workflow/test-instruction-hygiene-agents.sh`

## Test requirements

Both files must remain executable, exit 0 on all pass / 1 on any fail, and follow TAP conventions. No changes to tests that do not break.

## Acceptance criteria

- `test-code-review-structural.sh` tests 7, 16, 18 updated to match new Detector description, guide finding format fields, and guide sighting format fields
- `test-instruction-hygiene-agents.sh` tests 2, 3, 4, 5, 6 updated to match new Detector/Challenger structure and guide JSON format
- Both test files pass after the asset changes from tasks 21, 22, 24

## Model

sonnet

## Wave

2
