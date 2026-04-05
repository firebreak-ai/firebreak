#!/usr/bin/env bash
set -uo pipefail

PASS=0
FAIL=0
TOTAL=0

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
PROJECT_ROOT="$(cd "$SCRIPT_DIR/../.." && pwd)"
GUIDE="$PROJECT_ROOT/assets/fbk-docs/fbk-sdl-workflow/code-review-guide.md"
QUALITY="$PROJECT_ROOT/assets/fbk-docs/fbk-design-guidelines/quality-detection.md"

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

# --- Test 1: Guide contains AC verification precision requirement (AC-23) ---
if grep -qiE 'precision|individual|each AC|per.AC' "$GUIDE"; then
  ok "Guide contains AC verification precision requirement"
else
  not_ok "Guide contains AC verification precision requirement" "precision/individual/each AC/per-AC not found in $GUIDE"
fi

# --- Test 2: Guide test-integrity definition includes name-scope mismatch (AC-24) ---
if grep -qiE 'name.scope|scope.mismatch' "$GUIDE"; then
  ok "Guide test-integrity includes name-scope mismatch"
else
  not_ok "Guide test-integrity includes name-scope mismatch" "name-scope or scope-mismatch not found in $GUIDE"
fi

# --- Test 3: quality-detection.md contains dead infrastructure check (AC-25) ---
if grep -qiE 'dead infrastructure|disconnected infrastructure' "$QUALITY"; then
  ok "quality-detection.md contains dead infrastructure check"
else
  not_ok "quality-detection.md contains dead infrastructure check" "dead/disconnected infrastructure not found in $QUALITY"
fi

# --- Test 4: Guide contains explicit nit exclusion instruction (AC-26) ---
if grep -qiE 'nit.*exclud|exclud.*nit|nit.*(not|never).*finding' "$GUIDE"; then
  ok "Guide contains nit exclusion instruction"
else
  not_ok "Guide contains nit exclusion instruction" "nit exclusion instruction not found in $GUIDE"
fi

# --- Test 5: Guide contains structural sub-categorization in retrospective (AC-27) ---
if grep -qiE 'sub.categor|structural.*(breakdown|sub)' "$GUIDE"; then
  ok "Guide contains structural sub-categorization in retrospective"
else
  not_ok "Guide contains structural sub-categorization in retrospective" "structural sub-categorization not found in $GUIDE"
fi

# --- Test 6: Guide contains origin guidance for codebase-wide reviews (AC-28) ---
if grep -qiE 'pre.existing.*default|default.*pre.existing|codebase.wide.*origin' "$GUIDE"; then
  ok "Guide contains origin guidance for codebase-wide reviews"
else
  not_ok "Guide contains origin guidance for codebase-wide reviews" "origin guidance for codebase-wide reviews not found in $GUIDE"
fi

# --- Test 7: Guide no-spec section references quality-detection.md (AC-29) ---
# Extract the Source of Truth Handling section
sot_section=$(sed -n '/## Source of Truth Handling/,/^## /p' "$GUIDE" | head -n -1)
has_qd=$(echo "$sot_section" | grep -c 'quality-detection' 2>/dev/null || true)
if [ "$has_qd" -gt 0 ]; then
  ok "Guide no-spec section references quality-detection.md"
else
  not_ok "Guide no-spec section references quality-detection.md" "quality-detection not found in Source of Truth Handling section"
fi

echo ""
echo "1..$TOTAL"
[ "$FAIL" -eq 0 ]
