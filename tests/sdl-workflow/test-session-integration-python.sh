#!/usr/bin/env bash
# Test suite for session-logger and session-manager integration through dispatcher
# Verifies that council modules are relocatable and callable through dispatcher

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
PROJECT_ROOT="$(cd "$SCRIPT_DIR/../.." && pwd)"
DISPATCHER="$PROJECT_ROOT/assets/fbk-scripts/fbk.py"
TEST_SESSION="test-session-$(date +%s)"
TMPDIR=$(mktemp -d)
export COUNCIL_LOG_DIR="$TMPDIR/council-logs"
mkdir -p "$COUNCIL_LOG_DIR"
trap 'rm -rf "$TMPDIR"' EXIT

# Test 1: session-logger init creates log file
test_session_logger_init() {
    echo "Test 1: session-logger init creates log file..."

    local result
    result=$(python3 "$DISPATCHER" session-logger init "$TEST_SESSION" --tier quick --task "test")

    # Verify command exit code is 0
    if [ $? -ne 0 ]; then
        echo "FAIL: session-logger init exited with non-zero code"
        return 1
    fi

    # Verify session log file exists at expected location
    local log_path="$COUNCIL_LOG_DIR/${TEST_SESSION}.json"
    if [ ! -f "$log_path" ]; then
        echo "FAIL: session log file not found at $log_path"
        return 1
    fi

    # Verify log file contains expected data
    if ! grep -q '"session_id": "'$TEST_SESSION'"' "$log_path"; then
        echo "FAIL: session log does not contain expected session_id"
        return 1
    fi

    if ! grep -q '"tier": "quick"' "$log_path"; then
        echo "FAIL: session log does not contain expected tier"
        return 1
    fi

    echo "PASS: session-logger init created log file at expected location"
    return 0
}

# Test 2: session-manager register creates entry
test_session_manager_register() {
    echo "Test 2: session-manager register creates registry entry..."

    local result
    result=$(python3 "$DISPATCHER" session-manager register "$TEST_SESSION" quick)

    # Verify command exit code is 0
    if [ $? -ne 0 ]; then
        echo "FAIL: session-manager register exited with non-zero code"
        return 1
    fi

    # Verify registry file contains test-session
    local registry_path="$COUNCIL_LOG_DIR/active-council"
    if [ ! -f "$registry_path" ]; then
        echo "FAIL: registry file not found at $registry_path"
        return 1
    fi

    if ! grep -q "$TEST_SESSION" "$registry_path"; then
        echo "FAIL: registry JSON does not contain $TEST_SESSION"
        return 1
    fi

    echo "PASS: session-manager register created registry entry"
    return 0
}

# Test 3: session-manager unregister removes entry
test_session_manager_unregister() {
    echo "Test 3: session-manager unregister removes registry entry..."

    local result
    result=$(python3 "$DISPATCHER" session-manager unregister "$TEST_SESSION")

    # Verify command exit code is 0
    if [ $? -ne 0 ]; then
        echo "FAIL: session-manager unregister exited with non-zero code"
        return 1
    fi

    # Verify registry file does NOT contain test-session
    local registry_path="$COUNCIL_LOG_DIR/active-council"
    if [ ! -f "$registry_path" ]; then
        echo "FAIL: registry file not found at $registry_path"
        return 1
    fi

    if grep -q "$TEST_SESSION" "$registry_path"; then
        echo "FAIL: registry JSON still contains $TEST_SESSION after unregister"
        return 1
    fi

    echo "PASS: session-manager unregister removed registry entry"
    return 0
}

# Run all tests
main() {
    echo "Running session integration tests..."
    echo ""

    local failed=0

    if ! test_session_logger_init; then
        ((failed++))
    fi
    echo ""

    if ! test_session_manager_register; then
        ((failed++))
    fi
    echo ""

    if ! test_session_manager_unregister; then
        ((failed++))
    fi
    echo ""

    if [ $failed -eq 0 ]; then
        echo "All tests passed!"
        return 0
    else
        echo "$failed test(s) failed"
        return 1
    fi
}

main "$@"
