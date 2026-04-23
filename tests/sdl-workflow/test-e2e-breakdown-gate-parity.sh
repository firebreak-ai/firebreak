#!/usr/bin/env bash
set -uo pipefail

PASS=0
FAIL=0
TOTAL=0

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
PROJECT_ROOT="$(cd "$SCRIPT_DIR/../.." && pwd)"
DISPATCHER="$PROJECT_ROOT/assets/fbk-scripts/fbk.py"
GOLDEN="$PROJECT_ROOT/tests/fixtures/tasks"

ok() {
  TOTAL=$((TOTAL + 1))
  PASS=$((PASS + 1))
  echo "ok $TOTAL - $1"
}

not_ok() {
  TOTAL=$((TOTAL + 1))
  FAIL=$((FAIL + 1))
  echo "not ok $TOTAL - $1"
  echo "  $2"
}

# Test 1: valid breakdown produces same result as golden
STDOUT=$(python3 "$DISPATCHER" breakdown-gate "$GOLDEN/valid-spec.md" "$GOLDEN/valid" 2>/dev/null)
EXIT_CODE=$?
GOLDEN_RESULT=$(python3 -c "import json; print(json.load(open('$GOLDEN/golden-breakdown-gate-valid.json'))['result'])")

if [[ $EXIT_CODE -eq 0 ]]; then
  PYTHON_RESULT=$(echo "$STDOUT" | python3 -c "import sys,json; print(json.load(sys.stdin)['result'])" 2>/dev/null)
  if [[ "$PYTHON_RESULT" == "$GOLDEN_RESULT" ]]; then
    ok "valid breakdown: exit 0, result matches golden ($GOLDEN_RESULT)"
  else
    not_ok "valid breakdown: result mismatch" "expected=$GOLDEN_RESULT got=$PYTHON_RESULT"
  fi
else
  not_ok "valid breakdown: expected exit 0" "got exit $EXIT_CODE"
fi

# Test 2: invalid breakdown exits with error and reports the uncovered AC
STDERR_T2=$(python3 "$DISPATCHER" breakdown-gate "$GOLDEN/valid-spec.md" "$GOLDEN/uncovered-ac" 2>&1 >/dev/null)
EXIT_CODE=$?

if [[ $EXIT_CODE -eq 2 ]] && echo "$STDERR_T2" | grep -qi "coverage\|AC-"; then
  ok "invalid breakdown: exits 2, reports AC coverage failure"
else
  not_ok "invalid breakdown: expected exit 2 with AC coverage failure" "exit=$EXIT_CODE stderr=$STDERR_T2"
fi

echo ""
echo "$PASS/$TOTAL tests passed"
[[ $FAIL -eq 0 ]] && exit 0 || exit 1
