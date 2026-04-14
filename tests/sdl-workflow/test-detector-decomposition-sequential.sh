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

# --- Test 1: SKILL.md contains sequential execution language (AC-18) ---
if grep -qiE 'sequential|behavioral-only.*structural.*test-only' "$SKILL"; then
  ok "SKILL.md contains sequential execution language"
else
  not_ok "SKILL.md contains sequential execution language" "file: $SKILL"
fi

# --- Test 2: SKILL.md contains per-wave dedup and Challenger language (AC-18) ---
if grep -qiE 'per.*wave|each wave|wave.*dedup|wave.*challenger' "$SKILL"; then
  ok "SKILL.md contains per-wave dedup and Challenger language"
else
  not_ok "SKILL.md contains per-wave dedup and Challenger language" "file: $SKILL"
fi

# --- Test 3: SKILL.md contains cross-preset dedup language (AC-18) ---
if grep -qiE 'cross-preset.*dedup|cross.*preset.*finding' "$SKILL"; then
  ok "SKILL.md contains cross-preset dedup language"
else
  not_ok "SKILL.md contains cross-preset dedup language" "file: $SKILL"
fi

# --- Test 4: SKILL.md specifies cross-preset dedup is inline or orchestrator-level (AC-18) ---
if grep -qiE 'inline|orchestrator.*level|no.*agent.*spawn' "$SKILL"; then
  ok "SKILL.md specifies cross-preset dedup is inline or orchestrator-level"
else
  not_ok "SKILL.md specifies cross-preset dedup is inline or orchestrator-level" "file: $SKILL"
fi

# --- Test 5: SKILL.md contains single-agent Deduplicator bypass (AC-18) ---
if grep -qiE 'single.*agent.*skip|single.*agent.*bypass|skip.*dedup' "$SKILL"; then
  ok "SKILL.md contains single-agent Deduplicator bypass"
else
  not_ok "SKILL.md contains single-agent Deduplicator bypass" "file: $SKILL"
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
