#!/usr/bin/env bash
set -uo pipefail

TESTS=0
PASS=0
FAIL=0

ok() {
  TESTS=$((TESTS + 1))
  PASS=$((PASS + 1))
  echo "ok $TESTS - $1"
}

not_ok() {
  TESTS=$((TESTS + 1))
  FAIL=$((FAIL + 1))
  echo "not ok $TESTS - $1"
  [ -n "${2:-}" ] && echo "# $2"
}

# Setup
TMPDIR_STATE="$(mktemp -d)"
export STATE_DIR="$TMPDIR_STATE"
trap 'rm -rf "$TMPDIR_STATE"' EXIT

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(cd "$SCRIPT_DIR/../.." && pwd)"
DISPATCHER="$PROJECT_ROOT/assets/fbk-scripts/fbk.py"

echo "TAP version 13"
echo "1..3"

# ---- Test 1: state create outputs valid JSON with QUEUED ----
OUTPUT=$(python3 "$DISPATCHER" state create test-feature 2>&1)
if echo "$OUTPUT" | python3 -c "
import sys, json
d = json.load(sys.stdin)
assert d['current_state'] == 'QUEUED', f'expected QUEUED, got {d[\"current_state\"]}'
" 2>/dev/null; then
  ok "state create outputs valid JSON with current_state == QUEUED"
else
  not_ok "state create outputs valid JSON with current_state == QUEUED" "$OUTPUT"
fi

# ---- Test 2: state transition QUEUED->VALIDATING succeeds ----
OUTPUT=$(python3 "$DISPATCHER" state transition test-feature VALIDATING 2>&1)
if echo "$OUTPUT" | python3 -c "
import sys, json
d = json.load(sys.stdin)
assert d['current_state'] == 'VALIDATING', f'expected VALIDATING, got {d[\"current_state\"]}'
" 2>/dev/null; then
  ok "state transition QUEUED->VALIDATING succeeds with updated state"
else
  not_ok "state transition QUEUED->VALIDATING succeeds with updated state" "$OUTPUT"
fi

# ---- Test 3: invalid transition VALIDATING->COMPLETED rejected ----
if python3 "$DISPATCHER" state transition test-feature COMPLETED 2>/dev/null; then
  not_ok "invalid transition VALIDATING->COMPLETED rejected" "should have failed"
else
  ok "invalid transition VALIDATING->COMPLETED rejected"
fi

# ---- Summary ----
echo ""
echo "# Tests: $TESTS, Pass: $PASS, Fail: $FAIL"

if [ "$FAIL" -gt 0 ]; then
  exit 1
fi
exit 0
