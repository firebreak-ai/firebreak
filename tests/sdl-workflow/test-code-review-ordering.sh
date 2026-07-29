#!/usr/bin/env bash
set -uo pipefail

PASS=0
FAIL=0
TOTAL=0

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
PROJECT_ROOT="$(cd "$SCRIPT_DIR/../.." && pwd)"

CODE_REVIEW_SKILL="$PROJECT_ROOT/assets/skills/fbk-code-review/SKILL.md"

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

line_of_first_match() {
  grep -n "$1" "$2" 2>/dev/null | head -1 | cut -d: -f1
}

echo "TAP version 13"

# --- Test 1: skill file exists ---
if [ -s "$CODE_REVIEW_SKILL" ]; then
  ok "skill file exists"
else
  not_ok "skill file exists" "file: $CODE_REVIEW_SKILL"
fi

# --- Test 2-5: code-review ordering assertions ---
# Extract line numbers for the four sentinels
line_bug_finding=$(line_of_first_match 'Spawn Detector with:' "$CODE_REVIEW_SKILL")
line_quality_scan=$(line_of_first_match 'fbk-quality-scan' "$CODE_REVIEW_SKILL")
line_test_review=$(line_of_first_match 'fbk-test-review' "$CODE_REVIEW_SKILL")
line_gate=$(line_of_first_match 'code-review-gate' "$CODE_REVIEW_SKILL")

# Test 2: bug-finding invocation sentinel found
if [ -n "$line_bug_finding" ]; then
  ok "bug-finding invocation sentinel 'Spawn Detector with:' found in skill body"
else
  not_ok "bug-finding invocation sentinel 'Spawn Detector with:' found in skill body"
fi

# Test 3: fbk-quality-scan follows bug-finding
if [ -n "$line_quality_scan" ] && [ "$line_quality_scan" -gt "$line_bug_finding" ]; then
  ok "fbk-quality-scan follows bug-finding (line $line_quality_scan > $line_bug_finding)"
else
  not_ok "fbk-quality-scan follows bug-finding" "bug_finding=$line_bug_finding quality_scan=$line_quality_scan"
fi

# Test 4: fbk-test-review follows quality-scan
if [ -n "$line_test_review" ] && [ "$line_test_review" -gt "$line_quality_scan" ]; then
  ok "fbk-test-review follows quality-scan (line $line_test_review > $line_quality_scan)"
else
  not_ok "fbk-test-review follows quality-scan" "quality_scan=$line_quality_scan test_review=$line_test_review"
fi

# Test 5: code-review-gate follows test-review
if [ -n "$line_gate" ] && [ "$line_gate" -gt "$line_test_review" ]; then
  ok "code-review-gate follows test-review (line $line_gate > $line_test_review)"
else
  not_ok "code-review-gate follows test-review" "test_review=$line_test_review gate=$line_gate"
fi

# --- Test 6: check_prerequisites referenced in skill body ---
if grep -q 'fbk.py precheck code-review' "$CODE_REVIEW_SKILL"; then
  ok "fbk-code-review/SKILL.md references the precheck probe (capability-entry probe wired by task-24)"
else
  not_ok "fbk-code-review/SKILL.md references the precheck probe (capability-entry probe wired by task-24)"
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
