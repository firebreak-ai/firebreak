#!/bin/bash
# Test: Detector decomposition target coverage
# Verifies that every detection target from pre-decomposition documents appears
# in at least one post-decomposition agent-facing document, ensuring no detection
# capability is lost during decomposition.

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

# Define paths to post-decomposition agent-facing documents
T1_LOGIC_DETECTOR="$PROJECT_ROOT/assets/agents/fbk-t1-logic-detector.md"
T1_ASYNC_DETECTOR="$PROJECT_ROOT/assets/agents/fbk-t1-async-detector.md"
T1_STATE_DETECTOR="$PROJECT_ROOT/assets/agents/fbk-t1-state-detector.md"
T1_ERROR_DETECTOR="$PROJECT_ROOT/assets/agents/fbk-t1-error-detector.md"
T1_INTERFACE_DETECTOR="$PROJECT_ROOT/assets/agents/fbk-t1-interface-detector.md"
T1_TEST_DETECTOR="$PROJECT_ROOT/assets/agents/fbk-t1-test-detector.md"
T1_PATTERN_DETECTOR="$PROJECT_ROOT/assets/agents/fbk-t1-pattern-detector.md"
INTENT_TRACER="$PROJECT_ROOT/assets/agents/fbk-intent-path-tracer.md"
TEST_REVIEWER="$PROJECT_ROOT/assets/agents/fbk-cr-test-reviewer.md"
QUALITY="$PROJECT_ROOT/assets/fbk-docs/fbk-design-guidelines/quality-detection.md"
AI_FAILURE="$PROJECT_ROOT/assets/fbk-docs/fbk-sdl-workflow/ai-failure-modes.md"
GUIDE="$PROJECT_ROOT/assets/fbk-docs/fbk-sdl-workflow/code-review-guide.md"

# Combine all docs for grep queries
ALL_DOCS="$T1_LOGIC_DETECTOR $T1_ASYNC_DETECTOR $T1_STATE_DETECTOR $T1_ERROR_DETECTOR $T1_INTERFACE_DETECTOR $T1_TEST_DETECTOR $T1_PATTERN_DETECTOR $INTENT_TRACER $TEST_REVIEWER $QUALITY $AI_FAILURE $GUIDE"

# Helper function to check if a detection target appears in any agent-facing document
check_target() {
  local found=0
  for doc in $ALL_DOCS; do
    if grep -qi "$1" "$doc" 2>/dev/null; then
      found=1
      break
    fi
  done
  if [ "$found" -eq 1 ]; then
    ok "detection target present: $1"
  else
    not_ok "detection target present: $1" "not found in any agent-facing document"
  fi
}

# Tests from ai-failure-modes.md targets (14 items)
check_target "bare literal"
check_target "hardcoded coupling"
check_target "never connected"
check_target "name-assertion mismatch"
check_target "surface-level fix"
check_target "non-enforcing test"
check_target "dead infrastructure"
check_target "comment-code drift"
check_target "sentinel"
check_target "context discard"
check_target "string-based type discrimination"
check_target "semantically incoherent"
check_target "mock permissiveness"
check_target "dead conditional"

# Tests from quality-detection.md targets (15 items)
check_target "mixed logic and side effects"
check_target "ambient state"
check_target "non-importable"
check_target "multi-responsibility"
check_target "caller re-implementation"
check_target "composition opacity"
check_target "parallel collection"
check_target "semantic drift"
check_target "silent error discard"
check_target "context discard"
check_target "string-based type discrimination"
check_target "dual-path verification"
check_target "test-production string"
check_target "dead code after field"
check_target "unbounded data structure"
check_target "migration"
check_target "idempoten"
check_target "batch transaction"
check_target "logical redundancy"

# TAP summary
echo "1..$TOTAL"
if [ "$FAIL" -gt 0 ]; then
  exit 1
fi
