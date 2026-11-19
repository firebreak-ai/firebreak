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
  fbk_diag "$1${2:+: $2}"
}

setup_mock_source() {
  local src
  src=$(mktemp -d)
  mkdir -p "$src/assets/skills/fbk-spec"
  mkdir -p "$src/assets/agents"
  mkdir -p "$src/assets/fbk-scripts"
  mkdir -p "$src/assets/fbk-docs/workflow"
  echo "mock spec prompt" > "$src/assets/skills/fbk-spec/prompt.md"
  echo "mock agent" > "$src/assets/agents/fbk-review-researcher.md"
  echo "# mock fbk.py" > "$src/assets/fbk-scripts/fbk.py"
  echo "mock doc" > "$src/assets/fbk-docs/workflow/guide.md"
  echo '{"hooks":{"TaskCompleted":[{"hooks":[{"type":"command","command":"python3 \"$HOME\"/.claude/fbk-scripts/fbk.py workflow-hook"}]}]},"env":{"CLAUDE_CODE_EXPERIMENTAL_AGENT_TEAMS":"1"}}' \
    > "$src/assets/settings.json"
  echo "should not be installed" > "$src/assets/CLAUDE.md"
  echo "$src/assets"
}

# Build a second source tree from an existing one with one asset removed,
# modelling a release that drops a file it used to ship.
setup_shrunk_source() {
  local base="$1"
  local removed_rel="$2"
  local src
  src=$(mktemp -d)
  cp -R "$base/." "$src/"
  rm -f "$src/$removed_rel"
  echo "$src"
}

setup_target() {
  local tgt
  tgt=$(mktemp -d)
  echo "$tgt"
}

source "$PROJECT_ROOT/tests/lib/test-report.sh"
fbk_test_init "$0" || exit 2

for prerequisite in python3 uv; do
  if ! command -v "$prerequisite" >/dev/null 2>&1; then
    echo "Bail out! setup error: required command unavailable: $prerequisite"
    exit 2
  fi
done

echo "TAP version 13"

# --- upgrade overwrites fbk files ---
MOCK_SOURCE=$(setup_mock_source)
TARGET=$(setup_target)
fbk_run "install or upgrade" bash "$INSTALL_SCRIPT" --target "$TARGET" --source "$MOCK_SOURCE" 2>/dev/null
echo "user modified this" > "$TARGET/skills/fbk-spec/prompt.md"
fbk_run "install or upgrade" bash "$INSTALL_SCRIPT" --target "$TARGET" --source "$MOCK_SOURCE" 2>/dev/null
RC=$?
CONTENT=$(cat "$TARGET/skills/fbk-spec/prompt.md" 2>/dev/null || true)
if [ $RC -eq 0 ] && [ "$CONTENT" = "mock spec prompt" ]; then
  ok "upgrade overwrites fbk-prefixed files with source version"
else
  not_ok "upgrade overwrites fbk-prefixed files with source version" "rc=$RC content=$CONTENT"
fi

# --- upgrade updates manifest timestamp ---
MOCK_SOURCE=$(setup_mock_source)
TARGET=$(setup_target)
fbk_run "install or upgrade" bash "$INSTALL_SCRIPT" --target "$TARGET" --source "$MOCK_SOURCE" 2>/dev/null
ORIG_TS=$(fbk_run "inspect installed metadata" python3 -c "import json; d=json.load(open('$TARGET/.firebreak-manifest.json')); print(d.get('updated_at', d.get('installed_at','')))" 2>/dev/null || true)
sleep 1
fbk_run "install or upgrade" bash "$INSTALL_SCRIPT" --target "$TARGET" --source "$MOCK_SOURCE" 2>/dev/null
NEW_TS=$(fbk_run "inspect installed metadata" python3 -c "import json; d=json.load(open('$TARGET/.firebreak-manifest.json')); print(d.get('updated_at', d.get('installed_at','')))" 2>/dev/null || true)
if [ -n "$ORIG_TS" ] && [ -n "$NEW_TS" ] && [ "$ORIG_TS" != "$NEW_TS" ]; then
  ok "upgrade updates manifest timestamp"
else
  not_ok "upgrade updates manifest timestamp" "orig_ts=$ORIG_TS new_ts=$NEW_TS"
fi

# --- upgrade does not duplicate hooks ---
MOCK_SOURCE=$(setup_mock_source)
TARGET=$(setup_target)
fbk_run "install or upgrade" bash "$INSTALL_SCRIPT" --target "$TARGET" --source "$MOCK_SOURCE" 2>/dev/null
fbk_run "install or upgrade" bash "$INSTALL_SCRIPT" --target "$TARGET" --source "$MOCK_SOURCE" 2>/dev/null
HOOK_COUNT=$(fbk_run "inspect installed metadata" python3 -c "import json; d=json.load(open('$TARGET/settings.json')); print(len(d.get('hooks',{}).get('TaskCompleted',[])))" 2>/dev/null || true)
if [ "$HOOK_COUNT" = "1" ]; then
  ok "upgrade does not duplicate hooks in settings.json"
else
  not_ok "upgrade does not duplicate hooks in settings.json" "hook_count=$HOOK_COUNT"
fi

# --- upgrade preserves non-fbk files ---
MOCK_SOURCE=$(setup_mock_source)
TARGET=$(setup_target)
mkdir -p "$TARGET/agents"
echo "user agent" > "$TARGET/agents/my-agent.md"
fbk_run "install or upgrade" bash "$INSTALL_SCRIPT" --target "$TARGET" --source "$MOCK_SOURCE" 2>/dev/null
fbk_run "install or upgrade" bash "$INSTALL_SCRIPT" --target "$TARGET" --source "$MOCK_SOURCE" 2>/dev/null
CONTENT=$(cat "$TARGET/agents/my-agent.md" 2>/dev/null || true)
if [ "$CONTENT" = "user agent" ]; then
  ok "upgrade preserves non-fbk files"
else
  not_ok "upgrade preserves non-fbk files" "content=$CONTENT"
fi




# --- uninstall preserves env keys when user changed value ---
MOCK_SOURCE=$(setup_mock_source)
TARGET=$(setup_target)
fbk_run "install or upgrade" bash "$INSTALL_SCRIPT" --target "$TARGET" --source "$MOCK_SOURCE" 2>/dev/null
fbk_run "prepare metadata fixture" python3 -c "
import json
path = '$TARGET/settings.json'
d = json.load(open(path))
d.setdefault('env', {})['CLAUDE_CODE_EXPERIMENTAL_AGENT_TEAMS'] = 'custom-value'
json.dump(d, open(path, 'w'), indent=2)
" 2>/dev/null
fbk_run "uninstall" bash "$INSTALL_SCRIPT" --uninstall --target "$TARGET" >/dev/null 2>&1
ENV_VALUE=$(fbk_run "inspect installed metadata" python3 -c "import json; d=json.load(open('$TARGET/settings.json')); print(d.get('env',{}).get('CLAUDE_CODE_EXPERIMENTAL_AGENT_TEAMS','NOT_PRESENT'))" 2>/dev/null || true)
if [ "$ENV_VALUE" = "custom-value" ]; then
  ok "uninstall preserves env keys when user changed the value"
else
  not_ok "uninstall preserves env keys when user changed the value" "env_value=$ENV_VALUE"
fi




# --- uninstall with no manifest exits with error ---
TARGET=$(setup_target)
STDERR_OUT=$(fbk_run "uninstall" bash "$INSTALL_SCRIPT" --uninstall --target "$TARGET" 2>&1 >/dev/null)
RC=$?
if [ $RC -ne 0 ] && echo "$STDERR_OUT" | grep -qiE "no firebreak|not found|no installation|manifest"; then
  ok "uninstall with no manifest exits with error"
else
  not_ok "uninstall with no manifest exits with error" "rc=$RC stderr=$STDERR_OUT"
fi

# --- malformed settings.json on install exits with error, no changes made ---
MOCK_SOURCE=$(setup_mock_source)
TARGET=$(setup_target)
echo '{this is not valid json' > "$TARGET/settings.json"
STDERR_OUT=$(fbk_run "install or upgrade" bash "$INSTALL_SCRIPT" --target "$TARGET" --source "$MOCK_SOURCE" 2>&1 >/dev/null)
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

# --- upgrade removes an asset the new version no longer ships ---
MOCK_SOURCE=$(setup_mock_source)
TARGET=$(setup_target)
fbk_run "install or upgrade" bash "$INSTALL_SCRIPT" --target "$TARGET" --source "$MOCK_SOURCE" 2>/dev/null
SHRUNK_SOURCE=$(setup_shrunk_source "$MOCK_SOURCE" "agents/fbk-review-researcher.md")
fbk_run "install or upgrade" bash "$INSTALL_SCRIPT" --target "$TARGET" --source "$SHRUNK_SOURCE" 2>/dev/null
RC=$?
if [ $RC -eq 0 ] \
  && [ ! -f "$TARGET/agents/fbk-review-researcher.md" ] \
  && [ -f "$TARGET/skills/fbk-spec/prompt.md" ] \
  && [ -f "$TARGET/fbk-scripts/fbk.py" ]; then
  ok "upgrade removes a file the new version no longer ships"
else
  not_ok "upgrade removes a file the new version no longer ships" "rc=$RC dropped=$([ -f "$TARGET/agents/fbk-review-researcher.md" ] && echo exists || echo gone) kept=$([ -f "$TARGET/skills/fbk-spec/prompt.md" ] && echo exists || echo gone)"
fi

# --- pruning leaves user files created after the first install ---
MOCK_SOURCE=$(setup_mock_source)
TARGET=$(setup_target)
fbk_run "install or upgrade" bash "$INSTALL_SCRIPT" --target "$TARGET" --source "$MOCK_SOURCE" 2>/dev/null
echo "written after install" > "$TARGET/agents/my-later-agent.md"
SHRUNK_SOURCE=$(setup_shrunk_source "$MOCK_SOURCE" "agents/fbk-review-researcher.md")
fbk_run "install or upgrade" bash "$INSTALL_SCRIPT" --target "$TARGET" --source "$SHRUNK_SOURCE" 2>/dev/null
CONTENT=$(cat "$TARGET/agents/my-later-agent.md" 2>/dev/null || true)
if [ "$CONTENT" = "written after install" ]; then
  ok "pruning leaves user files created after the first install"
else
  not_ok "pruning leaves user files created after the first install" "content=$CONTENT"
fi

# --- pruning removes a directory left empty ---
MOCK_SOURCE=$(setup_mock_source)
TARGET=$(setup_target)
fbk_run "install or upgrade" bash "$INSTALL_SCRIPT" --target "$TARGET" --source "$MOCK_SOURCE" 2>/dev/null
SHRUNK_SOURCE=$(setup_shrunk_source "$MOCK_SOURCE" "skills/fbk-spec/prompt.md")
fbk_run "install or upgrade" bash "$INSTALL_SCRIPT" --target "$TARGET" --source "$SHRUNK_SOURCE" 2>/dev/null
if [ ! -d "$TARGET/skills/fbk-spec" ] && [ -d "$TARGET/agents" ]; then
  ok "pruning removes a directory left empty and keeps populated ones"
else
  not_ok "pruning removes a directory left empty and keeps populated ones" "emptied=$([ -d "$TARGET/skills/fbk-spec" ] && echo exists || echo gone) populated=$([ -d "$TARGET/agents" ] && echo exists || echo gone)"
fi




# --- manifest entry pointing outside the target is refused ---
MOCK_SOURCE=$(setup_mock_source)
TARGET=$(setup_target)
fbk_run "install or upgrade" bash "$INSTALL_SCRIPT" --target "$TARGET" --source "$MOCK_SOURCE" 2>/dev/null
VICTIM="$(dirname "$TARGET")/prune-escape-victim.txt"
echo "outside the install target" > "$VICTIM"
fbk_run "prepare metadata fixture" python3 -c "
import json, sys
path = '$TARGET/.firebreak-manifest.json'
d = json.load(open(path))
d['files'].append('../prune-escape-victim.txt')
json.dump(d, open(path, 'w'), indent=2)
" 2>/dev/null
STDERR_OUT=$(fbk_run "install or upgrade" bash "$INSTALL_SCRIPT" --target "$TARGET" --source "$MOCK_SOURCE" 2>&1 >/dev/null)
VICTIM_CONTENT=$(cat "$VICTIM" 2>/dev/null || true)
if [ "$VICTIM_CONTENT" = "outside the install target" ] \
  && echo "$STDERR_OUT" | grep -qi "outside the install target"; then
  ok "manifest entry pointing outside the target is refused"
else
  not_ok "manifest entry pointing outside the target is refused" "victim=$VICTIM_CONTENT stderr=$STDERR_OUT"
fi

# --- upgrade refreshes the recorded version but keeps the install date ---
MOCK_SOURCE=$(setup_mock_source)
TARGET=$(setup_target)
fbk_run "install or upgrade" bash "$INSTALL_SCRIPT" --target "$TARGET" --source "$MOCK_SOURCE" 2>/dev/null
fbk_run "prepare metadata fixture" python3 -c "
import json
path = '$TARGET/.firebreak-manifest.json'
d = json.load(open(path))
d['firebreak_version'] = '0.0.1'
d['installer_version'] = '0.0.1'
d['installed_at'] = '2020-01-01T00:00:00Z'
json.dump(d, open(path, 'w'), indent=2)
" 2>/dev/null
fbk_run "install or upgrade" bash "$INSTALL_SCRIPT" --target "$TARGET" --source "$MOCK_SOURCE" 2>/dev/null
NEW_VERSION=$(fbk_run "inspect installed metadata" python3 -c "import json; print(json.load(open('$TARGET/.firebreak-manifest.json')).get('firebreak_version',''))" 2>/dev/null || true)
KEPT_DATE=$(fbk_run "inspect installed metadata" python3 -c "import json; print(json.load(open('$TARGET/.firebreak-manifest.json')).get('installed_at',''))" 2>/dev/null || true)
# Expected value computed from the repo's own CHANGELOG, independently of the installer
EXPECTED_VERSION=$(fbk_run "inspect installed metadata" python3 - "$PROJECT_ROOT/CHANGELOG.md" <<'PYEOF' 2>/dev/null || true
import re, sys
heading = re.compile(r'^##\s*\[(\d+\.\d+\.\d+[^\]]*)\]')
for line in open(sys.argv[1], encoding='utf-8'):
    match = heading.match(line)
    if match:
        print(match.group(1))
        break
PYEOF
)
if [ -n "$EXPECTED_VERSION" ] && [ "$NEW_VERSION" = "$EXPECTED_VERSION" ] \
  && [ "$KEPT_DATE" = "2020-01-01T00:00:00Z" ]; then
  ok "upgrade refreshes the recorded version and preserves the original install date"
else
  not_ok "upgrade refreshes the recorded version and preserves the original install date" "expected=$EXPECTED_VERSION version=$NEW_VERSION installed_at=$KEPT_DATE"
fi

# --- Upgrade removes retired hook registrations and keeps operator hooks ---
MOCK_SOURCE=$(setup_mock_source)
TARGET=$(setup_target)
fbk_run "install outgoing hook" bash "$INSTALL_SCRIPT" --target "$TARGET" --source "$MOCK_SOURCE" >/dev/null 2>&1
python3 - "$TARGET/settings.json" "$MOCK_SOURCE/settings.json" <<'PYEOF'
import json, sys
from pathlib import Path
settings = Path(sys.argv[1])
data = json.loads(settings.read_text())
data['hooks']['TaskCompleted'].append({'hooks': [{'type': 'command', 'command': 'operator-hook'}]})
settings.write_text(json.dumps(data))
Path(sys.argv[2]).write_text(json.dumps({'hooks': {'SessionStart': [{'hooks': [{'type': 'command', 'command': 'new-hook'}]}]}}))
PYEOF
fbk_run "upgrade retired hooks" bash "$INSTALL_SCRIPT" --target "$TARGET" --source "$MOCK_SOURCE" >/dev/null 2>&1
if fbk_run "verify hook ownership after upgrade" python3 - "$TARGET" <<'PYEOF'
import json, sys
from pathlib import Path
root = Path(sys.argv[1])
settings = json.loads((root / 'settings.json').read_text())
commands = [h['command'] for groups in settings['hooks'].values() for g in groups for h in g['hooks']]
assert commands == ['operator-hook', 'new-hook'], commands
owned = json.loads((root / '.firebreak-manifest.json').read_text())['settings_entries']
assert set(owned['hooks_added']) == {'SessionStart'}, owned
assert 'CLAUDE_CODE_EXPERIMENTAL_AGENT_TEAMS' not in settings.get('env', {}), settings
PYEOF
then
  ok "upgrade removes retired hook and env entries while preserving operator hooks"
else
  not_ok "upgrade removes retired hook and env entries while preserving operator hooks"
fi

# --- Summary ---
echo ""
echo "# $PASS/$TOTAL tests passed"
echo "1..$TOTAL"

if [ "$FAIL" -gt 0 ]; then
  exit 1
fi
exit 0
