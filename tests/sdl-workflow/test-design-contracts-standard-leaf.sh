#!/bin/bash
# Test: Design contracts standard leaf and design-guide route
# Verifies that design-guide.md carries required-page note and conditional route,
# and that design-contracts-standard.md carries entry schema and design-page parse rule.

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

# Define paths
GUIDE="$PROJECT_ROOT/assets/fbk-docs/fbk-sdl-workflow/design-guide.md"
LEAF="$PROJECT_ROOT/assets/fbk-docs/fbk-sdl-workflow/design-contracts-standard.md"

# AC-14: Instruction hygiene (design-guide.md)

# Check that design-guide.md states contracts.md is required
if grep -q 'contracts.md' "$GUIDE" && grep -q -i 'required' "$GUIDE"; then
  ok "design-guide.md states contracts.md is required"
else
  not_ok "design-guide.md states contracts.md is required" "required-page note for contracts.md not found"
fi

# Check that design-guide.md routes to the standard leaf conditionally
if grep -q 'design-contracts-standard.md' "$GUIDE" && grep -q -i 'conditional\|only when\|when.*contract' "$GUIDE"; then
  ok "design-guide.md routes to standard leaf conditionally"
else
  not_ok "design-guide.md routes to standard leaf conditionally" "conditional route to design-contracts-standard.md not found"
fi

# AC-14: Instruction hygiene (design-contracts-standard.md)

# Check that the leaf exists
if [ -f "$LEAF" ]; then
  ok "design-contracts-standard.md file exists"
else
  not_ok "design-contracts-standard.md file exists" "leaf file not found at $LEAF"
fi

# Check that the leaf carries the IF-D-NN entry schema (heading form)
if grep -q '^## IF-D-NN' "$LEAF"; then
  ok "design-contracts-standard.md carries IF-D-NN heading form"
else
  not_ok "design-contracts-standard.md carries IF-D-NN heading form" "## IF-D-NN marker not found"
fi

# Check for the four schema fields: signature, invariants, consumed-by, produced-by
if grep -q 'signature' "$LEAF"; then
  ok "design-contracts-standard.md contains signature field"
else
  not_ok "design-contracts-standard.md contains signature field" "signature field not found"
fi

if grep -q 'invariants' "$LEAF"; then
  ok "design-contracts-standard.md contains invariants field"
else
  not_ok "design-contracts-standard.md contains invariants field" "invariants field not found"
fi

if grep -q 'consumed-by' "$LEAF"; then
  ok "design-contracts-standard.md contains consumed-by field"
else
  not_ok "design-contracts-standard.md contains consumed-by field" "consumed-by field not found"
fi

if grep -q 'produced-by' "$LEAF"; then
  ok "design-contracts-standard.md contains produced-by field"
else
  not_ok "design-contracts-standard.md contains produced-by field" "produced-by field not found"
fi

# Check that the leaf carries the design-page parse rule
if grep -qF '^## (IF-D-' "$LEAF"; then
  ok "design-contracts-standard.md carries design-page parse rule"
else
  not_ok "design-contracts-standard.md carries design-page parse rule" "parse rule ^## (IF-D- not found"
fi

# Reference-integrity: No installed asset body contains the literal assets/ source-path prefix
if grep -q 'assets/' "$LEAF"; then
  not_ok "design-contracts-standard.md contains no assets/ source-path prefix" "assets/ substring found in leaf body"
else
  ok "design-contracts-standard.md contains no assets/ source-path prefix"
fi

# TAP summary
echo "1..$TOTAL"
if [ "$FAIL" -gt 0 ]; then
  exit 1
fi
