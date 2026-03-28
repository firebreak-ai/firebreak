#!/usr/bin/env bash
set -uo pipefail

PASS=0
FAIL=0
TOTAL=0

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
PROJECT_ROOT="$(cd "$SCRIPT_DIR/../.." && pwd)"
SKILL_FILE="$PROJECT_ROOT/assets/skills/fbk-breakdown/SKILL.md"
BROWNFIELD_DOC="$PROJECT_ROOT/assets/fbk-docs/fbk-brownfield-breakdown.md"

ok() {
  TOTAL=$((TOTAL + 1))
  PASS=$((PASS + 1))
  echo "ok $TOTAL - $1"
}

not_ok() {
  TOTAL=$((TOTAL + 1))
  FAIL=$((FAIL + 1))
  echo "not ok $TOTAL - $1"
  [ -n "${2:-}" ] && echo "# $2"
}

echo "TAP version 13"

# --- Test 1: skill file exists ---
if [ -s "$SKILL_FILE" ]; then
  ok "skill file exists and is non-empty"
else
  not_ok "skill file exists and is non-empty"
fi

# --- Test 2: skill file has valid YAML frontmatter ---
first=$(head -1 "$SKILL_FILE")
closing=$(grep -c '^---$' "$SKILL_FILE")
has_desc=$(sed -n '2,/^---$/p' "$SKILL_FILE" | grep -c 'description:')
if [ "$first" = "---" ] && [ "$closing" -ge 2 ] && [ "$has_desc" -gt 0 ]; then
  ok "skill file has valid YAML frontmatter with description"
else
  not_ok "skill file has valid YAML frontmatter with description"
fi

# --- Test 3: skill specifies sequential agent execution ---
CONTENT=$(cat "$SKILL_FILE")
if echo "$CONTENT" | grep -qiE 'sequential|first.*then|step 1.*step 2|after.*completes|followed by'; then
  ok "skill specifies sequential agent execution"
else
  not_ok "skill specifies sequential agent execution"
fi

# --- Test 4: skill defines test task agent ---
if echo "$CONTENT" | grep -qiE 'test task agent|test task.*agent|test task.*teammate'; then
  ok "skill defines test task agent"
else
  not_ok "skill defines test task agent"
fi

# --- Test 5: test task agent receives only the spec ---
test_task_section=$(awk '/^## Test task agent/,/^## Implementation task agent/' "$SKILL_FILE")
if echo "$test_task_section" | grep -qiE 'only the spec|spec file|spec.*only'; then
  ok "test task agent receives only the spec"
else
  not_ok "test task agent receives only the spec"
fi

# --- Test 6: skill defines implementation task agent ---
if echo "$CONTENT" | grep -qiE 'implementation task agent|implementation task.*agent|implementation task.*teammate'; then
  ok "skill defines implementation task agent"
else
  not_ok "skill defines implementation task agent"
fi

# --- Test 7: implementation task agent receives spec plus test task output ---
impl_section=$(awk '/^## Implementation task agent/,/^## Task overview/' "$SKILL_FILE")
if echo "$impl_section" | grep -qiE 'spec.*test task|spec file.*test task|test task files'; then
  ok "implementation task agent receives spec plus test task output"
else
  not_ok "implementation task agent receives spec plus test task output"
fi

# --- Test 8: skill specifies Agent Teams invocation ---
at_count=$(echo "$CONTENT" | grep -ciE 'Agent Teams|teammate')
if [ "$at_count" -ge 2 ]; then
  ok "skill specifies Agent Teams invocation (${at_count} references)"
else
  not_ok "skill specifies Agent Teams invocation (need 2+, got $at_count)"
fi

# --- Test 9: implementation agent receives artifacts not reasoning ---
if echo "$CONTENT" | grep -qiE 'artifacts.*not.*reasoning|not.*reasoning|independent context|task files as artifacts'; then
  ok "implementation agent receives artifacts not reasoning"
else
  not_ok "implementation agent receives artifacts not reasoning"
fi

# --- Test 10: test task agent ordered before implementation task agent ---
test_line=$(grep -n '## Test task agent' "$SKILL_FILE" | head -1 | cut -d: -f1)
impl_line=$(grep -n '## Implementation task agent' "$SKILL_FILE" | head -1 | cut -d: -f1)
if [ -n "$test_line" ] && [ -n "$impl_line" ] && [ "$test_line" -lt "$impl_line" ]; then
  ok "test task agent ordered before implementation task agent"
else
  not_ok "test task agent ordered before implementation task agent" "test=$test_line impl=$impl_line"
fi

# --- Test 11: skill preserves existing breakdown-gate ---
if grep -qi 'breakdown-gate' "$SKILL_FILE"; then
  ok "skill preserves existing breakdown-gate invocation"
else
  not_ok "skill preserves existing breakdown-gate invocation"
fi

# --- Test 12: skill references task reviewer ---
if grep -qiE 'task-reviewer|task reviewer' "$SKILL_FILE"; then
  ok "skill references task reviewer"
else
  not_ok "skill references task reviewer"
fi

# --- Test 13: skill references test reviewer checkpoint 2 ---
if grep -qiE 'checkpoint 2|test reviewer' "$SKILL_FILE" && grep -qiE 'test reviewer|test-reviewer' "$SKILL_FILE"; then
  ok "skill references test reviewer checkpoint 2"
else
  not_ok "skill references test reviewer checkpoint 2"
fi

# --- Test 14: brownfield doc exists ---
if [ -s "$BROWNFIELD_DOC" ]; then
  ok "brownfield doc exists and is non-empty"
else
  not_ok "brownfield doc exists and is non-empty"
fi

# --- Test 15: brownfield doc — search for related functionality ---
if grep -qi 'search' "$BROWNFIELD_DOC" && grep -qiE 'related|existing|functionality' "$BROWNFIELD_DOC"; then
  ok "brownfield doc contains search-for-related-functionality instruction"
else
  not_ok "brownfield doc contains search-for-related-functionality instruction"
fi

# --- Test 16: brownfield doc — reference files by path ---
if grep -qiE 'reference|path' "$BROWNFIELD_DOC" && grep -qiE 'file|existing code' "$BROWNFIELD_DOC"; then
  ok "brownfield doc contains reference-files-by-path instruction"
else
  not_ok "brownfield doc contains reference-files-by-path instruction"
fi

# --- Test 17: brownfield doc — follow established patterns ---
if grep -qi 'pattern' "$BROWNFIELD_DOC" && grep -qiE 'follow|established' "$BROWNFIELD_DOC"; then
  ok "brownfield doc contains follow-established-patterns instruction"
else
  not_ok "brownfield doc contains follow-established-patterns instruction"
fi

# --- Test 18: brownfield doc — avoid new dependencies ---
if grep -qiE 'dependencies|dependency' "$BROWNFIELD_DOC" && grep -qiE 'new|equivalent|existing' "$BROWNFIELD_DOC"; then
  ok "brownfield doc contains avoid-new-dependencies instruction"
else
  not_ok "brownfield doc contains avoid-new-dependencies instruction"
fi

# --- Test 19: brownfield doc — search for existing equivalents ---
if grep -qi 'existing' "$BROWNFIELD_DOC" && grep -qiE 'equivalent|search' "$BROWNFIELD_DOC"; then
  ok "brownfield doc contains search-for-existing-equivalents instruction"
else
  not_ok "brownfield doc contains search-for-existing-equivalents instruction"
fi

# --- Summary ---
echo ""
echo "# $PASS/$TOTAL tests passed"
if [ "$FAIL" -gt 0 ]; then
  exit 1
fi
exit 0
