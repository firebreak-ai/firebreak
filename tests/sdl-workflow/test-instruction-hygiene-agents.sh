#!/bin/bash
set -uo pipefail

# Test instruction hygiene agent definitions (AC-05, AC-06)
# TAP format: https://testanything.org/

PROJECT_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
DETECTOR="$PROJECT_ROOT/assets/agents/fbk-t1-value-abstraction-detector.md"
CHALLENGER="$PROJECT_ROOT/assets/agents/fbk-code-review-challenger.md"
GUIDE="$PROJECT_ROOT/assets/fbk-docs/fbk-sdl-workflow/code-review-guide.md"

test_count=6
pass_count=0
fail_count=0

# Test 1 (AC-05): Detector contains "Exclude nits"
if grep -qi 'exclude nits' "$DETECTOR" 2>/dev/null; then
    echo "ok 1 - Detector contains 'Exclude nits'"
    ((pass_count++))
else
    echo "not ok 1 - Detector contains 'Exclude nits'"
    ((fail_count++))
fi

# Test 2 (AC-05): Nit suppression instruction in Scope discipline section
if sed -n '/## Scope discipline/,/^## /p' "$DETECTOR" 2>/dev/null | grep -qi 'nit'; then
    echo "ok 2 - Nit instruction in Detector's Scope discipline section"
    ((pass_count++))
else
    echo "not ok 2 - Nit instruction in Detector's Scope discipline section"
    ((fail_count++))
fi

# Test 3 (AC-06): Challenger contains "pattern label"
if grep -qi 'pattern label' "$CHALLENGER" 2>/dev/null; then
    echo "ok 3 - Challenger contains 'pattern label'"
    ((pass_count++))
else
    echo "not ok 3 - Challenger contains 'pattern label'"
    ((fail_count++))
fi

# Test 4 (AC-06): Challenger contains label correction or independent issues instruction
if grep -qiE 'label correction|independent issues' "$CHALLENGER" 2>/dev/null; then
    echo "ok 4 - Challenger contains label correction or independent issues instruction"
    ((pass_count++))
else
    echo "not ok 4 - Challenger contains label correction or independent issues instruction"
    ((fail_count++))
fi

# Test 5 (AC-06): Sighting Format template contains "Pattern label:"
if sed -n '/## Sighting Format/,/^## /p' "$GUIDE" 2>/dev/null | grep -qi 'pattern label'; then
    echo "ok 5 - Sighting Format template contains 'Pattern label:'"
    ((pass_count++))
else
    echo "not ok 5 - Sighting Format template contains 'Pattern label:'"
    ((fail_count++))
fi

# Test 6 (AC-06): Finding Format template contains "Pattern label:"
if sed -n '/## Finding Format/,/^## /p' "$GUIDE" 2>/dev/null | grep -qi 'pattern label'; then
    echo "ok 6 - Finding Format template contains 'Pattern label:'"
    ((pass_count++))
else
    echo "not ok 6 - Finding Format template contains 'Pattern label:'"
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
