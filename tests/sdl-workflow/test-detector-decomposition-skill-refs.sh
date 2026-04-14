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

# --- Test 1: SKILL.md exists and is non-empty ---
if [ -s "$SKILL" ]; then
  ok "SKILL.md exists and is non-empty"
else
  not_ok "SKILL.md exists and is non-empty" "file: $SKILL"
fi

# --- Test 2: SKILL.md references 'value-abstraction' T1 group agent ---
if grep -q 'value-abstraction' "$SKILL"; then
  ok "SKILL.md references 'value-abstraction' T1 group agent"
else
  not_ok "SKILL.md references 'value-abstraction' T1 group agent"
fi

# --- Test 3: SKILL.md references 'dead-code' T1 group agent ---
if grep -q 'dead-code' "$SKILL"; then
  ok "SKILL.md references 'dead-code' T1 group agent"
else
  not_ok "SKILL.md references 'dead-code' T1 group agent"
fi

# --- Test 4: SKILL.md references 'signal-loss' T1 group agent ---
if grep -q 'signal-loss' "$SKILL"; then
  ok "SKILL.md references 'signal-loss' T1 group agent"
else
  not_ok "SKILL.md references 'signal-loss' T1 group agent"
fi

# --- Test 5: SKILL.md references 'behavioral-drift' T1 group agent ---
if grep -q 'behavioral-drift' "$SKILL"; then
  ok "SKILL.md references 'behavioral-drift' T1 group agent"
else
  not_ok "SKILL.md references 'behavioral-drift' T1 group agent"
fi

# --- Test 6: SKILL.md references 'function-boundaries' T1 group agent ---
if grep -q 'function-boundaries' "$SKILL"; then
  ok "SKILL.md references 'function-boundaries' T1 group agent"
else
  not_ok "SKILL.md references 'function-boundaries' T1 group agent"
fi

# --- Test 7: SKILL.md references 'cross-boundary-structure' T1 group agent ---
if grep -q 'cross-boundary-structure' "$SKILL"; then
  ok "SKILL.md references 'cross-boundary-structure' T1 group agent"
else
  not_ok "SKILL.md references 'cross-boundary-structure' T1 group agent"
fi

# --- Test 8: SKILL.md references 'missing-safeguards' T1 group agent ---
if grep -q 'missing-safeguards' "$SKILL"; then
  ok "SKILL.md references 'missing-safeguards' T1 group agent"
else
  not_ok "SKILL.md references 'missing-safeguards' T1 group agent"
fi

# --- Test 9: Agent Team section references Tier 1 agents ---
if grep -qi 'Tier 1\|per-group\|T1' "$SKILL"; then
  ok "Agent Team section references Tier 1 agents"
else
  not_ok "Agent Team section references Tier 1 agents"
fi

# --- Test 10: Agent Team section references Deduplicator agent ---
if grep -qi 'Deduplicator' "$SKILL"; then
  ok "Agent Team section references Deduplicator agent"
else
  not_ok "Agent Team section references Deduplicator agent"
fi

# --- Test 11: Agent Team section references Challenger agent ---
if grep -qi 'Challenger' "$SKILL"; then
  ok "Agent Team section references Challenger agent"
else
  not_ok "Agent Team section references Challenger agent"
fi

# --- Test 12: Agent Team section references Intent Path Tracer agent ---
if grep -qi 'Intent Path Tracer\|intent-path-tracer' "$SKILL"; then
  ok "Agent Team section references Intent Path Tracer agent"
else
  not_ok "Agent Team section references Intent Path Tracer agent"
fi

# --- Test 13: Agent Team section references Test Reviewer agent ---
if grep -qi 'Test Reviewer\|test-reviewer' "$SKILL"; then
  ok "Agent Team section references Test Reviewer agent"
else
  not_ok "Agent Team section references Test Reviewer agent"
fi

# --- Test 14: SKILL.md specifies identical code payload ordering ---
if grep -qiE 'identical.*(payload|code).*order|payload.*identical.*order' "$SKILL"; then
  ok "SKILL.md specifies identical code payload ordering"
else
  not_ok "SKILL.md specifies identical code payload ordering"
fi

# --- Test 15: Broad-Scope Reviews section updated with preset per-unit or agent complement ---
if grep -qiE 'preset.*per.unit|per.unit.*preset|agent.*complement.*unit' "$SKILL"; then
  ok "Broad-Scope Reviews section updated with preset per-unit or agent complement"
else
  not_ok "Broad-Scope Reviews section updated with preset per-unit or agent complement"
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
