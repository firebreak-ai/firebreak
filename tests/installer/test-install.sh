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

# Test 12: Dev artifacts excluded from install (.venv, venv, __pycache__, .pytest_cache, *.pyc, .DS_Store)
MOCK_SOURCE=$(setup_mock_source)
TARGET=$(setup_target)
mkdir -p "$MOCK_SOURCE/fbk-scripts/.venv/lib"
echo "fake venv" > "$MOCK_SOURCE/fbk-scripts/.venv/lib/fake.py"
mkdir -p "$MOCK_SOURCE/fbk-scripts/venv/lib"
echo "fake venv" > "$MOCK_SOURCE/fbk-scripts/venv/lib/fake2.py"
mkdir -p "$MOCK_SOURCE/fbk-scripts/fbk/__pycache__"
echo "pyc content" > "$MOCK_SOURCE/fbk-scripts/fbk/__pycache__/mod.cpython-311.pyc"
mkdir -p "$MOCK_SOURCE/fbk-scripts/.pytest_cache"
echo "pytest" > "$MOCK_SOURCE/fbk-scripts/.pytest_cache/CACHEDIR.TAG"
echo "osjunk" > "$MOCK_SOURCE/.DS_Store"
bash "$INSTALL_SCRIPT" --target "$TARGET" --source "$MOCK_SOURCE" > /dev/null 2>&1
EXCLUDED_FOUND=0
for relpath in fbk-scripts/.venv/lib/fake.py fbk-scripts/venv/lib/fake2.py fbk-scripts/fbk/__pycache__/mod.cpython-311.pyc fbk-scripts/.pytest_cache/CACHEDIR.TAG .DS_Store; do
  if [ -e "$TARGET/$relpath" ]; then
    EXCLUDED_FOUND=$((EXCLUDED_FOUND + 1))
  fi
done
MANIFEST_BAD=$(python3 -c "
import json
d = json.load(open('$TARGET/.firebreak-manifest.json'))
bad = [f for f in d.get('files', []) if '.venv' in f or '/venv/' in f or '__pycache__' in f or '.pytest_cache' in f or f.endswith('.pyc') or f.endswith('.DS_Store')]
print(len(bad))
" 2>/dev/null)
if [ "$EXCLUDED_FOUND" -eq 0 ] && [ "$MANIFEST_BAD" = "0" ] && [ -f "$TARGET/skills/fbk-spec/prompt.md" ]; then
  ok "dev artifacts excluded from install (.venv/venv/__pycache__/.pytest_cache/*.pyc/.DS_Store)"
else
  not_ok "dev artifacts excluded from install" "excluded_on_disk=$EXCLUDED_FOUND manifest_bad=$MANIFEST_BAD"
fi

# Test 13: install builds the project-local uv venv with pyyaml importable.
# (Replaces an obsolete pip-era "pyyaml missing" path — the installer now
# requires uv and provisions deps into a project-local venv.)
MOCK_SOURCE=$(setup_mock_source)
TARGET=$(setup_target)
bash "$INSTALL_SCRIPT" --target "$TARGET" --source "$MOCK_SOURCE" < /dev/null > /dev/null 2>&1
VENV_PY="$TARGET/fbk-scripts/.venv/bin/python"
if [ -x "$VENV_PY" ] && "$VENV_PY" -c "import yaml" 2>/dev/null; then
  ok "install builds project-local venv with pyyaml importable"
else
  not_ok "install builds project-local venv with pyyaml importable" "venv_py=$([ -x "$VENV_PY" ] && echo yes || echo no)"
fi

# Test 14: dry-run makes no changes and reports the planned operations.
MOCK_SOURCE=$(setup_mock_source)
TARGET=$(setup_target)
DRY_STDERR=$(bash "$INSTALL_SCRIPT" --target "$TARGET" --source "$MOCK_SOURCE" --dry-run < /dev/null 2>&1 > /dev/null)
RC=$?
FILES_CREATED=$(find "$TARGET" -type f 2>/dev/null | wc -l)
if [ $RC -eq 0 ] && [ "$FILES_CREATED" -eq 0 ] && echo "$DRY_STDERR" | grep -q "\[DRY RUN\]"; then
  ok "dry-run: no changes made, planned operations reported"
else
  not_ok "dry-run: no changes made, planned operations reported" "rc=$RC files=$FILES_CREATED"
fi

# --- Version recording ---

# The version the repo's own CHANGELOG declares — computed here independently of
# the installer so the test does not confirm the installer against itself.
EXPECTED_VERSION=$(python3 -c "
import re, sys
heading = re.compile(r'^##\s*\[(\d+\.\d+\.\d+[^\]]*)\]')
for line in open('$PROJECT_ROOT/CHANGELOG.md', encoding='utf-8'):
    m = heading.match(line)
    if m:
        print(m.group(1))
        break
")

# Manifest records the release version, not a hardcoded placeholder
MOCK_SOURCE=$(setup_mock_source)
TARGET=$(setup_target)
bash "$INSTALL_SCRIPT" --target "$TARGET" --source "$MOCK_SOURCE" 2>/dev/null
RECORDED=$(python3 -c "import json; print(json.load(open('$TARGET/.firebreak-manifest.json')).get('firebreak_version',''))" 2>/dev/null || true)
RECORDED_INSTALLER=$(python3 -c "import json; print(json.load(open('$TARGET/.firebreak-manifest.json')).get('installer_version',''))" 2>/dev/null || true)
if [ -n "$EXPECTED_VERSION" ] && [ "$RECORDED" = "$EXPECTED_VERSION" ] && [ "$RECORDED_INSTALLER" = "$EXPECTED_VERSION" ]; then
  ok "manifest records the release version from the newest CHANGELOG entry"
else
  not_ok "manifest records the release version from the newest CHANGELOG entry" "expected=$EXPECTED_VERSION firebreak=$RECORDED installer=$RECORDED_INSTALLER"
fi

# A non-numeric newest heading is skipped in favour of the first real version
MOCK_SOURCE=$(setup_mock_source)
TARGET=$(setup_target)
cat > "$(dirname "$MOCK_SOURCE")/CHANGELOG.md" << 'EOF'
# Changelog

## [Unreleased]
- work in progress

## [9.8.7]
- a real release
EOF
bash "$INSTALL_SCRIPT" --target "$TARGET" --source "$MOCK_SOURCE" 2>/dev/null
RECORDED=$(python3 -c "import json; print(json.load(open('$TARGET/.firebreak-manifest.json')).get('firebreak_version',''))" 2>/dev/null || true)
if [ "$RECORDED" = "9.8.7" ]; then
  ok "an unreleased heading is skipped for the newest numbered version"
else
  not_ok "an unreleased heading is skipped for the newest numbered version" "recorded=$RECORDED"
fi

# No CHANGELOG anywhere: records "unknown", warns, and still installs.
# The installer is copied so that its own parent has no CHANGELOG to fall back on.
MOCK_SOURCE=$(setup_mock_source)
TARGET=$(setup_target)
ISOLATED=$(mktemp -d)
TEMP_DIRS+=("$ISOLATED")
mkdir -p "$ISOLATED/installer"
cp "$PROJECT_ROOT/installer/install.sh" "$PROJECT_ROOT/installer/merge-settings.py" "$ISOLATED/installer/"
STDERR_OUT=$(bash "$ISOLATED/installer/install.sh" --target "$TARGET" --source "$MOCK_SOURCE" 2>&1 >/dev/null)
RC=$?
RECORDED=$(python3 -c "import json; print(json.load(open('$TARGET/.firebreak-manifest.json')).get('firebreak_version',''))" 2>/dev/null || true)
if [ $RC -eq 0 ] && [ "$RECORDED" = "unknown" ] \
  && echo "$STDERR_OUT" | grep -qi "no CHANGELOG.md found" \
  && [ -f "$TARGET/skills/fbk-spec/prompt.md" ]; then
  ok "a missing CHANGELOG records an unknown version, warns, and still installs"
else
  not_ok "a missing CHANGELOG records an unknown version, warns, and still installs" "rc=$RC recorded=$RECORDED stderr=$STDERR_OUT"
fi

# The shipped Python package declares the same version the CHANGELOG does
PYPROJECT_VERSION=$(python3 - "$PROJECT_ROOT/assets/fbk-scripts/pyproject.toml" <<'PYEOF' 2>/dev/null || true
import re, sys
text = open(sys.argv[1], encoding='utf-8').read()
match = re.search(r'^version\s*=\s*["\']([^"\']+)', text, re.M)
print(match.group(1) if match else '')
PYEOF
)
if [ -n "$EXPECTED_VERSION" ] && [ "$PYPROJECT_VERSION" = "$EXPECTED_VERSION" ]; then
  ok "the shipped Python package version matches the newest CHANGELOG entry"
else
  not_ok "the shipped Python package version matches the newest CHANGELOG entry" "changelog=$EXPECTED_VERSION pyproject=$PYPROJECT_VERSION"
fi

# Summary
echo ""
echo "# $PASS/$TOTAL tests passed"
echo "1..$TOTAL"

if [ "$FAIL" -gt 0 ]; then
  exit 1
fi
exit 0
