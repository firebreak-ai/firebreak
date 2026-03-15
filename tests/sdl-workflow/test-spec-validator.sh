#!/usr/bin/env bash
set -uo pipefail

PASS=0
FAIL=0
TOTAL=0

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
PROJECT_ROOT="$(cd "$SCRIPT_DIR/../.." && pwd)"
GATE="$PROJECT_ROOT/home/.claude/hooks/sdl-workflow/spec-gate.sh"
FIXTURES="$PROJECT_ROOT/tests/fixtures/specs"

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

# --- Test 1: valid feature spec passes ---
STDOUT=$(bash "$GATE" "$FIXTURES/valid-spec.md" 2>/tmp/specgate-stderr)
RC=$?
STDERR=$(cat /tmp/specgate-stderr)
if [ $RC -eq 0 ] && echo "$STDOUT" | grep -q '"result":"pass"' && echo "$STDOUT" | grep -q '"scope":"feature"' && [ -z "$STDERR" ]; then
  ok "valid feature spec passes with exit 0, correct JSON, no stderr"
else
  not_ok "valid feature spec passes with exit 0, correct JSON, no stderr" "rc=$RC stdout=$STDOUT stderr=$STDERR"
fi

# --- Test 2: missing sections rejected ---
STDOUT=$(bash "$GATE" "$FIXTURES/missing-sections-spec.md" 2>/tmp/specgate-stderr)
RC=$?
STDERR=$(cat /tmp/specgate-stderr)
if [ $RC -eq 2 ] && echo "$STDERR" | grep -qi "Missing section"; then
  ok "missing sections rejected with exit 2"
else
  not_ok "missing sections rejected with exit 2" "rc=$RC stderr=$STDERR"
fi

# --- Test 3: bad AC format rejected ---
STDOUT=$(bash "$GATE" "$FIXTURES/bad-ac-format-spec.md" 2>/tmp/specgate-stderr)
RC=$?
STDERR=$(cat /tmp/specgate-stderr)
if [ $RC -eq 2 ] && echo "$STDERR" | grep -qiE "AC.*format|invalid AC"; then
  ok "bad AC format rejected with exit 2"
else
  not_ok "bad AC format rejected with exit 2" "rc=$RC stderr=$STDERR"
fi

# --- Test 4: missing AC traceability rejected ---
STDOUT=$(bash "$GATE" "$FIXTURES/no-ac-traceability-spec.md" 2>/tmp/specgate-stderr)
RC=$?
STDERR=$(cat /tmp/specgate-stderr)
if [ $RC -eq 2 ] && echo "$STDERR" | grep -qiE "testing strategy|trace.*AC|AC"; then
  ok "missing AC traceability rejected with exit 2"
else
  not_ok "missing AC traceability rejected with exit 2" "rc=$RC stderr=$STDERR"
fi

# --- Test 5: injection patterns detected ---
STDOUT=$(bash "$GATE" "$FIXTURES/injection-attempt-spec.md" 2>/tmp/specgate-stderr)
RC=$?
STDERR=$(cat /tmp/specgate-stderr)
WARN_COUNT=$(echo "$STDERR" | grep -c "WARNING" || true)
if [ $RC -eq 0 ] && [ "$WARN_COUNT" -ge 3 ]; then
  ok "injection patterns detected: exit 0 with $WARN_COUNT warnings"
else
  not_ok "injection patterns detected: exit 0 with 3+ warnings" "rc=$RC warnings=$WARN_COUNT stderr=$STDERR"
fi

# --- Test 6: legitimate HTML passes without warnings ---
STDOUT=$(bash "$GATE" "$FIXTURES/legitimate-html-spec.md" 2>/tmp/specgate-stderr)
RC=$?
STDERR=$(cat /tmp/specgate-stderr)
if [ $RC -eq 0 ] && [ -z "$STDERR" ]; then
  ok "legitimate HTML passes without false-positive warnings"
else
  not_ok "legitimate HTML passes without false-positive warnings" "rc=$RC stderr=$STDERR"
fi

# --- Test 7: unicode spec passes without warnings ---
STDOUT=$(bash "$GATE" "$FIXTURES/unicode-spec.md" 2>/tmp/specgate-stderr)
RC=$?
STDERR=$(cat /tmp/specgate-stderr)
if [ $RC -eq 0 ] && [ -z "$STDERR" ]; then
  ok "unicode spec passes without false-positive warnings"
else
  not_ok "unicode spec passes without false-positive warnings" "rc=$RC stderr=$STDERR"
fi

# --- Test 8: overview spec passes ---
STDOUT=$(bash "$GATE" "$FIXTURES/platform-overview.md" 2>/tmp/specgate-stderr)
RC=$?
if [ $RC -eq 0 ] && echo "$STDOUT" | grep -q '"scope":"project"'; then
  ok "overview spec passes with project scope"
else
  not_ok "overview spec passes with project scope" "rc=$RC stdout=$STDOUT"
fi

# --- Test 9: non-existent file rejected ---
STDOUT=$(bash "$GATE" "tests/fixtures/specs/nonexistent.md" 2>/dev/null)
RC=$?
if [ $RC -eq 2 ]; then
  ok "non-existent file rejected with exit 2"
else
  not_ok "non-existent file rejected with exit 2" "rc=$RC"
fi

# --- Test 10: unrecognized filename pattern rejected ---
TMPFILE=$(mktemp /tmp/test-random-name-XXXX.md)
cat "$FIXTURES/valid-spec.md" > "$TMPFILE"
STDOUT=$(bash "$GATE" "$TMPFILE" 2>/dev/null)
RC=$?
rm -f "$TMPFILE"
if [ $RC -eq 2 ]; then
  ok "unrecognized filename pattern rejected with exit 2"
else
  not_ok "unrecognized filename pattern rejected with exit 2" "rc=$RC"
fi

# --- Summary ---
rm -f /tmp/specgate-stderr
echo ""
echo "# $PASS/$TOTAL tests passed"
if [ "$FAIL" -gt 0 ]; then
  exit 1
fi
exit 0
