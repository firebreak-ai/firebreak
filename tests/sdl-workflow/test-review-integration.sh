#!/usr/bin/env bash
set -uo pipefail

PASS=0
FAIL=0
TOTAL=0

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
PROJECT_ROOT="$(cd "$SCRIPT_DIR/../.." && pwd)"
SKILL_FILE="$PROJECT_ROOT/assets/skills/fbk-spec-review/SKILL.md"
BROWNFIELD_DOC="$PROJECT_ROOT/assets/fbk-docs/fbk-brownfield-spec.md"

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

# --- Test 3: skill references test reviewer agent ---
if grep -qiE 'test-reviewer|test reviewer' "$SKILL_FILE"; then
  ok "skill references test reviewer agent"
else
  not_ok "skill references test reviewer agent"
fi

# --- Test 4: skill specifies checkpoint 1 context ---
if grep -qiE 'checkpoint 1|spec review' "$SKILL_FILE" && grep -qi 'testing strategy' "$SKILL_FILE"; then
  ok "skill specifies checkpoint 1 context (testing strategy evaluation)"
else
  not_ok "skill specifies checkpoint 1 context (testing strategy evaluation)"
fi

# --- Test 5: skill specifies Agent Teams invocation ---
if grep -qiE 'Agent Teams|teammate' "$SKILL_FILE"; then
  ok "skill specifies Agent Teams invocation for context isolation"
else
  not_ok "skill specifies Agent Teams invocation for context isolation"
fi

# --- Test 6: skill preserves council invocation ---
if grep -qi 'council' "$SKILL_FILE"; then
  ok "skill preserves existing council invocation"
else
  not_ok "skill preserves existing council invocation"
fi

# --- Test 7: skill preserves gate invocation ---
if grep -qiE 'review-gate|gate invocation|Gate invocation' "$SKILL_FILE"; then
  ok "skill preserves existing gate invocation"
else
  not_ok "skill preserves existing gate invocation"
fi

# --- Test 8: test strategy review is positioned between council and gate ---
council_line=$(grep -niE '## council invocation|invoke.*council' "$SKILL_FILE" | head -1 | cut -d: -f1)
test_review_line=$(grep -niE 'test-reviewer|test strategy review' "$SKILL_FILE" | head -1 | cut -d: -f1)
gate_line=$(grep -niE 'review-gate|## gate invocation|Gate invocation' "$SKILL_FILE" | head -1 | cut -d: -f1)
if [ -n "$council_line" ] && [ -n "$test_review_line" ] && [ -n "$gate_line" ] && \
   [ "$test_review_line" -gt "$council_line" ] && [ "$test_review_line" -lt "$gate_line" ]; then
  ok "test strategy review positioned between council and gate"
else
  not_ok "test strategy review positioned between council and gate" "council=$council_line test_review=$test_review_line gate=$gate_line"
fi

# --- Test 9: brownfield doc exists ---
if [ -s "$BROWNFIELD_DOC" ]; then
  ok "brownfield doc exists and is non-empty"
else
  not_ok "brownfield doc exists and is non-empty"
fi

# --- Test 10: brownfield doc — search for overlapping code ---
if grep -qi 'search' "$BROWNFIELD_DOC" && grep -qiE 'overlap|existing code' "$BROWNFIELD_DOC"; then
  ok "brownfield doc contains search-for-overlapping-code instruction"
else
  not_ok "brownfield doc contains search-for-overlapping-code instruction"
fi

# --- Test 11: brownfield doc — identify patterns ---
if grep -qiE 'pattern|convention|abstraction' "$BROWNFIELD_DOC"; then
  ok "brownfield doc contains identify-patterns instruction"
else
  not_ok "brownfield doc contains identify-patterns instruction"
fi

# --- Test 12: brownfield doc — distinguish new from extended ---
if grep -qiE 'distinguish|new' "$BROWNFIELD_DOC" && grep -qiE 'extend|modify' "$BROWNFIELD_DOC"; then
  ok "brownfield doc contains distinguish-new-from-extended instruction"
else
  not_ok "brownfield doc contains distinguish-new-from-extended instruction"
fi

# --- Test 13: brownfield doc — replace existing functionality ---
if grep -qiE 'replace|removal|migration' "$BROWNFIELD_DOC"; then
  ok "brownfield doc contains replace-existing-functionality instruction"
else
  not_ok "brownfield doc contains replace-existing-functionality instruction"
fi

# --- Test 14: brownfield doc — avoid duplication ---
if grep -qiE 'duplicate|duplication' "$BROWNFIELD_DOC"; then
  ok "brownfield doc contains avoid-duplication instruction"
else
  not_ok "brownfield doc contains avoid-duplication instruction"
fi

# --- Summary ---
echo ""
echo "# $PASS/$TOTAL tests passed"
if [ "$FAIL" -gt 0 ]; then
  exit 1
fi
exit 0
