#!/usr/bin/env bash
set -uo pipefail

PASS=0
FAIL=0
TOTAL=0

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
PROJECT_ROOT="$(cd "$SCRIPT_DIR/../.." && pwd)"
IMPL_GUIDE="$PROJECT_ROOT/assets/fbk-docs/fbk-sdl-workflow/implementation-guide.md"
TASK_COMP="$PROJECT_ROOT/assets/fbk-docs/fbk-sdl-workflow/task-compilation.md"
TEST_AUTH="$PROJECT_ROOT/assets/fbk-docs/fbk-design-guidelines/test-authoring.md"

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

# --- Test 1: Implementation guide contains hook retry cap (AC-01) ---
if grep -qiE 'retry.*(cap|limit|3)|hook.*reject.*retry|3.*retries' "$IMPL_GUIDE"; then
  ok "Implementation guide contains hook retry cap"
else
  not_ok "Implementation guide contains hook retry cap" "file: $IMPL_GUIDE"
fi

# --- Test 2: Implementation guide contains fresh agent per task rule (AC-02) ---
if grep -qiE 'fresh.*agent|agent.*per.*task|do not reuse|no.*worker.*reuse|context.*pollution' "$IMPL_GUIDE"; then
  ok "Implementation guide contains fresh agent per task rule"
else
  not_ok "Implementation guide contains fresh agent per task rule" "file: $IMPL_GUIDE"
fi

# --- Test 3: Implementation guide contains foreground execution rule (AC-03) ---
if grep -qiE 'foreground|background.*empty' "$IMPL_GUIDE"; then
  ok "Implementation guide contains foreground execution rule"
else
  not_ok "Implementation guide contains foreground execution rule" "file: $IMPL_GUIDE"
fi

# --- Test 4: Task compilation contains E2E harness exception (AC-05) ---
if grep -qiE 'e2e.*harness|harness.*exception|combine.*(test|impl)' "$TASK_COMP"; then
  ok "Task compilation contains E2E harness exception"
else
  not_ok "Task compilation contains E2E harness exception" "file: $TASK_COMP"
fi

# --- Test 5: Task compilation contains per-site completion conditions (AC-06) ---
if grep -qiE 'per.site|mutation site|completion.*condition.*site' "$TASK_COMP"; then
  ok "Task compilation contains per-site completion conditions"
else
  not_ok "Task compilation contains per-site completion conditions" "file: $TASK_COMP"
fi

# --- Test 6: Test authoring contains assertion specificity rule (AC-07) ---
if grep -qiE 'assertion.*specific|specific.*value|truthi|specificity' "$TEST_AUTH"; then
  ok "Test authoring contains assertion specificity rule"
else
  not_ok "Test authoring contains assertion specificity rule" "file: $TEST_AUTH"
fi

# --- Test 7: Test authoring contains test name accuracy rule (AC-08) ---
if grep -qiE 'test.*name.*(accura|descri)|name.*(accura|match).*behavior' "$TEST_AUTH"; then
  ok "Test authoring contains test name accuracy rule"
else
  not_ok "Test authoring contains test name accuracy rule" "file: $TEST_AUTH"
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
