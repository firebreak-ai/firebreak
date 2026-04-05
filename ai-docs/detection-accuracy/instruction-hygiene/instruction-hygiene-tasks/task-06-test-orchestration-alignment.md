---
id: task-06
type: test
wave: 1
covers: [AC-07, AC-12, AC-13]
files_to_create:
  - tests/sdl-workflow/test-instruction-hygiene-orchestration.sh
completion_gate: "tests compile and fail before implementation"
---

## Objective

Creates a new shell test file verifying SKILL.md prompt ordering, SKILL.md initial read instructions, and `code-review-guide.md` alignment changes.

## Context

The instruction hygiene spec makes three orchestration-layer changes:
- SKILL.md steps 1 and 3 rewritten to specify content-first/instructions-last ordering (AC-07)
- SKILL.md initial read instructions include both `ai-failure-modes` and `quality-detection` (AC-12)
- `code-review-guide.md` Source of Truth Handling removes "Supplement with" hierarchy language; Orchestration Protocol step 1 reflects content-first ordering (AC-13)

The SKILL.md file is at `assets/skills/fbk-code-review/SKILL.md`. Follow the TAP format convention from existing test files.

## Instructions

1. Create `tests/sdl-workflow/test-instruction-hygiene-orchestration.sh` with the standard boilerplate. Define variables:
   - `SKILL="$PROJECT_ROOT/assets/skills/fbk-code-review/SKILL.md"`
   - `GUIDE="$PROJECT_ROOT/assets/fbk-docs/fbk-sdl-workflow/code-review-guide.md"`

2. Add Test 1 (AC-07): assert SKILL.md contains content-first ordering language in step 1. Use `grep -qiE 'contents? first|code.*first.*then.*instructions|file contents first' "$SKILL"`.

3. Add Test 2 (AC-07): assert SKILL.md step 3 contains content-first ordering language. Extract the step 3 context (search for "Spawn Challenger" in SKILL.md) and verify it contains ordering language. Use `grep -A3 'Spawn Challenger' "$SKILL" | grep -qiE 'contents? first|code.*first|file contents first'`.

4. Add Test 3 (AC-12): assert SKILL.md initial read instructions reference `ai-failure-modes`. The initial read instructions are near the top of the file (lines 10-11 area). Use `head -20 "$SKILL" | grep -qi 'ai-failure-modes'`.

5. Add Test 4 (AC-12): assert SKILL.md initial read instructions reference `quality-detection`. Use `head -20 "$SKILL" | grep -qi 'quality-detection'`.

6. Add Test 5 (AC-13): assert `code-review-guide.md` Source of Truth Handling does NOT contain "Supplement with" hierarchy language. Use `! grep -qi 'supplement with' "$GUIDE"`.

7. Add Test 6 (AC-13): assert `code-review-guide.md` Orchestration Protocol step 1 contains content-first ordering language. Use `sed -n '/## Orchestration Protocol/,/^## /p' "$GUIDE" | grep -qiE 'contents? first|code.*first|file contents first'`.

8. Add the standard summary block. Make the file executable.

## Files to create/modify

- `tests/sdl-workflow/test-instruction-hygiene-orchestration.sh` (create)

## Test requirements

New shell tests (6 tests total):
- Tests 1-2: AC-07 SKILL.md content-first ordering in steps 1 and 3 (will fail pre-implementation)
- Tests 3-4: AC-12 SKILL.md initial reads reference both documents (Test 3 passes now since ai-failure-modes is already referenced; Test 4 will fail pre-implementation since quality-detection is not in the initial reads)
- Tests 5-6: AC-13 guide alignment (Test 5 will fail pre-implementation since "Supplement with" currently exists; Test 6 will fail pre-implementation since Orchestration Protocol lacks ordering language)

## Acceptance criteria

- AC-07: Tests verify SKILL.md steps 1 and 3 specify content-first ordering. Note: UV-7 (runtime observation of actual prompt construction order) is a human verification step not covered by this automated test. These tests verify the orchestrator's instructions contain the correct ordering; UV-7 verifies the orchestrator follows them.
- AC-12: Tests verify SKILL.md initial reads include both ai-failure-modes and quality-detection
- AC-13: Tests verify code-review-guide.md removes hierarchy language and Orchestration Protocol reflects ordering

## Model

Haiku

## Wave

Wave 1
