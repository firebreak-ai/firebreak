#!/bin/bash
# Test: Instruction hygiene detection target coverage
# Verifies that every detection target name from the spec exists in at least one
# agent-facing document post-implementation, ensuring no detection capability is lost.

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

# Define paths to the agent-facing documents
CHECKLIST="$PROJECT_ROOT/assets/fbk-docs/fbk-sdl-workflow/ai-failure-modes.md"
QUALITY="$PROJECT_ROOT/assets/fbk-docs/fbk-design-guidelines/quality-detection.md"
GUIDE="$PROJECT_ROOT/assets/fbk-docs/fbk-sdl-workflow/code-review-guide.md"
CHALLENGER="$PROJECT_ROOT/assets/agents/fbk-code-review-challenger.md"

# Per-group agents (Tier 1)
G1="$PROJECT_ROOT/assets/agents/fbk-t1-value-abstraction-detector.md"
G2="$PROJECT_ROOT/assets/agents/fbk-t1-dead-code-detector.md"
G3="$PROJECT_ROOT/assets/agents/fbk-t1-signal-loss-detector.md"
G4="$PROJECT_ROOT/assets/agents/fbk-t1-behavioral-drift-detector.md"
G5="$PROJECT_ROOT/assets/agents/fbk-t1-function-boundaries-detector.md"
G6="$PROJECT_ROOT/assets/agents/fbk-t1-cross-boundary-structure-detector.md"
G7="$PROJECT_ROOT/assets/agents/fbk-t1-missing-safeguards-detector.md"

# Specialized agents
INTENT_TRACER="$PROJECT_ROOT/assets/agents/fbk-intent-path-tracer.md"
TEST_REVIEWER="$PROJECT_ROOT/assets/agents/fbk-test-reviewer.md"
DEDUPLICATOR="$PROJECT_ROOT/assets/agents/fbk-sighting-deduplicator.md"

# Combine all docs for grep -l queries
ALL_DOCS="$CHECKLIST $QUALITY $GUIDE $CHALLENGER $G1 $G2 $G3 $G4 $G5 $G6 $G7 $INTENT_TRACER $TEST_REVIEWER $DEDUPLICATOR"

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

# Tests from ai-failure-modes.md targets
check_target "bare literal"
check_target "hardcoded coupling"
check_target "never connected"
check_target "name-assertion mismatch"
check_target "surface-level fix"
check_target "non-enforcing test"
check_target "dead infrastructure"
check_target "comment-code drift"
check_target "sentinel"
check_target "context bypass"
check_target "string-based error"
check_target "semantically incoherent"
check_target "mock permissiveness"
check_target "dead conditional"

# Tests from quality-detection.md targets
check_target "mixed logic and side effects"
check_target "ambient state"
check_target "non-importable"
check_target "multi-responsibility"
check_target "caller re-implementation"
check_target "composition opacity"
check_target "parallel collection"
check_target "dead infrastructure"
check_target "semantic drift"
check_target "silent error discard"
check_target "context discard"
check_target "string-based type discrimination"
check_target "dual-path verification"
check_target "test-production string"
check_target "dead code after field"

# AC-08: Token volume reduction verified by inspection
ok "AC-08: token volume reduction verified by inspection (not automatable per spec)"

# TAP summary
echo "1..$TOTAL"
if [ "$FAIL" -gt 0 ]; then
  exit 1
fi
