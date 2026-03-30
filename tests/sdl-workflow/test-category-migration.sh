#!/usr/bin/env bash
set -uo pipefail

PASS=0
FAIL=0
TOTAL=0

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
PROJECT_ROOT="$(cd "$SCRIPT_DIR/../.." && pwd)"
GUIDE="$PROJECT_ROOT/assets/fbk-docs/fbk-sdl-workflow/code-review-guide.md"
DETECTOR="$PROJECT_ROOT/assets/agents/fbk-code-review-detector.md"
CHALLENGER="$PROJECT_ROOT/assets/agents/fbk-code-review-challenger.md"

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

# --- Test 1: Guide sighting format contains Type field (AC-55) ---
if grep -q 'Type:' "$GUIDE"; then
  ok "Guide sighting format contains Type field"
else
  not_ok "Guide sighting format contains Type field"
fi

# --- Test 2: Guide sighting format contains Severity field (AC-55) ---
if grep -q 'Severity:' "$GUIDE"; then
  ok "Guide sighting format contains Severity field"
else
  not_ok "Guide sighting format contains Severity field"
fi

# --- Test 3: Guide format templates do not contain Category field (AC-55) ---
category_in_blocks=$(sed -n '/^```/,/^```/p' "$GUIDE" | grep -c 'Category:' 2>/dev/null || true)
if [ "$category_in_blocks" -eq 0 ]; then
  ok "Guide format templates do not contain Category field"
else
  not_ok "Guide format templates do not contain Category field" "category_in_blocks=$category_in_blocks"
fi

# --- Test 4: Guide does not contain Category Values section heading (AC-57) ---
if ! grep -q '## Category Values' "$GUIDE"; then
  ok "Guide does not contain Category Values section heading"
else
  not_ok "Guide does not contain Category Values section heading"
fi

# --- Test 5: Guide contains all four type axis values (AC-57) ---
if grep -q 'behavioral' "$GUIDE" && grep -q 'structural' "$GUIDE" && grep -q 'test-integrity' "$GUIDE" && grep -q 'fragile' "$GUIDE"; then
  ok "Guide contains all four type axis values"
else
  not_ok "Guide contains all four type axis values"
fi

# --- Test 6: Guide contains all four severity axis values (AC-57) ---
if grep -q 'critical' "$GUIDE" && grep -q 'major' "$GUIDE" && grep -q 'minor' "$GUIDE" && grep -q 'info' "$GUIDE"; then
  ok "Guide contains all four severity axis values"
else
  not_ok "Guide contains all four severity axis values"
fi

# --- Test 7: Guide contains type disambiguation rule (AC-57) ---
if grep -qi 'disambigu' "$GUIDE"; then
  ok "Guide contains type disambiguation rule"
else
  not_ok "Guide contains type disambiguation rule"
fi

# --- Test 8: Detector output uses type and severity, not category (AC-58) ---
body=$(sed -n '/^---$/,/^---$/!p' "$DETECTOR" | tail -n +2)
cat_count=$(echo "$body" | grep -ci 'category' 2>/dev/null || true)
has_type=$(echo "$body" | grep -ci 'type' 2>/dev/null || true)
has_sev=$(echo "$body" | grep -ci 'severity' 2>/dev/null || true)
if [ "$cat_count" -eq 0 ] && [ "$has_type" -gt 0 ] && [ "$has_sev" -gt 0 ]; then
  ok "Detector output uses type and severity, not category"
else
  not_ok "Detector output uses type and severity, not category" "cat_count=$cat_count has_type=$has_type has_sev=$has_sev"
fi

# --- Test 9: Challenger rejects nits instead of downgrading (AC-59) ---
has_reject_nit=$(grep -ciE 'reject.*(as )?nit' "$CHALLENGER" 2>/dev/null || true)
has_downgrade_nit=$(grep -ci 'downgrade.*nit\|downgrade to nit' "$CHALLENGER" 2>/dev/null || true)
if [ "$has_reject_nit" -gt 0 ] && [ "$has_downgrade_nit" -eq 0 ]; then
  ok "Challenger rejects nits instead of downgrading"
else
  not_ok "Challenger rejects nits instead of downgrading" "has_reject_nit=$has_reject_nit has_downgrade_nit=$has_downgrade_nit"
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
