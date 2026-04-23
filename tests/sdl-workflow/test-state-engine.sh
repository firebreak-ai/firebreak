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
echo "1..15"

# ---- Test 1: create produces valid JSON with QUEUED and correct schema ----
OUTPUT=$(python3 "$DISPATCHER" state create test-spec-1 2>&1)
if echo "$OUTPUT" | python3 -c "
import sys, json
d = json.load(sys.stdin)
assert d['current_state'] == 'QUEUED'
assert d['spec_name'] == 'test-spec-1'
assert 'stage_timestamps' in d
assert 'agent_ids' in d
assert 'verification_results' in d
assert 'error_history' in d
assert 'parked_info' in d
assert 'QUEUED' in d['stage_timestamps']
" 2>/dev/null; then
  ok "create produces valid JSON with QUEUED and correct schema"
else
  not_ok "create produces valid JSON with QUEUED and correct schema" "$OUTPUT"
fi

# ---- Test 2: create persists to file ----
if [ -f "$STATE_DIR/test-spec-1.json" ]; then
  FILE_STATE=$(python3 -c "import json; d=json.load(open('$STATE_DIR/test-spec-1.json')); print(d['current_state'])")
  if [ "$FILE_STATE" = "QUEUED" ]; then
    ok "create persists to file"
  else
    not_ok "create persists to file" "state=$FILE_STATE"
  fi
else
  not_ok "create persists to file" "file not found"
fi

# ---- Test 3: valid transition QUEUED->VALIDATING ----
OUTPUT=$(python3 "$DISPATCHER" state transition test-spec-1 VALIDATING 2>&1)
CURRENT=$(echo "$OUTPUT" | python3 -c "import sys, json; print(json.load(sys.stdin)['current_state'])" 2>/dev/null)
if [ "$CURRENT" = "VALIDATING" ]; then
  ok "valid transition QUEUED->VALIDATING"
else
  not_ok "valid transition QUEUED->VALIDATING" "$OUTPUT"
fi

# ---- Test 4: multi-step chain QUEUED->...->BREAKING_DOWN ----
python3 "$DISPATCHER" state create test-chain >/dev/null 2>&1
python3 "$DISPATCHER" state transition test-chain VALIDATING >/dev/null 2>&1
python3 "$DISPATCHER" state transition test-chain VALIDATED >/dev/null 2>&1
python3 "$DISPATCHER" state transition test-chain REVIEWING >/dev/null 2>&1
python3 "$DISPATCHER" state transition test-chain REVIEWED >/dev/null 2>&1
OUTPUT=$(python3 "$DISPATCHER" state transition test-chain BREAKING_DOWN 2>&1)
CURRENT=$(echo "$OUTPUT" | python3 -c "import sys, json; print(json.load(sys.stdin)['current_state'])" 2>/dev/null)
if [ "$CURRENT" = "BREAKING_DOWN" ]; then
  ok "multi-step chain QUEUED->...->BREAKING_DOWN"
else
  not_ok "multi-step chain QUEUED->...->BREAKING_DOWN" "$OUTPUT"
fi

# ---- Test 5: invalid transition QUEUED->COMPLETED rejected ----
python3 "$DISPATCHER" state create test-invalid-1 >/dev/null 2>&1
if python3 "$DISPATCHER" state transition test-invalid-1 COMPLETED 2>/dev/null; then
  not_ok "invalid transition QUEUED->COMPLETED rejected" "should have failed"
else
  ok "invalid transition QUEUED->COMPLETED rejected"
fi

# ---- Test 6: invalid transition QUEUED->REVIEWED rejected ----
python3 "$DISPATCHER" state create test-invalid-2 >/dev/null 2>&1
if python3 "$DISPATCHER" state transition test-invalid-2 REVIEWED 2>/dev/null; then
  not_ok "invalid transition QUEUED->REVIEWED rejected" "should have failed"
else
  ok "invalid transition QUEUED->REVIEWED rejected"
fi

# ---- Test 7: state persists and reads back ----
READ_OUTPUT=$(python3 "$DISPATCHER" state read test-spec-1 2>&1)
READ_STATE=$(echo "$READ_OUTPUT" | python3 -c "import sys, json; print(json.load(sys.stdin)['current_state'])" 2>/dev/null)
if [ "$READ_STATE" = "VALIDATING" ]; then
  ok "state persists and reads back"
else
  not_ok "state persists and reads back" "expected VALIDATING got $READ_STATE"
fi

# ---- Test 8: PARKED records failed_stage and reason ----
python3 "$DISPATCHER" state create test-parked >/dev/null 2>&1
python3 "$DISPATCHER" state transition test-parked VALIDATING >/dev/null 2>&1
OUTPUT=$(python3 "$DISPATCHER" state transition test-parked PARKED --reason "needs clarification" 2>&1)
PARKED_OK=$(echo "$OUTPUT" | python3 -c "
import sys, json
d = json.load(sys.stdin)
assert d['current_state'] == 'PARKED'
assert d['parked_info']['failed_stage'] == 'VALIDATING'
assert d['parked_info']['reason'] == 'needs clarification'
print('yes')
" 2>/dev/null)
if [ "$PARKED_OK" = "yes" ]; then
  ok "PARKED records failed_stage and reason"
else
  not_ok "PARKED records failed_stage and reason" "$OUTPUT"
fi

# ---- Test 9: PARKED->READY->resume lifecycle ----
python3 "$DISPATCHER" state transition test-parked READY >/dev/null 2>&1
OUTPUT=$(python3 "$DISPATCHER" state transition test-parked VALIDATING 2>&1)
RESUME_STATE=$(echo "$OUTPUT" | python3 -c "import sys, json; print(json.load(sys.stdin)['current_state'])" 2>/dev/null)
if [ "$RESUME_STATE" = "VALIDATING" ]; then
  ok "PARKED->READY->resume lifecycle"
else
  not_ok "PARKED->READY->resume lifecycle" "expected VALIDATING got $RESUME_STATE"
fi

# ---- Test 10: timestamps are ISO8601 and increasing ----
READ_OUTPUT=$(python3 "$DISPATCHER" state read test-chain 2>&1)
TS_OK=$(echo "$READ_OUTPUT" | python3 -c "
import sys, json
from datetime import datetime
d = json.load(sys.stdin)
ts = d['stage_timestamps']
expected_order = ['QUEUED', 'VALIDATING', 'VALIDATED', 'REVIEWING', 'REVIEWED', 'BREAKING_DOWN']
prev = None
for state in expected_order:
    t = datetime.fromisoformat(ts[state])
    if prev and t < prev:
        print('no')
        sys.exit(0)
    prev = t
print('yes')
" 2>/dev/null)
if [ "$TS_OK" = "yes" ]; then
  ok "timestamps are ISO8601 and increasing"
else
  not_ok "timestamps are ISO8601 and increasing"
fi

# ---- Test 11: get-valid-transitions returns correct states ----
python3 "$DISPATCHER" state create test-transitions >/dev/null 2>&1
OUTPUT=$(python3 "$DISPATCHER" state get-valid-transitions test-transitions 2>&1)
TRANS_OK=$(echo "$OUTPUT" | python3 -c "
import sys, json
states = json.load(sys.stdin)
assert states == ['VALIDATING'], f'expected [VALIDATING] got {states}'
print('yes')
" 2>/dev/null)
if [ "$TRANS_OK" = "yes" ]; then
  ok "get-valid-transitions returns correct states for QUEUED"
else
  not_ok "get-valid-transitions returns correct states for QUEUED" "$OUTPUT"
fi

# ---- Test 12: get-valid-transitions for VALIDATING ----
python3 "$DISPATCHER" state transition test-transitions VALIDATING >/dev/null 2>&1
OUTPUT=$(python3 "$DISPATCHER" state get-valid-transitions test-transitions 2>&1)
TRANS_OK=$(echo "$OUTPUT" | python3 -c "
import sys, json
states = sorted(json.load(sys.stdin))
assert states == ['PARKED', 'VALIDATED'], f'got {states}'
print('yes')
" 2>/dev/null)
if [ "$TRANS_OK" = "yes" ]; then
  ok "get-valid-transitions returns correct states for VALIDATING"
else
  not_ok "get-valid-transitions returns correct states for VALIDATING" "$OUTPUT"
fi

# ---- Test 13: get-valid-transitions for COMPLETED (terminal) ----
python3 "$DISPATCHER" state create test-terminal >/dev/null 2>&1
# fast-forward to COMPLETED
python3 "$DISPATCHER" state transition test-terminal VALIDATING >/dev/null 2>&1
python3 "$DISPATCHER" state transition test-terminal VALIDATED >/dev/null 2>&1
python3 "$DISPATCHER" state transition test-terminal REVIEWING >/dev/null 2>&1
python3 "$DISPATCHER" state transition test-terminal REVIEWED >/dev/null 2>&1
python3 "$DISPATCHER" state transition test-terminal BREAKING_DOWN >/dev/null 2>&1
python3 "$DISPATCHER" state transition test-terminal BROKEN_DOWN >/dev/null 2>&1
python3 "$DISPATCHER" state transition test-terminal TASK_REVIEWING >/dev/null 2>&1
python3 "$DISPATCHER" state transition test-terminal TASKS_READY >/dev/null 2>&1
python3 "$DISPATCHER" state transition test-terminal TESTING >/dev/null 2>&1
python3 "$DISPATCHER" state transition test-terminal TESTS_WRITTEN >/dev/null 2>&1
python3 "$DISPATCHER" state transition test-terminal TEST_REVIEWING >/dev/null 2>&1
python3 "$DISPATCHER" state transition test-terminal TESTS_READY >/dev/null 2>&1
python3 "$DISPATCHER" state transition test-terminal IMPLEMENTING >/dev/null 2>&1
python3 "$DISPATCHER" state transition test-terminal IMPLEMENTED >/dev/null 2>&1
python3 "$DISPATCHER" state transition test-terminal VERIFYING >/dev/null 2>&1
python3 "$DISPATCHER" state transition test-terminal COMPLETED >/dev/null 2>&1
OUTPUT=$(python3 "$DISPATCHER" state get-valid-transitions test-terminal 2>&1)
TRANS_OK=$(echo "$OUTPUT" | python3 -c "
import sys, json
states = json.load(sys.stdin)
assert states == [], f'got {states}'
print('yes')
" 2>/dev/null)
if [ "$TRANS_OK" = "yes" ]; then
  ok "get-valid-transitions returns empty for COMPLETED (terminal)"
else
  not_ok "get-valid-transitions returns empty for COMPLETED (terminal)" "$OUTPUT"
fi

# ---- Test 14: get-valid-transitions for READY resolves dynamically ----
OUTPUT=$(python3 "$DISPATCHER" state get-valid-transitions test-parked 2>&1)
# test-parked was READY after test 9, then transitioned to VALIDATING
# We need a fresh parked spec in READY state
python3 "$DISPATCHER" state create test-ready-trans >/dev/null 2>&1
python3 "$DISPATCHER" state transition test-ready-trans VALIDATING >/dev/null 2>&1
python3 "$DISPATCHER" state transition test-ready-trans PARKED --reason "test" >/dev/null 2>&1
python3 "$DISPATCHER" state transition test-ready-trans READY >/dev/null 2>&1
OUTPUT=$(python3 "$DISPATCHER" state get-valid-transitions test-ready-trans 2>&1)
TRANS_OK=$(echo "$OUTPUT" | python3 -c "
import sys, json
states = json.load(sys.stdin)
assert states == ['VALIDATING'], f'expected [VALIDATING] got {states}'
print('yes')
" 2>/dev/null)
if [ "$TRANS_OK" = "yes" ]; then
  ok "get-valid-transitions for READY resolves dynamically"
else
  not_ok "get-valid-transitions for READY resolves dynamically" "$OUTPUT"
fi

# ---- Test 15: duplicate create fails ----
if python3 "$DISPATCHER" state create test-spec-1 2>/dev/null; then
  not_ok "duplicate create fails" "should have failed"
else
  ok "duplicate create fails"
fi

# ---- Summary ----
echo ""
echo "# Tests: $TESTS, Pass: $PASS, Fail: $FAIL"

if [ "$FAIL" -gt 0 ]; then
  exit 1
fi
exit 0
