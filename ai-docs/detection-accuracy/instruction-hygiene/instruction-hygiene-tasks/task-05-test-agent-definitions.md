---
id: task-05
type: test
wave: 1
covers: [AC-05, AC-06]
files_to_create:
  - tests/sdl-workflow/test-instruction-hygiene-agents.sh
completion_gate: "tests compile and fail before implementation"
---

## Objective

Creates a new shell test file verifying the Detector nit suppression instruction, the Challenger pattern-label instructions, and the pattern-label fields in the Sighting Format and Finding Format templates.

## Context

The instruction hygiene spec adds:
- A nit suppression instruction to the Detector agent definition's "Scope discipline" section (AC-05)
- Two pattern-label instructions to the Challenger agent definition's "Verified finding" section: one for preservation, one for correction (AC-06)
- A `Pattern label:` field to both the Sighting Format and Finding Format templates in `code-review-guide.md` (AC-06)

Follow the TAP format convention from existing test files.

## Instructions

1. Create `tests/sdl-workflow/test-instruction-hygiene-agents.sh` with the standard boilerplate. Define variables:
   - `DETECTOR="$PROJECT_ROOT/assets/agents/fbk-code-review-detector.md"`
   - `CHALLENGER="$PROJECT_ROOT/assets/agents/fbk-code-review-challenger.md"`
   - `GUIDE="$PROJECT_ROOT/assets/fbk-docs/fbk-sdl-workflow/code-review-guide.md"`

2. Add Test 1 (AC-05): assert `fbk-code-review-detector.md` contains "Exclude nits" (case-insensitive). Use `grep -qi 'exclude nits' "$DETECTOR"`.

3. Add Test 2 (AC-05): assert the nit suppression instruction appears in the Scope discipline section. Use `sed -n '/## Scope discipline/,/^## /p' "$DETECTOR" | grep -qi 'nit'`.

4. Add Test 3 (AC-06 preservation): assert `fbk-code-review-challenger.md` contains "pattern label" (case-insensitive). Use `grep -qi 'pattern label' "$CHALLENGER"`.

5. Add Test 4 (AC-06 correction): assert `fbk-code-review-challenger.md` contains "label correction" or "independent issues" (case-insensitive). Use `grep -qiE 'label correction|independent issues' "$CHALLENGER"`.

6. Add Test 5 (AC-06 sighting format): assert `code-review-guide.md` Sighting Format template contains "Pattern label:". Extract the Sighting Format section (between `## Sighting Format` and the next `## `) and grep for `Pattern label:`. Use `sed -n '/## Sighting Format/,/^## /p' "$GUIDE" | grep -qi 'pattern label'`.

7. Add Test 6 (AC-06 finding format): assert `code-review-guide.md` Finding Format template contains "Pattern label:". Extract the Finding Format section and grep. Use `sed -n '/## Finding Format/,/^## /p' "$GUIDE" | grep -qi 'pattern label'`.

8. Add the standard summary block. Make the file executable.

## Files to create/modify

- `tests/sdl-workflow/test-instruction-hygiene-agents.sh` (create)

## Test requirements

New shell tests (6 tests total):
- Tests 1-2: AC-05 nit suppression in Detector (will fail pre-implementation — Detector currently has no nit instruction)
- Tests 3-4: AC-06 pattern-label handling in Challenger (will fail pre-implementation — Challenger has no pattern-label instructions)
- Tests 5-6: AC-06 pattern-label field in Sighting/Finding Format templates (will fail pre-implementation — templates lack Pattern label field)

## Acceptance criteria

- AC-05: Tests verify nit suppression instruction exists in Detector's Scope discipline section
- AC-06: Tests verify pattern-label preservation and correction instructions in Challenger, and Pattern label field in both format templates

## Model

Haiku

## Wave

Wave 1
