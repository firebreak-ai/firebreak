#!/bin/bash

set -e

# Test script to verify no old script paths remain in test files after migration
# AC-10: all old path patterns eliminated from test files

echo "=== Test 1: Verify no old hook paths in test files ==="
hook_matches=$(grep -r "hooks/fbk-sdl-workflow" tests/sdl-workflow/ tests/installer/ --include='*.sh' --exclude='test-verify-*' --exclude='test-no-old-*' --exclude='test-settings-*' --exclude='test-council-*' --exclude='test-e2e-*' --exclude='test-old-locations-*' 2>/dev/null || true)
if [ -z "$hook_matches" ]; then
    echo "✓ PASS: No old hook paths found"
else
    echo "✗ FAIL: Found old hook paths:"
    echo "$hook_matches"
    exit 1
fi

echo ""
echo "=== Test 2: Verify no 'uv run' in test files ==="
uv_run_matches=$(grep -r "uv run" tests/sdl-workflow/ --include='*.sh' --exclude='test-verify-*' --exclude='test-inject-script.sh' --exclude='test-benchmark-*' --exclude='test-no-old-*' --exclude='test-orchestrator-*' 2>/dev/null || true)
if [ -z "$uv_run_matches" ]; then
    echo "✓ PASS: No 'uv run' found in test files"
else
    echo "✗ FAIL: Found 'uv run' in test files:"
    echo "$uv_run_matches"
    exit 1
fi

echo ""
echo "=== Test 3: Verify no old pipeline path in test files ==="
pipeline_matches=$(grep -r "scripts/fbk-pipeline.py" tests/sdl-workflow/ tests/installer/ --include='*.sh' --exclude='test-verify-*' 2>/dev/null || true)
if [ -z "$pipeline_matches" ]; then
    echo "✓ PASS: No old pipeline paths found"
else
    echo "✗ FAIL: Found old pipeline paths:"
    echo "$pipeline_matches"
    exit 1
fi

echo ""
echo "=== Test 4: Verify no old installer paths in test files ==="
installer_matches=$(grep -r "task-completed\.sh" tests/installer/ --include='*.sh' 2>/dev/null || true)
if [ -z "$installer_matches" ]; then
    echo "✓ PASS: No old installer paths found"
else
    echo "✗ FAIL: Found old installer paths:"
    echo "$installer_matches"
    exit 1
fi

echo ""
echo "=== Test 5: Verify no old preset path in test files ==="
preset_matches=$(grep -r "assets/config/fbk-presets.json" tests/sdl-workflow/test-preset-config.sh 2>/dev/null || true)
if [ -z "$preset_matches" ]; then
    echo "✓ PASS: No old preset paths found"
else
    echo "✗ FAIL: Found old preset paths:"
    echo "$preset_matches"
    exit 1
fi

echo ""
echo "=== All tests passed ==="
