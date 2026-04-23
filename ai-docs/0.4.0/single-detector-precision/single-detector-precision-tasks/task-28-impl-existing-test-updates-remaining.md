---
id: task-28
type: implementation
wave: 3
covers: [AC-02, AC-03, AC-08, AC-11]
files_to_modify:
  - tests/sdl-workflow/test-code-review-integration.sh
  - tests/sdl-workflow/test-challenger-extensions.sh
test_tasks: [task-17]
completion_gate: "bash tests/sdl-workflow/test-code-review-integration.sh exits 0 && bash tests/sdl-workflow/test-challenger-extensions.sh exits 0"
---

## Objective

Update two existing test files with likely breakage from the persona rewrite and orchestrator pipeline update. These test Detector/Challenger ID formats and Challenger extension features.

## Context

Task-21 rewrites the Detector. Task-22 rewrites the Challenger. Task-27 updates SKILL.md. The new Detector and Challenger may not contain `S-` or `F-` ID format strings if ID assignment is fully delegated to the orchestrator. The new Challenger uses JSON field names like `adjacent_observations` instead of prose like "adjacent observation."

The SKILL.md variable path in the test file is `SKILL_FILE="$PROJECT_ROOT/assets/skills/fbk-code-review/SKILL.md"`. Verify this variable exists in the test file; if not, add it to the variable definitions block.

## Instructions

Apply every change described in test task-17.

### File 1: `tests/sdl-workflow/test-code-review-integration.sh`

**Test 7** (~line 93-97): Currently checks Detector and Challenger both contain `S-`. The new Detector from task-21 contains `S-01` in its examples. The new Challenger from task-22 does not contain `S-` — it refers to "sightings provided by the orchestrator." Add a fallback: if both Detector and Challenger contain `S-`, pass. Otherwise, if SKILL.md and Challenger together reference sighting IDs, pass. Use:

```bash
if grep -q 'S-' "$DETECTOR" && grep -q 'S-' "$CHALLENGER"; then
  ok "..."
elif grep -q 'S-' "$SKILL_FILE" && grep -q 'sighting' "$CHALLENGER"; then
  ok "..."
else
  not_ok "..."
fi
```

Ensure `SKILL_FILE` is defined in the variable block at the top of the test.

**Test 8** (~line 99-104): Check guide for orchestration terms. The updated guide still uses `round`, `terminat`, and `sighting`/`finding`. Verify during implementation — likely no change needed.

**Test 20** (~line 209-213): Currently checks Detector uses `S-` and Challenger uses `F-`. The new Challenger from task-22 does not contain `F-` literally — finding ID assignment is in the orchestrator. Add fallback:

```bash
if grep -q 'S-' "$DETECTOR" && grep -q 'F-' "$CHALLENGER"; then
  ok "..."
elif grep -q 'S-' "$DETECTOR" || grep -q 'S-' "$SKILL_FILE"; then
  if grep -q 'F-' "$CHALLENGER" || grep -q 'F-' "$SKILL_FILE" || grep -q 'finding_id' "$SKILL_FILE"; then
    ok "..."
  else
    not_ok "..."
  fi
else
  not_ok "..."
fi
```

### File 2: `tests/sdl-workflow/test-challenger-extensions.sh`

**Test 1** (~line 27-29): Update grep to `grep -qiE 'adjacent.observation' "$CHALLENGER"` to match both `adjacent observation` and `adjacent_observations`.

**Test 2** (~line 34-38): Update grep to include new Challenger language: `grep -qiE 'informational|do not.*finding|not.*surface|not.*detection|do not generate|not.*new sighting' "$CHALLENGER"`.

**Test 3** (~line 42-44): Likely no change — the new Challenger contains "trace" and "caller" language. Verify.

**Test 4** (~line 48-52): Likely no change — the new Challenger contains "behavioral" and "caller" language. Verify.

**Test 5** (~line 55-59): Update grep to `grep -qiE 'verified.pending.execution|verified-pending-execution' "$CHALLENGER"`.

**Test 6** (~line 62-66): Update grep to `grep -qiE 'test.integrity.*pending|test.integrity.*execution|pending.*test|verified-pending-execution' "$CHALLENGER"`.

## Files to create/modify

Modify: `tests/sdl-workflow/test-code-review-integration.sh`
Modify: `tests/sdl-workflow/test-challenger-extensions.sh`

## Test requirements

Both files remain executable, exit 0/1, TAP conventions. Only modify tests that actually break.

## Acceptance criteria

- `test-code-review-integration.sh` tests 7, 20 handle delegated ID assignment with fallback to SKILL.md
- `test-challenger-extensions.sh` tests 1, 2, 5, 6 accept both old and new Challenger language patterns
- Both test files pass after the asset changes from tasks 21, 22, 27

## Model

sonnet

## Wave

3
