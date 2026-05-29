#!/usr/bin/env bash
set -uo pipefail

PASS=0
FAIL=0
TOTAL=0

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
PROJECT_ROOT="$(cd "$SCRIPT_DIR/../.." && pwd)"

GRILLING="$PROJECT_ROOT/assets/skills/fbk-grilling/SKILL.md"
FRESH_EYES="$PROJECT_ROOT/assets/skills/fbk-fresh-eyes/SKILL.md"
QUALITY_SCAN="$PROJECT_ROOT/assets/skills/fbk-quality-scan/SKILL.md"
TEST_REVIEW="$PROJECT_ROOT/assets/skills/fbk-test-review/SKILL.md"
FRESH_EYES_AGENT="$PROJECT_ROOT/assets/agents/fbk-fresh-eyes-reviewer.md"
DETECTOR_AGENT="$PROJECT_ROOT/assets/agents/fbk-code-review-detector.md"
TEST_REVIEWER_AGENT="$PROJECT_ROOT/assets/agents/fbk-test-reviewer.md"

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

# Helper: extract frontmatter (lines between first --- and second ---)
frontmatter() {
  sed -n '2,/^---$/p' "$1" | sed '$d'
}

echo "TAP version 13"

# --- Test 1: fbk-grilling SKILL.md exists ---
if [ -s "$GRILLING" ]; then
  ok "fbk-grilling SKILL.md exists and is non-empty"
else
  not_ok "fbk-grilling SKILL.md exists and is non-empty" "file: $GRILLING"
fi

# --- Test 2: fbk-grilling has description frontmatter ---
if [ -s "$GRILLING" ] && frontmatter "$GRILLING" | grep -q 'description:'; then
  ok "fbk-grilling has description frontmatter"
else
  not_ok "fbk-grilling has description frontmatter"
fi

# --- Test 3: fbk-grilling has argument-hint frontmatter ---
if [ -s "$GRILLING" ] && frontmatter "$GRILLING" | grep -q 'argument-hint:'; then
  ok "fbk-grilling has argument-hint frontmatter"
else
  not_ok "fbk-grilling has argument-hint frontmatter"
fi

# --- Test 4: fbk-fresh-eyes SKILL.md exists ---
if [ -s "$FRESH_EYES" ]; then
  ok "fbk-fresh-eyes SKILL.md exists and is non-empty"
else
  not_ok "fbk-fresh-eyes SKILL.md exists and is non-empty" "file: $FRESH_EYES"
fi

# --- Test 5: fbk-fresh-eyes has description frontmatter ---
if [ -s "$FRESH_EYES" ] && frontmatter "$FRESH_EYES" | grep -q 'description:'; then
  ok "fbk-fresh-eyes has description frontmatter"
else
  not_ok "fbk-fresh-eyes has description frontmatter"
fi

# --- Test 6: fbk-fresh-eyes has argument-hint frontmatter ---
if [ -s "$FRESH_EYES" ] && frontmatter "$FRESH_EYES" | grep -q 'argument-hint:'; then
  ok "fbk-fresh-eyes has argument-hint frontmatter"
else
  not_ok "fbk-fresh-eyes has argument-hint frontmatter"
fi

# --- Test 7: fbk-quality-scan SKILL.md exists ---
if [ -s "$QUALITY_SCAN" ]; then
  ok "fbk-quality-scan SKILL.md exists and is non-empty"
else
  not_ok "fbk-quality-scan SKILL.md exists and is non-empty" "file: $QUALITY_SCAN"
fi

# --- Test 8: fbk-quality-scan has description frontmatter ---
if [ -s "$QUALITY_SCAN" ] && frontmatter "$QUALITY_SCAN" | grep -q 'description:'; then
  ok "fbk-quality-scan has description frontmatter"
else
  not_ok "fbk-quality-scan has description frontmatter"
fi

# --- Test 9: fbk-quality-scan has argument-hint frontmatter ---
if [ -s "$QUALITY_SCAN" ] && frontmatter "$QUALITY_SCAN" | grep -q 'argument-hint:'; then
  ok "fbk-quality-scan has argument-hint frontmatter"
else
  not_ok "fbk-quality-scan has argument-hint frontmatter"
fi

# --- Test 10: fbk-test-review SKILL.md exists ---
if [ -s "$TEST_REVIEW" ]; then
  ok "fbk-test-review SKILL.md exists and is non-empty"
else
  not_ok "fbk-test-review SKILL.md exists and is non-empty" "file: $TEST_REVIEW"
fi

# --- Test 11: fbk-test-review has description frontmatter ---
if [ -s "$TEST_REVIEW" ] && frontmatter "$TEST_REVIEW" | grep -q 'description:'; then
  ok "fbk-test-review has description frontmatter"
else
  not_ok "fbk-test-review has description frontmatter"
fi

# --- Test 12: fbk-test-review has argument-hint frontmatter ---
if [ -s "$TEST_REVIEW" ] && frontmatter "$TEST_REVIEW" | grep -q 'argument-hint:'; then
  ok "fbk-test-review has argument-hint frontmatter"
else
  not_ok "fbk-test-review has argument-hint frontmatter"
fi

# --- Test 13: fbk-grilling credits Matt Pocock ---
if [ -s "$GRILLING" ] && grep -qF 'Matt Pocock' "$GRILLING"; then
  ok "fbk-grilling credits Matt Pocock"
else
  not_ok "fbk-grilling credits Matt Pocock"
fi

# --- Test 14: fbk-grilling contains exact Matt Pocock source URL ---
if [ -s "$GRILLING" ] && grep -qF 'https://github.com/mattpocock/skills/blob/main/skills/productivity/grill-me/SKILL.md' "$GRILLING"; then
  ok "fbk-grilling contains exact Matt Pocock source URL"
else
  not_ok "fbk-grilling contains exact Matt Pocock source URL"
fi

# --- Test 15: fbk-grilling specifies one question at a time ---
if [ -s "$GRILLING" ] && grep -qi 'one question at a time' "$GRILLING"; then
  ok "fbk-grilling specifies one question at a time"
else
  not_ok "fbk-grilling specifies one question at a time"
fi

# --- Test 16: fbk-grilling contains Confirmed: sentinel ---
if [ -s "$GRILLING" ] && grep -qF 'Confirmed:' "$GRILLING"; then
  ok "fbk-grilling contains Confirmed: sentinel"
else
  not_ok "fbk-grilling contains Confirmed: sentinel"
fi

# --- Test 17: fbk-quality-scan specifies limit of five findings ---
if [ -s "$QUALITY_SCAN" ] && grep -qE '\b5\b|five' "$QUALITY_SCAN"; then
  ok "fbk-quality-scan specifies limit of five findings"
else
  not_ok "fbk-quality-scan specifies limit of five findings"
fi

# --- Test 18: fbk-quality-scan specifies ranking or severity indicator ---
if [ -s "$QUALITY_SCAN" ] && grep -qi 'ranked\|severity\|top' "$QUALITY_SCAN"; then
  ok "fbk-quality-scan specifies ranking or severity indicator"
else
  not_ok "fbk-quality-scan specifies ranking or severity indicator"
fi

# --- Test 19: fbk-fresh-eyes-reviewer agent excludes Write tool ---
if [ -s "$FRESH_EYES_AGENT" ]; then
  tools_line=$(frontmatter "$FRESH_EYES_AGENT" | grep '^tools:')
  has_write=$(echo "$tools_line" | grep -c 'Write')
  if [ "$has_write" -eq 0 ]; then
    ok "fbk-fresh-eyes-reviewer excludes Write tool"
  else
    not_ok "fbk-fresh-eyes-reviewer excludes Write tool" "has_write=$has_write"
  fi
else
  not_ok "fbk-fresh-eyes-reviewer excludes Write tool" "file: $FRESH_EYES_AGENT"
fi

# --- Test 20: fbk-fresh-eyes-reviewer agent excludes Edit tool ---
if [ -s "$FRESH_EYES_AGENT" ]; then
  tools_line=$(frontmatter "$FRESH_EYES_AGENT" | grep '^tools:')
  has_edit=$(echo "$tools_line" | grep -c 'Edit')
  if [ "$has_edit" -eq 0 ]; then
    ok "fbk-fresh-eyes-reviewer excludes Edit tool"
  else
    not_ok "fbk-fresh-eyes-reviewer excludes Edit tool" "has_edit=$has_edit"
  fi
else
  not_ok "fbk-fresh-eyes-reviewer excludes Edit tool" "file: $FRESH_EYES_AGENT"
fi

# --- Test 21: fbk-code-review-detector agent excludes Write tool ---
if [ -s "$DETECTOR_AGENT" ]; then
  tools_line=$(frontmatter "$DETECTOR_AGENT" | grep '^tools:')
  has_write=$(echo "$tools_line" | grep -c 'Write')
  if [ "$has_write" -eq 0 ]; then
    ok "fbk-code-review-detector excludes Write tool"
  else
    not_ok "fbk-code-review-detector excludes Write tool" "has_write=$has_write"
  fi
else
  not_ok "fbk-code-review-detector excludes Write tool" "file: $DETECTOR_AGENT"
fi

# --- Test 22: fbk-code-review-detector agent excludes Edit tool ---
if [ -s "$DETECTOR_AGENT" ]; then
  tools_line=$(frontmatter "$DETECTOR_AGENT" | grep '^tools:')
  has_edit=$(echo "$tools_line" | grep -c 'Edit')
  if [ "$has_edit" -eq 0 ]; then
    ok "fbk-code-review-detector excludes Edit tool"
  else
    not_ok "fbk-code-review-detector excludes Edit tool" "has_edit=$has_edit"
  fi
else
  not_ok "fbk-code-review-detector excludes Edit tool" "file: $DETECTOR_AGENT"
fi

# --- Test 23: fbk-test-reviewer agent excludes Write tool ---
if [ -s "$TEST_REVIEWER_AGENT" ]; then
  tools_line=$(frontmatter "$TEST_REVIEWER_AGENT" | grep '^tools:')
  has_write=$(echo "$tools_line" | grep -c 'Write')
  if [ "$has_write" -eq 0 ]; then
    ok "fbk-test-reviewer excludes Write tool"
  else
    not_ok "fbk-test-reviewer excludes Write tool" "has_write=$has_write"
  fi
else
  not_ok "fbk-test-reviewer excludes Write tool" "file: $TEST_REVIEWER_AGENT"
fi

# --- Test 24: fbk-test-reviewer agent excludes Edit tool ---
if [ -s "$TEST_REVIEWER_AGENT" ]; then
  tools_line=$(frontmatter "$TEST_REVIEWER_AGENT" | grep '^tools:')
  has_edit=$(echo "$tools_line" | grep -c 'Edit')
  if [ "$has_edit" -eq 0 ]; then
    ok "fbk-test-reviewer excludes Edit tool"
  else
    not_ok "fbk-test-reviewer excludes Edit tool" "has_edit=$has_edit"
  fi
else
  not_ok "fbk-test-reviewer excludes Edit tool" "file: $TEST_REVIEWER_AGENT"
fi

# --- Summary ---
echo ""
echo "1..$TOTAL"
echo "# $PASS/$TOTAL tests passed"
if [ "$FAIL" -gt 0 ]; then
  echo "# FAIL $FAIL"
  exit 1
fi
exit 0
