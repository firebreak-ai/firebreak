---
id: task-17
type: test
wave: 1
covers: [AC-02, AC-03, AC-08, AC-11]
files_to_modify:
  - tests/sdl-workflow/test-code-review-integration.sh
  - tests/sdl-workflow/test-challenger-extensions.sh
completion_gate: "bash tests/sdl-workflow/test-code-review-integration.sh exits 0 && bash tests/sdl-workflow/test-challenger-extensions.sh exits 0"
---

## Objective

Update two more existing test files with likely breakage from the persona rewrite and orchestrator pipeline update. These are "likely breakage" tests identified in the spec.

## Context

The Detector and Challenger agents are being rewritten with persona-driven definitions. The Challenger now uses JSON output with `status`, `verification_evidence`, `rejection_reason`, and `reclassified_from` fields instead of markdown-style verification/rejection protocols. The SKILL.md orchestrator is being updated to reference `pipeline.py` and JSON-throughout workflow. Sighting ID format (S-NN) and finding ID format (F-NN) are preserved.

## Instructions

### File 1: `tests/sdl-workflow/test-code-review-integration.sh`

**Test 7 (line ~93-97)**: Checks that both Detector and Challenger reference sighting ID format `S-`. The new Detector references `S-01` in examples or sequential IDs. The new Challenger references `S-` via sighting verification. Verify during implementation: if both files still contain `S-`, no change needed. If the Detector no longer contains `S-` (because ID assignment is delegated to the orchestrator), update to check the SKILL.md or guide instead. Use a fallback approach:
```bash
if grep -q 'S-' "$DETECTOR" && grep -q 'S-' "$CHALLENGER"; then
  ok "..."
elif grep -q 'S-' "$SKILL_FILE" && grep -q 'S-' "$CHALLENGER"; then
  ok "..."
else
  not_ok "..."
fi
```

**Test 8 (line ~99-104)**: Checks the guide for orchestration loop/iteration/round combined with sighting/finding/terminat. The updated guide orchestration protocol still uses these terms. Likely no change needed. Verify and update only if the terms changed.

**Test 20 (line ~209-213)**: Checks that Detector uses `S-` sighting IDs and Challenger uses `F-` finding IDs. The new Challenger may not contain `F-` literally if finding ID assignment is delegated to the orchestrator. Update with fallback:
```bash
if grep -q 'S-' "$DETECTOR" && grep -q 'F-' "$CHALLENGER"; then
  ok "..."
elif grep -q 'S-' "$DETECTOR" || grep -q 'S-' "$SKILL_FILE"; then
  # Check that F- assignment exists somewhere in the pipeline
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

**Test 1 (line ~27-29)**: Checks Challenger for `adjacent observation`. The new Challenger persona definition contains `adjacent_observations` as a JSON field name. Update the grep to accept both forms: `grep -qiE 'adjacent.observation' "$CHALLENGER"`. This matches both `adjacent observation` and `adjacent_observations`.

**Test 2 (line ~34-38)**: Checks for `informational|do not.*finding|not.*surface|not.*detection loop|exclude.*finding`. The new Challenger states verdicts only — it does not generate new sightings. Update to also accept `do not generate new sightings` or `not.*sighting` language: `grep -qiE 'informational|do not.*finding|not.*surface|not.*detection|do not generate|not.*new sighting' "$CHALLENGER"`.

**Test 3 (line ~42-44)**: Checks for `caller.trac|trace.*caller|cross.reference.*caller`. The new Challenger contains `trace.*caller` language. Likely no change needed.

**Test 4 (line ~48-52)**: Checks for `behavioral.*caller|behavioral.*trac|caller.*behavioral`. The new Challenger contains `behavioral.*caller` for caller tracing of behavioral sightings. Likely no change needed.

**Test 5 (line ~55-59)**: Checks for `verified.pending.execution`. The new Challenger may not use this exact phrase if the status values are listed differently. Update to also accept the status enum: `grep -qiE 'verified.pending.execution|verified-pending-execution' "$CHALLENGER"`.

**Test 6 (line ~62-66)**: Checks for `test.integrity.*pending|test.integrity.*execution|pending.*test.integrity`. The new Challenger may not explicitly scope verified-pending-execution to test-integrity in the body text. If the Challenger defines the four status values and their usage, verify the association exists. Update to also accept broader language: `grep -qiE 'test.integrity.*pending|test.integrity.*execution|pending.*test|verified-pending-execution' "$CHALLENGER"`.

## Files to create/modify

Modify: `tests/sdl-workflow/test-code-review-integration.sh`
Modify: `tests/sdl-workflow/test-challenger-extensions.sh`

## Test requirements

Both files remain executable, exit 0/1, TAP conventions.

## Acceptance criteria

- `test-code-review-integration.sh` tests 7, 20 updated with fallback checks for delegated ID assignment
- `test-challenger-extensions.sh` tests 1, 2, 5, 6 updated to accept both old and new Challenger language patterns
- All updates are backward-compatible (pass with both old and new asset versions where possible)
- Both test files pass after implementation of the corresponding asset changes

## Model

sonnet

## Wave

1
