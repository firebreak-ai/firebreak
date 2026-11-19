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
for required in "$MERGE_SCRIPT" "$FIXTURES/firebreak-settings.json" "$FIXTURES/settings-empty.json" "$FIXTURES/settings-existing-env.json" "$FIXTURES/settings-malformed.json"; do
  [ -r "$required" ] || setup_error "required file unreadable: $required"
done
TEST_TMPDIR=$(mktemp -d) || setup_error "cannot allocate settings fixture" || setup_error "cannot allocate fixture"

echo "TAP version 13"

# Helper: extract the settings block (before ---MANIFEST---) from merge output
settings_block() {
  echo "$1" | awk '/^---MANIFEST---$/{exit} {print}'
}

# Helper: extract the manifest block (after ---MANIFEST---) from merge output
manifest_block() {
  echo "$1" | awk 'found{print} /^---MANIFEST---$/{found=1}'
}

# --- Test 1: add env to empty settings creates env object with firebreak entries ---
cp "$FIXTURES/settings-empty.json" "$TEST_TMPDIR/settings-empty.json" || setup_error "cannot prepare fixture"
STDOUT=$(fbk_run "settings inspection before assessment $((TOTAL + 1))" python3 "$MERGE_SCRIPT" "$TEST_TMPDIR/settings-empty.json" "$FIXTURES/firebreak-settings.json" 2>/dev/null)
RC=$?
VALUE=$(settings_block "$STDOUT" | fbk_run "settings inspection before assessment $((TOTAL + 1))" python3 -c "import sys,json; d=json.load(sys.stdin); print(d.get('env',{}).get('CLAUDE_CODE_EXPERIMENTAL_AGENT_TEAMS',''))" 2>/dev/null || true)
if [ "$VALUE" = "1" ]; then
  ok "add env to empty settings: CLAUDE_CODE_EXPERIMENTAL_AGENT_TEAMS equals 1"
else
  not_ok "add env to empty settings: CLAUDE_CODE_EXPERIMENTAL_AGENT_TEAMS equals 1" "rc=$RC value=$VALUE stdout=$STDOUT" "value=1"
fi

# --- Test 2: existing env key with same name is not overwritten ---
cp "$FIXTURES/settings-existing-env.json" "$TEST_TMPDIR/settings-existing-env.json" || setup_error "cannot prepare fixture"
STDOUT=$(fbk_run "settings inspection before assessment $((TOTAL + 1))" python3 "$MERGE_SCRIPT" "$TEST_TMPDIR/settings-existing-env.json" "$FIXTURES/firebreak-settings.json" 2>/dev/null)
RC=$?
FB_VALUE=$(settings_block "$STDOUT" | fbk_run "settings inspection before assessment $((TOTAL + 1))" python3 -c "import sys,json; d=json.load(sys.stdin); print(d.get('env',{}).get('CLAUDE_CODE_EXPERIMENTAL_AGENT_TEAMS',''))" 2>/dev/null || true)
MY_VALUE=$(settings_block "$STDOUT" | fbk_run "settings inspection before assessment $((TOTAL + 1))" python3 -c "import sys,json; d=json.load(sys.stdin); print(d.get('env',{}).get('MY_CUSTOM_VAR',''))" 2>/dev/null || true)
if [ "$FB_VALUE" = "0" ] && [ "$MY_VALUE" = "my-value" ]; then
  ok "existing env keys not overwritten: CLAUDE_CODE_EXPERIMENTAL_AGENT_TEAMS stays 0, MY_CUSTOM_VAR preserved"
else
  not_ok "existing env keys not overwritten: CLAUDE_CODE_EXPERIMENTAL_AGENT_TEAMS stays 0, MY_CUSTOM_VAR preserved" "rc=$RC fb_value=$FB_VALUE my_value=$MY_VALUE" "fb_value=0 my_value=my-value"
fi

# --- Test 3: actually-added tracking records new keys ---
cp "$FIXTURES/settings-empty.json" "$TEST_TMPDIR/settings-empty2.json" || setup_error "cannot prepare fixture"
STDOUT=$(fbk_run "settings inspection before assessment $((TOTAL + 1))" python3 "$MERGE_SCRIPT" "$TEST_TMPDIR/settings-empty2.json" "$FIXTURES/firebreak-settings.json" 2>/dev/null)
RC=$?
ADDED_VALUE=$(manifest_block "$STDOUT" | fbk_run "settings inspection before assessment $((TOTAL + 1))" python3 -c "import sys,json; d=json.load(sys.stdin); print(d.get('env_added',{}).get('CLAUDE_CODE_EXPERIMENTAL_AGENT_TEAMS',''))" 2>/dev/null || true)
if [ "$ADDED_VALUE" = "1" ]; then
  ok "actually-added tracking records new key CLAUDE_CODE_EXPERIMENTAL_AGENT_TEAMS"
else
  not_ok "actually-added tracking records new key CLAUDE_CODE_EXPERIMENTAL_AGENT_TEAMS" "rc=$RC added_value=$ADDED_VALUE stdout=$STDOUT" "added_value=1"
fi

# --- Test 4: actually-added tracking omits pre-existing keys ---
cp "$FIXTURES/settings-existing-env.json" "$TEST_TMPDIR/settings-existing-env2.json" || setup_error "cannot prepare fixture"
STDOUT=$(fbk_run "settings inspection before assessment $((TOTAL + 1))" python3 "$MERGE_SCRIPT" "$TEST_TMPDIR/settings-existing-env2.json" "$FIXTURES/firebreak-settings.json" 2>/dev/null)
RC=$?
ADDED_VALUE=$(manifest_block "$STDOUT" | fbk_run "settings inspection before assessment $((TOTAL + 1))" python3 -c "import sys,json; d=json.load(sys.stdin); print(d.get('env_added',{}).get('CLAUDE_CODE_EXPERIMENTAL_AGENT_TEAMS','NOT_PRESENT'))" 2>/dev/null || true)
if [ "$ADDED_VALUE" = "NOT_PRESENT" ]; then
  ok "actually-added tracking omits pre-existing key CLAUDE_CODE_EXPERIMENTAL_AGENT_TEAMS"
else
  not_ok "actually-added tracking omits pre-existing key CLAUDE_CODE_EXPERIMENTAL_AGENT_TEAMS" "rc=$RC added_value=$ADDED_VALUE stdout=$STDOUT" "added_value=NOT_PRESENT"
fi

# --- Test 5: malformed JSON input exits non-zero with error message and no stdout ---
cp "$FIXTURES/settings-malformed.json" "$TEST_TMPDIR/settings-malformed.json" || setup_error "cannot prepare fixture"
MERGE_STDERR_FILE="$(mktemp)"
STDOUT=$(fbk_run "settings inspection before assessment $((TOTAL + 1))" python3 "$MERGE_SCRIPT" "$TEST_TMPDIR/settings-malformed.json" "$FIXTURES/firebreak-settings.json" 2>"$MERGE_STDERR_FILE")
RC=$?
STDERR=$(cat "$MERGE_STDERR_FILE")
rm -f "$MERGE_STDERR_FILE"
if [ $RC -ne 0 ] && echo "$STDERR" | grep -qiE "malformed|json|parse" && [ -z "$STDOUT" ]; then
  ok "malformed JSON input exits non-zero with error message and no stdout"
else
  not_ok "malformed JSON input exits non-zero with error message and no stdout" "rc=$RC stdout=$STDOUT stderr=$STDERR" "rc != 0; empty stdout; stderr matches malformed|json|parse"
fi

# --- Test 6: missing settings.json creates env with firebreak entries ---
STDOUT=$(fbk_run "settings inspection before assessment $((TOTAL + 1))" python3 "$MERGE_SCRIPT" "$TEST_TMPDIR/nonexistent-settings.json" "$FIXTURES/firebreak-settings.json" 2>/dev/null)
RC=$?
VALUE=$(settings_block "$STDOUT" | fbk_run "settings inspection before assessment $((TOTAL + 1))" python3 -c "import sys,json; d=json.load(sys.stdin); print(d.get('env',{}).get('CLAUDE_CODE_EXPERIMENTAL_AGENT_TEAMS',''))" 2>/dev/null || true)
if [ "$VALUE" = "1" ]; then
  ok "missing settings.json creates env with firebreak entries"
else
  not_ok "missing settings.json creates env with firebreak entries" "rc=$RC value=$VALUE stdout=$STDOUT" "value=1"
fi

# --- Summary ---
echo ""
echo "# $PASS/$TOTAL tests passed"
echo "1..$TOTAL"
if [ "$FAIL" -gt 0 ]; then
  exit 1
fi
exit 0
