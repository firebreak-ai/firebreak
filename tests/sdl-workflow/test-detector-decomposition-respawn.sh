#!/usr/bin/env bash
set -uo pipefail

PASS=0
FAIL=0
TOTAL=0

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
PROJECT_ROOT="$(cd "$SCRIPT_DIR/../.." && pwd)"

SKILL="$PROJECT_ROOT/assets/skills/fbk-code-review/SKILL.md"

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

# --- Test 1: SKILL.md contains "respawn" reference (AC-20) ---
if grep -qi 'respawn' "$SKILL"; then
  ok "SKILL.md contains respawn reference"
else
  not_ok "SKILL.md contains respawn reference" "file: $SKILL"
fi

# --- Test 2: SKILL.md contains "verified" near respawn context (AC-20) ---
if grep -qiE 'verified.*sighting|sighting.*verified' "$SKILL"; then
  ok "SKILL.md contains verified near respawn context"
else
  not_ok "SKILL.md contains verified near respawn context" "file: $SKILL"
fi

# --- Test 3: SKILL.md contains "info" level gating near respawn context (AC-20) ---
if grep -qiE 'above info|info.*level|info.*only' "$SKILL"; then
  ok "SKILL.md contains info level gating near respawn context"
else
  not_ok "SKILL.md contains info level gating near respawn context" "file: $SKILL"
fi

# --- Test 4: SKILL.md contains "5 repetitions" or "maximum 5" or "5 rounds" per-agent limit (AC-20) ---
if grep -qiE 'maximum 5|5 repetition|5 round' "$SKILL"; then
  ok "SKILL.md contains maximum repetitions per-agent limit"
else
  not_ok "SKILL.md contains maximum repetitions per-agent limit" "file: $SKILL"
fi

# --- Summary ---
echo ""
echo "1..$TOTAL"
echo "# $PASS/$TOTAL tests passed"
if [ "$FAIL" -gt 0 ]; then
  echo "# FAIL $FAIL"
  exit 1
fi
exit 0
