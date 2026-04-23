#!/usr/bin/env bash
set -uo pipefail

PASS=0
FAIL=0
TOTAL=0

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
PROJECT_ROOT="$(cd "$SCRIPT_DIR/../.." && pwd)"
DISPATCHER="$PROJECT_ROOT/assets/fbk-scripts/fbk.py"
FIXTURES="$PROJECT_ROOT/tests/fixtures/state"

TMPDIR_BASE="$(mktemp -d)"
trap 'rm -rf "$TMPDIR_BASE"' EXIT

STATE_DIR="$TMPDIR_BASE/state"
mkdir -p "$STATE_DIR"
cp "$FIXTURES"/*.json "$STATE_DIR/"
export STATE_DIR

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

# --- Test 1: queued spec shows spec name, QUEUED, and timestamp ---
OUTPUT=$(python3 "$DISPATCHER" dispatch-status queued-spec 2>&1)
RC=$?
if [ $RC -eq 0 ] && echo "$OUTPUT" | grep -q "queued-spec" && echo "$OUTPUT" | grep -q "QUEUED" && echo "$OUTPUT" | grep -q "2026-03-14"; then
  ok "queued spec shows spec name, QUEUED, and timestamp"
else
  not_ok "queued spec shows spec name, QUEUED, and timestamp" "rc=$RC output: $OUTPUT"
fi

# --- Test 2: reviewing spec shows REVIEWING and stage history ---
OUTPUT=$(python3 "$DISPATCHER" dispatch-status reviewing-spec 2>&1)
RC=$?
if [ $RC -eq 0 ] && echo "$OUTPUT" | grep -q "REVIEWING" && echo "$OUTPUT" | grep -q "QUEUED" && echo "$OUTPUT" | grep -q "VALIDATING" && echo "$OUTPUT" | grep -q "VALIDATED"; then
  ok "reviewing spec shows REVIEWING and stage history"
else
  not_ok "reviewing spec shows REVIEWING and stage history" "rc=$RC output: $OUTPUT"
fi

# --- Test 3: parked spec shows PARKED, failed stage, and reason ---
OUTPUT=$(python3 "$DISPATCHER" dispatch-status parked-spec 2>&1)
RC=$?
if [ $RC -eq 0 ] && echo "$OUTPUT" | grep -q "PARKED" && echo "$OUTPUT" | grep -q "VALIDATING" && echo "$OUTPUT" | grep -q "missing required section"; then
  ok "parked spec shows PARKED, failed stage, and reason"
else
  not_ok "parked spec shows PARKED, failed stage, and reason" "rc=$RC output: $OUTPUT"
fi

# --- Test 4: completed spec shows COMPLETED ---
OUTPUT=$(python3 "$DISPATCHER" dispatch-status completed-spec 2>&1)
RC=$?
if [ $RC -eq 0 ] && echo "$OUTPUT" | grep -q "COMPLETED"; then
  ok "completed spec shows COMPLETED"
else
  not_ok "completed spec shows COMPLETED" "rc=$RC output: $OUTPUT"
fi

# --- Test 5: non-existent spec exits 1 with not-found message ---
OUTPUT=$(python3 "$DISPATCHER" dispatch-status does-not-exist 2>&1)
RC=$?
if [ $RC -eq 1 ] && echo "$OUTPUT" | grep -qi "not found\|no pipeline state"; then
  ok "non-existent spec exits 1 with not-found message"
else
  not_ok "non-existent spec exits 1 with not-found message" "rc=$RC output: $OUTPUT"
fi

# --- Test 6: output is human-readable, not JSON ---
OUTPUT=$(python3 "$DISPATCHER" dispatch-status queued-spec 2>&1)
FIRST_CHAR=$(echo "$OUTPUT" | head -c1)
if [ "$FIRST_CHAR" != "{" ] && echo "$OUTPUT" | grep -qE "^[A-Za-z]+:"; then
  ok "output is human-readable with labeled fields, not JSON"
else
  not_ok "output is human-readable with labeled fields, not JSON" "first char: $FIRST_CHAR"
fi

# --- Test 7: error history displayed for parked spec ---
OUTPUT=$(python3 "$DISPATCHER" dispatch-status parked-spec 2>&1)
if echo "$OUTPUT" | grep -q "spec validation failed"; then
  ok "error history displayed for parked spec"
else
  not_ok "error history displayed for parked spec" "output: $OUTPUT"
fi

# ---- Summary ----
echo ""
echo "# Tests: $TOTAL, Pass: $PASS, Fail: $FAIL"

if [ "$FAIL" -gt 0 ]; then
  exit 1
fi
exit 0
