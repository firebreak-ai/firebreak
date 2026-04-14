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

# --- Test 1: SKILL.md contains behavioral-only preset name (AC-16) ---
if grep -q 'behavioral-only' "$SKILL"; then
  ok "SKILL.md contains behavioral-only preset name"
else
  not_ok "SKILL.md contains behavioral-only preset name" "file: $SKILL"
fi

# --- Test 2: SKILL.md contains structural preset name (AC-16) ---
if grep -q 'structural' "$SKILL"; then
  ok "SKILL.md contains structural preset name"
else
  not_ok "SKILL.md contains structural preset name" "file: $SKILL"
fi

# --- Test 3: SKILL.md contains test-only preset name (AC-16) ---
if grep -q 'test-only' "$SKILL"; then
  ok "SKILL.md contains test-only preset name"
else
  not_ok "SKILL.md contains test-only preset name" "file: $SKILL"
fi

# --- Test 4: SKILL.md contains full preset name in preset context (AC-16) ---
if grep -qE '\bfull\b' "$SKILL"; then
  ok "SKILL.md contains full preset name"
else
  not_ok "SKILL.md contains full preset name" "file: $SKILL"
fi

# --- Test 5: SKILL.md specifies behavioral-only as default (AC-16) ---
if grep -qiE 'default.*behavioral-only|behavioral-only.*default' "$SKILL"; then
  ok "SKILL.md specifies behavioral-only as default"
else
  not_ok "SKILL.md specifies behavioral-only as default" "file: $SKILL"
fi

# --- Test 6: SKILL.md contains preset-to-group mapping (AC-16) ---
if grep -qiE 'groups? 1|groups? 2|groups? 3|groups? 4|value-abstraction.*dead-code|behavioral-only.*groups' "$SKILL"; then
  ok "SKILL.md contains preset-to-group mapping"
else
  not_ok "SKILL.md contains preset-to-group mapping" "file: $SKILL"
fi

# --- Test 7: SKILL.md contains per-group toggle or override language (AC-17) ---
if grep -qiE 'per-group toggle|toggle.*override|override.*preset|enable.*disable.*group' "$SKILL"; then
  ok "SKILL.md contains per-group toggle or override language"
else
  not_ok "SKILL.md contains per-group toggle or override language" "file: $SKILL"
fi

# --- Test 8: SKILL.md contains preset combination example or description (AC-17) ---
if grep -qiE 'behavioral-only.*test-reviewer|override|individual group' "$SKILL"; then
  ok "SKILL.md contains preset combination example or description"
else
  not_ok "SKILL.md contains preset combination example or description" "file: $SKILL"
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
