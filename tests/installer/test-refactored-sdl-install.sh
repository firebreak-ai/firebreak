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

setup_mock_home() {
  MOCK_HOME=$(mktemp -d)
  TEMP_DIRS+=("$MOCK_HOME")
}

cleanup() {
  for d in "${TEMP_DIRS[@]:-}"; do
    rm -rf "$d"
  done
}

trap cleanup EXIT

echo "TAP version 13"

# Setup
setup_mock_home

# Phase 1: Install
HOME="$MOCK_HOME" bash "$INSTALL_SCRIPT" >/dev/null 2>&1
INSTALL_EXIT=$?

# T1: Installer exits 0
if [ "$INSTALL_EXIT" -eq 0 ]; then
  ok "Installer exits 0"
else
  not_ok "Installer exits 0" "exit code: $INSTALL_EXIT"
fi

# T2: fbk-scripts tree present
if [ -d "$MOCK_HOME/.claude/fbk-scripts" ]; then
  ok "fbk-scripts tree present"
else
  not_ok "fbk-scripts tree present" "directory not found at $MOCK_HOME/.claude/fbk-scripts"
fi

# T3-T8: New skills installed
if [ -f "$MOCK_HOME/.claude/skills/fbk-intent/SKILL.md" ]; then
  ok "fbk-intent skill installed"
else
  not_ok "fbk-intent skill installed" "file not found"
fi

if [ -f "$MOCK_HOME/.claude/skills/fbk-design/SKILL.md" ]; then
  ok "fbk-design skill installed"
else
  not_ok "fbk-design skill installed" "file not found"
fi

if [ -f "$MOCK_HOME/.claude/skills/fbk-grilling/SKILL.md" ]; then
  ok "fbk-grilling skill installed"
else
  not_ok "fbk-grilling skill installed" "file not found"
fi

if [ -f "$MOCK_HOME/.claude/skills/fbk-fresh-eyes/SKILL.md" ]; then
  ok "fbk-fresh-eyes skill installed"
else
  not_ok "fbk-fresh-eyes skill installed" "file not found"
fi

if [ -f "$MOCK_HOME/.claude/skills/fbk-quality-scan/SKILL.md" ]; then
  ok "fbk-quality-scan skill installed"
else
  not_ok "fbk-quality-scan skill installed" "file not found"
fi

if [ -f "$MOCK_HOME/.claude/skills/fbk-test-review/SKILL.md" ]; then
  ok "fbk-test-review skill installed"
else
  not_ok "fbk-test-review skill installed" "file not found"
fi

# T9-T11: New agents installed
if [ -f "$MOCK_HOME/.claude/agents/fbk-product-author.md" ]; then
  ok "fbk-product-author agent installed"
else
  not_ok "fbk-product-author agent installed" "file not found"
fi

if [ -f "$MOCK_HOME/.claude/agents/fbk-architect.md" ]; then
  ok "fbk-architect agent installed"
else
  not_ok "fbk-architect agent installed" "file not found"
fi

if [ -f "$MOCK_HOME/.claude/agents/fbk-fresh-eyes-reviewer.md" ]; then
  ok "fbk-fresh-eyes-reviewer agent installed"
else
  not_ok "fbk-fresh-eyes-reviewer agent installed" "file not found"
fi

# T12-T14: New routed docs installed
if [ -f "$MOCK_HOME/.claude/fbk-docs/fbk-sdl-workflow/intent-guide.md" ]; then
  ok "fbk-sdl-workflow/intent-guide.md installed"
else
  not_ok "fbk-sdl-workflow/intent-guide.md installed" "file not found"
fi

if [ -f "$MOCK_HOME/.claude/fbk-docs/fbk-sdl-workflow/design-guide.md" ]; then
  ok "fbk-sdl-workflow/design-guide.md installed"
else
  not_ok "fbk-sdl-workflow/design-guide.md installed" "file not found"
fi

if [ -f "$MOCK_HOME/.claude/fbk-docs/fbk-sdl-workflow/capability-entry.md" ]; then
  ok "fbk-sdl-workflow/capability-entry.md installed"
else
  not_ok "fbk-sdl-workflow/capability-entry.md installed" "file not found"
fi

# T15: No installed asset body contains 'assets/' path prefix
LEAKED_PATHS=$(grep -rl '\bassets/' "$MOCK_HOME/.claude" --include="*.md" --include="*.py" 2>/dev/null | head -5)
if [ -z "$LEAKED_PATHS" ]; then
  ok "No installed asset body contains 'assets/' path prefix"
else
  not_ok "No installed asset body contains 'assets/' path prefix" "leaked in: $LEAKED_PATHS"
fi

# Phase 2: Uninstall
HOME="$MOCK_HOME" bash "$INSTALL_SCRIPT" --uninstall >/dev/null 2>&1

# T16: fbk-scripts tree gone after uninstall
if [ ! -d "$MOCK_HOME/.claude/fbk-scripts" ]; then
  ok "fbk-scripts tree absent after uninstall"
else
  not_ok "fbk-scripts tree absent after uninstall" "directory still exists"
fi

# Summary
echo ""
echo "# $PASS/$TOTAL tests passed"
echo "1..$TOTAL"

if [ "$FAIL" -gt 0 ]; then
  exit 1
fi
exit 0
