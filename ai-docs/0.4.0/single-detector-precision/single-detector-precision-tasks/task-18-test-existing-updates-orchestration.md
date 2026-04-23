---
id: task-18
type: test
wave: 1
covers: [AC-08, AC-11]
files_to_modify:
  - tests/sdl-workflow/test-orchestration-extensions.sh
  - tests/sdl-workflow/test-instruction-hygiene-orchestration.sh
completion_gate: "bash tests/sdl-workflow/test-orchestration-extensions.sh exits 0 && bash tests/sdl-workflow/test-instruction-hygiene-orchestration.sh exits 0"
---

## Objective

Update two existing test files that test SKILL.md and guide orchestration content, which may break from the orchestrator pipeline rewrite.

## Context

SKILL.md is being updated to reference `pipeline.py` for JSON validation, domain filtering, severity filtering, and markdown conversion. The Detection-Verification Loop changes from markdown-based agent communication to JSON-throughout with a single markdown conversion at the end. The guide's Orchestration Protocol section is updated to match.

## Instructions

### File 1: `tests/sdl-workflow/test-orchestration-extensions.sh`

**Test 5 (line ~57-61)**: Checks SKILL.md for `stuck.agent|unresponsive|relaunch`. The orchestrator rewrite preserves the Stuck-Agent Recovery section. Likely no change needed. Verify during implementation.

**Test 8 (line ~78-82)**: Checks SKILL.md Detector spawn references `quality-detection`. The new Detection-Verification Loop still includes quality-detection.md in the Detector spawn prompt. Likely no change needed. Verify during implementation.

**Test 9 (line ~84-88)**: Checks SKILL.md for `detection source` tagging. The new pipeline still tags detection sources. Likely no change needed. Verify during implementation.

For tests 5, 8, 9: verify they still pass after the SKILL.md rewrite. Only modify if the specific wording has changed. If `quality-detection` or `detection source` references move within SKILL.md but still exist, no change is needed.

### File 2: `tests/sdl-workflow/test-instruction-hygiene-orchestration.sh`

**Test 1 (line ~30-33)**: Checks SKILL.md step 1 for `contents? first|code.*first.*then.*instructions|file contents first`. The new SKILL.md Detection-Verification Loop step 1 still specifies content-first ordering: the Detector receives "target code file contents first, then..." Likely no change needed. Verify during implementation.

**Test 2 (line ~36-40)**: Checks `Spawn Challenger` section for content-first ordering. The new SKILL.md step 3 (Challenger spawn) still specifies "target code file contents first, then sightings to verify, then verification instructions last." Likely no change needed. Verify during implementation.

**Test 6 (line ~65-69)**: Checks guide Orchestration Protocol for content-first ordering language. The new guide Orchestration Protocol step 1 still specifies "target code file contents first." Likely no change needed. Verify during implementation.

For all three tests: these check for content-first ordering which is a principle that survives the rewrite. However, if the exact section heading `## Detection-Verification Loop` changes or the `Spawn Challenger` text changes, update the grep context accordingly. The most likely required change is if `Spawn Challenger` becomes part of a numbered list without a heading — in that case, update the `grep -A3 'Spawn Challenger'` to search for the appropriate anchor text.

### Verification approach for both files

Run each test file against the current (pre-rewrite) assets. Note which tests pass. After the asset rewrite, run again and update only the tests that fail. For each failing test:
1. Read the current SKILL.md/guide to find the new location of the tested content
2. Update the grep pattern to match the new wording while testing the same property
3. Update the test name if the wording change is significant

## Files to create/modify

Modify: `tests/sdl-workflow/test-orchestration-extensions.sh`
Modify: `tests/sdl-workflow/test-instruction-hygiene-orchestration.sh`

## Test requirements

Both files remain executable, exit 0/1, TAP conventions.

## Acceptance criteria

- Both test files pass after the SKILL.md and guide orchestration rewrite
- Minimal changes: only modify tests that actually break
- Tests continue to verify the same properties (stuck-agent recovery, quality-detection reference, detection source tagging, content-first ordering)

## Model

sonnet

## Wave

1
