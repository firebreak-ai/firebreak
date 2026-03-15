#!/usr/bin/env bash
set -uo pipefail

PASS=0
FAIL=0
TOTAL=0

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
PROJECT_ROOT="$(cd "$SCRIPT_DIR/../.." && pwd)"
GATE="$PROJECT_ROOT/home/.claude/hooks/sdl-workflow/task-reviewer-gate.sh"
FIXTURES="$PROJECT_ROOT/tests/fixtures/tasks"

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

# --- Test 1: valid task set passes ---
STDOUT=$(bash "$GATE" "$FIXTURES/valid-spec.md" "$FIXTURES/valid/" 2>/tmp/tr-stderr)
RC=$?
STDERR=$(cat /tmp/tr-stderr)
if [ $RC -eq 0 ] && echo "$STDOUT" | grep -q '"result"'; then
  ok "valid task set passes with exit 0"
else
  not_ok "valid task set passes with exit 0" "rc=$RC stdout=$STDOUT stderr=$STDERR"
fi

# --- Test 2: missing required fields rejected ---
STDOUT=$(bash "$GATE" "$FIXTURES/valid-spec.md" "$FIXTURES/missing-fields/" 2>/tmp/tr-stderr)
RC=$?
STDERR=$(cat /tmp/tr-stderr)
if [ $RC -eq 2 ] && echo "$STDERR" | grep -qi "missing"; then
  ok "missing required fields rejected with exit 2"
else
  not_ok "missing required fields rejected with exit 2" "rc=$RC stderr=$STDERR"
fi

# --- Test 3: impl without test_tasks rejected ---
STDOUT=$(bash "$GATE" "$FIXTURES/valid-spec.md" "$FIXTURES/impl-no-test-tasks/" 2>/tmp/tr-stderr)
RC=$?
STDERR=$(cat /tmp/tr-stderr)
if [ $RC -eq 2 ] && echo "$STDERR" | grep -qi "test_tasks"; then
  ok "implementation task without test_tasks rejected"
else
  not_ok "implementation task without test_tasks rejected" "rc=$RC stderr=$STDERR"
fi

# --- Test 4: overlapping file boundaries rejected ---
STDOUT=$(bash "$GATE" "$FIXTURES/valid-spec.md" "$FIXTURES/overlap/" 2>/tmp/tr-stderr)
RC=$?
STDERR=$(cat /tmp/tr-stderr)
if [ $RC -eq 2 ] && echo "$STDERR" | grep -qi "shared.py\|conflict"; then
  ok "overlapping file boundaries rejected with exit 2"
else
  not_ok "overlapping file boundaries rejected with exit 2" "rc=$RC stderr=$STDERR"
fi

# --- Test 5: uncovered AC rejected ---
STDOUT=$(bash "$GATE" "$FIXTURES/valid-spec.md" "$FIXTURES/uncovered-ac/" 2>/tmp/tr-stderr)
RC=$?
STDERR=$(cat /tmp/tr-stderr)
if [ $RC -eq 2 ] && echo "$STDERR" | grep -qi "AC-03"; then
  ok "uncovered AC rejected with exit 2, mentions AC-03"
else
  not_ok "uncovered AC rejected with exit 2, mentions AC-03" "rc=$RC stderr=$STDERR"
fi

# --- Test 6: invalid test_tasks reference rejected ---
STDOUT=$(bash "$GATE" "$FIXTURES/valid-spec.md" "$FIXTURES/bad-test-ref/" 2>/tmp/tr-stderr)
RC=$?
STDERR=$(cat /tmp/tr-stderr)
if [ $RC -eq 2 ] && echo "$STDERR" | grep -qiE "task-99|invalid|does not match"; then
  ok "invalid test_tasks reference rejected"
else
  not_ok "invalid test_tasks reference rejected" "rc=$RC stderr=$STDERR"
fi

# --- Test 7: missing file lists rejected ---
STDOUT=$(bash "$GATE" "$FIXTURES/valid-spec.md" "$FIXTURES/no-files/" 2>/tmp/tr-stderr)
RC=$?
STDERR=$(cat /tmp/tr-stderr)
if [ $RC -eq 2 ] && echo "$STDERR" | grep -qiE "files_to_create|files_to_modify|neither"; then
  ok "missing file lists rejected"
else
  not_ok "missing file lists rejected" "rc=$RC stderr=$STDERR"
fi

# --- Test 8: files_to_modify with non-existent path rejected ---
STDOUT=$(bash "$GATE" "$FIXTURES/valid-spec.md" "$FIXTURES/bad-path/" 2>/tmp/tr-stderr)
RC=$?
STDERR=$(cat /tmp/tr-stderr)
if [ $RC -eq 2 ] && echo "$STDERR" | grep -qi "nonexistent\|does not exist"; then
  ok "files_to_modify with non-existent path rejected"
else
  not_ok "files_to_modify with non-existent path rejected" "rc=$RC stderr=$STDERR"
fi

# --- Test 9: valid task set with full AC coverage passes ---
STDOUT=$(bash "$GATE" "$FIXTURES/valid-spec.md" "$FIXTURES/valid/" 2>/tmp/tr-stderr)
RC=$?
if [ $RC -eq 0 ]; then
  ok "valid task set with full AC coverage passes without false rejections"
else
  not_ok "valid task set with full AC coverage passes without false rejections" "rc=$RC"
fi

# --- Summary ---
rm -f /tmp/tr-stderr
echo ""
echo "# $PASS/$TOTAL tests passed"
if [ "$FAIL" -gt 0 ]; then
  exit 1
fi
exit 0
