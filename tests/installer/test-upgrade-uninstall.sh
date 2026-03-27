#!/usr/bin/env bash
set -uo pipefail

PASS=0
FAIL=0
TOTAL=0

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
PROJECT_ROOT="$(cd "$SCRIPT_DIR/../.." && pwd)"
INSTALL_SCRIPT="$PROJECT_ROOT/installer/install.sh"

TMPDIRS=()

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

setup_mock_source() {
  local src
  src=$(mktemp -d)
  TMPDIRS+=("$src")
  mkdir -p "$src/home/dot-claude/skills/fbk-spec"
  mkdir -p "$src/home/dot-claude/agents"
  mkdir -p "$src/home/dot-claude/hooks/fbk-sdl-workflow"
  mkdir -p "$src/home/dot-claude/docs/fbk-sdl-workflow"
  echo "mock spec prompt" > "$src/home/dot-claude/skills/fbk-spec/prompt.md"
  echo "mock agent" > "$src/home/dot-claude/agents/fbk-code-review-detector.md"
  printf '#!/usr/bin/env bash\necho done' > "$src/home/dot-claude/hooks/fbk-sdl-workflow/task-completed.sh"
  echo "mock doc" > "$src/home/dot-claude/docs/fbk-sdl-workflow/guide.md"
  echo '{"hooks":{"TaskCompleted":[{"hooks":[{"type":"command","command":"\"$HOME\"/.claude/hooks/fbk-sdl-workflow/task-completed.sh"}]}]},"env":{"CLAUDE_CODE_EXPERIMENTAL_AGENT_TEAMS":"1"}}' \
    > "$src/home/dot-claude/settings.json"
  echo "should not be installed" > "$src/home/dot-claude/CLAUDE.md"
  echo "$src/home/dot-claude"
}

setup_target() {
  local tgt
  tgt=$(mktemp -d)
  TMPDIRS+=("$tgt")
  echo "$tgt"
}

cleanup() {
  for d in "${TMPDIRS[@]:-}"; do
    [ -n "$d" ] && [ -d "$d" ] && rm -rf "$d"
  done
}

trap cleanup EXIT

echo "TAP version 13"

# --- Test 1: upgrade overwrites fbk files ---
MOCK_SOURCE=$(setup_mock_source)
TARGET=$(setup_target)
bash "$INSTALL_SCRIPT" --target "$TARGET" --source "$MOCK_SOURCE" 2>/dev/null
echo "user modified this" > "$TARGET/skills/fbk-spec/prompt.md"
bash "$INSTALL_SCRIPT" --target "$TARGET" --source "$MOCK_SOURCE" 2>/dev/null
RC=$?
CONTENT=$(cat "$TARGET/skills/fbk-spec/prompt.md" 2>/dev/null || true)
if [ $RC -eq 0 ] && [ "$CONTENT" = "mock spec prompt" ]; then
  ok "upgrade overwrites fbk-prefixed files with source version"
else
  not_ok "upgrade overwrites fbk-prefixed files with source version" "rc=$RC content=$CONTENT"
fi

# --- Test 2: upgrade updates manifest timestamp ---
MOCK_SOURCE=$(setup_mock_source)
TARGET=$(setup_target)
bash "$INSTALL_SCRIPT" --target "$TARGET" --source "$MOCK_SOURCE" 2>/dev/null
ORIG_TS=$(python3 -c "import json; d=json.load(open('$TARGET/.firebreak-manifest.json')); print(d.get('updated_at', d.get('installed_at','')))" 2>/dev/null || true)
sleep 1
bash "$INSTALL_SCRIPT" --target "$TARGET" --source "$MOCK_SOURCE" 2>/dev/null
NEW_TS=$(python3 -c "import json; d=json.load(open('$TARGET/.firebreak-manifest.json')); print(d.get('updated_at', d.get('installed_at','')))" 2>/dev/null || true)
if [ -n "$ORIG_TS" ] && [ -n "$NEW_TS" ] && [ "$ORIG_TS" != "$NEW_TS" ]; then
  ok "upgrade updates manifest timestamp"
else
  not_ok "upgrade updates manifest timestamp" "orig_ts=$ORIG_TS new_ts=$NEW_TS"
fi

# --- Test 3: upgrade does not duplicate hooks ---
MOCK_SOURCE=$(setup_mock_source)
TARGET=$(setup_target)
bash "$INSTALL_SCRIPT" --target "$TARGET" --source "$MOCK_SOURCE" 2>/dev/null
bash "$INSTALL_SCRIPT" --target "$TARGET" --source "$MOCK_SOURCE" 2>/dev/null
HOOK_COUNT=$(python3 -c "import json; d=json.load(open('$TARGET/settings.json')); print(len(d.get('hooks',{}).get('TaskCompleted',[])))" 2>/dev/null || true)
if [ "$HOOK_COUNT" = "1" ]; then
  ok "upgrade does not duplicate hooks in settings.json"
else
  not_ok "upgrade does not duplicate hooks in settings.json" "hook_count=$HOOK_COUNT"
fi

# --- Test 4: upgrade preserves non-fbk files ---
MOCK_SOURCE=$(setup_mock_source)
TARGET=$(setup_target)
mkdir -p "$TARGET/agents"
echo "user agent" > "$TARGET/agents/my-agent.md"
bash "$INSTALL_SCRIPT" --target "$TARGET" --source "$MOCK_SOURCE" 2>/dev/null
bash "$INSTALL_SCRIPT" --target "$TARGET" --source "$MOCK_SOURCE" 2>/dev/null
CONTENT=$(cat "$TARGET/agents/my-agent.md" 2>/dev/null || true)
if [ "$CONTENT" = "user agent" ]; then
  ok "upgrade preserves non-fbk files"
else
  not_ok "upgrade preserves non-fbk files" "content=$CONTENT"
fi

# --- Test 5: uninstall removes fbk files ---
MOCK_SOURCE=$(setup_mock_source)
TARGET=$(setup_target)
bash "$INSTALL_SCRIPT" --target "$TARGET" --source "$MOCK_SOURCE" 2>/dev/null
bash "$INSTALL_SCRIPT" --uninstall --target "$TARGET" 2>/dev/null
RC=$?
if [ $RC -eq 0 ] \
  && [ ! -f "$TARGET/skills/fbk-spec/prompt.md" ] \
  && [ ! -f "$TARGET/agents/fbk-code-review-detector.md" ] \
  && [ ! -f "$TARGET/hooks/fbk-sdl-workflow/task-completed.sh" ]; then
  ok "uninstall removes fbk-prefixed files"
else
  not_ok "uninstall removes fbk-prefixed files" "rc=$RC skill=$([ -f "$TARGET/skills/fbk-spec/prompt.md" ] && echo exists || echo gone) agent=$([ -f "$TARGET/agents/fbk-code-review-detector.md" ] && echo exists || echo gone)"
fi

# --- Test 6: uninstall removes hooks from settings.json ---
MOCK_SOURCE=$(setup_mock_source)
TARGET=$(setup_target)
bash "$INSTALL_SCRIPT" --target "$TARGET" --source "$MOCK_SOURCE" 2>/dev/null
bash "$INSTALL_SCRIPT" --uninstall --target "$TARGET" 2>/dev/null
HOOK_COUNT=$(python3 -c "import json; d=json.load(open('$TARGET/settings.json')); print(len(d.get('hooks',{}).get('TaskCompleted',[])))" 2>/dev/null || echo "0")
if [ "$HOOK_COUNT" = "0" ]; then
  ok "uninstall removes firebreak hooks from settings.json"
else
  not_ok "uninstall removes firebreak hooks from settings.json" "hook_count=$HOOK_COUNT"
fi

# --- Test 7: uninstall removes env keys when value matches ---
MOCK_SOURCE=$(setup_mock_source)
TARGET=$(setup_target)
bash "$INSTALL_SCRIPT" --target "$TARGET" --source "$MOCK_SOURCE" 2>/dev/null
bash "$INSTALL_SCRIPT" --uninstall --target "$TARGET" 2>/dev/null
ENV_VALUE=$(python3 -c "import json; d=json.load(open('$TARGET/settings.json')); print(d.get('env',{}).get('CLAUDE_CODE_EXPERIMENTAL_AGENT_TEAMS','NOT_PRESENT'))" 2>/dev/null || echo "NOT_PRESENT")
if [ "$ENV_VALUE" = "NOT_PRESENT" ]; then
  ok "uninstall removes env keys when value matches installed value"
else
  not_ok "uninstall removes env keys when value matches installed value" "env_value=$ENV_VALUE"
fi

# --- Test 8: uninstall preserves env keys when user changed value ---
MOCK_SOURCE=$(setup_mock_source)
TARGET=$(setup_target)
bash "$INSTALL_SCRIPT" --target "$TARGET" --source "$MOCK_SOURCE" 2>/dev/null
python3 -c "
import json
path = '$TARGET/settings.json'
d = json.load(open(path))
d.setdefault('env', {})['CLAUDE_CODE_EXPERIMENTAL_AGENT_TEAMS'] = 'custom-value'
json.dump(d, open(path, 'w'), indent=2)
" 2>/dev/null
bash "$INSTALL_SCRIPT" --uninstall --target "$TARGET" 2>/dev/null
ENV_VALUE=$(python3 -c "import json; d=json.load(open('$TARGET/settings.json')); print(d.get('env',{}).get('CLAUDE_CODE_EXPERIMENTAL_AGENT_TEAMS','NOT_PRESENT'))" 2>/dev/null || true)
if [ "$ENV_VALUE" = "custom-value" ]; then
  ok "uninstall preserves env keys when user changed the value"
else
  not_ok "uninstall preserves env keys when user changed the value" "env_value=$ENV_VALUE"
fi

# --- Test 9: uninstall removes manifest ---
MOCK_SOURCE=$(setup_mock_source)
TARGET=$(setup_target)
bash "$INSTALL_SCRIPT" --target "$TARGET" --source "$MOCK_SOURCE" 2>/dev/null
bash "$INSTALL_SCRIPT" --uninstall --target "$TARGET" 2>/dev/null
if [ ! -f "$TARGET/.firebreak-manifest.json" ]; then
  ok "uninstall removes the manifest file"
else
  not_ok "uninstall removes the manifest file" "manifest still exists"
fi

# --- Test 10: uninstall removes empty fbk directories ---
MOCK_SOURCE=$(setup_mock_source)
TARGET=$(setup_target)
bash "$INSTALL_SCRIPT" --target "$TARGET" --source "$MOCK_SOURCE" 2>/dev/null
bash "$INSTALL_SCRIPT" --uninstall --target "$TARGET" 2>/dev/null
if [ ! -d "$TARGET/hooks/fbk-sdl-workflow" ] && [ ! -d "$TARGET/skills/fbk-spec" ]; then
  ok "uninstall removes empty fbk-prefixed directories"
else
  not_ok "uninstall removes empty fbk-prefixed directories" "hooks_dir=$([ -d "$TARGET/hooks/fbk-sdl-workflow" ] && echo exists || echo gone) skills_dir=$([ -d "$TARGET/skills/fbk-spec" ] && echo exists || echo gone)"
fi

# --- Test 11: uninstall retains pre-firebreak backup ---
MOCK_SOURCE=$(setup_mock_source)
TARGET=$(setup_target)
echo '{"existing":"config"}' > "$TARGET/settings.json"
bash "$INSTALL_SCRIPT" --target "$TARGET" --source "$MOCK_SOURCE" 2>/dev/null
bash "$INSTALL_SCRIPT" --uninstall --target "$TARGET" 2>/dev/null
if [ -f "$TARGET/settings.json.pre-firebreak" ]; then
  ok "uninstall retains .pre-firebreak backup"
else
  not_ok "uninstall retains .pre-firebreak backup" "backup not found"
fi

# --- Test 12: uninstall with no manifest exits with error ---
TARGET=$(setup_target)
STDERR_OUT=$(bash "$INSTALL_SCRIPT" --uninstall --target "$TARGET" 2>&1 >/dev/null)
RC=$?
if [ $RC -ne 0 ] && echo "$STDERR_OUT" | grep -qiE "no firebreak|not found|no installation|manifest"; then
  ok "uninstall with no manifest exits with error"
else
  not_ok "uninstall with no manifest exits with error" "rc=$RC stderr=$STDERR_OUT"
fi

# --- Test 13: malformed settings.json on install exits with error, no changes made ---
MOCK_SOURCE=$(setup_mock_source)
TARGET=$(setup_target)
echo '{this is not valid json' > "$TARGET/settings.json"
STDERR_OUT=$(bash "$INSTALL_SCRIPT" --target "$TARGET" --source "$MOCK_SOURCE" 2>&1 >/dev/null)
RC=$?
FBK_FILES=$(find "$TARGET" -name 'fbk-*' 2>/dev/null | wc -l)
SETTINGS_CONTENT=$(cat "$TARGET/settings.json" 2>/dev/null)
BACKUP_EXISTS=$([ -f "$TARGET/settings.json.pre-firebreak" ] && echo "yes" || echo "no")
if [ $RC -ne 0 ] && echo "$STDERR_OUT" | grep -qiE "malformed|invalid|json|parse" && [ "$FBK_FILES" -eq 0 ] && \
   [ "$SETTINGS_CONTENT" = '{this is not valid json' ] && [ "$BACKUP_EXISTS" = "no" ]; then
  ok "malformed settings.json on install exits with error and makes no changes"
else
  not_ok "malformed settings.json on install exits with error and makes no changes" "rc=$RC fbk_files=$FBK_FILES settings_unchanged=$([ "$SETTINGS_CONTENT" = '{this is not valid json' ] && echo yes || echo no) backup=$BACKUP_EXISTS"
fi

# --- Summary ---
echo ""
echo "# $PASS/$TOTAL tests passed"
echo "1..$TOTAL"

if [ "$FAIL" -gt 0 ]; then
  exit 1
fi
exit 0
