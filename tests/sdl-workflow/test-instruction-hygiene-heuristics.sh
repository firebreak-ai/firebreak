#!/bin/bash

# Test: instruction hygiene heuristics promotion and removal
# Coverage: AC-04 (promoted heuristics appear in standard format in quality-detection.md,
#                   all 6 detection heuristic sections removed from existing-code-review.md)

set -euo pipefail

PROJECT_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
QUALITY="$PROJECT_ROOT/assets/fbk-docs/fbk-design-guidelines/quality-detection.md"
EXISTING="$PROJECT_ROOT/assets/skills/fbk-code-review/references/existing-code-review.md"

test_count=0
pass_count=0

tap_ok() {
  test_count=$((test_count + 1))
  pass_count=$((pass_count + 1))
  echo "ok $test_count - $1"
}

tap_not_ok() {
  test_count=$((test_count + 1))
  echo "not ok $test_count - $1"
}

# Test 1: AC-04 presence - "Dual-path verification" section heading exists
if grep -qi '## Dual-path verification' "$QUALITY"; then
  tap_ok "quality-detection.md contains 'Dual-path verification' section"
else
  tap_not_ok "quality-detection.md contains 'Dual-path verification' section"
fi

# Test 2: AC-04 presence - "Test-production string alignment" section heading exists
if grep -qi '## Test-production string alignment' "$QUALITY"; then
  tap_ok "quality-detection.md contains 'Test-production string alignment' section"
else
  tap_not_ok "quality-detection.md contains 'Test-production string alignment' section"
fi

# Test 3: AC-04 presence - "Dead code after field" section heading exists
if grep -qi '## Dead code after field' "$QUALITY"; then
  tap_ok "quality-detection.md contains 'Dead code after field' section"
else
  tap_not_ok "quality-detection.md contains 'Dead code after field' section"
fi

# Test 4: AC-04 format - promoted sections contain "Detect this when" heuristic
count=$(grep -c 'Detect this when' "$QUALITY" || true)
if [ "$count" -ge 11 ]; then
  tap_ok "quality-detection.md contains 'Detect this when' at least 11 times (found $count)"
else
  tap_not_ok "quality-detection.md contains 'Detect this when' at least 11 times (found $count, expected >= 11)"
fi

# Test 5: AC-04 removal - "Dual-path verification" section heading absent
if ! grep -qi '## Dual-path verification' "$EXISTING"; then
  tap_ok "existing-code-review.md does not contain 'Dual-path verification' section"
else
  tap_not_ok "existing-code-review.md does not contain 'Dual-path verification' section"
fi

# Test 6: AC-04 removal - "Sentinel value confusion" section heading absent
if ! grep -qi '## Sentinel value confusion' "$EXISTING"; then
  tap_ok "existing-code-review.md does not contain 'Sentinel value confusion' section"
else
  tap_not_ok "existing-code-review.md does not contain 'Sentinel value confusion' section"
fi

# Test 7: AC-04 removal - "Test-production string alignment" section heading absent
if ! grep -qi '## Test-production string alignment' "$EXISTING"; then
  tap_ok "existing-code-review.md does not contain 'Test-production string alignment' section"
else
  tap_not_ok "existing-code-review.md does not contain 'Test-production string alignment' section"
fi

# Test 8: AC-04 removal - "String-based error classification" section heading absent
if ! grep -qi '## String-based error classification' "$EXISTING"; then
  tap_ok "existing-code-review.md does not contain 'String-based error classification' section"
else
  tap_not_ok "existing-code-review.md does not contain 'String-based error classification' section"
fi

# Test 9: AC-04 removal - "Dead infrastructure detection" section heading absent
if ! grep -qi '## Dead infrastructure detection' "$EXISTING"; then
  tap_ok "existing-code-review.md does not contain 'Dead infrastructure detection' section"
else
  tap_not_ok "existing-code-review.md does not contain 'Dead infrastructure detection' section"
fi

# Test 10: AC-04 removal - "Dead code after field" section heading absent
if ! grep -qi '## Dead code after field' "$EXISTING"; then
  tap_ok "existing-code-review.md does not contain 'Dead code after field' section"
else
  tap_not_ok "existing-code-review.md does not contain 'Dead code after field' section"
fi

# Summary
echo ""
echo "# Tests: $pass_count/$test_count passed"

if [ "$pass_count" -eq "$test_count" ]; then
  exit 0
else
  exit 1
fi
