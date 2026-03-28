#!/usr/bin/env bash
set -uo pipefail

PASS=0
FAIL=0
TOTAL=0

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
PROJECT_ROOT="$(cd "$SCRIPT_DIR/../.." && pwd)"
INSTALL_SCRIPT="$PROJECT_ROOT/installer/install.sh"

TEMP_DIRS=()

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
  local MOCK_DIR
  MOCK_DIR=$(mktemp -d)
  TEMP_DIRS+=("$MOCK_DIR")

  mkdir -p "$MOCK_DIR/assets/skills/fbk-spec"
  mkdir -p "$MOCK_DIR/assets/agents"
  mkdir -p "$MOCK_DIR/assets/hooks/fbk-sdl-workflow"
  mkdir -p "$MOCK_DIR/assets/fbk-docs/fbk-sdl-workflow"

  echo "mock spec prompt" > "$MOCK_DIR/assets/skills/fbk-spec/prompt.md"
  echo "mock agent" > "$MOCK_DIR/assets/agents/fbk-code-review-detector.md"
  echo -e "#!/usr/bin/env bash\necho done" > "$MOCK_DIR/assets/hooks/fbk-sdl-workflow/task-completed.sh"
  echo "mock doc" > "$MOCK_DIR/assets/fbk-docs/fbk-sdl-workflow/guide.md"

  cat > "$MOCK_DIR/assets/settings.json" << 'EOF'
{
  "hooks": {
    "TaskCompleted": [
      {
        "hooks": [
          {
            "type": "command",
            "command": "\"$HOME\"/.claude/hooks/fbk-sdl-workflow/task-completed.sh"
          }
        ]
      }
    ]
  },
  "env": {
    "CLAUDE_CODE_EXPERIMENTAL_AGENT_TEAMS": "1"
  }
}
EOF

  echo "should not be installed" > "$MOCK_DIR/assets/CLAUDE.md"

  echo "$MOCK_DIR/assets"
}

cleanup() {
  for dir in "${TEMP_DIRS[@]}"; do
    [ -n "$dir" ] && [ -d "$dir" ] && rm -rf "$dir"
  done
}

trap cleanup EXIT

echo "TAP version 13"

# Setup
MOCK_SOURCE=$(setup_mock_source)
TARGET=$(mktemp -d)
TEMP_DIRS+=("$TARGET")

# Create pre-existing settings.json
cat > "$TARGET/settings.json" << 'EOF'
{
  "hooks": {
    "PreToolUse": [
      {
        "matcher": "Bash",
        "hooks": [{"type": "command", "command": "/usr/local/bin/user-guard.sh"}]
      }
    ]
  },
  "permissions": {
    "allow": ["Read"]
  },
  "env": {
    "USER_VAR": "keep-me"
  }
}
EOF

# Phase 1: Fresh install
bash "$INSTALL_SCRIPT" --target "$TARGET" --source "$MOCK_SOURCE" > /dev/null 2>&1
RC=$?

# Test 1: Post-install fbk files exist
if [ -f "$TARGET/skills/fbk-spec/prompt.md" ] && [ -f "$TARGET/agents/fbk-code-review-detector.md" ] && \
   [ -f "$TARGET/hooks/fbk-sdl-workflow/task-completed.sh" ] && [ -f "$TARGET/fbk-docs/fbk-sdl-workflow/guide.md" ]; then
  ok "post-install: fbk-prefixed files exist"
else
  not_ok "post-install: fbk-prefixed files exist" "not all fbk files found"
fi

# Test 2: Post-install CLAUDE.md not installed
if [ ! -f "$TARGET/CLAUDE.md" ]; then
  ok "post-install: CLAUDE.md not installed"
else
  not_ok "post-install: CLAUDE.md not installed" "CLAUDE.md exists"
fi

# Test 3: Post-install manifest exists
if [ -f "$TARGET/.firebreak-manifest.json" ] && python3 -c "import json; json.load(open('$TARGET/.firebreak-manifest.json'))" 2>/dev/null; then
  ok "post-install: manifest exists and is valid JSON"
else
  not_ok "post-install: manifest exists and is valid JSON" "manifest missing or invalid"
fi

# Test 4: Post-install hooks merged additively
PRETOOL_HAS_USER=$(python3 -c "import sys, json; data = json.load(open('$TARGET/settings.json')); hooks = data.get('hooks', {}).get('PreToolUse', []); print(any('user-guard.sh' in str(h) for h in hooks))" 2>/dev/null)
TASK_HAS_FBK=$(python3 -c "import sys, json; data = json.load(open('$TARGET/settings.json')); hooks = data.get('hooks', {}).get('TaskCompleted', []); print(any('fbk-sdl-workflow' in str(h) for h in hooks))" 2>/dev/null)
if [ "$PRETOOL_HAS_USER" = "True" ] && [ "$TASK_HAS_FBK" = "True" ]; then
  ok "post-install: hooks merged additively"
else
  not_ok "post-install: hooks merged additively" "user_hook=$PRETOOL_HAS_USER fbk_hook=$TASK_HAS_FBK"
fi

# Test 5: Post-install permissions untouched
PERMS=$(python3 -c "import sys, json; data = json.load(open('$TARGET/settings.json')); print(data.get('permissions', {}).get('allow', []) == ['Read'])" 2>/dev/null)
if [ "$PERMS" = "True" ]; then
  ok "post-install: permissions untouched"
else
  not_ok "post-install: permissions untouched" "permissions=$PERMS"
fi

# Test 6: Post-install env merged
USER_VAR=$(python3 -c "import sys, json; data = json.load(open('$TARGET/settings.json')); print(data.get('env', {}).get('USER_VAR', ''))" 2>/dev/null)
FBK_VAR=$(python3 -c "import sys, json; data = json.load(open('$TARGET/settings.json')); print(data.get('env', {}).get('CLAUDE_CODE_EXPERIMENTAL_AGENT_TEAMS', ''))" 2>/dev/null)
if [ "$USER_VAR" = "keep-me" ] && [ "$FBK_VAR" = "1" ]; then
  ok "post-install: env merged"
else
  not_ok "post-install: env merged" "user_var=$USER_VAR fbk_var=$FBK_VAR"
fi

# Test 7: Post-install backup created
if [ -f "$TARGET/settings.json.pre-firebreak" ]; then
  BACKUP_HAS_USER=$(python3 -c "import sys, json; data = json.load(open('$TARGET/settings.json.pre-firebreak')); hooks = data.get('hooks', {}).get('PreToolUse', []); print(any('user-guard.sh' in str(h) for h in hooks))" 2>/dev/null)
  BACKUP_NO_FBK=$(python3 -c "import sys, json; data = json.load(open('$TARGET/settings.json.pre-firebreak')); print('TaskCompleted' not in data.get('hooks', {}))" 2>/dev/null)
  if [ "$BACKUP_HAS_USER" = "True" ] && [ "$BACKUP_NO_FBK" = "True" ]; then
    ok "post-install: backup created with original content"
  else
    not_ok "post-install: backup created with original content" "backup_user=$BACKUP_HAS_USER backup_no_fbk=$BACKUP_NO_FBK"
  fi
else
  not_ok "post-install: backup created with original content" "backup file not found"
fi

# Phase 2: Upgrade
echo "updated spec prompt" > "$MOCK_SOURCE/skills/fbk-spec/prompt.md"
bash "$INSTALL_SCRIPT" --target "$TARGET" --source "$MOCK_SOURCE" > /dev/null 2>&1

# Test 8: Post-upgrade fbk file updated
PROMPT_CONTENT=$(cat "$TARGET/skills/fbk-spec/prompt.md" 2>/dev/null)
if [ "$PROMPT_CONTENT" = "updated spec prompt" ]; then
  ok "post-upgrade: fbk file updated to new version"
else
  not_ok "post-upgrade: fbk file updated to new version" "content=$PROMPT_CONTENT"
fi

# Test 9: Post-upgrade no duplicate hooks
TASK_COUNT=$(python3 -c "import sys, json; data = json.load(open('$TARGET/settings.json')); print(len(data.get('hooks', {}).get('TaskCompleted', [])))" 2>/dev/null)
if [ "$TASK_COUNT" = "1" ]; then
  ok "post-upgrade: no duplicate hooks"
else
  not_ok "post-upgrade: no duplicate hooks" "task_count=$TASK_COUNT"
fi

# Test 10: Post-upgrade user content preserved
USER_VAR=$(python3 -c "import sys, json; data = json.load(open('$TARGET/settings.json')); print(data.get('env', {}).get('USER_VAR', ''))" 2>/dev/null)
PRETOOL_HAS_USER=$(python3 -c "import sys, json; data = json.load(open('$TARGET/settings.json')); hooks = data.get('hooks', {}).get('PreToolUse', []); print(any('user-guard.sh' in str(h) for h in hooks))" 2>/dev/null)
PERMS=$(python3 -c "import sys, json; data = json.load(open('$TARGET/settings.json')); print(data.get('permissions', {}).get('allow', []) == ['Read'])" 2>/dev/null)
if [ "$USER_VAR" = "keep-me" ] && [ "$PRETOOL_HAS_USER" = "True" ] && [ "$PERMS" = "True" ]; then
  ok "post-upgrade: user content preserved"
else
  not_ok "post-upgrade: user content preserved" "user_var=$USER_VAR pretool=$PRETOOL_HAS_USER perms=$PERMS"
fi

# Phase 3: Uninstall
bash "$INSTALL_SCRIPT" --uninstall --target "$TARGET" > /dev/null 2>&1

# Test 11: Post-uninstall fbk files removed
if [ ! -f "$TARGET/skills/fbk-spec/prompt.md" ] && [ ! -f "$TARGET/agents/fbk-code-review-detector.md" ]; then
  ok "post-uninstall: fbk files removed"
else
  not_ok "post-uninstall: fbk files removed" "fbk files still exist"
fi

# Test 12: Post-uninstall manifest removed
if [ ! -f "$TARGET/.firebreak-manifest.json" ]; then
  ok "post-uninstall: manifest removed"
else
  not_ok "post-uninstall: manifest removed" "manifest still exists"
fi

# Test 13: Post-uninstall firebreak hooks removed, user hooks preserved
TASK_EMPTY=$(python3 -c "import sys, json; data = json.load(open('$TARGET/settings.json')); hooks = data.get('hooks', {}).get('TaskCompleted', []); print(len(hooks) == 0)" 2>/dev/null)
PRETOOL_HAS_USER=$(python3 -c "import sys, json; data = json.load(open('$TARGET/settings.json')); hooks = data.get('hooks', {}).get('PreToolUse', []); print(any('user-guard.sh' in str(h) for h in hooks))" 2>/dev/null)
if [ "$TASK_EMPTY" = "True" ] && [ "$PRETOOL_HAS_USER" = "True" ]; then
  ok "post-uninstall: firebreak hooks removed, user hooks preserved"
else
  not_ok "post-uninstall: firebreak hooks removed, user hooks preserved" "task_empty=$TASK_EMPTY pretool_user=$PRETOOL_HAS_USER"
fi

# Test 14: Post-uninstall firebreak env removed, user env preserved
NO_FBK_VAR=$(python3 -c "import sys, json; data = json.load(open('$TARGET/settings.json')); print('CLAUDE_CODE_EXPERIMENTAL_AGENT_TEAMS' not in data.get('env', {}))" 2>/dev/null)
USER_VAR=$(python3 -c "import sys, json; data = json.load(open('$TARGET/settings.json')); print(data.get('env', {}).get('USER_VAR', ''))" 2>/dev/null)
if [ "$NO_FBK_VAR" = "True" ] && [ "$USER_VAR" = "keep-me" ]; then
  ok "post-uninstall: firebreak env removed, user env preserved"
else
  not_ok "post-uninstall: firebreak env removed, user env preserved" "no_fbk=$NO_FBK_VAR user_var=$USER_VAR"
fi

# Test 15: Post-uninstall permissions untouched
PERMS=$(python3 -c "import sys, json; data = json.load(open('$TARGET/settings.json')); print(data.get('permissions', {}).get('allow', []) == ['Read'])" 2>/dev/null)
if [ "$PERMS" = "True" ]; then
  ok "post-uninstall: permissions still untouched"
else
  not_ok "post-uninstall: permissions still untouched" "perms=$PERMS"
fi

# Test 16: Post-uninstall backup retained
if [ -f "$TARGET/settings.json.pre-firebreak" ]; then
  ok "post-uninstall: backup retained"
else
  not_ok "post-uninstall: backup retained" "backup file missing"
fi

# Summary
echo ""
echo "# $PASS/$TOTAL tests passed"
echo "1..$TOTAL"

if [ "$FAIL" -gt 0 ]; then
  exit 1
fi
exit 0
