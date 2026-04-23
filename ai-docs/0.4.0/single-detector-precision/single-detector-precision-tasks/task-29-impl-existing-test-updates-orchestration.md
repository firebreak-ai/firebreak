---
id: task-29
type: implementation
wave: 3
covers: [AC-08, AC-11]
files_to_modify:
  - tests/sdl-workflow/test-orchestration-extensions.sh
  - tests/sdl-workflow/test-instruction-hygiene-orchestration.sh
test_tasks: [task-18]
completion_gate: "bash tests/sdl-workflow/test-orchestration-extensions.sh exits 0 && bash tests/sdl-workflow/test-instruction-hygiene-orchestration.sh exits 0"
---

## Objective

Update two existing test files that test SKILL.md and guide orchestration content, which may break from the orchestrator pipeline rewrite.

## Context

Task-27 updates SKILL.md's Detection-Verification Loop to reference `pipeline.py` and JSON. Task-24 updates the guide's Orchestration Protocol. The key preserved properties are: stuck-agent recovery, quality-detection reference, detection source tagging, and content-first ordering. These tests verify those properties survive the rewrite.

## Instructions

Apply the verification approach from test task-18. Run each test file against the rewritten assets. Only modify tests that fail.

### File 1: `tests/sdl-workflow/test-orchestration-extensions.sh`

**Test 5** (~line 57-61): Checks SKILL.md for `stuck.agent|unresponsive|relaunch`. The SKILL.md rewrite from task-27 preserves the Stuck-Agent Recovery section unchanged. This test should pass without modification. Verify and skip if passing.

**Test 8** (~line 78-82): Checks SKILL.md Detector spawn references `quality-detection`. The new Detection-Verification Loop step 1 still includes `quality-detection.md`. This test should pass without modification. Verify and skip if passing.

**Test 9** (~line 84-88): Checks SKILL.md for `detection source` tagging. The new Detection-Verification Loop step 1 still instructs tagging detection sources. This test should pass without modification. Verify and skip if passing.

For each test: run against the rewritten SKILL.md. Only update if the grep pattern fails to match due to wording changes. If the content moved within SKILL.md but the grep still matches (since these tests grep the full file), no change is needed.

### File 2: `tests/sdl-workflow/test-instruction-hygiene-orchestration.sh`

**Test 1** (~line 30-33): Checks SKILL.md step 1 for content-first ordering (`contents? first|code.*first.*then.*instructions|file contents first`). The new SKILL.md step 1 says "target code file contents first, then linter output..." — the phrase "file contents first" still matches the pattern `file contents first`. This test should pass. Verify and skip if passing.

**Test 2** (~line 36-40): Checks Challenger spawn for content-first ordering. The new SKILL.md step 4 says "target code file contents first, then the filtered JSON sightings..." The test likely uses `grep -A3 'Spawn Challenger'` or similar anchor. If the anchor text changed from "Spawn Challenger" to the numbered step format, update the anchor. The new text uses "Spawn Challenger with:" in step 4 — check whether the test searches for the exact string. If the test uses `sed -n` with a section heading that no longer exists, update to search for the Challenger spawn step directly:

```bash
# If old anchor was: sed -n '/Spawn Challenger/,/^[0-9]/p'
# New anchor: grep for the Challenger spawn line in the detection loop
section=$(sed -n '/## Detection-Verification Loop/,/^## /p' "$SKILL")
echo "$section" | grep -qiE 'Challenger.*first|Challenger.*code.*content'
```

**Test 6** (~line 65-69): Checks guide Orchestration Protocol for content-first ordering language. The new guide Orchestration Protocol step 1 says "target code file contents first." This test should match. Verify and skip if passing.

### Implementation approach

1. Run both test files against the rewritten assets (after tasks 24, 27)
2. For each failing test, read the specific test code, identify what changed, and update the grep pattern to match the new wording while testing the same underlying property
3. For tests that pass, make no changes

## Files to create/modify

Modify: `tests/sdl-workflow/test-orchestration-extensions.sh`
Modify: `tests/sdl-workflow/test-instruction-hygiene-orchestration.sh`

## Test requirements

Both files remain executable, exit 0/1, TAP conventions. Minimal changes.

## Acceptance criteria

- Both test files pass after the SKILL.md and guide orchestration rewrite
- Tests continue to verify: stuck-agent recovery, quality-detection reference, detection source tagging, content-first ordering
- Only tests that actually break are modified

## Model

sonnet

## Wave

3
