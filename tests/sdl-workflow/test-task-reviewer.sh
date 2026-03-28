#!/usr/bin/env bash
set -uo pipefail

PASS=0
FAIL=0
TOTAL=0

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
PROJECT_ROOT="$(cd "$SCRIPT_DIR/../.." && pwd)"
GATE="$PROJECT_ROOT/assets/hooks/fbk-sdl-workflow/task-reviewer-gate.sh"
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

# --- Test 10: corrective category passes with test-only AC coverage ---
# AC-02 is covered only by a test task; corrective category should allow this.
STDOUT=$(bash "$GATE" "$FIXTURES/corrective/corrective-spec.md" "$FIXTURES/corrective/" 2>/tmp/tr-stderr)
RC=$?
STDERR=$(cat /tmp/tr-stderr)
if [ $RC -eq 0 ] && echo "$STDOUT" | grep -q '"result"'; then
  ok "corrective category passes with test-only AC coverage"
else
  not_ok "corrective category passes with test-only AC coverage" "rc=$RC stdout=$STDOUT stderr=$STDERR"
fi

# --- Test 11: corrective category rejects AC covered by neither ---
# Remove AC-02 from task-01's covers inline so AC-02 has no coverage at all.
TMPDIR_T11="$(mktemp -d)"
cp "$FIXTURES/corrective/task-02-impl-fix.md" "$TMPDIR_T11/"
cp "$FIXTURES/corrective/task.json" "$TMPDIR_T11/"
# Write task-01 with AC-02 removed from covers
cat > "$TMPDIR_T11/task-01-test-fix.md" <<'TASKEOF'
---
id: T-01
type: test
wave: 1
covers: ["AC-01"]
files_to_create: [tests/regression/test-fix.sh]
completion_gate: "regression tests compile and fail"
---

# Task 01: Regression Tests for Corrective Fix

Write regression tests covering AC-01 only (AC-02 removed to trigger failure).
TASKEOF
STDOUT=$(bash "$GATE" "$FIXTURES/corrective/corrective-spec.md" "$TMPDIR_T11/" 2>/tmp/tr-stderr)
RC=$?
STDERR=$(cat /tmp/tr-stderr)
rm -rf "$TMPDIR_T11"
if [ $RC -eq 2 ] && echo "$STDERR" | grep -qi "AC-02"; then
  ok "corrective category rejects AC covered by neither test nor impl"
else
  not_ok "corrective category rejects AC covered by neither test nor impl" "rc=$RC stderr=$STDERR"
fi

# --- Test 12: testing-infrastructure passes with test-only ACs ---
# AC-01 is covered only by a test task; testing-infrastructure category should allow this.
STDOUT=$(bash "$GATE" "$FIXTURES/testing-infra/testing-infra-spec.md" "$FIXTURES/testing-infra/" 2>/tmp/tr-stderr)
RC=$?
STDERR=$(cat /tmp/tr-stderr)
if [ $RC -eq 0 ] && echo "$STDOUT" | grep -q '"result"'; then
  ok "testing-infrastructure category passes with test-only ACs"
else
  not_ok "testing-infrastructure category passes with test-only ACs" "rc=$RC stdout=$STDOUT stderr=$STDERR"
fi

# --- Test 13: feature category rejects test-only AC ---
# Use testing-infra fixtures but override task.json with category "feature".
TMPDIR_T13="$(mktemp -d)"
cp "$FIXTURES/testing-infra/task-01-test-infra.md" "$TMPDIR_T13/"
cat > "$TMPDIR_T13/task.json" <<'JSONEOF'
{
  "category": "feature",
  "tasks": [
    "task-01-test-infra.md"
  ]
}
JSONEOF
STDOUT=$(bash "$GATE" "$FIXTURES/testing-infra/testing-infra-spec.md" "$TMPDIR_T13/" 2>/tmp/tr-stderr)
RC=$?
STDERR=$(cat /tmp/tr-stderr)
rm -rf "$TMPDIR_T13"
if [ $RC -eq 2 ] && echo "$STDERR" | grep -qi "AC-01\|implementation"; then
  ok "feature category rejects test-only AC coverage"
else
  not_ok "feature category rejects test-only AC coverage" "rc=$RC stderr=$STDERR"
fi

# --- Test 14: absent category defaults to feature behavior ---
# Use testing-infra fixtures but override task.json with category field removed.
TMPDIR_T14="$(mktemp -d)"
cp "$FIXTURES/testing-infra/task-01-test-infra.md" "$TMPDIR_T14/"
cat > "$TMPDIR_T14/task.json" <<'JSONEOF'
{
  "tasks": [
    "task-01-test-infra.md"
  ]
}
JSONEOF
STDOUT=$(bash "$GATE" "$FIXTURES/testing-infra/testing-infra-spec.md" "$TMPDIR_T14/" 2>/tmp/tr-stderr)
RC=$?
STDERR=$(cat /tmp/tr-stderr)
rm -rf "$TMPDIR_T14"
if [ $RC -eq 2 ] && echo "$STDERR" | grep -qi "AC-01\|implementation"; then
  ok "absent category defaults to feature behavior and rejects test-only AC"
else
  not_ok "absent category defaults to feature behavior and rejects test-only AC" "rc=$RC stderr=$STDERR"
fi

# --- Test 15: unrecognized category rejected with error listing valid categories ---
# Use corrective fixtures but override task.json with an unrecognized category.
TMPDIR_T15="$(mktemp -d)"
cp "$FIXTURES/corrective/task-01-test-fix.md" "$TMPDIR_T15/"
cp "$FIXTURES/corrective/task-02-impl-fix.md" "$TMPDIR_T15/"
cat > "$TMPDIR_T15/task.json" <<'JSONEOF'
{
  "category": "experimental",
  "tasks": [
    "task-01-test-fix.md",
    "task-02-impl-fix.md"
  ]
}
JSONEOF
STDOUT=$(bash "$GATE" "$FIXTURES/corrective/corrective-spec.md" "$TMPDIR_T15/" 2>/tmp/tr-stderr)
RC=$?
STDERR=$(cat /tmp/tr-stderr)
rm -rf "$TMPDIR_T15"
if [ $RC -eq 2 ] && echo "$STDERR" | grep -qi "experimental\|valid categor\|corrective\|testing-infrastructure"; then
  ok "unrecognized category rejected with error listing valid categories"
else
  not_ok "unrecognized category rejected with error listing valid categories" "rc=$RC stderr=$STDERR"
fi

# --- Summary ---
rm -f /tmp/tr-stderr
echo ""
echo "# $PASS/$TOTAL tests passed"
if [ "$FAIL" -gt 0 ]; then
  exit 1
fi
exit 0
