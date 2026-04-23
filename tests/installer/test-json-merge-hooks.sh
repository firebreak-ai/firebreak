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
  [ -n "${2:-}" ] && echo "# $2"
}

TEMP_DIRS=()

cleanup() {
  for dir in "${TEMP_DIRS[@]}"; do
    [ -n "$dir" ] && [ -d "$dir" ] && rm -rf "$dir"
  done
}

trap cleanup EXIT

make_tmpdir() {
  local d
  d=$(mktemp -d)
  TEMP_DIRS+=("$d")
  echo "$d"
}

settings_block() {
  echo "$1" | awk '/^---MANIFEST---$/{exit} {print}'
}

echo "TAP version 13"

# Test 1: Merge hooks into empty settings
TEST_TMPDIR=$(make_tmpdir)
cp "$FIXTURES/settings-empty.json" "$TEST_TMPDIR/settings.json"
OUTPUT=$(python3 "$MERGE_SCRIPT" "$TEST_TMPDIR/settings.json" "$FIXTURES/firebreak-settings.json" 2>/dev/null)
RC=$?
TASK_COMPLETED_COUNT=$(settings_block "$OUTPUT" | python3 -c "import sys, json; data = json.load(sys.stdin); print(len(data.get('hooks', {}).get('TaskCompleted', [])))" 2>/dev/null)
COMMAND_MATCH=$(settings_block "$OUTPUT" | python3 -c "import sys, json; data = json.load(sys.stdin); cmd = data.get('hooks', {}).get('TaskCompleted', [{}])[0].get('hooks', [{}])[0].get('command', ''); print('fbk-scripts/fbk.py task-completed' in cmd)" 2>/dev/null)
if [ "$TASK_COMPLETED_COUNT" = "1" ] && [ "$COMMAND_MATCH" = "True" ]; then
  ok "merge hooks into empty settings produces correct hooks structure"
else
  not_ok "merge hooks into empty settings produces correct hooks structure" "task_completed_count=$TASK_COMPLETED_COUNT command_match=$COMMAND_MATCH output=$OUTPUT"
fi

# Test 2: Append hooks preserves existing entries
TEST_TMPDIR=$(make_tmpdir)
cp "$FIXTURES/settings-existing-hooks.json" "$TEST_TMPDIR/settings.json"
OUTPUT=$(python3 "$MERGE_SCRIPT" "$TEST_TMPDIR/settings.json" "$FIXTURES/firebreak-settings.json" 2>/dev/null)
RC=$?
PRETOOL_COUNT=$(settings_block "$OUTPUT" | python3 -c "import sys, json; data = json.load(sys.stdin); print(len(data.get('hooks', {}).get('PreToolUse', [])))" 2>/dev/null)
PRETOOL_COMMAND=$(settings_block "$OUTPUT" | python3 -c "import sys, json; data = json.load(sys.stdin); cmd = data.get('hooks', {}).get('PreToolUse', [{}])[0].get('hooks', [{}])[0].get('command', ''); print('my-bash-guard.sh' in cmd)" 2>/dev/null)
TASK_COMPLETED_COUNT=$(settings_block "$OUTPUT" | python3 -c "import sys, json; data = json.load(sys.stdin); print(len(data.get('hooks', {}).get('TaskCompleted', [])))" 2>/dev/null)
if [ "$PRETOOL_COUNT" = "1" ] && [ "$PRETOOL_COMMAND" = "True" ] && [ "$TASK_COMPLETED_COUNT" = "1" ]; then
  ok "append hooks preserves existing hook entries and adds firebreak entries"
else
  not_ok "append hooks preserves existing hook entries and adds firebreak entries" "pretool_count=$PRETOOL_COUNT pretool_command=$PRETOOL_COMMAND task_completed_count=$TASK_COMPLETED_COUNT output=$OUTPUT"
fi

# Test 3: Re-merging identical matcher groups does not create duplicates
TEST_TMPDIR=$(make_tmpdir)
cp "$FIXTURES/settings-empty.json" "$TEST_TMPDIR/settings.json"
FIRST_OUTPUT=$(python3 "$MERGE_SCRIPT" "$TEST_TMPDIR/settings.json" "$FIXTURES/firebreak-settings.json" 2>/dev/null)
settings_block "$FIRST_OUTPUT" > "$TEST_TMPDIR/settings.json"
SECOND_OUTPUT=$(python3 "$MERGE_SCRIPT" "$TEST_TMPDIR/settings.json" "$FIXTURES/firebreak-settings.json" 2>/dev/null)
TASK_COMPLETED_COUNT=$(settings_block "$SECOND_OUTPUT" | python3 -c "import sys, json; data = json.load(sys.stdin); print(len(data.get('hooks', {}).get('TaskCompleted', [])))" 2>/dev/null)
if [ "$TASK_COMPLETED_COUNT" = "1" ]; then
  ok "re-merging identical matcher groups does not create duplicates"
else
  not_ok "re-merging identical matcher groups does not create duplicates" "task_completed_count=$TASK_COMPLETED_COUNT second_output=$SECOND_OUTPUT"
fi

# Test 4: Different matchers with same command are preserved as separate entries
TEST_TMPDIR=$(make_tmpdir)
cat > "$TEST_TMPDIR/settings.json" << 'EOF'
{
  "hooks": {
    "TaskCompleted": [
      {
        "matcher": "Read",
        "hooks": [
          {
            "type": "command",
            "command": "python3 \"$HOME\"/.claude/fbk-scripts/fbk.py task-completed"
          }
        ]
      }
    ]
  }
}
EOF
OUTPUT=$(python3 "$MERGE_SCRIPT" "$TEST_TMPDIR/settings.json" "$FIXTURES/firebreak-settings.json" 2>/dev/null)
RC=$?
TASK_COMPLETED_COUNT=$(settings_block "$OUTPUT" | python3 -c "import sys, json; data = json.load(sys.stdin); print(len(data.get('hooks', {}).get('TaskCompleted', [])))" 2>/dev/null)
if [ "$TASK_COMPLETED_COUNT" = "2" ]; then
  ok "different matchers with same command are preserved as separate entries"
else
  not_ok "different matchers with same command are preserved as separate entries" "task_completed_count=$TASK_COMPLETED_COUNT output=$OUTPUT"
fi

# Test 5: Permissions object is not modified by the merge
TEST_TMPDIR=$(make_tmpdir)
cp "$FIXTURES/settings-with-permissions.json" "$TEST_TMPDIR/settings.json"
OUTPUT=$(python3 "$MERGE_SCRIPT" "$TEST_TMPDIR/settings.json" "$FIXTURES/firebreak-settings.json" 2>/dev/null)
RC=$?
ALLOW_MATCH=$(settings_block "$OUTPUT" | python3 -c "import sys, json; data = json.load(sys.stdin); allow = data.get('permissions', {}).get('allow', []); print(allow == ['Read', 'Glob'])" 2>/dev/null)
DENY_MATCH=$(settings_block "$OUTPUT" | python3 -c "import sys, json; data = json.load(sys.stdin); deny = data.get('permissions', {}).get('deny', []); print(deny == ['Bash'])" 2>/dev/null)
if [ "$ALLOW_MATCH" = "True" ] && [ "$DENY_MATCH" = "True" ]; then
  ok "permissions object is not modified by the merge"
else
  not_ok "permissions object is not modified by the merge" "allow_match=$ALLOW_MATCH deny_match=$DENY_MATCH output=$OUTPUT"
fi

# Summary
echo ""
echo "# $PASS/$TOTAL tests passed"
echo "1..$TOTAL"

if [ "$FAIL" -gt 0 ]; then
  exit 1
fi
exit 0
