#!/usr/bin/env bash
set -uo pipefail

PASS=0
FAIL=0
TOTAL=0

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
PROJECT_ROOT="$(cd "$SCRIPT_DIR/../.." && pwd)"

# Define agent file paths
IPT="$PROJECT_ROOT/assets/agents/fbk-intent-path-tracer.md"
DEAD_CODE="$PROJECT_ROOT/assets/agents/fbk-t1-dead-code-detector.md"
CROSS_BOUNDARY="$PROJECT_ROOT/assets/agents/fbk-t1-cross-boundary-structure-detector.md"
VALUE_ABSTRACTION="$PROJECT_ROOT/assets/agents/fbk-t1-value-abstraction-detector.md"
SIGNAL_LOSS="$PROJECT_ROOT/assets/agents/fbk-t1-signal-loss-detector.md"
BEHAVIORAL_DRIFT="$PROJECT_ROOT/assets/agents/fbk-t1-behavioral-drift-detector.md"
FUNCTION_BOUNDARIES="$PROJECT_ROOT/assets/agents/fbk-t1-function-boundaries-detector.md"
MISSING_SAFEGUARDS="$PROJECT_ROOT/assets/agents/fbk-t1-missing-safeguards-detector.md"
TEST_REVIEWER="$PROJECT_ROOT/assets/agents/fbk-cr-test-reviewer.md"

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

# --- Positive tests: agents that SHOULD reference Mermaid or diagram ---

# Test 1: Intent Path Tracer contains "mermaid" or "diagram"
if [ -s "$IPT" ] && grep -qiE 'mermaid|diagram' "$IPT"; then
  ok "Intent Path Tracer references Mermaid/diagram"
else
  not_ok "Intent Path Tracer references Mermaid/diagram" "file: $IPT"
fi

# Test 2: Dead Code Detector contains "mermaid" or "diagram"
if [ -s "$DEAD_CODE" ] && grep -qiE 'mermaid|diagram' "$DEAD_CODE"; then
  ok "Dead Code Detector references Mermaid/diagram"
else
  not_ok "Dead Code Detector references Mermaid/diagram" "file: $DEAD_CODE"
fi

# Test 3: Cross Boundary Structure Detector contains "mermaid" or "diagram"
if [ -s "$CROSS_BOUNDARY" ] && grep -qiE 'mermaid|diagram' "$CROSS_BOUNDARY"; then
  ok "Cross Boundary Structure Detector references Mermaid/diagram"
else
  not_ok "Cross Boundary Structure Detector references Mermaid/diagram" "file: $CROSS_BOUNDARY"
fi

# --- Negative tests: agents that should NOT reference Mermaid or diagram ---

# Test 4: Value Abstraction Detector does NOT contain "mermaid" or "diagram"
if [ ! -s "$VALUE_ABSTRACTION" ] || ! grep -qiE 'mermaid|diagram' "$VALUE_ABSTRACTION"; then
  ok "Value Abstraction Detector does not reference Mermaid/diagram"
else
  not_ok "Value Abstraction Detector does not reference Mermaid/diagram" "file: $VALUE_ABSTRACTION"
fi

# Test 5: Signal Loss Detector does NOT contain "mermaid" or "diagram"
if [ ! -s "$SIGNAL_LOSS" ] || ! grep -qiE 'mermaid|diagram' "$SIGNAL_LOSS"; then
  ok "Signal Loss Detector does not reference Mermaid/diagram"
else
  not_ok "Signal Loss Detector does not reference Mermaid/diagram" "file: $SIGNAL_LOSS"
fi

# Test 6: Behavioral Drift Detector does NOT contain "mermaid" or "diagram"
if [ ! -s "$BEHAVIORAL_DRIFT" ] || ! grep -qiE 'mermaid|diagram' "$BEHAVIORAL_DRIFT"; then
  ok "Behavioral Drift Detector does not reference Mermaid/diagram"
else
  not_ok "Behavioral Drift Detector does not reference Mermaid/diagram" "file: $BEHAVIORAL_DRIFT"
fi

# Test 7: Function Boundaries Detector does NOT contain "mermaid" or "diagram"
if [ ! -s "$FUNCTION_BOUNDARIES" ] || ! grep -qiE 'mermaid|diagram' "$FUNCTION_BOUNDARIES"; then
  ok "Function Boundaries Detector does not reference Mermaid/diagram"
else
  not_ok "Function Boundaries Detector does not reference Mermaid/diagram" "file: $FUNCTION_BOUNDARIES"
fi

# Test 8: Missing Safeguards Detector does NOT contain "mermaid" or "diagram"
if [ ! -s "$MISSING_SAFEGUARDS" ] || ! grep -qiE 'mermaid|diagram' "$MISSING_SAFEGUARDS"; then
  ok "Missing Safeguards Detector does not reference Mermaid/diagram"
else
  not_ok "Missing Safeguards Detector does not reference Mermaid/diagram" "file: $MISSING_SAFEGUARDS"
fi

# Test 9: Test Reviewer does NOT contain "mermaid" or "diagram"
if [ ! -s "$TEST_REVIEWER" ] || ! grep -qiE 'mermaid|diagram' "$TEST_REVIEWER"; then
  ok "Test Reviewer does not reference Mermaid/diagram"
else
  not_ok "Test Reviewer does not reference Mermaid/diagram" "file: $TEST_REVIEWER"
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
