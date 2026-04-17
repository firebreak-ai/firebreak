---
id: task-26
type: implementation
wave: 2
covers: [AC-01, AC-02, AC-03, AC-08, AC-11]
files_to_modify:
  - tests/sdl-workflow/test-classification-system.sh
  - tests/sdl-workflow/test-code-review-guide-extensions.sh
test_tasks: [task-06]
completion_gate: "bash tests/sdl-workflow/test-classification-system.sh exits 0 && bash tests/sdl-workflow/test-code-review-guide-extensions.sh exits 0"
---

## Objective

Update two existing test files with likely breakage from the Detector/Challenger rewrite and guide update. These require verification during implementation.

## Context

Task-21 rewrites the Detector to a persona-driven definition that embeds type and severity definitions inline (not delegated to the orchestrator). Task-24 updates the guide with new consequence-based type definitions. The Detector body from task-21 contains all four type values (`behavioral`, `structural`, `test-integrity`, `fragile`) and all four severity values (`critical`, `major`, `minor`, `info`) directly in its type and severity definition sections. The guide's test-integrity definition changes from "name-scope" language to "passes but does not verify what it claims" and "implies coverage."

## Instructions

Apply every change described in test task-06.

### File 1: `tests/sdl-workflow/test-classification-system.sh`

**Test 8** (~line 80-88): The Detector body from task-21 contains all four type values in its type definitions section. The existing test checks the Detector body for all four types. After task-21 is applied, verify the test still passes as-is. If it does, no change needed.

If the test fails (unexpected wording change), implement the fallback approach: check the Detector body first for all four type values. If not all found, fall back to checking the guide. Use this pattern:

```bash
has_behavioral=$(echo "$body" | grep -c 'behavioral' 2>/dev/null || true)
has_structural=$(echo "$body" | grep -c 'structural' 2>/dev/null || true)
has_test_integrity=$(echo "$body" | grep -c 'test-integrity' 2>/dev/null || true)
has_fragile=$(echo "$body" | grep -c 'fragile' 2>/dev/null || true)
if [ "$has_behavioral" -gt 0 ] && [ "$has_structural" -gt 0 ] && [ "$has_test_integrity" -gt 0 ] && [ "$has_fragile" -gt 0 ]; then
  ok "Type values defined in Detector or guide"
else
  has_behavioral=$(grep -c 'behavioral' "$GUIDE" 2>/dev/null || true)
  has_structural=$(grep -c 'structural' "$GUIDE" 2>/dev/null || true)
  has_test_integrity=$(grep -c 'test-integrity' "$GUIDE" 2>/dev/null || true)
  has_fragile=$(grep -c 'fragile' "$GUIDE" 2>/dev/null || true)
  if [ "$has_behavioral" -gt 0 ] && [ "$has_structural" -gt 0 ] && [ "$has_test_integrity" -gt 0 ] && [ "$has_fragile" -gt 0 ]; then
    ok "Type values defined in Detector or guide"
  else
    not_ok "Type values defined in Detector or guide"
  fi
fi
```

Update the test name to `"Type values defined in Detector or guide"`.

**Test 10** (~line 116-125): Same approach as Test 8 but for severity values. The Detector body from task-21 contains all four severity values. Verify first, apply fallback only if needed. Update test name to `"Severity values defined in Detector or guide"`.

### File 2: `tests/sdl-workflow/test-code-review-guide-extensions.sh`

**Test 2** (~line 35-39): Update the grep pattern from `name.scope|scope.mismatch` to `name.scope|scope.mismatch|does not verify|implies coverage`. Update test name to `"Guide test-integrity includes coverage gap language"`.

## Files to create/modify

Modify: `tests/sdl-workflow/test-classification-system.sh`
Modify: `tests/sdl-workflow/test-code-review-guide-extensions.sh`

## Test requirements

Both files remain executable, exit 0/1, TAP conventions. No changes to tests that do not break.

## Acceptance criteria

- `test-classification-system.sh` tests 8, 10 pass with the new Detector (either directly or via fallback to guide)
- `test-code-review-guide-extensions.sh` test 2 accepts new consequence-based test-integrity language
- Both test files pass after the asset changes from tasks 21, 24

## Model

sonnet

## Wave

2
