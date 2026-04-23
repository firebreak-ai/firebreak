#!/bin/bash

set -euo pipefail

PROJECT_ROOT="$(git rev-parse --show-toplevel)"
SETTINGS="$PROJECT_ROOT/assets/settings.json"

echo "Testing settings.json hook command format..."
echo "PROJECT_ROOT: $PROJECT_ROOT"
echo "SETTINGS: $SETTINGS"

# Test 1: assert settings.json contains "fbk-scripts/fbk.py task-completed"
echo ""
echo "Test 1: Checking for new dispatcher command format..."
if grep -q "fbk-scripts/fbk.py task-completed" "$SETTINGS"; then
    echo "✓ PASS: settings.json contains 'fbk-scripts/fbk.py task-completed'"
else
    echo "✗ FAIL: settings.json does NOT contain 'fbk-scripts/fbk.py task-completed'"
    exit 1
fi

# Test 2: assert settings.json does NOT contain "hooks/fbk-sdl-workflow/task-completed.sh"
echo ""
echo "Test 2: Checking for absence of old hook path..."
if grep -q "hooks/fbk-sdl-workflow/task-completed.sh" "$SETTINGS"; then
    echo "✗ FAIL: settings.json still contains old hook path 'hooks/fbk-sdl-workflow/task-completed.sh'"
    exit 1
else
    echo "✓ PASS: settings.json does NOT contain 'hooks/fbk-sdl-workflow/task-completed.sh'"
fi

# Test 3: assert settings.json contains "python3"
echo ""
echo "Test 3: Checking for python3 invocation..."
if grep -q "python3" "$SETTINGS"; then
    echo "✓ PASS: settings.json contains 'python3'"
else
    echo "✗ FAIL: settings.json does NOT contain 'python3'"
    exit 1
fi

echo ""
echo "All tests passed!"
