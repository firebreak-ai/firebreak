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

# Helper: extract frontmatter (lines between first --- and second ---)
frontmatter() {
  sed -n '2,/^---$/p' "$1" | sed '$d'
}

echo "TAP version 13"

# --- Tests 1-21: For each of 7 agent files, test existence, name field, and tools field (3 tests per file) ---
for agent_file in "${AGENT_FILES[@]}"; do
  agent_name=$(basename "$agent_file" .md)

  # Test: File exists and is non-empty
  if [ -s "$agent_file" ]; then
    ok "$agent_name file exists and is non-empty"
  else
    not_ok "$agent_name file exists and is non-empty" "file: $agent_file"
  fi

  # Test: Frontmatter name field contains "detector"
  fm=$(frontmatter "$agent_file" 2>/dev/null || true)
  name_val=$(echo "$fm" | grep '^name:' | sed 's/^name:[[:space:]]*//;s/[[:space:]]*$//')
  if echo "$name_val" | grep -qi 'detector'; then
    ok "$agent_name name field contains 'detector'"
  else
    not_ok "$agent_name name field contains 'detector'" "name_val='$name_val'"
  fi

  # Test: Frontmatter tools field lists Read, Grep, Glob without Bash, Write, or Edit
  tools_line=$(echo "$fm" | grep '^tools:')
  has_read=$(echo "$tools_line" | grep -c 'Read' || true)
  has_grep=$(echo "$tools_line" | grep -c 'Grep' || true)
  has_glob=$(echo "$tools_line" | grep -c 'Glob' || true)
  has_bash=$(echo "$tools_line" | grep -c 'Bash' || true)
  has_write=$(echo "$tools_line" | grep -c 'Write' || true)
  has_edit=$(echo "$tools_line" | grep -c 'Edit' || true)
  if [ "$has_read" -gt 0 ] && [ "$has_grep" -gt 0 ] && [ "$has_glob" -gt 0 ] && [ "$has_bash" -eq 0 ] && [ "$has_write" -eq 0 ] && [ "$has_edit" -eq 0 ]; then
    ok "$agent_name tools field lists Read, Grep, Glob without Bash, Write, or Edit"
  else
    not_ok "$agent_name tools field lists Read, Grep, Glob without Bash, Write, or Edit" "tools_line='$tools_line'"
  fi
done

# --- Test 22: All 7 agent files have model: sonnet in frontmatter ---
all_sonnet=true
for agent_file in "${AGENT_FILES[@]}"; do
  fm=$(frontmatter "$agent_file" 2>/dev/null || true)
  if ! echo "$fm" | grep -q 'model:.*sonnet'; then
    all_have_sonnet=false
    break
  fi
done

if [ "$all_sonnet" = true ]; then
  ok "All 7 agents specify model: sonnet"
else
  not_ok "All 7 agents specify model: sonnet"
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
