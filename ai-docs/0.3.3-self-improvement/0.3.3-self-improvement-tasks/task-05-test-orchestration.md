---
id: task-05
type: test
wave: 1
covers: [AC-60, AC-61, AC-16, AC-17, AC-18, AC-21, AC-22]
files_to_create:
  - tests/sdl-workflow/test-orchestration-extensions.sh
completion_gate: "tests compile and fail before implementation"
---

## Objective

Creates `tests/sdl-workflow/test-orchestration-extensions.sh` — a structural test suite validating the code review skill orchestration additions in SKILL.md and the `linter` detection source value in code-review-guide.md.

## Context

Seven modifications to `assets/skills/fbk-code-review/SKILL.md`:

- AC-60: Pre-spawn linter execution — orchestrator discovers and runs project linters, includes raw text output (truncated to first 100 findings) as supplementary context in Detector spawn prompts. Linter output is context, not pre-formed sightings.
- AC-16: Parallel Detector agent team spawning instruction for broad-scope reviews.
- AC-17: Stuck-agent recovery instruction (relaunch once; if still unresponsive, escalate to user; never perform the agent's work directly).
- AC-18: Cross-unit pattern deduplication and naming instruction.
- AC-21: Inject `quality-detection.md` reference into Detector spawn instructions.
- AC-22: Detection source tagging reminder in Detector spawn instructions.

One modification to `code-review-guide.md`:
- AC-61: Detection source values include `linter` alongside existing `spec-ac`, `checklist`, `structural-target`.

Current state of SKILL.md: The file has sections for Entry and Path Routing, Source of Truth Handling, Agent Team, Detection-Verification Loop, Broad-Scope Reviews, Spec Conflict Detection, and Retrospective. None of the new orchestration instructions exist. The Agent Team section currently mentions `Bash` in the Detector tools line (line 28: `Tools: Read, Grep, Glob, Bash`).

Current state of code-review-guide.md detection source values (lines 32-34): `spec-ac`, `checklist`, `structural-target`. No `linter` value.

Follow the TAP format from existing test files.

## Instructions

1. Create `tests/sdl-workflow/test-orchestration-extensions.sh` with shebang and `set -uo pipefail`.

2. Add standard boilerplate. Define:
   - `SKILL="$PROJECT_ROOT/assets/skills/fbk-code-review/SKILL.md"`
   - `GUIDE="$PROJECT_ROOT/assets/fbk-docs/fbk-sdl-workflow/code-review-guide.md"`

3. Add the following tests:

   **Test 1: SKILL.md contains linter execution instruction (AC-60, AC-09 relocation half)**
   Grep case-insensitively for `linter` in `$SKILL`. Use: `grep -qi 'linter' "$SKILL"`. Test name: "SKILL.md contains linter execution instruction".

   **Test 2: SKILL.md linter instruction mentions truncation (AC-60)**
   Grep for `100` or `truncat` in `$SKILL` near linter context. Use: `grep -qiE 'truncat|100 findings|first 100' "$SKILL"`. Test name: "SKILL.md linter instruction specifies truncation".

   **Test 3: SKILL.md linter instruction mentions supplementary context (AC-60)**
   Grep for `supplementary context` or `context.*not.*sighting` or `not.*pre-formed` in `$SKILL`. Use: `grep -qiE 'supplementary context|not.*pre.formed|context.*not.*sighting' "$SKILL"`. Test name: "SKILL.md linter output described as supplementary context".

   **Test 4: SKILL.md contains parallel spawning instruction (AC-16)**
   Grep for `parallel` in `$SKILL`. Use: `grep -qi 'parallel' "$SKILL"`. Test name: "SKILL.md contains parallel spawning instruction".

   **Test 5: SKILL.md contains stuck-agent recovery instruction (AC-17)**
   Grep for `stuck.agent\|unresponsive.*agent\|relaunch` in `$SKILL`. Use: `grep -qiE 'stuck.agent|unresponsive|relaunch' "$SKILL"`. Test name: "SKILL.md contains stuck-agent recovery instruction".

   **Test 6: Stuck-agent recovery does not allow performing agent's work directly (AC-17)**
   Grep for `never.*perform.*directly\|do not.*perform.*work\|escalate.*user` in `$SKILL`. Use: `grep -qiE 'never.*perform.*direct|do not.*perform|escalate.*user' "$SKILL"`. Test name: "Stuck-agent recovery escalates instead of substituting".

   **Test 7: SKILL.md contains pattern deduplication instruction (AC-18)**
   Grep for `deduplicat\|cross.unit.*pattern\|pattern.*dedup\|pattern.*group` in `$SKILL`. Use: `grep -qiE 'deduplicat|cross.unit.*pattern|pattern.*(dedup|group|naming)' "$SKILL"`. Test name: "SKILL.md contains pattern deduplication instruction".

   **Test 8: SKILL.md Detector spawn references quality-detection.md (AC-21)**
   Grep for `quality-detection` in `$SKILL`. Use: `grep -q 'quality-detection' "$SKILL"`. Test name: "SKILL.md Detector spawn references quality-detection.md".

   **Test 9: SKILL.md Detector spawn includes detection source tagging (AC-22)**
   Grep for `detection source` in `$SKILL`. Use: `grep -qi 'detection source' "$SKILL"`. Test name: "SKILL.md Detector spawn includes detection source tagging".

   **Test 10: code-review-guide.md detection source values include linter (AC-61)**
   Grep for `linter` as a detection source value in `$GUIDE`. Use: `grep -qi 'linter' "$GUIDE"`. Test name: "Guide detection source values include linter".

4. Add standard summary footer.

5. Make the file executable.

## Files to create/modify

- `tests/sdl-workflow/test-orchestration-extensions.sh` (create)

## Test requirements

10 structural tests covering AC-60, AC-61, AC-16, AC-17, AC-18, AC-21, AC-22. Tests must fail before implementation.

## Acceptance criteria

- AC-60: Tests 1-3 verify linter instruction with truncation and supplementary context framing.
- AC-16: Test 4 verifies parallel spawning instruction.
- AC-17: Tests 5-6 verify stuck-agent recovery with escalation (no direct substitution).
- AC-18: Test 7 verifies pattern deduplication instruction.
- AC-21: Test 8 verifies quality-detection.md reference in spawn instructions.
- AC-22: Test 9 verifies detection source tagging in spawn instructions.
- AC-61: Test 10 verifies linter detection source value in guide.

## Model

Haiku

## Wave

Wave 1
