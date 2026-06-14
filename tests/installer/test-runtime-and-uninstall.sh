#!/usr/bin/env bash
# Runtime lifecycle of a real install: the hook router captures through the
# installed tree, the per-project gate holds, and uninstall removes everything —
# including files generated *after* install when the tool is actually used.
#
# This complements test-install.sh (fresh-install fidelity) and
# test-refactored-sdl-install.sh (asset presence). Those install and immediately
# uninstall, so they never exercise the post-use state: once fbk.py runs it
# writes __pycache__ bytecode into the install tree, which is not in the manifest
# and once orphaned the whole fbk-scripts directory the same way a stray venv did.
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

cleanup() {
  for d in "${TEMP_DIRS[@]:-}"; do
    rm -rf "$d"
  done
}
trap cleanup EXIT

echo "TAP version 13"

# uv is the installer's hard prerequisite; skip cleanly if the runner lacks it.
if ! command -v uv >/dev/null 2>&1; then
  echo "1..0 # SKIP uv not available"
  exit 0
fi

MOCK_HOME="$(mktemp -d)"
TEMP_DIRS+=("$MOCK_HOME")
TARGET="$MOCK_HOME/.claude"

# Global install (TARGET == $HOME/.claude keeps the $HOME-rooted hook paths).
if HOME="$MOCK_HOME" bash "$INSTALL_SCRIPT" --source "$PROJECT_ROOT/assets" --target "$TARGET" >/dev/null 2>&1; then
  ok "install completes"
else
  not_ok "install completes" "installer exited non-zero"
  echo "1..$TOTAL"
  exit 1
fi

# --- Hook router captures through the installed tree, in a MARKED project ---
PROJ="$MOCK_HOME/proj"
mkdir -p "$PROJ/.claude/automation"
: > "$PROJ/.claude/automation/.fbk-managed"
EVENT='{"hook_event_name":"PostToolUse","tool_name":"Edit","tool_input":{"file_path":"x"}}'
( cd "$PROJ" && echo "$EVENT" | HOME="$MOCK_HOME" python3 "$TARGET/fbk-scripts/fbk/capture/hook_router.py" ) >/dev/null 2>&1
router_rc=$?

if [ "$router_rc" -eq 0 ]; then
  ok "hook router exits 0 (fail-silent contract)"
else
  not_ok "hook router exits 0 (fail-silent contract)" "rc=$router_rc"
fi

if [ -s "$PROJ/.fbk-capture/events.jsonl" ]; then
  ok "marked project captures an event to .fbk-capture/events.jsonl"
else
  not_ok "marked project captures an event to .fbk-capture/events.jsonl" "events file missing or empty"
fi

# --- Per-project gate: an UNMARKED project must not capture ---
PROJ_U="$MOCK_HOME/proj-unmarked"
mkdir -p "$PROJ_U"
( cd "$PROJ_U" && echo "$EVENT" | HOME="$MOCK_HOME" python3 "$TARGET/fbk-scripts/fbk/capture/hook_router.py" ) >/dev/null 2>&1
if [ ! -d "$PROJ_U/.fbk-capture" ]; then
  ok "unmarked project does not capture"
else
  not_ok "unmarked project does not capture" ".fbk-capture/ created without a sentinel"
fi

# --- Use the install, then uninstall: nothing may be left behind ---
# Running the dispatcher generates __pycache__ bytecode in the install tree,
# reproducing real operator use before removal.
HOME="$MOCK_HOME" python3 "$TARGET/fbk-scripts/fbk.py" >/dev/null 2>&1 || true

if [ -n "$(find "$TARGET/fbk-scripts" -type d -name __pycache__ -print -quit)" ]; then
  ok "use generates bytecode caches in the install tree (precondition)"
else
  not_ok "use generates bytecode caches in the install tree (precondition)" "no __pycache__ produced; test cannot exercise the orphan path"
fi

if HOME="$MOCK_HOME" bash "$INSTALL_SCRIPT" --uninstall --target "$TARGET" >/dev/null 2>&1; then
  ok "uninstall completes"
else
  not_ok "uninstall completes" "uninstaller exited non-zero"
fi

if [ ! -d "$TARGET/fbk-scripts" ]; then
  ok "fbk-scripts tree fully removed after use + uninstall"
else
  not_ok "fbk-scripts tree fully removed after use + uninstall" "orphaned: $(find "$TARGET/fbk-scripts" | head -5 | tr '\n' ' ')"
fi

if [ ! -f "$TARGET/.firebreak-manifest.json" ]; then
  ok "manifest removed"
else
  not_ok "manifest removed" "manifest still present"
fi

echo ""
echo "# $PASS/$TOTAL tests passed"
echo "1..$TOTAL"

if [ "$FAIL" -gt 0 ]; then
  exit 1
fi
exit 0
