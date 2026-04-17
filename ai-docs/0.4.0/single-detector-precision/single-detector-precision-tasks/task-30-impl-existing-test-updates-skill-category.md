---
id: task-30
type: implementation
wave: 3
covers: [AC-02, AC-03, AC-11]
files_to_modify:
  - tests/sdl-workflow/test-code-review-skill.sh
  - tests/sdl-workflow/test-category-migration.sh
test_tasks: [task-19]
completion_gate: "bash tests/sdl-workflow/test-code-review-skill.sh exits 0 && bash tests/sdl-workflow/test-category-migration.sh exits 0"
---

## Objective

Update two existing test files that may break from the SKILL.md orchestrator rewrite and Detector/Challenger persona changes: the skill path-reference tests and the category-to-type migration tests.

## Context

Task-27 updates SKILL.md with the JSON pipeline. Tasks 21 and 22 rewrite the Detector and Challenger agents. The category-to-type migration tests verify that the old "category" terminology was replaced with "type" and "severity." The Detector from task-21 contains `type` and `severity` in its definitions but may not use the exact phrase "type and severity."

## Instructions

Apply the changes described in test task-19 using the verify-first approach.

### File 1: `tests/sdl-workflow/test-code-review-skill.sh`

**Tests 5-9** (~lines 77-115): These check SKILL.md for path references to `existing-code-review`, `post-impl-review`, `code-review-guide`, `ai-failure-modes`, and path routing language. The SKILL.md rewrite from task-27 only changes the Detection-Verification Loop section — the preamble read instructions and Entry/Path Routing sections are unchanged. These tests should pass without modification.

Run the test file against the rewritten SKILL.md. Only update tests that fail. If any path reference moved or was removed, update the grep to match the new location.

### File 2: `tests/sdl-workflow/test-category-migration.sh`

**Test 8** (~line 80-88): Currently checks the Detector body for `type and severity` not `category`. The new Detector body from task-21 uses `type` and `severity` extensively in its definitions but may not have the exact phrase "type and severity." Update the check to be more flexible — grep for both `type` and `severity` appearing in the body (both must appear), and `category` must NOT appear:

```bash
body=$(awk '/^---$/{c++; if(c==2){found=1; next}} found' "$DETECTOR")
has_type=$(echo "$body" | grep -ci 'type' 2>/dev/null || true)
has_sev=$(echo "$body" | grep -ci 'severity' 2>/dev/null || true)
cat_count=$(echo "$body" | grep -ci 'category' 2>/dev/null || true)
if [ "$cat_count" -eq 0 ] && [ "$has_type" -gt 0 ] && [ "$has_sev" -gt 0 ]; then
  ok "Detector output uses type and severity, not category"
else
  not_ok "Detector output uses type and severity, not category" "type=$has_type severity=$has_sev category=$cat_count"
fi
```

Use the body extraction method that matches the existing test pattern in this file (check whether it uses `sed` or `awk` for frontmatter extraction).

**Test 9** (~line 90-97): Checks Challenger for `reject.*(as )?nit` and absence of `downgrade.*nit`. The new Challenger from task-22 contains "Reject sightings that are technically accurate but functionally irrelevant (naming, formatting, style) as nits." The existing grep pattern should match. Verify and skip if passing.

### Implementation approach

1. Run both test files against the rewritten assets (after tasks 21, 22, 27)
2. For each failing test, apply the specific update described above
3. For tests that pass, make no changes

## Files to create/modify

Modify: `tests/sdl-workflow/test-code-review-skill.sh`
Modify: `tests/sdl-workflow/test-category-migration.sh`

## Test requirements

Both files remain executable, exit 0/1, TAP conventions. Minimal changes.

## Acceptance criteria

- Both test files pass after the SKILL.md and agent persona rewrites
- `test-code-review-skill.sh` path reference tests preserved
- `test-category-migration.sh` type/severity vs category distinction maintained
- Only tests that actually break are modified

## Model

sonnet

## Wave

3
