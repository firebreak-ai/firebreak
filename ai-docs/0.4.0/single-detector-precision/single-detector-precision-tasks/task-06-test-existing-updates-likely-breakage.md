---
id: task-06
type: test
wave: 1
covers: [AC-01, AC-02, AC-03, AC-08, AC-11]
files_to_modify:
  - tests/sdl-workflow/test-classification-system.sh
  - tests/sdl-workflow/test-code-review-guide-extensions.sh
completion_gate: "bash tests/sdl-workflow/test-classification-system.sh exits 0 && bash tests/sdl-workflow/test-code-review-guide-extensions.sh exits 0"
---

## Objective

Update two existing test files with likely breakage from the Detector/Challenger rewrite and guide update. These require verification during implementation — the spec flagged them as probable breakage.

## Context

The Detector is being rewritten to a persona-driven definition that delegates type/severity values to the orchestrator via a reference to `code-review-guide.md`. The new Detector body does not enumerate all four type values or all four severity values inline — it references "the type and severity definitions provided by the orchestrator." The Challenger is rewritten similarly. The guide's test-integrity definition is being updated with new consequence-based language.

## Instructions

### File 1: `tests/sdl-workflow/test-classification-system.sh`

**Test 8 (line ~80-88)**: Currently checks the Detector body for all four type values (`behavioral`, `structural`, `test-integrity`, `fragile`) appearing literally. The new Detector body contains `behavioral` (in the type definition for behavioral) but delegates the other type values to the orchestrator. However, the new Detector DOES contain all four type values in its embedded type definitions (section 4.4 of the spec is embedded in the Detector). Verify during implementation: if the Detector body contains all four type values, no change needed. If the new Detector only references "the type and severity definitions provided by the orchestrator" without listing them, update Test 8 to check the guide instead of the Detector body. The update would change `echo "$body"` to `cat "$GUIDE"` in the grep commands. Update the test name to `"Type values defined in Detector or guide"`.

**Test 10 (line ~116-125)**: Currently checks the Detector body for all four severity values (`critical`, `major`, `minor`, `info`) appearing literally. Same situation as Test 8. If the new Detector contains severity definitions inline, no change needed. If not, redirect to check the guide. Update test name to `"Severity values defined in Detector or guide"`.

For both tests 8 and 10: implement a fallback approach. Check the Detector body first; if all values are found, pass. If not all values are found in the Detector, check the guide as fallback. Example pattern:
```bash
has_behavioral=$(echo "$body" | grep -c 'behavioral' 2>/dev/null || true)
# ... check all four
if [ "$has_behavioral" -gt 0 ] && ... ; then
  ok "..."
else
  # Fallback: check guide
  has_behavioral=$(grep -c 'behavioral' "$GUIDE" 2>/dev/null || true)
  # ...
  if [ "$has_behavioral" -gt 0 ] && ... ; then
    ok "..."
  else
    not_ok "..."
  fi
fi
```

### File 2: `tests/sdl-workflow/test-code-review-guide-extensions.sh`

**Test 2 (line ~35-39)**: Currently checks guide test-integrity definition for `name.scope|scope.mismatch`. The new test-integrity definition uses consequence-based language: "A test passes but does not verify what it claims. The test name, docstring, or surrounding context implies coverage that the assertions do not provide." The phrase `name-scope` may or may not survive. Update the grep to also accept the new language: change pattern from `name.scope|scope.mismatch` to `name.scope|scope.mismatch|does not verify|implies coverage`. Update test name to `"Guide test-integrity includes coverage gap language"`.

## Files to create/modify

Modify: `tests/sdl-workflow/test-classification-system.sh`
Modify: `tests/sdl-workflow/test-code-review-guide-extensions.sh`

## Test requirements

Both files must remain executable, exit 0/1, TAP conventions.

## Acceptance criteria

- `test-classification-system.sh` tests 8 and 10 updated with fallback to guide when Detector delegates type/severity definitions
- `test-code-review-guide-extensions.sh` test 2 updated to accept new consequence-based test-integrity language
- No changes to tests that do not break
- Both test files pass after implementation of the corresponding asset changes

## Model

sonnet

## Wave

1
