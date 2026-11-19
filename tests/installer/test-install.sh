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

setup_target() {
  local TARGET_DIR
  TARGET_DIR=$(mktemp -d) || setup_error "cannot allocate fixture"

  echo "$TARGET_DIR"
}

echo "TAP version 13"

# Test 1: Fresh install creates fbk-prefixed files
MOCK_SOURCE=$(setup_mock_source) || setup_error "cannot allocate fixture"
TARGET=$(setup_target) || setup_error "cannot allocate fixture"
fbk_run "installer before assessment $((TOTAL + 1))" bash "$INSTALL_SCRIPT" --target "$TARGET" --source "$MOCK_SOURCE" > /dev/null 2>&1
RC=$?
if [ -f "$TARGET/skills/fbk-spec/prompt.md" ] && [ -f "$TARGET/agents/fbk-review-researcher.md" ] && \
   [ -f "$TARGET/fbk-scripts/fbk.py" ] && [ -f "$TARGET/fbk-docs/workflow/guide.md" ]; then
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

# Test 5: Existing settings.json backed up with .pre-firebreak suffix
MOCK_SOURCE=$(setup_mock_source) || setup_error "cannot allocate fixture"
TARGET=$(setup_target) || setup_error "cannot allocate fixture"
echo '{"hooks":{}}' > "$TARGET/settings.json" || setup_error "cannot write fixture"
fbk_run "installer before assessment $((TOTAL + 1))" bash "$INSTALL_SCRIPT" --target "$TARGET" --source "$MOCK_SOURCE" > /dev/null 2>&1
if [ -f "$TARGET/settings.json.pre-firebreak" ]; then
  BACKUP_CONTENT=$(cat "$TARGET/settings.json.pre-firebreak" 2>/dev/null)
  if [ "$BACKUP_CONTENT" = '{"hooks":{}}' ]; then
    ok "existing settings.json backed up with .pre-firebreak suffix"
  else
    not_ok "existing settings.json backed up with .pre-firebreak suffix" "backup_content=$BACKUP_CONTENT" '{"hooks":{}}'
  fi
else
  not_ok "existing settings.json backed up with .pre-firebreak suffix" "backup file not found"
fi

# Test 7: Missing Python 3 exits with error, makes no changes
MOCK_SOURCE=$(setup_mock_source) || setup_error "cannot allocate fixture"
TARGET=$(setup_target) || setup_error "cannot allocate fixture"
TEMP_BIN=$(mktemp -d) || setup_error "cannot allocate fixture"

ln -s /bin/bash "$TEMP_BIN/bash" || setup_error "cannot prepare fixture"
ln -s /usr/bin/env "$TEMP_BIN/env" || setup_error "cannot prepare fixture"
STDERR_OUT=$(fbk_run "install without Python" env PATH="$TEMP_BIN" bash "$INSTALL_SCRIPT" --target "$TARGET" --source "$MOCK_SOURCE" 2>&1)
RC=$?
FILES_CREATED=$(find "$TARGET" -type f 2>/dev/null | wc -l)
if [ $RC -ne 0 ] && echo "$STDERR_OUT" | grep -iq "python 3" && [ "$FILES_CREATED" -eq 0 ]; then
  ok "missing Python 3 exits with error and makes no changes"
else
  not_ok "missing Python 3 exits with error and makes no changes" "rc=$RC files_created=$FILES_CREATED" "rc != 0; files_created=0; output mentions Python 3"
fi

# Test 8: Project-level install
MOCK_SOURCE=$(setup_mock_source) || setup_error "cannot allocate fixture"
PROJECT_DIR=$(mktemp -d) || setup_error "cannot allocate fixture"

fbk_run "installer before assessment $((TOTAL + 1))" bash "$INSTALL_SCRIPT" --target "$PROJECT_DIR/.claude" --source "$MOCK_SOURCE" > /dev/null 2>&1
if [ -f "$PROJECT_DIR/.claude/skills/fbk-spec/prompt.md" ] && [ -f "$PROJECT_DIR/.claude/agents/fbk-review-researcher.md" ]; then
  ok "project-level install creates files at correct path"
else
  not_ok "project-level install creates files at correct path" "files not found at .claude subdir"
fi

# Test 9: Dry-run makes no changes
MOCK_SOURCE=$(setup_mock_source) || setup_error "cannot allocate fixture"
TARGET=$(setup_target) || setup_error "cannot allocate fixture"
DRY_OUTPUT=$(fbk_run "installer before assessment $((TOTAL + 1))" bash "$INSTALL_SCRIPT" --target "$TARGET" --source "$MOCK_SOURCE" --dry-run 2>&1)
RC=$?
FILES_CREATED=$(find "$TARGET" -type f 2>/dev/null | wc -l)
if [ $RC -eq 0 ] && (echo "$DRY_OUTPUT" | grep -qE "(would|copying|installing)") && [ "$FILES_CREATED" -eq 0 ]; then
  ok "dry-run prints operations but makes no changes"
else
  not_ok "dry-run prints operations but makes no changes" "rc=$RC files_created=$FILES_CREATED dry_output=$DRY_OUTPUT"
fi

# Test 10: Existing non-fbk files in target are untouched
MOCK_SOURCE=$(setup_mock_source) || setup_error "cannot allocate fixture"
TARGET=$(setup_target) || setup_error "cannot allocate fixture"
mkdir -p "$TARGET/skills/my-custom-skill" || setup_error "cannot prepare fixture"
echo "user content" > "$TARGET/skills/my-custom-skill/prompt.md" || setup_error "cannot write fixture"
fbk_run "installer before assessment $((TOTAL + 1))" bash "$INSTALL_SCRIPT" --target "$TARGET" --source "$MOCK_SOURCE" > /dev/null 2>&1
CUSTOM_CONTENT=$(cat "$TARGET/skills/my-custom-skill/prompt.md" 2>/dev/null)
if [ "$CUSTOM_CONTENT" = "user content" ]; then
  ok "existing non-fbk files in target are untouched"
else
  not_ok "existing non-fbk files in target are untouched" "content=$CUSTOM_CONTENT" "user content"
fi

# Test 12: Dev artifacts excluded from install (.venv, venv, __pycache__, .pytest_cache, *.pyc, .DS_Store)
MOCK_SOURCE=$(setup_mock_source) || setup_error "cannot allocate fixture"
TARGET=$(setup_target) || setup_error "cannot allocate fixture"
mkdir -p "$MOCK_SOURCE/fbk-scripts/.venv/lib" || setup_error "cannot prepare fixture"
echo "fake venv" > "$MOCK_SOURCE/fbk-scripts/.venv/lib/fake.py" || setup_error "cannot write fixture"
mkdir -p "$MOCK_SOURCE/fbk-scripts/venv/lib" || setup_error "cannot prepare fixture"
echo "fake venv" > "$MOCK_SOURCE/fbk-scripts/venv/lib/fake2.py" || setup_error "cannot write fixture"
mkdir -p "$MOCK_SOURCE/fbk-scripts/fbk/__pycache__" || setup_error "cannot prepare fixture"
echo "pyc content" > "$MOCK_SOURCE/fbk-scripts/fbk/__pycache__/mod.cpython-311.pyc" || setup_error "cannot write fixture"
mkdir -p "$MOCK_SOURCE/fbk-scripts/.pytest_cache" || setup_error "cannot prepare fixture"
echo "pytest" > "$MOCK_SOURCE/fbk-scripts/.pytest_cache/CACHEDIR.TAG" || setup_error "cannot write fixture"
echo "osjunk" > "$MOCK_SOURCE/.DS_Store" || setup_error "cannot write fixture"
fbk_run "installer before assessment $((TOTAL + 1))" bash "$INSTALL_SCRIPT" --target "$TARGET" --source "$MOCK_SOURCE" > /dev/null 2>&1
EXCLUDED_FOUND=0
for relpath in fbk-scripts/.venv/lib/fake.py fbk-scripts/venv/lib/fake2.py fbk-scripts/fbk/__pycache__/mod.cpython-311.pyc fbk-scripts/.pytest_cache/CACHEDIR.TAG .DS_Store; do
  if [ -e "$TARGET/$relpath" ]; then
    EXCLUDED_FOUND=$((EXCLUDED_FOUND + 1))
  fi
done
MANIFEST_BAD=$(fbk_run "settings inspection before assessment $((TOTAL + 1))" python3 -c "
import json
d = json.load(open('$TARGET/.firebreak-manifest.json'))
bad = [f for f in d.get('files', []) if '.venv' in f or '/venv/' in f or '__pycache__' in f or '.pytest_cache' in f or f.endswith('.pyc') or f.endswith('.DS_Store')]
print(len(bad))
" 2>/dev/null)
if [ "$EXCLUDED_FOUND" -eq 0 ] && [ "$MANIFEST_BAD" = "0" ] && [ -f "$TARGET/skills/fbk-spec/prompt.md" ]; then
  ok "dev artifacts excluded from install (.venv/venv/__pycache__/.pytest_cache/*.pyc/.DS_Store)"
else
  not_ok "dev artifacts excluded from install" "excluded_on_disk=$EXCLUDED_FOUND manifest_bad=$MANIFEST_BAD" "excluded_on_disk=0 manifest_bad=0; installed prompt exists"
fi

# Test 13: install builds the project-local uv venv with pyyaml importable.
# (Replaces an obsolete pip-era "pyyaml missing" path — the installer now
# requires uv and provisions deps into a project-local venv.)
MOCK_SOURCE=$(setup_mock_source) || setup_error "cannot allocate fixture"
TARGET=$(setup_target) || setup_error "cannot allocate fixture"
fbk_run "installer before assessment $((TOTAL + 1))" bash "$INSTALL_SCRIPT" --target "$TARGET" --source "$MOCK_SOURCE" < /dev/null > /dev/null 2>&1
VENV_PY="$TARGET/fbk-scripts/.venv/bin/python"
if [ -x "$VENV_PY" ] && fbk_run "import installed yaml" "$VENV_PY" -c "import yaml" 2>/dev/null; then
  ok "install builds project-local venv with pyyaml importable"
else
  not_ok "install builds project-local venv with pyyaml importable" "venv_py=$([ -x "$VENV_PY" ] && echo yes || echo no)"
fi

# --- Version recording ---

# The version the repo's own CHANGELOG declares — computed here independently of
# the installer so the test does not confirm the installer against itself.
EXPECTED_VERSION=$(fbk_run "settings inspection before assessment $((TOTAL + 1))" python3 -c "
import re, sys
heading = re.compile(r'^##\s*\[(\d+\.\d+\.\d+[^\]]*)\]')
for line in open('$PROJECT_ROOT/CHANGELOG.md', encoding='utf-8'):
    m = heading.match(line)
    if m:
        print(m.group(1))
        break
")

# Manifest records the release version, not a hardcoded placeholder
MOCK_SOURCE=$(setup_mock_source) || setup_error "cannot allocate fixture"
TARGET=$(setup_target) || setup_error "cannot allocate fixture"
fbk_run "installer before assessment $((TOTAL + 1))" bash "$INSTALL_SCRIPT" --target "$TARGET" --source "$MOCK_SOURCE" 2>/dev/null
RECORDED=$(fbk_run "settings inspection before assessment $((TOTAL + 1))" python3 -c "import json; print(json.load(open('$TARGET/.firebreak-manifest.json')).get('firebreak_version',''))" 2>/dev/null || true)
RECORDED_INSTALLER=$(fbk_run "settings inspection before assessment $((TOTAL + 1))" python3 -c "import json; print(json.load(open('$TARGET/.firebreak-manifest.json')).get('installer_version',''))" 2>/dev/null || true)
if [ -n "$EXPECTED_VERSION" ] && [ "$RECORDED" = "$EXPECTED_VERSION" ] && [ "$RECORDED_INSTALLER" = "$EXPECTED_VERSION" ]; then
  ok "manifest records the release version from the newest CHANGELOG entry"
else
  not_ok "manifest records the release version from the newest CHANGELOG entry" "expected=$EXPECTED_VERSION firebreak=$RECORDED installer=$RECORDED_INSTALLER"
fi

# A non-numeric newest heading is skipped in favour of the first real version
MOCK_SOURCE=$(setup_mock_source) || setup_error "cannot allocate fixture"
TARGET=$(setup_target) || setup_error "cannot allocate fixture"
cat > "$(dirname "$MOCK_SOURCE")/CHANGELOG.md" << 'EOF' || setup_error "cannot write fixture"
# Changelog

## [Unreleased]
- work in progress

## [9.8.7]
- a real release
EOF
fbk_run "installer before assessment $((TOTAL + 1))" bash "$INSTALL_SCRIPT" --target "$TARGET" --source "$MOCK_SOURCE" 2>/dev/null
RECORDED=$(fbk_run "settings inspection before assessment $((TOTAL + 1))" python3 -c "import json; print(json.load(open('$TARGET/.firebreak-manifest.json')).get('firebreak_version',''))" 2>/dev/null || true)
if [ "$RECORDED" = "9.8.7" ]; then
  ok "an unreleased heading is skipped for the newest numbered version"
else
  not_ok "an unreleased heading is skipped for the newest numbered version" "recorded=$RECORDED" "recorded=9.8.7"
fi

# No CHANGELOG anywhere: records "unknown", warns, and still installs.
# The installer is copied so that its own parent has no CHANGELOG to fall back on.
MOCK_SOURCE=$(setup_mock_source) || setup_error "cannot allocate fixture"
TARGET=$(setup_target) || setup_error "cannot allocate fixture"
ISOLATED=$(mktemp -d) || setup_error "cannot allocate fixture"

mkdir -p "$ISOLATED/installer" || setup_error "cannot prepare fixture"
cp "$PROJECT_ROOT/installer/install.sh" "$PROJECT_ROOT/installer/merge-settings.py" "$ISOLATED/installer/" || setup_error "cannot prepare fixture"
STDERR_OUT=$(fbk_run "install without changelog" bash "$ISOLATED/installer/install.sh" --target "$TARGET" --source "$MOCK_SOURCE" 2>&1 >/dev/null)
RC=$?
RECORDED=$(fbk_run "settings inspection before assessment $((TOTAL + 1))" python3 -c "import json; print(json.load(open('$TARGET/.firebreak-manifest.json')).get('firebreak_version',''))" 2>/dev/null || true)
if [ $RC -eq 0 ] && [ "$RECORDED" = "unknown" ] \
  && echo "$STDERR_OUT" | grep -qi "no CHANGELOG.md found" \
  && [ -f "$TARGET/skills/fbk-spec/prompt.md" ]; then
  ok "a missing CHANGELOG records an unknown version, warns, and still installs"
else
  not_ok "a missing CHANGELOG records an unknown version, warns, and still installs" "rc=$RC recorded=$RECORDED stderr=$STDERR_OUT"
fi

# The shipped Python package declares the same version the CHANGELOG does
PYPROJECT_VERSION=$(fbk_run "settings inspection before assessment $((TOTAL + 1))" python3 - "$PROJECT_ROOT/assets/fbk-scripts/pyproject.toml" <<'PYEOF' 2>/dev/null || true
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

# The lock file records the package version too, and drifted unnoticed through
# 0.5.2 (package at 0.5.2, lock still at 0.4.0) because the check above did not
# reach it. Read the version from the fbk-scripts entry specifically — the lock
# lists dependency packages with versions of their own.
LOCK_VERSION=$(fbk_run "settings inspection before assessment $((TOTAL + 1))" python3 - "$PROJECT_ROOT/assets/fbk-scripts/uv.lock" <<'PYEOF' 2>/dev/null || true
import re, sys
text = open(sys.argv[1], encoding='utf-8').read()
version = ''
for block in text.split('[[package]]'):
    if re.search(r'^name\s*=\s*["\']fbk-scripts["\']', block, re.M):
        match = re.search(r'^version\s*=\s*["\']([^"\']+)', block, re.M)
        if match:
            version = match.group(1)
        break
print(version)
PYEOF
)
if [ -n "$EXPECTED_VERSION" ] && [ "$LOCK_VERSION" = "$EXPECTED_VERSION" ]; then
  ok "the Python lock file version matches the newest CHANGELOG entry"
else
  not_ok "the Python lock file version matches the newest CHANGELOG entry" "changelog=$EXPECTED_VERSION lock=$LOCK_VERSION"
fi

# Summary
echo ""
echo "# $PASS/$TOTAL tests passed"
echo "1..$TOTAL"

if [ "$FAIL" -gt 0 ]; then
  exit 1
fi
exit 0
