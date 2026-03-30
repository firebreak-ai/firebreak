#!/usr/bin/env bash
set -uo pipefail

PASS=0
FAIL=0
TOTAL=0

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
PROJECT_ROOT="$(cd "$SCRIPT_DIR/../.." && pwd)"
SKILL="$PROJECT_ROOT/assets/skills/fbk-code-review/SKILL.md"
GUIDE="$PROJECT_ROOT/assets/fbk-docs/fbk-sdl-workflow/code-review-guide.md"

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

# --- Test 1: SKILL.md contains linter execution instruction (AC-60, AC-09 relocation half) ---
if grep -qi 'linter' "$SKILL"; then
  ok "SKILL.md contains linter execution instruction"
else
  not_ok "SKILL.md contains linter execution instruction" "file: $SKILL"
fi

# --- Test 2: SKILL.md linter instruction specifies truncation (AC-60) ---
if grep -qiE 'truncat|100 findings|first 100' "$SKILL"; then
  ok "SKILL.md linter instruction specifies truncation"
else
  not_ok "SKILL.md linter instruction specifies truncation" "file: $SKILL"
fi

# --- Test 3: SKILL.md linter output described as supplementary context (AC-60) ---
if grep -qiE 'supplementary context|not.*pre.formed|context.*not.*sighting' "$SKILL"; then
  ok "SKILL.md linter output described as supplementary context"
else
  not_ok "SKILL.md linter output described as supplementary context" "file: $SKILL"
fi

# --- Test 4: SKILL.md contains parallel spawning instruction (AC-16) ---
if grep -qi 'parallel' "$SKILL"; then
  ok "SKILL.md contains parallel spawning instruction"
else
  not_ok "SKILL.md contains parallel spawning instruction" "file: $SKILL"
fi

# --- Test 5: SKILL.md contains stuck-agent recovery instruction (AC-17) ---
if grep -qiE 'stuck.agent|unresponsive|relaunch' "$SKILL"; then
  ok "SKILL.md contains stuck-agent recovery instruction"
else
  not_ok "SKILL.md contains stuck-agent recovery instruction" "file: $SKILL"
fi

# --- Test 6: Stuck-agent recovery escalates instead of substituting (AC-17) ---
if grep -qiE 'never.*perform.*direct|do not.*perform|escalate.*user' "$SKILL"; then
  ok "Stuck-agent recovery escalates instead of substituting"
else
  not_ok "Stuck-agent recovery escalates instead of substituting" "file: $SKILL"
fi

# --- Test 7: SKILL.md contains pattern deduplication instruction (AC-18) ---
if grep -qiE 'deduplicat|cross.unit.*pattern|pattern.*(dedup|group|naming)' "$SKILL"; then
  ok "SKILL.md contains pattern deduplication instruction"
else
  not_ok "SKILL.md contains pattern deduplication instruction" "file: $SKILL"
fi

# --- Test 8: SKILL.md Detector spawn references quality-detection.md (AC-21) ---
if grep -q 'quality-detection' "$SKILL"; then
  ok "SKILL.md Detector spawn references quality-detection.md"
else
  not_ok "SKILL.md Detector spawn references quality-detection.md" "file: $SKILL"
fi

# --- Test 9: SKILL.md Detector spawn includes detection source tagging (AC-22) ---
if grep -qi 'detection source' "$SKILL"; then
  ok "SKILL.md Detector spawn includes detection source tagging"
else
  not_ok "SKILL.md Detector spawn includes detection source tagging" "file: $SKILL"
fi

# --- Test 10: Guide detection source values include linter (AC-61) ---
if grep -qi 'linter' "$GUIDE"; then
  ok "Guide detection source values include linter"
else
  not_ok "Guide detection source values include linter" "file: $GUIDE"
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
