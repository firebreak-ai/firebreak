#!/bin/bash
# Test: Architecture-reviewer contract-drift brief
# Verifies that the architecture-reviewer brief in review-perspectives.md carries
# the three contract-drift conditions as informational findings.

set -euo pipefail

PROJECT_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"

# TAP functions
PASS=0
FAIL=0
TOTAL=0

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

BRIEF="$PROJECT_ROOT/assets/fbk-docs/fbk-sdl-workflow/review-perspectives.md"

# Test 1: Brief carries spec-added contract absent from design condition
# Check for IF-S- token in context of architecture-reviewer brief
if grep -q "^## .*[Aa]rchitecture.*[Rr]eviewer.*[Bb]rief" "$BRIEF" && \
   grep -A 50 "^## .*[Aa]rchitecture.*[Rr]eviewer.*[Bb]rief" "$BRIEF" | grep -q "IF-S-"; then
  ok "brief carries spec-added contract condition (IF-S- token present)"
else
  not_ok "brief carries spec-added contract condition (IF-S- token present)" "IF-S- token not found in architecture-reviewer brief section"
fi

# Test 2: Brief carries preserved identifier but changed name/signature condition
# Check for IF-D- token in context of architecture-reviewer brief
if grep -q "^## .*[Aa]rchitecture.*[Rr]eviewer.*[Bb]rief" "$BRIEF" && \
   grep -A 50 "^## .*[Aa]rchitecture.*[Rr]eviewer.*[Bb]rief" "$BRIEF" | grep -q "IF-D-"; then
  ok "brief carries preserved-identifier condition (IF-D- token present)"
else
  not_ok "brief carries preserved-identifier condition (IF-D- token present)" "IF-D- token not found in architecture-reviewer brief section"
fi

# Test 3: Brief carries count/name mismatch condition
# Check for mismatch marker in context of architecture-reviewer brief
if grep -q "^## .*[Aa]rchitecture.*[Rr]eviewer.*[Bb]rief" "$BRIEF" && \
   grep -A 50 "^## .*[Aa]rchitecture.*[Rr]eviewer.*[Bb]rief" "$BRIEF" | grep -iq "mismatch"; then
  ok "brief carries count/name mismatch condition"
else
  not_ok "brief carries count/name mismatch condition" "mismatch marker not found in architecture-reviewer brief section"
fi

# Test 4: Brief frames all conditions as informational
# Check for literal "informational" in context of architecture-reviewer brief
if grep -q "^## .*[Aa]rchitecture.*[Rr]eviewer.*[Bb]rief" "$BRIEF" && \
   grep -A 50 "^## .*[Aa]rchitecture.*[Rr]eviewer.*[Bb]rief" "$BRIEF" | grep -q "informational"; then
  ok "brief frames conditions as informational"
else
  not_ok "brief frames conditions as informational" "informational framing not found in architecture-reviewer brief section"
fi

# TAP summary
echo "1..$TOTAL"
if [ "$FAIL" -gt 0 ]; then
  exit 1
fi
