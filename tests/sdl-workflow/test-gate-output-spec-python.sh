#!/usr/bin/env bash
set -uo pipefail

PASS=0
FAIL=0
TOTAL=0

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
PROJECT_ROOT="$(cd "$SCRIPT_DIR/../.." && pwd)"
DISPATCHER="$PROJECT_ROOT/assets/fbk-scripts/fbk.py"
FIXTURES="$PROJECT_ROOT/tests/fixtures/specs"

LOG_DIR="$(mktemp -d)"
export LOG_DIR
trap 'rm -rf "$LOG_DIR"' EXIT

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

# --- Test 1: valid feature spec produces pass JSON ---
STDOUT=$(python3 "$DISPATCHER" spec-gate "$FIXTURES/valid-spec.md" 2>/tmp/gate-stderr)
RC=$?
STDERR=$(cat /tmp/gate-stderr)
if [ $RC -eq 0 ] && echo "$STDOUT" | grep -q '"result": "pass"' && echo "$STDOUT" | grep -q '"scope": "feature"' && [ -z "$STDERR" ]; then
  ok "valid feature spec produces pass JSON with exit 0"
else
  not_ok "valid feature spec produces pass JSON with exit 0" "rc=$RC stdout=$STDOUT stderr=$STDERR"
fi

# --- Test 2: missing sections exits 2 ---
STDOUT=$(python3 "$DISPATCHER" spec-gate "$FIXTURES/missing-sections-spec.md" 2>/tmp/gate-stderr)
RC=$?
STDERR=$(cat /tmp/gate-stderr)
if [ $RC -eq 2 ] && echo "$STDERR" | grep -qi "Missing section"; then
  ok "missing sections exits 2 with 'Missing section' error"
else
  not_ok "missing sections exits 2 with 'Missing section' error" "rc=$RC stderr=$STDERR"
fi

# --- Test 3: injection warnings emitted ---
STDOUT=$(python3 "$DISPATCHER" spec-gate "$FIXTURES/injection-attempt-spec.md" 2>/tmp/gate-stderr)
RC=$?
STDERR=$(cat /tmp/gate-stderr)
WARN_COUNT=$(echo "$STDERR" | grep -c "WARNING" || true)
if [ $RC -eq 0 ] && [ "$WARN_COUNT" -ge 3 ]; then
  ok "injection patterns produce exit 0 with $WARN_COUNT warnings"
else
  not_ok "injection patterns produce exit 0 with 3+ warnings" "rc=$RC warnings=$WARN_COUNT stderr=$STDERR"
fi

# --- Test 4: empty file exits 2 with descriptive error ---
STDOUT=$(python3 "$DISPATCHER" spec-gate /dev/null 2>/tmp/gate-stderr)
RC=$?
STDERR=$(cat /tmp/gate-stderr)
if [ $RC -eq 2 ] && echo "$STDERR" | grep -qiE "Missing section|empty|no content|not found|unrecognized"; then
  ok "empty file exits 2 with descriptive error"
else
  not_ok "empty file exits 2 with descriptive error" "rc=$RC stderr=$STDERR"
fi

# --- Test 5: overview spec recognized as project scope ---
STDOUT=$(python3 "$DISPATCHER" spec-gate "$FIXTURES/platform-overview.md" 2>/tmp/gate-stderr)
RC=$?
STDERR=$(cat /tmp/gate-stderr)
if [ $RC -eq 0 ] && echo "$STDOUT" | grep -q '"scope": "project"'; then
  ok "overview spec recognized with project scope"
else
  not_ok "overview spec recognized with project scope" "rc=$RC stdout=$STDOUT stderr=$STDERR"
fi

# --- Summary ---
rm -f /tmp/gate-stderr
echo ""
echo "# $PASS/$TOTAL tests passed"
if [ "$FAIL" -gt 0 ]; then
  exit 1
fi
exit 0
