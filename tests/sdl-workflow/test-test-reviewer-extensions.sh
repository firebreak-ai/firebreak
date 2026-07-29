#!/usr/bin/env bash
set -uo pipefail

PASS=0
FAIL=0
TOTAL=0

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
PROJECT_ROOT="$(cd "$SCRIPT_DIR/../.." && pwd)"
# fbk-test-reviewer.md was deleted in the unified-review-shape consolidation.
# Test-review-specific content now lives in test-lens.md.
LENS="$PROJECT_ROOT/assets/fbk-docs/fbk-review-lenses/test-lens.md"

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

# retired: "Tier 1" was a structural concept specific to fbk-test-reviewer.md.
# In the unified-review-shape architecture the tiered structure was replaced by
# the lens's finding-type taxonomy (weakened-assertion, untested-behavior,
# trivially-passing, manifest-drift) and the shared-detection.md audit. The three
# Tier 1 criteria (stale failure annotation, empty gate test, advisory assertion)
# map conceptually to test-lens types but with different labels — preserving the
# old pattern-match assertions would produce false failures, not meaningful coverage.
# unified-review-shape consolidation.

# --- Test 1: Lens defines weakened-assertion with stale/weakened check language ---
if grep -qiE 'weakened|weakening|narrowed|relaxed' "$LENS"; then
  ok "Lens defines weakened assertion criterion"
else
  not_ok "Lens defines weakened assertion criterion" "file: $LENS"
fi

# --- Test 2: Lens defines trivially-passing with vacuous assertion language ---
if grep -qiE 'vacuous|trivially.passing|error.absence|passes unconditionally' "$LENS"; then
  ok "Lens defines trivially-passing (vacuous/unconditional) criterion"
else
  not_ok "Lens defines trivially-passing (vacuous/unconditional) criterion" "file: $LENS"
fi

# --- Test 3: Lens defines untested-behavior type ---
if grep -qi 'untested-behavior' "$LENS"; then
  ok "Lens defines untested-behavior finding type"
else
  not_ok "Lens defines untested-behavior finding type" "file: $LENS"
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
