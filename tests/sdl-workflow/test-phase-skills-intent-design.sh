#!/usr/bin/env bash
set -uo pipefail

PASS=0
FAIL=0
TOTAL=0

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
PROJECT_ROOT="$(cd "$SCRIPT_DIR/../.." && pwd)"

INTENT="$PROJECT_ROOT/assets/skills/fbk-intent/SKILL.md"
DESIGN="$PROJECT_ROOT/assets/skills/fbk-design/SKILL.md"
SPEC="$PROJECT_ROOT/assets/skills/fbk-spec/SKILL.md"
BREAKDOWN="$PROJECT_ROOT/assets/skills/fbk-breakdown/SKILL.md"

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

# --- Test 1: fbk-intent SKILL.md exists and is non-empty ---
if [ -s "$INTENT" ]; then
  ok "fbk-intent SKILL.md exists and is non-empty"
else
  not_ok "fbk-intent SKILL.md exists and is non-empty" "file: $INTENT"
fi

# --- Test 2: fbk-intent has description frontmatter ---
if [ -s "$INTENT" ] && frontmatter "$INTENT" | grep -q 'description:'; then
  ok "fbk-intent has description frontmatter"
else
  not_ok "fbk-intent has description frontmatter"
fi

# --- Test 3: fbk-intent has argument-hint frontmatter ---
if [ -s "$INTENT" ] && frontmatter "$INTENT" | grep -q 'argument-hint:'; then
  ok "fbk-intent has argument-hint frontmatter"
else
  not_ok "fbk-intent has argument-hint frontmatter"
fi

# --- Test 4: fbk-intent routes to intent-guide.md ---
if [ -s "$INTENT" ] && grep -q 'intent-guide.md' "$INTENT"; then
  ok "fbk-intent routes to intent-guide.md"
else
  not_ok "fbk-intent routes to intent-guide.md"
fi

# --- Test 5: fbk-intent composes fbk-grilling ---
if [ -s "$INTENT" ] && grep -q 'fbk-grilling' "$INTENT"; then
  ok "fbk-intent composes fbk-grilling"
else
  not_ok "fbk-intent composes fbk-grilling"
fi

# --- Test 6: fbk-intent composes fbk-fresh-eyes ---
if [ -s "$INTENT" ] && grep -q 'fbk-fresh-eyes' "$INTENT"; then
  ok "fbk-intent composes fbk-fresh-eyes"
else
  not_ok "fbk-intent composes fbk-fresh-eyes"
fi

# --- Test 7: fbk-intent delegates to fbk-product-author agent ---
if [ -s "$INTENT" ] && grep -q 'fbk-product-author' "$INTENT"; then
  ok "fbk-intent delegates to fbk-product-author agent"
else
  not_ok "fbk-intent delegates to fbk-product-author agent"
fi

# --- Test 8: fbk-intent runs intent-gate ---
if [ -s "$INTENT" ] && grep -q 'intent-gate' "$INTENT"; then
  ok "fbk-intent runs intent-gate"
else
  not_ok "fbk-intent runs intent-gate"
fi

# --- Test 9: fbk-intent reads/updates architecture-overview.md ---
if [ -s "$INTENT" ] && grep -q 'architecture-overview.md' "$INTENT"; then
  ok "fbk-intent reads/updates architecture-overview.md"
else
  not_ok "fbk-intent reads/updates architecture-overview.md"
fi

# --- Test 10: fbk-design SKILL.md exists and is non-empty ---
if [ -s "$DESIGN" ]; then
  ok "fbk-design SKILL.md exists and is non-empty"
else
  not_ok "fbk-design SKILL.md exists and is non-empty" "file: $DESIGN"
fi

# --- Test 11: fbk-design has description frontmatter ---
if [ -s "$DESIGN" ] && frontmatter "$DESIGN" | grep -q 'description:'; then
  ok "fbk-design has description frontmatter"
else
  not_ok "fbk-design has description frontmatter"
fi

# --- Test 12: fbk-design has argument-hint frontmatter ---
if [ -s "$DESIGN" ] && frontmatter "$DESIGN" | grep -q 'argument-hint:'; then
  ok "fbk-design has argument-hint frontmatter"
else
  not_ok "fbk-design has argument-hint frontmatter"
fi

# --- Test 13: fbk-design routes to design-guide.md ---
if [ -s "$DESIGN" ] && grep -q 'design-guide.md' "$DESIGN"; then
  ok "fbk-design routes to design-guide.md"
else
  not_ok "fbk-design routes to design-guide.md"
fi

# --- Test 14: fbk-design composes fbk-grilling ---
if [ -s "$DESIGN" ] && grep -q 'fbk-grilling' "$DESIGN"; then
  ok "fbk-design composes fbk-grilling"
else
  not_ok "fbk-design composes fbk-grilling"
fi

# --- Test 15: fbk-design composes fbk-fresh-eyes ---
if [ -s "$DESIGN" ] && grep -q 'fbk-fresh-eyes' "$DESIGN"; then
  ok "fbk-design composes fbk-fresh-eyes"
else
  not_ok "fbk-design composes fbk-fresh-eyes"
fi

# --- Test 16: fbk-design delegates to fbk-architect agent ---
if [ -s "$DESIGN" ] && grep -q 'fbk-architect' "$DESIGN"; then
  ok "fbk-design delegates to fbk-architect agent"
else
  not_ok "fbk-design delegates to fbk-architect agent"
fi

# --- Test 17: fbk-design runs design-gate ---
if [ -s "$DESIGN" ] && grep -q 'design-gate' "$DESIGN"; then
  ok "fbk-design runs design-gate"
else
  not_ok "fbk-design runs design-gate"
fi

# --- Test 18: fbk-design appends to decisions-log.md ---
if [ -s "$DESIGN" ] && grep -q 'decisions-log.md' "$DESIGN"; then
  ok "fbk-design appends to decisions-log.md"
else
  not_ok "fbk-design appends to decisions-log.md"
fi

# --- Test 19: fbk-design invokes check_prerequisites ---
if [ -s "$DESIGN" ] && grep -q 'check_prerequisites' "$DESIGN"; then
  ok "fbk-design invokes check_prerequisites"
else
  not_ok "fbk-design invokes check_prerequisites"
fi

# --- Test 20: fbk-spec references check_prerequisites ---
if [ -s "$SPEC" ] && grep -q 'check_prerequisites' "$SPEC"; then
  ok "fbk-spec references check_prerequisites (design-missing-at-spec case)"
else
  not_ok "fbk-spec references check_prerequisites (design-missing-at-spec case)"
fi

# --- Test 21: fbk-breakdown references check_prerequisites ---
if [ -s "$BREAKDOWN" ] && grep -q 'check_prerequisites' "$BREAKDOWN"; then
  ok "fbk-breakdown references check_prerequisites (spec-missing-at-breakdown case)"
else
  not_ok "fbk-breakdown references check_prerequisites (spec-missing-at-breakdown case)"
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
