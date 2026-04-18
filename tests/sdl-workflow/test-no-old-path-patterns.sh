#!/usr/bin/env bash

# Test: Verify all context asset files contain no old path patterns
# Task: task-19 (AC-06)
# Acceptance Criteria: all 38 references updated, no old path patterns remain

set -e

# Define the 11 context asset files
declare -a files=(
  "assets/skills/fbk-spec/SKILL.md"
  "assets/skills/fbk-spec-review/SKILL.md"
  "assets/skills/fbk-breakdown/SKILL.md"
  "assets/skills/fbk-implement/SKILL.md"
  "assets/skills/fbk-code-review/SKILL.md"
  "assets/skills/fbk-council/SKILL.md"
  "assets/skills/fbk-code-review/references/existing-code-review.md"
  "assets/fbk-docs/fbk-sdl-workflow/code-review-guide.md"
  "assets/fbk-docs/fbk-sdl-workflow/verify-yml-schema.md"
  "assets/fbk-docs/fbk-sdl-workflow/corrective-workflow.md"
  "assets/settings.json"
)

fail_count=0

# Test 1: grep all files for hooks/fbk-sdl-workflow — assert zero matches
echo "Test 1: Checking for 'hooks/fbk-sdl-workflow' references..."
test1_count=$(grep -r "hooks/fbk-sdl-workflow" "${files[@]}" 2>/dev/null | wc -l)
if [ "$test1_count" -eq 0 ]; then
  echo "  PASS: zero matches"
else
  echo "  FAIL: found $test1_count matches"
  grep -r "hooks/fbk-sdl-workflow" "${files[@]}" 2>/dev/null | sed 's/^/    /'
  ((fail_count++))
fi

# Test 2: grep all files for scripts/fbk-pipeline — assert zero matches
echo "Test 2: Checking for 'scripts/fbk-pipeline' references..."
test2_count=$(grep -r "scripts/fbk-pipeline" "${files[@]}" 2>/dev/null | wc -l)
if [ "$test2_count" -eq 0 ]; then
  echo "  PASS: zero matches"
else
  echo "  FAIL: found $test2_count matches"
  grep -r "scripts/fbk-pipeline" "${files[@]}" 2>/dev/null | sed 's/^/    /'
  ((fail_count++))
fi

# Test 3: grep all files for uv run — assert zero matches
echo "Test 3: Checking for 'uv run' references..."
test3_count=$(grep -r "uv run" "${files[@]}" 2>/dev/null | wc -l)
if [ "$test3_count" -eq 0 ]; then
  echo "  PASS: zero matches"
else
  echo "  FAIL: found $test3_count matches"
  grep -r "uv run" "${files[@]}" 2>/dev/null | sed 's/^/    /'
  ((fail_count++))
fi

# Test 4: grep all files for ~/.claude/skills/fbk-council/ — assert zero matches
echo "Test 4: Checking for '~/.claude/skills/fbk-council/' references..."
test4_count=$(grep -r "~/.claude/skills/fbk-council/" "${files[@]}" 2>/dev/null | wc -l)
if [ "$test4_count" -eq 0 ]; then
  echo "  PASS: zero matches"
else
  echo "  FAIL: found $test4_count matches"
  grep -r "~/.claude/skills/fbk-council/" "${files[@]}" 2>/dev/null | sed 's/^/    /'
  ((fail_count++))
fi

# Report results
echo ""
if [ "$fail_count" -eq 0 ]; then
  echo "All tests passed!"
  exit 0
else
  echo "FAILED: $fail_count test(s) failed"
  exit 1
fi
