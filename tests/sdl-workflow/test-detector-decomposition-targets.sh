#!/bin/bash
# Test: Detector decomposition detection target exclusivity
# Verifies that each detection target appears in exactly one Tier 1 group agent file
# and that no target is duplicated across groups (AC-19).

set -euo pipefail

PROJECT_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"

# TAP functions
PASS=0
FAIL=0
TOTAL=0

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

# Define all 7 agent file paths
G1="$PROJECT_ROOT/assets/agents/fbk-t1-value-abstraction-detector.md"
G2="$PROJECT_ROOT/assets/agents/fbk-t1-dead-code-detector.md"
G3="$PROJECT_ROOT/assets/agents/fbk-t1-signal-loss-detector.md"
G4="$PROJECT_ROOT/assets/agents/fbk-t1-behavioral-drift-detector.md"
G5="$PROJECT_ROOT/assets/agents/fbk-t1-function-boundaries-detector.md"
G6="$PROJECT_ROOT/assets/agents/fbk-t1-cross-boundary-structure-detector.md"
G7="$PROJECT_ROOT/assets/agents/fbk-t1-missing-safeguards-detector.md"

# Helper function to check if a detection target appears in exactly one agent file
check_target_exclusive() {
  local target="$1"
  local expected_file="$2"
  local agent_files=("$G1" "$G2" "$G3" "$G4" "$G5" "$G6" "$G7")
  local match_count=0
  local matched_file=""

  # Count matches across all 7 agent files
  for file in "${agent_files[@]}"; do
    if grep -qi "$target" "$file" 2>/dev/null; then
      match_count=$((match_count + 1))
      matched_file="$file"
    fi
  done

  if [ "$match_count" -eq 1 ] && [ "$matched_file" = "$expected_file" ]; then
    ok "target exclusive: $target"
  else
    not_ok "target exclusive: $target" "match_count=$match_count matched_file=$matched_file expected=$expected_file"
  fi
}

# Group 1: value-abstraction targets
check_target_exclusive "bare literal" "$G1"
check_target_exclusive "hardcoded coupling" "$G1"
check_target_exclusive "string-based type discrimination" "$G1"

# Group 2: dead-code targets
check_target_exclusive "dead infrastructure" "$G2"
check_target_exclusive "never connected" "$G2"
check_target_exclusive "dead code after field" "$G2"
check_target_exclusive "dead conditional" "$G2"
check_target_exclusive "logical redundancy" "$G2"

# Group 3: signal-loss targets
check_target_exclusive "sentinel" "$G3"
check_target_exclusive "context discard" "$G3"
check_target_exclusive "silent error discard" "$G3"

# Group 4: behavioral-drift targets
check_target_exclusive "comment-code drift" "$G4"
check_target_exclusive "semantic drift" "$G4"
check_target_exclusive "dual-path verification" "$G4"

# Group 5: function-boundaries targets
check_target_exclusive "mixed logic and side effects" "$G5"
check_target_exclusive "ambient state" "$G5"
check_target_exclusive "non-importable" "$G5"

# Group 6: cross-boundary-structure targets
check_target_exclusive "caller re-implementation" "$G6"
check_target_exclusive "parallel collection" "$G6"
check_target_exclusive "multi-responsibility" "$G6"
check_target_exclusive "composition opacity" "$G6"

# Group 7: missing-safeguards targets
check_target_exclusive "surface-level fix" "$G7"
check_target_exclusive "unbounded data structure" "$G7"
check_target_exclusive "migration" "$G7"
check_target_exclusive "batch transaction" "$G7"

# TAP summary
echo "1..$TOTAL"
if [ "$FAIL" -gt 0 ]; then
  exit 1
fi
