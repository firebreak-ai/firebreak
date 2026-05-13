#!/usr/bin/env bash
set -uo pipefail

PASS=0
FAIL=0
TOTAL=0

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
PROJECT_ROOT="$(cd "$SCRIPT_DIR/../.." && pwd)"

ok() { TOTAL=$((TOTAL + 1)); PASS=$((PASS + 1)); echo "ok $TOTAL - $1"; }
not_ok() { TOTAL=$((TOTAL + 1)); FAIL=$((FAIL + 1)); echo "not ok $TOTAL - $1"; echo "  $2"; }

# Test 1: no .sh files in old hooks directory
sh_files=$(find "$PROJECT_ROOT/assets/hooks/fbk-sdl-workflow/" -name '*.sh' 2>/dev/null || true)
if [ -z "$sh_files" ]; then
  ok "no .sh files in assets/hooks/fbk-sdl-workflow/"
else
  not_ok "no .sh files in assets/hooks/fbk-sdl-workflow/" "found: $sh_files"
fi

# Test 2: no .py files in old hooks directory
py_files=$(find "$PROJECT_ROOT/assets/hooks/fbk-sdl-workflow/" -name '*.py' 2>/dev/null || true)
if [ -z "$py_files" ]; then
  ok "no .py files in assets/hooks/fbk-sdl-workflow/"
else
  not_ok "no .py files in assets/hooks/fbk-sdl-workflow/" "found: $py_files"
fi

# Test 3: assets/scripts/ is empty or absent
if [ ! -d "$PROJECT_ROOT/assets/scripts/" ] || [ -z "$(ls -A "$PROJECT_ROOT/assets/scripts/" 2>/dev/null)" ]; then
  ok "assets/scripts/ is empty or absent"
else
  not_ok "assets/scripts/ is empty or absent" "directory exists with content"
fi

# Test 4: no .py files in council skills directory
council_py=$(find "$PROJECT_ROOT/assets/skills/fbk-council/" -name '*.py' 2>/dev/null || true)
if [ -z "$council_py" ]; then
  ok "no .py files in assets/skills/fbk-council/"
else
  not_ok "no .py files in assets/skills/fbk-council/" "found: $council_py"
fi

# Test 5: council SKILL.md retained
if [ -f "$PROJECT_ROOT/assets/skills/fbk-council/SKILL.md" ]; then
  ok "assets/skills/fbk-council/SKILL.md retained"
else
  not_ok "assets/skills/fbk-council/SKILL.md retained" "file missing"
fi

# Test 6: assets/fbk-docs/fbk-council/ directory exists
if [ -d "$PROJECT_ROOT/assets/fbk-docs/fbk-council/" ]; then
  ok "assets/fbk-docs/fbk-council/ directory exists"
else
  not_ok "assets/fbk-docs/fbk-council/ directory exists" "directory missing"
fi

# Test 7: consensus-failure.md exists and is non-empty
if [ -s "$PROJECT_ROOT/assets/fbk-docs/fbk-council/consensus-failure.md" ]; then
  ok "consensus-failure.md exists"
else
  not_ok "consensus-failure.md exists" "file missing or empty"
fi

# Test 8: compaction-recovery.md exists and is non-empty
if [ -s "$PROJECT_ROOT/assets/fbk-docs/fbk-council/compaction-recovery.md" ]; then
  ok "compaction-recovery.md exists"
else
  not_ok "compaction-recovery.md exists" "file missing or empty"
fi

# Test 9: ralph-integration.md exists and is non-empty
if [ -s "$PROJECT_ROOT/assets/fbk-docs/fbk-council/ralph-integration.md" ]; then
  ok "ralph-integration.md exists"
else
  not_ok "ralph-integration.md exists" "file missing or empty"
fi

echo ""
echo "$PASS/$TOTAL tests passed"
[[ $FAIL -eq 0 ]] && exit 0 || exit 1
