---
id: task-19
type: test
wave: 1
covers: [AC-02, AC-03, AC-11]
files_to_modify:
  - tests/sdl-workflow/test-code-review-skill.sh
  - tests/sdl-workflow/test-category-migration.sh
completion_gate: "bash tests/sdl-workflow/test-code-review-skill.sh exits 0 && bash tests/sdl-workflow/test-category-migration.sh exits 0"
---

## Objective

Update two existing test files that may break from the SKILL.md orchestrator rewrite and Detector/Challenger persona changes: the skill path-reference tests and the category-to-type migration tests.

## Context

SKILL.md is being updated with the JSON pipeline. The Detector and Challenger agents are being rewritten to persona-driven definitions. The category-to-type migration tests verify that the old "category" terminology was replaced with "type" and "severity" — these should still pass but may need adjustment for the new Detector/Challenger wording.

## Instructions

### File 1: `tests/sdl-workflow/test-code-review-skill.sh`

**Tests 5-9 (lines ~77-115)**: These check SKILL.md for references to `existing-code-review`, `post-impl-review`, `code-review-guide`, `ai-failure-modes`, and path routing language. The orchestrator rewrite preserves these references — they are in the preamble and Entry/Path Routing sections, which are not changed by the pipeline update. Likely no changes needed.

Verify during implementation by running the test file against the rewritten SKILL.md. Only update tests that fail. If the rewrite changes the preamble read instructions (e.g., adds `pipeline.py` to the list of files to read), the path references still exist. The most likely change: if the SKILL.md preamble changes from `Read ... code-review-guide.md for the behavioral comparison methodology, finding format, sighting format` to a different description, test 7's grep for `code-review-guide` would still match.

### File 2: `tests/sdl-workflow/test-category-migration.sh`

**Test 8 (line ~80-88)**: Currently checks the Detector body for `type and severity` not `category`. The new Detector body uses `type` and `severity` in its definitions but may not have the exact phrase `type and severity`. Update the check to be more flexible: grep for `type` and `severity` appearing in the body (both must appear, but not necessarily as the exact phrase "type and severity"). Replace the check with:
```bash
body=$(sed -n '/^---$/,/^---$/!p' "$DETECTOR" | tail -n +2)
has_type=$(echo "$body" | grep -ci 'type' 2>/dev/null || true)
has_sev=$(echo "$body" | grep -ci 'severity' 2>/dev/null || true)
cat_count=$(echo "$body" | grep -ci 'category' 2>/dev/null || true)
if [ "$cat_count" -eq 0 ] && [ "$has_type" -gt 0 ] && [ "$has_sev" -gt 0 ]; then
  ok "Detector output uses type and severity, not category"
else
  not_ok "..."
fi
```
This is the same logic already in test-classification-system.sh test 8 — keep them consistent.

**Test 9 (line ~90-97)**: Currently checks Challenger for `reject.*(as )?nit` and absence of `downgrade.*nit`. The new Challenger contains nit rejection language: "Reject sightings that are technically accurate but functionally irrelevant (naming, formatting, style) as nits." The grep `reject.*(as )?nit` should still match `reject.*nit` in the new text. Also verify `downgrade.*nit` does not appear. Likely no change needed.

## Files to create/modify

Modify: `tests/sdl-workflow/test-code-review-skill.sh`
Modify: `tests/sdl-workflow/test-category-migration.sh`

## Test requirements

Both files remain executable, exit 0/1, TAP conventions.

## Acceptance criteria

- Both test files pass after the SKILL.md and agent persona rewrites
- Minimal changes: only modify tests that actually break
- `test-code-review-skill.sh` path reference tests preserved
- `test-category-migration.sh` type/severity vs category distinction maintained

## Model

sonnet

## Wave

1
