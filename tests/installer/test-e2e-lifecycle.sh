#!/usr/bin/env bash
set -uo pipefail

PASS=0
FAIL=0
TOTAL=0

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
PROJECT_ROOT="$(cd "$SCRIPT_DIR/../.." && pwd)"
INSTALL_SCRIPT="$PROJECT_ROOT/installer/install.sh"

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

for tool in python3 uv; do
  command -v "$tool" >/dev/null 2>&1 || setup_error "required tool unavailable: $tool"
done
for required in "$INSTALL_SCRIPT" "$PROJECT_ROOT/installer/merge-settings.py"; do
  [ -r "$required" ] || setup_error "required file unreadable: $required"
done

setup_mock_source() {
  local MOCK_DIR
  MOCK_DIR=$(mktemp -d) || setup_error "cannot allocate fixture"

  mkdir -p "$MOCK_DIR/assets/skills/fbk-spec" || setup_error "cannot prepare fixture"
  mkdir -p "$MOCK_DIR/assets/agents" || setup_error "cannot prepare fixture"
  mkdir -p "$MOCK_DIR/assets/fbk-scripts" || setup_error "cannot prepare fixture"
  mkdir -p "$MOCK_DIR/assets/fbk-docs/workflow" || setup_error "cannot prepare fixture"

  echo "mock spec prompt" > "$MOCK_DIR/assets/skills/fbk-spec/prompt.md" || setup_error "cannot write fixture"
  echo "mock agent" > "$MOCK_DIR/assets/agents/fbk-review-researcher.md" || setup_error "cannot write fixture"
  echo "# mock fbk.py" > "$MOCK_DIR/assets/fbk-scripts/fbk.py" || setup_error "cannot write fixture"
  echo "mock doc" > "$MOCK_DIR/assets/fbk-docs/workflow/guide.md" || setup_error "cannot write fixture"

  cat > "$MOCK_DIR/assets/settings.json" << 'EOF' || setup_error "cannot write fixture"
{
  "hooks": {
    "TaskCompleted": [
      {
        "hooks": [
          {
            "type": "command",
            "command": "python3 \"$HOME\"/.claude/fbk-scripts/fbk.py workflow-hook"
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

  echo "should not be installed" > "$MOCK_DIR/assets/CLAUDE.md" || setup_error "cannot write fixture"

  echo "$MOCK_DIR/assets"
}

echo "TAP version 13"

# Setup
MOCK_SOURCE=$(setup_mock_source) || setup_error "cannot allocate fixture"
TARGET=$(mktemp -d) || setup_error "cannot allocate fixture"

# Create pre-existing settings.json
cat > "$TARGET/settings.json" << 'EOF' || setup_error "cannot write fixture"
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
fbk_run "installer before assessment $((TOTAL + 1))" bash "$INSTALL_SCRIPT" --target "$TARGET" --source "$MOCK_SOURCE" > /dev/null 2>&1
RC=$?

# Test 1: Post-install fbk files exist
if [ -f "$TARGET/skills/fbk-spec/prompt.md" ] && [ -f "$TARGET/agents/fbk-review-researcher.md" ] && \
   [ -f "$TARGET/fbk-scripts/fbk.py" ] && [ -f "$TARGET/fbk-docs/workflow/guide.md" ]; then
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
if [ -f "$TARGET/.firebreak-manifest.json" ] && fbk_run "settings inspection before assessment $((TOTAL + 1))" python3 -c "import json; json.load(open('$TARGET/.firebreak-manifest.json'))" 2>/dev/null; then
  ok "post-install: manifest exists and is valid JSON"
else
  not_ok "post-install: manifest exists and is valid JSON" "manifest missing or invalid"
fi

# Test 5: Post-install permissions untouched
PERMS=$(fbk_run "settings inspection before assessment $((TOTAL + 1))" python3 -c "import sys, json; data = json.load(open('$TARGET/settings.json')); print(data.get('permissions', {}).get('allow', []) == ['Read'])" 2>/dev/null)
if [ "$PERMS" = "True" ]; then
  ok "post-install: permissions untouched"
else
  not_ok "post-install: permissions untouched" "permissions=$PERMS" "permissions.allow=[Read] (comparison=True)"
fi

# Test 6: Post-install env merged
USER_VAR=$(fbk_run "settings inspection before assessment $((TOTAL + 1))" python3 -c "import sys, json; data = json.load(open('$TARGET/settings.json')); print(data.get('env', {}).get('USER_VAR', ''))" 2>/dev/null)
FBK_VAR=$(fbk_run "settings inspection before assessment $((TOTAL + 1))" python3 -c "import sys, json; data = json.load(open('$TARGET/settings.json')); print(data.get('env', {}).get('CLAUDE_CODE_EXPERIMENTAL_AGENT_TEAMS', ''))" 2>/dev/null)
if [ "$USER_VAR" = "keep-me" ] && [ "$FBK_VAR" = "1" ]; then
  ok "post-install: env merged"
else
  not_ok "post-install: env merged" "user_var=$USER_VAR fbk_var=$FBK_VAR" "USER_VAR=keep-me; CLAUDE_CODE_EXPERIMENTAL_AGENT_TEAMS=1"
fi

# Phase 2: Upgrade
echo "updated spec prompt" > "$MOCK_SOURCE/skills/fbk-spec/prompt.md" || setup_error "cannot write fixture"
fbk_run "installer before assessment $((TOTAL + 1))" bash "$INSTALL_SCRIPT" --target "$TARGET" --source "$MOCK_SOURCE" > /dev/null 2>&1

# Test 8: Post-upgrade fbk file updated
PROMPT_CONTENT=$(cat "$TARGET/skills/fbk-spec/prompt.md" 2>/dev/null)
if [ "$PROMPT_CONTENT" = "updated spec prompt" ]; then
  ok "post-upgrade: fbk file updated to new version"
else
  not_ok "post-upgrade: fbk file updated to new version" "content=$PROMPT_CONTENT" "updated spec prompt"
fi

# Test 10: Post-upgrade user content preserved
USER_VAR=$(fbk_run "settings inspection before assessment $((TOTAL + 1))" python3 -c "import sys, json; data = json.load(open('$TARGET/settings.json')); print(data.get('env', {}).get('USER_VAR', ''))" 2>/dev/null)
PRETOOL_HAS_USER=$(fbk_run "settings inspection before assessment $((TOTAL + 1))" python3 -c "import sys, json; data = json.load(open('$TARGET/settings.json')); hooks = data.get('hooks', {}).get('PreToolUse', []); print(any('user-guard.sh' in str(h) for h in hooks))" 2>/dev/null)
PERMS=$(fbk_run "settings inspection before assessment $((TOTAL + 1))" python3 -c "import sys, json; data = json.load(open('$TARGET/settings.json')); print(data.get('permissions', {}).get('allow', []) == ['Read'])" 2>/dev/null)
if [ "$USER_VAR" = "keep-me" ] && [ "$PRETOOL_HAS_USER" = "True" ] && [ "$PERMS" = "True" ]; then
  ok "post-upgrade: user content preserved"
else
  not_ok "post-upgrade: user content preserved" "user_var=$USER_VAR pretool=$PRETOOL_HAS_USER perms=$PERMS" "user_var=keep-me pretool=True perms=True"
fi

# Phase 3: Uninstall
fbk_run "installer before assessment $((TOTAL + 1))" bash "$INSTALL_SCRIPT" --uninstall --target "$TARGET" > /dev/null 2>&1

# Test 12: Post-uninstall manifest removed
if [ ! -f "$TARGET/.firebreak-manifest.json" ]; then
  ok "post-uninstall: manifest removed"
else
  not_ok "post-uninstall: manifest removed" "manifest still exists"
fi

# Test 13: Post-uninstall firebreak hooks removed, user hooks preserved
TASK_EMPTY=$(fbk_run "settings inspection before assessment $((TOTAL + 1))" python3 -c "import sys, json; data = json.load(open('$TARGET/settings.json')); hooks = data.get('hooks', {}).get('TaskCompleted', []); print(len(hooks) == 0)" 2>/dev/null)
PRETOOL_HAS_USER=$(fbk_run "settings inspection before assessment $((TOTAL + 1))" python3 -c "import sys, json; data = json.load(open('$TARGET/settings.json')); hooks = data.get('hooks', {}).get('PreToolUse', []); print(any('user-guard.sh' in str(h) for h in hooks))" 2>/dev/null)
if [ "$TASK_EMPTY" = "True" ] && [ "$PRETOOL_HAS_USER" = "True" ]; then
  ok "post-uninstall: firebreak hooks removed, user hooks preserved"
else
  not_ok "post-uninstall: firebreak hooks removed, user hooks preserved" "task_empty=$TASK_EMPTY pretool_user=$PRETOOL_HAS_USER" "task_empty=True pretool_user=True"
fi

# Test 14: Post-uninstall firebreak env removed, user env preserved
NO_FBK_VAR=$(fbk_run "settings inspection before assessment $((TOTAL + 1))" python3 -c "import sys, json; data = json.load(open('$TARGET/settings.json')); print('CLAUDE_CODE_EXPERIMENTAL_AGENT_TEAMS' not in data.get('env', {}))" 2>/dev/null)
USER_VAR=$(fbk_run "settings inspection before assessment $((TOTAL + 1))" python3 -c "import sys, json; data = json.load(open('$TARGET/settings.json')); print(data.get('env', {}).get('USER_VAR', ''))" 2>/dev/null)
if [ "$NO_FBK_VAR" = "True" ] && [ "$USER_VAR" = "keep-me" ]; then
  ok "post-uninstall: firebreak env removed, user env preserved"
else
  not_ok "post-uninstall: firebreak env removed, user env preserved" "no_fbk=$NO_FBK_VAR user_var=$USER_VAR" "no_fbk=True user_var=keep-me"
fi

# Test 15: Post-uninstall permissions untouched
PERMS=$(fbk_run "settings inspection before assessment $((TOTAL + 1))" python3 -c "import sys, json; data = json.load(open('$TARGET/settings.json')); print(data.get('permissions', {}).get('allow', []) == ['Read'])" 2>/dev/null)
if [ "$PERMS" = "True" ]; then
  ok "post-uninstall: permissions still untouched"
else
  not_ok "post-uninstall: permissions still untouched" "perms=$PERMS" "perms=True"
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
