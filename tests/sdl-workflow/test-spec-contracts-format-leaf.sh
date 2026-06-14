#!/bin/bash
# Test: Spec interface contracts format leaf and feature-spec-guide route
# Verifies that feature-spec-guide.md carries the required-section note and conditional route,
# and that interface-contracts-format.md carries the three section shapes and blast-radius derivation.

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

# Define paths to the spec documents
GUIDE="$PROJECT_ROOT/assets/fbk-docs/fbk-sdl-workflow/feature-spec-guide.md"
LEAF="$PROJECT_ROOT/assets/fbk-docs/fbk-sdl-workflow/interface-contracts-format.md"

# Instruction-hygiene tests (AC-15)

# Test 1: feature-spec-guide.md states Interface contracts is a required section
if grep -q "^## Interface contracts" "$GUIDE" && grep -q "required" "$GUIDE"; then
  ok "feature-spec-guide.md states Interface contracts as required section"
else
  not_ok "feature-spec-guide.md states Interface contracts as required section" "heading or required marker not found"
fi

# Test 2: feature-spec-guide.md routes to interface-contracts-format.md conditionally
if grep -q "interface-contracts-format" "$GUIDE"; then
  if grep -B2 -A2 "interface-contracts-format" "$GUIDE" | grep -qE "(when|if|only|condition|enumerate|exclude|uncovered)"; then
    ok "feature-spec-guide.md routes to interface-contracts-format.md conditionally"
  else
    not_ok "feature-spec-guide.md routes to interface-contracts-format.md conditionally" "reference found but no conditional clause nearby"
  fi
else
  not_ok "feature-spec-guide.md routes to interface-contracts-format.md conditionally" "no reference to interface-contracts-format found"
fi

# Test 3: interface-contracts-format.md carries section shape - Interface contracts
if grep -q "^## Interface contracts" "$LEAF"; then
  ok "interface-contracts-format.md carries Interface contracts section"
else
  not_ok "interface-contracts-format.md carries Interface contracts section" "anchored heading not found"
fi

# Test 4: interface-contracts-format.md carries section shape - Excluded contracts
if grep -q "^## Excluded contracts" "$LEAF"; then
  ok "interface-contracts-format.md carries Excluded contracts section"
else
  not_ok "interface-contracts-format.md carries Excluded contracts section" "anchored heading not found"
fi

# Test 5: interface-contracts-format.md carries section shape - Uncovered acceptance criteria
if grep -q "^## Uncovered acceptance criteria" "$LEAF"; then
  ok "interface-contracts-format.md carries Uncovered acceptance criteria section"
else
  not_ok "interface-contracts-format.md carries Uncovered acceptance criteria section" "anchored heading not found"
fi

# Test 6: interface-contracts-format.md carries blast-radius derivation instruction
if grep -q "blast" "$LEAF"; then
  ok "interface-contracts-format.md carries blast-radius derivation instruction"
else
  not_ok "interface-contracts-format.md carries blast-radius derivation instruction" "structural marker 'blast' not found"
fi

# Test 7: interface-contracts-format.md carries IF-S-NN id marking rule
if grep -q "IF-S-" "$LEAF"; then
  ok "interface-contracts-format.md marks pre-existing entries with IF-S-NN ids"
else
  not_ok "interface-contracts-format.md marks pre-existing entries with IF-S-NN ids" "IF-S- token not found"
fi

# Reference-integrity tests

# Test 8: The leaf file exists
if [ -f "$LEAF" ]; then
  ok "interface-contracts-format.md file exists"
else
  not_ok "interface-contracts-format.md file exists" "file not found at $LEAF"
fi

# Test 9: Leaf contains no assets/ source-path prefix (must use installed paths)
if ! grep -q "assets/" "$LEAF"; then
  ok "interface-contracts-format.md contains no assets/ source-path prefix"
else
  not_ok "interface-contracts-format.md contains no assets/ source-path prefix" "literal 'assets/' found in leaf body"
fi

# TAP summary
echo "1..$TOTAL"
if [ "$FAIL" -gt 0 ]; then
  exit 1
fi
