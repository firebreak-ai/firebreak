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
  mkdir -p "$MOCK_DIR/assets/fbk-scripts"
  mkdir -p "$MOCK_DIR/assets/fbk-docs/fbk-sdl-workflow"

  echo "mock spec prompt" > "$MOCK_DIR/assets/skills/fbk-spec/prompt.md"
  echo "mock agent" > "$MOCK_DIR/assets/agents/fbk-code-review-detector.md"
  echo "# mock fbk.py" > "$MOCK_DIR/assets/fbk-scripts/fbk.py"
  echo "mock doc" > "$MOCK_DIR/assets/fbk-docs/fbk-sdl-workflow/guide.md"

  cat > "$MOCK_DIR/assets/settings.json" << 'EOF'
{
  "hooks": {
    "TaskCompleted": [
      {
        "hooks": [
          {
            "type": "command",
            "command": "python3 \"$HOME\"/.claude/fbk-scripts/fbk.py task-completed"
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

setup_target() {
  local TARGET_DIR
  TARGET_DIR=$(mktemp -d)
  TEMP_DIRS+=("$TARGET_DIR")
  echo "$TARGET_DIR"
}

cleanup() {
  for dir in "${TEMP_DIRS[@]}"; do
    [ -n "$dir" ] && [ -d "$dir" ] && rm -rf "$dir"
  done
}

trap cleanup EXIT

echo "TAP version 13"

# Test 1: Fresh install creates fbk-prefixed files
MOCK_SOURCE=$(setup_mock_source)
TARGET=$(setup_target)
bash "$INSTALL_SCRIPT" --target "$TARGET" --source "$MOCK_SOURCE" > /dev/null 2>&1
RC=$?
if [ -f "$TARGET/skills/fbk-spec/prompt.md" ] && [ -f "$TARGET/agents/fbk-code-review-detector.md" ] && \
   [ -f "$TARGET/fbk-scripts/fbk.py" ] && [ -f "$TARGET/fbk-docs/fbk-sdl-workflow/guide.md" ]; then
  ok "fresh install creates fbk-prefixed files in target"
else
  not_ok "fresh install creates fbk-prefixed files in target" "rc=$RC files_check_failed"
fi

# Test 2: CLAUDE.md not installed
if [ ! -f "$TARGET/CLAUDE.md" ]; then
  ok "CLAUDE.md is not installed"
else
  not_ok "CLAUDE.md is not installed" "CLAUDE.md exists in target"
fi

# Test 3: No non-fbk files created (check paths, not contents)
NON_FBK_COUNT=0
while IFS= read -r filepath; do
  # Get path relative to target
  relpath="${filepath#$TARGET/}"
  # Skip allowed non-fbk files
  case "$relpath" in
    settings.json|.firebreak-manifest.json|settings.json.pre-firebreak*) continue ;;
  esac
  # Check if any path component starts with fbk-
  if ! echo "$relpath" | grep -q "fbk-"; then
    NON_FBK_COUNT=$((NON_FBK_COUNT + 1))
  fi
done < <(find "$TARGET" -type f 2>/dev/null)
if [ "$NON_FBK_COUNT" -eq 0 ]; then
  ok "no non-fbk files created (except settings.json, manifest, backups)"
else
  not_ok "no non-fbk files created (except settings.json, manifest, backups)" "found $NON_FBK_COUNT non-fbk files"
fi

# Test 4: Manifest created with correct structure
if [ -f "$TARGET/.firebreak-manifest.json" ]; then
  SCHEMA_VERSION=$(python3 -c "import sys, json; data = json.load(open('$TARGET/.firebreak-manifest.json')); print(data.get('schema_version', ''))" 2>/dev/null)
  FILES_COUNT=$(python3 -c "import sys, json; data = json.load(open('$TARGET/.firebreak-manifest.json')); print(len(data.get('files', [])))" 2>/dev/null)
  HAS_HOOKS=$(python3 -c "import sys, json; data = json.load(open('$TARGET/.firebreak-manifest.json')); print('hooks_added' in data.get('settings_entries', {}))" 2>/dev/null)
  HAS_ENV=$(python3 -c "import sys, json; data = json.load(open('$TARGET/.firebreak-manifest.json')); print('env_added' in data.get('settings_entries', {}))" 2>/dev/null)

  if [ "$SCHEMA_VERSION" = "1.0.0" ] && [ "$FILES_COUNT" -ge 4 ] && [ "$HAS_HOOKS" = "True" ] && [ "$HAS_ENV" = "True" ]; then
    ok "manifest created with correct schema and contents"
  else
    not_ok "manifest created with correct schema and contents" "schema=$SCHEMA_VERSION files=$FILES_COUNT hooks=$HAS_HOOKS env=$HAS_ENV"
  fi
else
  not_ok "manifest created with correct schema and contents" "manifest file not found"
fi

# Test 5: Existing settings.json backed up with .pre-firebreak suffix
MOCK_SOURCE=$(setup_mock_source)
TARGET=$(setup_target)
echo '{"hooks":{}}' > "$TARGET/settings.json"
bash "$INSTALL_SCRIPT" --target "$TARGET" --source "$MOCK_SOURCE" > /dev/null 2>&1
if [ -f "$TARGET/settings.json.pre-firebreak" ]; then
  BACKUP_CONTENT=$(cat "$TARGET/settings.json.pre-firebreak" 2>/dev/null)
  if [ "$BACKUP_CONTENT" = '{"hooks":{}}' ]; then
    ok "existing settings.json backed up with .pre-firebreak suffix"
  else
    not_ok "existing settings.json backed up with .pre-firebreak suffix" "backup content mismatch"
  fi
else
  not_ok "existing settings.json backed up with .pre-firebreak suffix" "backup file not found"
fi

# Test 6: Timestamped backup when .pre-firebreak already exists
MOCK_SOURCE=$(setup_mock_source)
TARGET=$(setup_target)
echo '{"hooks":{}}' > "$TARGET/settings.json"
echo '{"old":"backup"}' > "$TARGET/settings.json.pre-firebreak"
bash "$INSTALL_SCRIPT" --target "$TARGET" --source "$MOCK_SOURCE" > /dev/null 2>&1
TIMESTAMPED_BACKUP=$(ls "$TARGET"/settings.json.pre-firebreak.* 2>/dev/null | head -1)
ORIGINAL_BACKUP=$(cat "$TARGET/settings.json.pre-firebreak" 2>/dev/null)
if [ -n "$TIMESTAMPED_BACKUP" ] && [ "$ORIGINAL_BACKUP" = '{"old":"backup"}' ]; then
  ok "timestamped backup when .pre-firebreak already exists"
else
  not_ok "timestamped backup when .pre-firebreak already exists" "timestamped=$TIMESTAMPED_BACKUP original=$ORIGINAL_BACKUP"
fi

# Test 7: Missing Python 3 exits with error, makes no changes
MOCK_SOURCE=$(setup_mock_source)
TARGET=$(setup_target)
TEMP_BIN=$(mktemp -d)
TEMP_DIRS+=("$TEMP_BIN")
ln -s /bin/bash "$TEMP_BIN/bash"
ln -s /usr/bin/env "$TEMP_BIN/env"
STDERR_OUT=$(PATH="$TEMP_BIN" bash "$INSTALL_SCRIPT" --target "$TARGET" --source "$MOCK_SOURCE" 2>&1)
RC=$?
FILES_CREATED=$(find "$TARGET" -type f 2>/dev/null | wc -l)
if [ $RC -ne 0 ] && echo "$STDERR_OUT" | grep -iq "python 3" && [ "$FILES_CREATED" -eq 0 ]; then
  ok "missing Python 3 exits with error and makes no changes"
else
  not_ok "missing Python 3 exits with error and makes no changes" "rc=$RC files_created=$FILES_CREATED"
fi

# Test 8: Project-level install
MOCK_SOURCE=$(setup_mock_source)
PROJECT_DIR=$(mktemp -d)
TEMP_DIRS+=("$PROJECT_DIR")
bash "$INSTALL_SCRIPT" --target "$PROJECT_DIR/.claude" --source "$MOCK_SOURCE" > /dev/null 2>&1
if [ -f "$PROJECT_DIR/.claude/skills/fbk-spec/prompt.md" ] && [ -f "$PROJECT_DIR/.claude/agents/fbk-code-review-detector.md" ]; then
  ok "project-level install creates files at correct path"
else
  not_ok "project-level install creates files at correct path" "files not found at .claude subdir"
fi

# Test 9: Dry-run makes no changes
MOCK_SOURCE=$(setup_mock_source)
TARGET=$(setup_target)
DRY_OUTPUT=$(bash "$INSTALL_SCRIPT" --target "$TARGET" --source "$MOCK_SOURCE" --dry-run 2>&1)
RC=$?
FILES_CREATED=$(find "$TARGET" -type f 2>/dev/null | wc -l)
if [ $RC -eq 0 ] && (echo "$DRY_OUTPUT" | grep -qE "(would|copying|installing)") && [ "$FILES_CREATED" -eq 0 ]; then
  ok "dry-run prints operations but makes no changes"
else
  not_ok "dry-run prints operations but makes no changes" "rc=$RC files_created=$FILES_CREATED dry_output=$DRY_OUTPUT"
fi

# Test 10: Existing non-fbk files in target are untouched
MOCK_SOURCE=$(setup_mock_source)
TARGET=$(setup_target)
mkdir -p "$TARGET/skills/my-custom-skill"
echo "user content" > "$TARGET/skills/my-custom-skill/prompt.md"
bash "$INSTALL_SCRIPT" --target "$TARGET" --source "$MOCK_SOURCE" > /dev/null 2>&1
CUSTOM_CONTENT=$(cat "$TARGET/skills/my-custom-skill/prompt.md" 2>/dev/null)
if [ "$CUSTOM_CONTENT" = "user content" ]; then
  ok "existing non-fbk files in target are untouched"
else
  not_ok "existing non-fbk files in target are untouched" "file was modified or deleted"
fi

# Test 11: Attempts GitHub download when no local source exists
TARGET=$(setup_target)
ISOLATED_DIR=$(mktemp -d)
TEMP_DIRS+=("$ISOLATED_DIR")
cp "$INSTALL_SCRIPT" "$ISOLATED_DIR/install.sh"
STDERR_OUT=$(FIREBREAK_GITHUB_REPO="nonexistent-owner/nonexistent-repo" \
  bash "$ISOLATED_DIR/install.sh" --target "$TARGET" 2>&1 >/dev/null)
RC=$?
if [ $RC -ne 0 ] && echo "$STDERR_OUT" | grep -q "Downloading firebreak"; then
  ok "attempts GitHub download when local source is missing"
else
  not_ok "attempts GitHub download when local source is missing" "rc=$RC stderr=$STDERR_OUT"
fi

# Summary
echo ""
echo "# $PASS/$TOTAL tests passed"
echo "1..$TOTAL"

if [ "$FAIL" -gt 0 ]; then
  exit 1
fi
exit 0
