---
id: task-03
type: test
wave: 1
covers: [AC-10, AC-13, AC-14, AC-15, AC-16]
files_to_create:
  - tests/sdl-workflow/test-technique-skills.sh
completion_gate: "tests compile and fail before implementation"
---

## 1. Objective

Creates `tests/sdl-workflow/test-technique-skills.sh`, a TAP-format shell integration test asserting structure, attribution, and behavioral contracts for all four technique skills and the three observe/scan agents.

## 2. Context

Four new technique skills are being created under `assets/skills/`:
- `fbk-grilling/SKILL.md` — grilling technique with Matt Pocock attribution
- `fbk-fresh-eyes/SKILL.md` — cold-comprehension technique
- `fbk-quality-scan/SKILL.md` — top-five quality scan
- `fbk-test-review/SKILL.md` — test-review technique

Three observe/scan agents that must declare no Write or Edit tool:
- `assets/agents/fbk-fresh-eyes-reviewer.md`
- `assets/agents/fbk-code-review-detector.md` (pre-existing; already no Write/Edit — but must still pass)
- `assets/agents/fbk-test-reviewer.md` (pre-existing)

The test checks the following from the spec:
- AC-16: `fbk-grilling/SKILL.md` frontmatter contains "Matt Pocock" and the exact URL `https://github.com/mattpocock/skills/blob/main/skills/productivity/grill-me/SKILL.md`
- AC-13: `fbk-grilling/SKILL.md` body contains the phrase "one question at a time" and a `Confirmed:` line (the reflect-back sentinel from Interface contract #6)
- AC-10: `fbk-quality-scan/SKILL.md` body specifies a maximum of five findings (grep for `5` or `five` near "ranked" or "findings")
- AC-14: Each of the four skill directories + SKILL.md files exist; each has a non-empty `description:` frontmatter field and an `argument-hint:` frontmatter field
- AC-15: The three observe/scan agent files declare no `Write` and no `Edit` in their `tools:` frontmatter line

Follow the TAP helper pattern from `tests/sdl-workflow/test-code-review-structural.sh`: use `frontmatter()` helper, `ok`/`not_ok` functions, `echo "TAP version 13"`.

Before implementation these assertions all fail because the skill directories and agent files do not exist. That is the correct red state.

## 3. Instructions

1. Create `tests/sdl-workflow/test-technique-skills.sh` with the standard TAP boilerplate (`#!/usr/bin/env bash`, `set -uo pipefail`, `PASS=0`, `FAIL=0`, `TOTAL=0`, `ok()`, `not_ok()`, `SCRIPT_DIR`, `PROJECT_ROOT`).

2. Add the `frontmatter()` helper (copies the pattern from `test-code-review-structural.sh`):
   ```bash
   frontmatter() {
     sed -n '2,/^---$/p' "$1" | sed '$d'
   }
   ```

3. Define these path variables:
   ```bash
   GRILLING="$PROJECT_ROOT/assets/skills/fbk-grilling/SKILL.md"
   FRESH_EYES="$PROJECT_ROOT/assets/skills/fbk-fresh-eyes/SKILL.md"
   QUALITY_SCAN="$PROJECT_ROOT/assets/skills/fbk-quality-scan/SKILL.md"
   TEST_REVIEW="$PROJECT_ROOT/assets/skills/fbk-test-review/SKILL.md"
   FRESH_EYES_AGENT="$PROJECT_ROOT/assets/agents/fbk-fresh-eyes-reviewer.md"
   DETECTOR_AGENT="$PROJECT_ROOT/assets/agents/fbk-code-review-detector.md"
   TEST_REVIEWER_AGENT="$PROJECT_ROOT/assets/agents/fbk-test-reviewer.md"
   ```

4. Write assertions for AC-14 — each skill exists with required frontmatter fields (8 tests, 2 per skill):
   - For each skill file (`$GRILLING`, `$FRESH_EYES`, `$QUALITY_SCAN`, `$TEST_REVIEW`):
     - `[ -s "$SKILL" ]` — file exists and non-empty
     - `frontmatter "$SKILL" | grep -q 'description:'` — has description
     - `frontmatter "$SKILL" | grep -q 'argument-hint:'` — has argument-hint

   Write: T1 `fbk-grilling SKILL.md exists`, T2 `fbk-grilling has description`, T3 `fbk-grilling has argument-hint`, T4–T6 for fbk-fresh-eyes, T7–T9 for fbk-quality-scan, T10–T12 for fbk-test-review.

5. Write assertions for AC-16 — grilling attribution (2 tests):
   - T13: `grep -qF 'Matt Pocock' "$GRILLING"` — frontmatter or body credits Matt Pocock
   - T14: `grep -qF 'https://github.com/mattpocock/skills/blob/main/skills/productivity/grill-me/SKILL.md' "$GRILLING"` — exact source URL present

6. Write assertions for AC-13 — grilling behavioral contract (2 tests):
   - T15: `grep -qi 'one question at a time' "$GRILLING"` — body specifies one-question-at-a-time
   - T16: `grep -qF 'Confirmed:' "$GRILLING"` — body contains the reflect-back line sentinel from Interface contract #6

7. Write assertion for AC-10 — quality scan output limit (1 test):
   - T17: `grep -qE '\b5\b|five' "$QUALITY_SCAN"` — skill body specifies a limit of five findings. Additionally check for a severity or ranking indicator: `grep -qi 'ranked\|severity\|top' "$QUALITY_SCAN"` — T18.

8. Write assertions for AC-15 — observe/scan agents carry no Write/Edit tool (6 tests, 2 per agent):
   For each agent file (`$FRESH_EYES_AGENT`, `$DETECTOR_AGENT`, `$TEST_REVIEWER_AGENT`):
   - Extract `tools_line=$(frontmatter "$AGENT" | grep '^tools:')`.
   - T19/T21/T23: `echo "$tools_line" | grep -qv 'Write'` — no Write tool declared
   - T20/T22/T24: `echo "$tools_line" | grep -qv 'Edit'` — no Edit tool declared

   Use `grep -c 'Write'` / `grep -c 'Edit'` pattern (count == 0) matching `test-code-review-structural.sh` Test 5/6 pattern.

9. Add the TAP summary block at the end (same pattern as the existing shell tests).

10. Note: tests T19–T24 for the pre-existing agents (`fbk-code-review-detector.md`, `fbk-test-reviewer.md`) will pass immediately since those agents already declare no Write/Edit. Test T19/T20 for the new `fbk-fresh-eyes-reviewer.md` will fail until that agent is created. That asymmetry is acceptable — the test provides a forward-looking check.

## 4. Files to create/modify

- `tests/sdl-workflow/test-technique-skills.sh` (create)

## 5. Test requirements

24 TAP assertions covering:
- Skill existence and frontmatter structure (T1–T12, AC-14)
- Grilling attribution (T13–T14, AC-16)
- Grilling behavioral contract (T15–T16, AC-13)
- Quality scan output constraint (T17–T18, AC-10)
- Observe/scan agent tool-list enforcement (T19–T24, AC-15)

## 6. Acceptance criteria

- All four technique skills exist under `assets/skills/fbk-grilling/`, `fbk-fresh-eyes/`, `fbk-quality-scan/`, `fbk-test-review/` with `SKILL.md` files carrying `description` and `argument-hint` frontmatter.
- `fbk-grilling` frontmatter or body contains "Matt Pocock" and the exact source URL.
- `fbk-grilling` body contains "one question at a time" and "Confirmed:".
- `fbk-quality-scan` body specifies a limit of 5 ranked findings.
- `fbk-fresh-eyes-reviewer.md`, `fbk-code-review-detector.md`, and `fbk-test-reviewer.md` each declare no Write or Edit tool.

## 7. Model

Haiku

## 8. Wave

Wave 1
