#!/usr/bin/env bash
set -uo pipefail

PASS=0
FAIL=0
TOTAL=0

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
PROJECT_ROOT="$(cd "$SCRIPT_DIR/../.." && pwd)"
REVIEWER="$PROJECT_ROOT/assets/agents/fbk-test-reviewer.md"

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

# --- Test 1: Test reviewer Tier 1 contains stale failure annotation criterion (AC-49) ---
tier1=$(sed -n '/### Tier 1/,/### Tier 2/p' "$REVIEWER" | head -n -1)
has_stale=$(echo "$tier1" | grep -ciE 'stale.*fail|fail.*annotation|expected.to.fail' 2>/dev/null || true)
if [ "$has_stale" -gt 0 ]; then
  ok "Test reviewer Tier 1 contains stale failure annotation criterion"
else
  not_ok "Test reviewer Tier 1 contains stale failure annotation criterion" "has_stale=$has_stale"
fi

# --- Test 2: Test reviewer Tier 1 contains empty gate test criterion (AC-50) ---
has_empty=$(echo "$tier1" | grep -ciE 'empty.*gate|zero.*assert|no.*assert' 2>/dev/null || true)
if [ "$has_empty" -gt 0 ]; then
  ok "Test reviewer Tier 1 contains empty gate test criterion"
else
  not_ok "Test reviewer Tier 1 contains empty gate test criterion" "has_empty=$has_empty"
fi

# --- Test 3: Test reviewer Tier 1 contains advisory assertion criterion (AC-51) ---
has_advisory=$(echo "$tier1" | grep -ciE 'advisory|non.failing.*output' 2>/dev/null || true)
if [ "$has_advisory" -gt 0 ]; then
  ok "Test reviewer Tier 1 contains advisory assertion criterion"
else
  not_ok "Test reviewer Tier 1 contains advisory assertion criterion" "has_advisory=$has_advisory"
fi

# Tests 4-6 (CP5 mutation-testing criteria: unconditionally-skipped, phantom assertion,
# build-tag consistency) retired by the refactored-sdl Wave 1 work — task-20 removed CP5
# from fbk-test-reviewer.md per the spec, so these sentinels no longer apply.

# --- Summary ---
echo ""
echo "1..$TOTAL"
echo "# $PASS/$TOTAL tests passed"
if [ "$FAIL" -gt 0 ]; then
  echo "# FAIL $FAIL"
  exit 1
fi
exit 0
