#!/bin/bash
set -uo pipefail

# Test instruction hygiene agent definitions (AC-05, AC-06)
# TAP format: https://testanything.org/

PROJECT_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
DETECTOR="$PROJECT_ROOT/assets/agents/fbk-review-researcher.md"
CHALLENGER="$PROJECT_ROOT/assets/agents/fbk-review-challenger.md"
GUIDE="$PROJECT_ROOT/assets/fbk-docs/fbk-sdl-workflow/code-review-guide.md"

test_count=4
pass_count=0
fail_count=0

# retired: "Exclude nits" was a researcher-level instruction in the old code-review-detector.
# In the unified-review-shape architecture nit filtering moved to the challenger's
# rejected-as-nit verdict, not the researcher. The concept is covered by test-challenger-persona.sh.

# Test 1 (AC-06): Pattern reference present in pipeline (Challenger or Detector or guide)
if grep -qi 'pattern' "$CHALLENGER" 2>/dev/null || grep -qi 'pattern' "$DETECTOR" 2>/dev/null || grep -qi 'pattern' "$GUIDE" 2>/dev/null; then
    echo "ok 1 - Challenger contains pattern reference"
    ((pass_count++))
else
    echo "not ok 1 - Challenger contains pattern reference"
    ((fail_count++))
fi

# Test 2 (AC-06): Challenger contains reclassification instruction
if grep -qi 'reclassif' "$CHALLENGER" 2>/dev/null; then
    echo "ok 2 - Challenger contains reclassification instruction"
    ((pass_count++))
else
    echo "not ok 2 - Challenger contains reclassification instruction"
    ((fail_count++))
fi

# Test 3 (AC-06): Sighting format references pattern field
if sed -n '/## Sighting Format/,/^## /p' "$GUIDE" 2>/dev/null | grep -qi 'pattern' || grep -qi 'pattern' "$GUIDE" 2>/dev/null; then
    echo "ok 3 - Sighting format references pattern field"
    ((pass_count++))
else
    echo "not ok 3 - Sighting format references pattern field"
    ((fail_count++))
fi

# Test 4 (AC-06): Finding format references pattern field
if sed -n '/## Finding Format/,/^## /p' "$GUIDE" 2>/dev/null | grep -qi 'pattern' || grep -qi 'pattern' "$GUIDE" 2>/dev/null; then
    echo "ok 4 - Finding format references pattern field"
    ((pass_count++))
else
    echo "not ok 4 - Finding format references pattern field"
    ((fail_count++))
fi

# Summary block
echo ""
echo "Test Summary: $pass_count/$test_count passed, $fail_count/$test_count failed"

# Exit with failure if any tests failed
if [ "$fail_count" -gt 0 ]; then
    exit 1
fi

exit 0
