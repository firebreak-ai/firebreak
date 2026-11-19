#!/usr/bin/env bash
set -uo pipefail

PASS=0
FAIL=0
TOTAL=0

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
PROJECT_ROOT="$(cd "$SCRIPT_DIR/../.." && pwd)"
MERGE_SCRIPT="$PROJECT_ROOT/installer/merge-settings.py"
FIXTURES="$PROJECT_ROOT/tests/fixtures/installer"

ok() {
  TOTAL=$((TOTAL + 1))
  PASS=$((PASS + 1))
  echo "ok $TOTAL - $1"
}

not_ok() {
  TOTAL=$((TOTAL + 1))
  FAIL=$((FAIL + 1))
  echo "not ok $TOTAL - $1"
  fbk_diag "$1" "${3:-$1}" "${2:-assertion did not hold}"
}

source "$SCRIPT_DIR/../lib/test-report.sh" || exit 2
fbk_test_init "$0" || exit 2

setup_error() {
  fbk_diag "setup error: $1"
  exit 2
}

for tool in python3; do
  command -v "$tool" >/dev/null 2>&1 || setup_error "required tool unavailable: $tool"
done
for required in "$MERGE_SCRIPT" "$FIXTURES/firebreak-settings.json" "$FIXTURES/settings-existing-hooks.json" "$FIXTURES/settings-with-permissions.json"; do
  [ -r "$required" ] || setup_error "required file unreadable: $required"
done

make_tmpdir() {
  local d
  d=$(mktemp -d) || setup_error "cannot allocate fixture"

  echo "$d"
}

settings_block() {
  echo "$1" | awk '/^---MANIFEST---$/{exit} {print}'
}

echo "TAP version 13"

# Test 2: Append hooks preserves existing entries
TEST_TMPDIR=$(make_tmpdir) || setup_error "cannot allocate fixture"
cp "$FIXTURES/settings-existing-hooks.json" "$TEST_TMPDIR/settings.json" || setup_error "cannot prepare fixture"
OUTPUT=$(fbk_run "settings inspection before assessment $((TOTAL + 1))" python3 "$MERGE_SCRIPT" "$TEST_TMPDIR/settings.json" "$FIXTURES/firebreak-settings.json" 2>/dev/null)
RC=$?
PRETOOL_COUNT=$(settings_block "$OUTPUT" | fbk_run "settings inspection before assessment $((TOTAL + 1))" python3 -c "import sys, json; data = json.load(sys.stdin); print(len(data.get('hooks', {}).get('PreToolUse', [])))" 2>/dev/null)
PRETOOL_COMMAND=$(settings_block "$OUTPUT" | fbk_run "settings inspection before assessment $((TOTAL + 1))" python3 -c "import sys, json; data = json.load(sys.stdin); cmd = data.get('hooks', {}).get('PreToolUse', [{}])[0].get('hooks', [{}])[0].get('command', ''); print('my-bash-guard.sh' in cmd)" 2>/dev/null)
TASK_COMPLETED_COUNT=$(settings_block "$OUTPUT" | fbk_run "settings inspection before assessment $((TOTAL + 1))" python3 -c "import sys, json; data = json.load(sys.stdin); print(len(data.get('hooks', {}).get('TaskCompleted', [])))" 2>/dev/null)
if [ "$PRETOOL_COUNT" = "1" ] && [ "$PRETOOL_COMMAND" = "True" ] && [ "$TASK_COMPLETED_COUNT" = "1" ]; then
  ok "append hooks preserves existing hook entries and adds firebreak entries"
else
  not_ok "append hooks preserves existing hook entries and adds firebreak entries" "pretool_count=$PRETOOL_COUNT pretool_command=$PRETOOL_COMMAND task_completed_count=$TASK_COMPLETED_COUNT output=$OUTPUT" "pretool_count=1 pretool_command=True task_completed_count=1"
fi

# Test 5: Permissions object is not modified by the merge
TEST_TMPDIR=$(make_tmpdir) || setup_error "cannot allocate fixture"
cp "$FIXTURES/settings-with-permissions.json" "$TEST_TMPDIR/settings.json" || setup_error "cannot prepare fixture"
OUTPUT=$(fbk_run "settings inspection before assessment $((TOTAL + 1))" python3 "$MERGE_SCRIPT" "$TEST_TMPDIR/settings.json" "$FIXTURES/firebreak-settings.json" 2>/dev/null)
RC=$?
ALLOW_MATCH=$(settings_block "$OUTPUT" | fbk_run "settings inspection before assessment $((TOTAL + 1))" python3 -c "import sys, json; data = json.load(sys.stdin); allow = data.get('permissions', {}).get('allow', []); print(allow == ['Read', 'Glob'])" 2>/dev/null)
DENY_MATCH=$(settings_block "$OUTPUT" | fbk_run "settings inspection before assessment $((TOTAL + 1))" python3 -c "import sys, json; data = json.load(sys.stdin); deny = data.get('permissions', {}).get('deny', []); print(deny == ['Bash'])" 2>/dev/null)
if [ "$ALLOW_MATCH" = "True" ] && [ "$DENY_MATCH" = "True" ]; then
  ok "permissions object is not modified by the merge"
else
  not_ok "permissions object is not modified by the merge" "allow_match=$ALLOW_MATCH deny_match=$DENY_MATCH output=$OUTPUT" "allow_match=True deny_match=True"
fi

# Summary
echo ""
echo "# $PASS/$TOTAL tests passed"
echo "1..$TOTAL"

if [ "$FAIL" -gt 0 ]; then
  exit 1
fi
exit 0
