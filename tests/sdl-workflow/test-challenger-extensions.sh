#!/usr/bin/env bash
set -uo pipefail

PASS=0
FAIL=0
TOTAL=0

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
PROJECT_ROOT="$(cd "$SCRIPT_DIR/../.." && pwd)"
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

# --- Test 1: Challenger contains "adjacent observation" keyword (AC-13) ---
if grep -qi 'adjacent observation' "$CHALLENGER"; then
  ok "Challenger includes adjacent observation channel"
else
  not_ok "Challenger includes adjacent observation channel" "file: $CHALLENGER"
fi

# --- Test 2: Adjacent observations do not surface as findings (AC-13) ---
if grep -qiE 'informational|do not.*finding|not.*surface|not.*detection loop|exclude.*finding' "$CHALLENGER"; then
  ok "Adjacent observations documented as informational"
else
  not_ok "Adjacent observations documented as informational" "file: $CHALLENGER"
fi

# --- Test 3: Challenger contains caller tracing requirement (AC-14) ---
if grep -qiE 'caller.trac|trace.*caller|cross.reference.*caller' "$CHALLENGER"; then
  ok "Challenger includes caller tracing requirement"
else
  not_ok "Challenger includes caller tracing requirement" "file: $CHALLENGER"
fi

# --- Test 4: Caller tracing applies to behavioral type (AC-14) ---
if grep -qiE 'behavioral.*caller|behavioral.*trac|caller.*behavioral' "$CHALLENGER"; then
  ok "Caller tracing scoped to behavioral type"
else
  not_ok "Caller tracing scoped to behavioral type" "file: $CHALLENGER"
fi

# --- Test 5: Challenger contains verified-pending-execution status (AC-15) ---
if grep -qiE 'verified.pending.execution' "$CHALLENGER"; then
  ok "Challenger includes verified-pending-execution status"
else
  not_ok "Challenger includes verified-pending-execution status" "file: $CHALLENGER"
fi

# --- Test 6: Verified-pending-execution applies to test-integrity type (AC-15) ---
if grep -qiE 'test.integrity.*pending|test.integrity.*execution|pending.*test.integrity' "$CHALLENGER"; then
  ok "Verified-pending-execution scoped to test-integrity type"
else
  not_ok "Verified-pending-execution scoped to test-integrity type" "file: $CHALLENGER"
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
