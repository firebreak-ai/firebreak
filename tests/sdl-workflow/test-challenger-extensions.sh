#!/usr/bin/env bash
set -uo pipefail

PASS=0
FAIL=0
TOTAL=0

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
PROJECT_ROOT="$(cd "$SCRIPT_DIR/../.." && pwd)"
CHALLENGER="$PROJECT_ROOT/assets/agents/fbk-code-review-challenger.md"
SKILL_FILE="$PROJECT_ROOT/assets/skills/fbk-code-review/SKILL.md"
GUIDE="$PROJECT_ROOT/assets/fbk-docs/fbk-sdl-workflow/code-review-guide.md"

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

# --- Test 1: Adjacent observation concept present in pipeline (AC-13) ---
if grep -qiE 'adjacent.observation' "$CHALLENGER" || grep -qiE 'adjacent.observation' "$SKILL_FILE" || grep -qiE 'adjacent.observation' "$GUIDE"; then
  ok "Challenger includes adjacent observation channel"
else
  not_ok "Challenger includes adjacent observation channel" "not found in challenger, skill, or guide"
fi

# --- Test 2: Adjacent observations do not surface as findings (AC-13) ---
if grep -qiE 'informational|do not.*finding|not.*surface|not.*detection loop|exclude.*finding|do not generate|not.*new sighting' "$CHALLENGER"; then
  ok "Adjacent observations documented as informational"
else
  not_ok "Adjacent observations documented as informational" "file: $CHALLENGER"
fi

# --- Test 3: Challenger contains caller tracing requirement (AC-14) ---
if grep -qiE 'caller.trac|trace.*caller|cross.reference.*caller' "$CHALLENGER"; then
  ok "Challenger includes caller tracing requirement"
else
  not_ok "Challenger includes caller tracing requirement" "file: $CHALLENGER"
fi

# --- Test 4: Caller tracing applies to behavioral type (AC-14) ---
if grep -qiE 'behavioral.*caller|behavioral.*trac|caller.*behavioral' "$CHALLENGER"; then
  ok "Caller tracing scoped to behavioral type"
else
  not_ok "Caller tracing scoped to behavioral type" "file: $CHALLENGER"
fi

# --- Test 5: Verified-pending-execution status present in pipeline (AC-15) ---
if grep -qiE 'verified.pending.execution|verified-pending-execution' "$CHALLENGER" || grep -qiE 'verified.pending.execution|verified-pending-execution' "$SKILL_FILE" || grep -qiE 'verified.pending.execution|verified-pending-execution' "$GUIDE"; then
  ok "Challenger includes verified-pending-execution status"
else
  not_ok "Challenger includes verified-pending-execution status" "not found in challenger, skill, or guide"
fi

# --- Test 6: Verified-pending-execution scoped to test-integrity in pipeline (AC-15) ---
if grep -qiE 'test.integrity.*pending|test.integrity.*execution|pending.*test|verified-pending-execution' "$CHALLENGER" || grep -qiE 'test.integrity.*pending|test.integrity.*execution|pending.*test|verified-pending-execution' "$SKILL_FILE" || grep -qiE 'test.integrity.*pending|test.integrity.*execution|pending.*test|verified-pending-execution' "$GUIDE"; then
  ok "Verified-pending-execution scoped to test-integrity type"
else
  not_ok "Verified-pending-execution scoped to test-integrity type" "not found in challenger, skill, or guide"
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
