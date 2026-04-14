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

# --- Test 1: SKILL.md contains batch size guidance (AC-09) ---
if grep -qiE 'per 5 sighting|5 sighting' "$SKILL"; then
  ok "SKILL.md contains batch size guidance (5 sightings)"
else
  not_ok "SKILL.md contains batch size guidance (5 sightings)" "file: $SKILL"
fi

# --- Test 2: SKILL.md contains detection category grouping guidance (AC-09) ---
if grep -qi 'detection category\|originating.*category\|grouped by' "$SKILL"; then
  ok "SKILL.md contains detection category grouping guidance"
else
  not_ok "SKILL.md contains detection category grouping guidance" "file: $SKILL"
fi

# --- Test 3: SKILL.md contains parallel spawning guidance (AC-09) ---
if grep -qi 'parallel' "$SKILL"; then
  ok "SKILL.md contains parallel spawning guidance"
else
  not_ok "SKILL.md contains parallel spawning guidance" "file: $SKILL"
fi

# --- Test 4: SKILL.md contains preset wave scoping guidance (AC-09) ---
if grep -qiE 'per.*wave|wave.*challenger' "$SKILL"; then
  ok "SKILL.md contains preset wave scoping guidance"
else
  not_ok "SKILL.md contains preset wave scoping guidance" "file: $SKILL"
fi

# --- Test 5: SKILL.md Challenger step references deduplicated sightings (AC-09) ---
if grep -qiE 'deduplicated.*sighting.*challenger|challenger.*deduplicated|scoped.*wave.*deduplicated' "$SKILL"; then
  ok "SKILL.md Challenger step references deduplicated sightings"
else
  not_ok "SKILL.md Challenger step references deduplicated sightings" "file: $SKILL"
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
