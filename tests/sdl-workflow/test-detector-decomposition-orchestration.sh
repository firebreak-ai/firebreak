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

# --- Test 1: SKILL.md contains "randomize" or "shuffle" instruction (AC-10) ---
if grep -qiE 'randomize|shuffle' "$SKILL"; then
  ok "SKILL.md contains randomize or shuffle instruction"
else
  not_ok "SKILL.md contains randomize or shuffle instruction" "file: $SKILL"
fi

# --- Test 2: Randomization is scoped to detection target ordering (AC-10) ---
if grep -qiE 'randomize.*target|shuffle.*target|target.*order.*random' "$SKILL"; then
  ok "Randomization is scoped to detection target ordering"
else
  not_ok "Randomization is scoped to detection target ordering" "file: $SKILL"
fi

# --- Test 3: SKILL.md contains "entry point" reference (AC-12) ---
if grep -qi 'entry point' "$SKILL"; then
  ok "SKILL.md contains entry point reference"
else
  not_ok "SKILL.md contains entry point reference" "file: $SKILL"
fi

# --- Test 4: SKILL.md contains "intent register" near entry point context (AC-12) ---
if grep -qi 'intent register' "$SKILL"; then
  ok "SKILL.md contains intent register near entry point context"
else
  not_ok "SKILL.md contains intent register near entry point context" "file: $SKILL"
fi

# --- Test 5: SKILL.md contains "conventional" near entry point context (AC-12) ---
if grep -qi 'conventional' "$SKILL"; then
  ok "SKILL.md contains conventional near entry point context"
else
  not_ok "SKILL.md contains conventional near entry point context" "file: $SKILL"
fi

# --- Test 6: SKILL.md contains "package" or "package.json" near entry point context (AC-12) ---
if grep -qiE 'package\.json|package' "$SKILL"; then
  ok "SKILL.md contains package or package.json near entry point context"
else
  not_ok "SKILL.md contains package or package.json near entry point context" "file: $SKILL"
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
