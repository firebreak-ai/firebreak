#!/usr/bin/env bash
set -uo pipefail

PASS=0
FAIL=0
TOTAL=0

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
PROJECT_ROOT="$(cd "$SCRIPT_DIR/../.." && pwd)"

# Define all 7 agent file paths
AGENT_VALUE_ABSTRACTION="$PROJECT_ROOT/assets/agents/fbk-t1-value-abstraction-detector.md"
AGENT_DEAD_CODE="$PROJECT_ROOT/assets/agents/fbk-t1-dead-code-detector.md"
AGENT_SIGNAL_LOSS="$PROJECT_ROOT/assets/agents/fbk-t1-signal-loss-detector.md"
AGENT_BEHAVIORAL_DRIFT="$PROJECT_ROOT/assets/agents/fbk-t1-behavioral-drift-detector.md"
AGENT_FUNCTION_BOUNDARIES="$PROJECT_ROOT/assets/agents/fbk-t1-function-boundaries-detector.md"
AGENT_CROSS_BOUNDARY="$PROJECT_ROOT/assets/agents/fbk-t1-cross-boundary-structure-detector.md"
AGENT_MISSING_SAFEGUARDS="$PROJECT_ROOT/assets/agents/fbk-t1-missing-safeguards-detector.md"

# Array of all agent files for iteration
AGENT_FILES=(
  "$AGENT_VALUE_ABSTRACTION"
  "$AGENT_DEAD_CODE"
  "$AGENT_SIGNAL_LOSS"
  "$AGENT_BEHAVIORAL_DRIFT"
  "$AGENT_FUNCTION_BOUNDARIES"
  "$AGENT_CROSS_BOUNDARY"
  "$AGENT_MISSING_SAFEGUARDS"
)

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

# --- Tests 1-14: For each of 7 agent files, test enumeration and cross-instance instructions (2 tests per file) ---
for agent_file in "${AGENT_FILES[@]}"; do
  agent_name=$(basename "$agent_file" .md)

  # Test: Contains enumeration instruction
  if grep -qiE 'clean files|summary line|files.*issues.*found|enumerat' "$agent_file"; then
    ok "$agent_name contains enumeration instruction"
  else
    not_ok "$agent_name contains enumeration instruction" "file: $agent_file"
  fi

  # Test: Contains cross-instance instruction
  if grep -qiE 'after completing.*detection|search the full project|cross-instance|phase 2' "$agent_file"; then
    ok "$agent_name contains cross-instance instruction"
  else
    not_ok "$agent_name contains cross-instance instruction" "file: $agent_file"
  fi
done

# --- Summary ---
echo ""
echo "1..$TOTAL"
echo "# $PASS/$TOTAL tests passed"
if [ "$FAIL" -gt 0 ]; then
  echo "# FAIL $FAIL"
  exit 1
fi
exit 0
