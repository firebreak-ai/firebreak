#!/bin/bash

# Test: detector-decomposition quality detection new targets
# Coverage: AC-06 (4 new detection targets added to quality-detection.md
#                   with standard format and "Detect this when" heuristics)

set -euo pipefail

PROJECT_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
QUALITY="$PROJECT_ROOT/assets/fbk-docs/fbk-design-guidelines/quality-detection.md"

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

# Test 1: AC-06 presence - "Unbounded data structure growth" section heading exists
if grep -qi '## Unbounded data structure growth' "$QUALITY"; then
  tap_ok "quality-detection.md contains 'Unbounded data structure growth' section"
else
  tap_not_ok "quality-detection.md contains 'Unbounded data structure growth' section"
fi

# Test 2: AC-06 presence - "Migration" with "idempoten" section heading exists
if grep -qiE 'migration.*idempoten|idempoten.*migration' "$QUALITY"; then
  tap_ok "quality-detection.md contains 'Migration' with 'idempoten' section"
else
  tap_not_ok "quality-detection.md contains 'Migration' with 'idempoten' section"
fi

# Test 3: AC-06 presence - "Batch transaction atomicity" section heading exists
if grep -qi '## Batch transaction atomicity' "$QUALITY"; then
  tap_ok "quality-detection.md contains 'Batch transaction atomicity' section"
else
  tap_not_ok "quality-detection.md contains 'Batch transaction atomicity' section"
fi

# Test 4: AC-06 presence - "Intra-function logical redundancy" or "logical redundancy" section heading exists
if grep -qi '## .*logical redundancy' "$QUALITY"; then
  tap_ok "quality-detection.md contains logical redundancy section"
else
  tap_not_ok "quality-detection.md contains logical redundancy section"
fi

# Test 5: AC-06 format - "Unbounded data structure growth" section contains "Detect this when"
section=$(sed -n '/^## Unbounded data structure growth/,/^## /p' "$QUALITY" | head -n -1)
if echo "$section" | grep -qi 'Detect this when'; then
  tap_ok "'Unbounded data structure growth' section contains 'Detect this when' heuristic"
else
  tap_not_ok "'Unbounded data structure growth' section contains 'Detect this when' heuristic"
fi

# Test 6: AC-06 format - Total detection target count >= 15
count=$(grep -cE '^## ' "$QUALITY" || true)
if [ "$count" -ge 15 ]; then
  tap_ok "quality-detection.md has >= 15 '## ' sections (found $count)"
else
  tap_not_ok "quality-detection.md has >= 15 '## ' sections (found $count, expected >= 15)"
fi

# Summary
echo ""
echo "# Tests: $pass_count/$test_count passed"

if [ "$pass_count" -eq "$test_count" ]; then
  exit 0
else
  exit 1
fi
