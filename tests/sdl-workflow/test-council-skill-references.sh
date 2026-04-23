#!/usr/bin/env bash
set -uo pipefail

PASS=0
FAIL=0
TOTAL=0

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
PROJECT_ROOT="$(cd "$SCRIPT_DIR/../.." && pwd)"
SKILL="$PROJECT_ROOT/assets/skills/fbk-council/SKILL.md"

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

echo "TAP version 13"

# Test 1: SKILL.md has session-manager dispatcher reference
session_manager_count=$(grep -c 'fbk-scripts/fbk\.py session-manager' "$SKILL" 2>/dev/null || true)
if [ "$session_manager_count" -ge 1 ]; then
  ok "SKILL.md has session-manager dispatcher ref (count=$session_manager_count)"
else
  not_ok "SKILL.md has session-manager dispatcher ref" "Expected >= 1, found: $session_manager_count"
fi

# Test 2: SKILL.md has session-logger dispatcher reference
session_logger_count=$(grep -c 'fbk-scripts/fbk\.py session-logger' "$SKILL" 2>/dev/null || true)
if [ "$session_logger_count" -ge 1 ]; then
  ok "SKILL.md has session-logger dispatcher ref (count=$session_logger_count)"
else
  not_ok "SKILL.md has session-logger dispatcher ref" "Expected >= 1, found: $session_logger_count"
fi

# Test 3: SKILL.md has no old session- script references
old_session_count=$(grep -c '~/.claude/skills/fbk-council/session-' "$SKILL" 2>/dev/null || true)
if [ "$old_session_count" -eq 0 ]; then
  ok "SKILL.md has no old session- script refs"
else
  not_ok "SKILL.md has no old session- script refs" "Expected 0, found: $old_session_count"
fi

# Test 4: SKILL.md has no old ralph- script references
old_ralph_count=$(grep -c '~/.claude/skills/fbk-council/ralph-' "$SKILL" 2>/dev/null || true)
if [ "$old_ralph_count" -eq 0 ]; then
  ok "SKILL.md has no old ralph- script refs"
else
  not_ok "SKILL.md has no old ralph- script refs" "Expected 0, found: $old_ralph_count"
fi

echo "1..$TOTAL"

if [ "$FAIL" -gt 0 ]; then
  exit 1
fi
