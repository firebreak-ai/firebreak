#!/usr/bin/env bash
set -uo pipefail

TESTS=0
PASS=0
FAIL=0

ok() {
  TESTS=$((TESTS + 1))
  PASS=$((PASS + 1))
  echo "ok $TESTS - $1"
}

not_ok() {
  TESTS=$((TESTS + 1))
  FAIL=$((FAIL + 1))
  echo "not ok $TESTS - $1"
  [ -n "${2:-}" ] && echo "# $2"
}

# Setup
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(cd "$SCRIPT_DIR/../.." && pwd)"
GATE="$PROJECT_ROOT/assets/hooks/fbk-sdl-workflow/test-hash-gate.sh"
FIXTURES="$PROJECT_ROOT/tests/fixtures/hash-gate/sample-tests"

TMPDIR_TEST="$(mktemp -d)"
trap 'rm -rf "$TMPDIR_TEST"' EXIT

# Simulate ai-docs/feature/ with tests/ subdirectory
FEATURE_DIR="$TMPDIR_TEST/ai-docs/my-feature"
mkdir -p "$FEATURE_DIR/tests/helpers"
cp "$FIXTURES/test-alpha.sh" "$FEATURE_DIR/tests/test-alpha.sh"
cp "$FIXTURES/test-beta.sh" "$FEATURE_DIR/tests/test-beta.sh"
cp "$FIXTURES/helpers/test-utils.sh" "$FEATURE_DIR/tests/helpers/test-utils.sh"

echo "TAP version 13"
echo "1..7"

# ---- Test 1: First run creates manifest with correct JSON ----
OUTPUT=$(bash "$GATE" "$FEATURE_DIR" 2>&1)
EXIT_CODE=$?
if [[ $EXIT_CODE -eq 0 ]] && [[ -f "$FEATURE_DIR/test-hashes.json" ]]; then
  VALID=$(python3 -c "
import json, sys
m = json.load(open(sys.argv[1]))
files = m.get('files', {})
ca = m.get('computed_at', '')
# Check 3 entries
assert len(files) == 3, f'expected 3 files, got {len(files)}'
# Check 64-char hex hashes
for path, h in files.items():
    assert len(h) == 64, f'hash for {path} is {len(h)} chars'
    int(h, 16)  # validates hex
# Check ISO8601 computed_at
assert 'T' in ca, f'computed_at missing T: {ca}'
print('valid')
" "$FEATURE_DIR/test-hashes.json" 2>&1)
  if [[ "$VALID" == "valid" ]]; then
    ok "first run creates manifest with correct JSON"
  else
    not_ok "first run creates manifest with correct JSON" "$VALID"
  fi
else
  not_ok "first run creates manifest with correct JSON" "exit=$EXIT_CODE output=$OUTPUT"
fi

# ---- Test 2: Subsequent run with no changes exits 0 ----
OUTPUT=$(bash "$GATE" "$FEATURE_DIR" 2>&1)
EXIT_CODE=$?
if [[ $EXIT_CODE -eq 0 ]]; then
  ok "subsequent run with no changes exits 0"
else
  not_ok "subsequent run with no changes exits 0" "exit=$EXIT_CODE output=$OUTPUT"
fi

# ---- Test 3: Modified file detected — exit 2, stderr names file ----
echo "# modified" >> "$FEATURE_DIR/tests/test-alpha.sh"
OUTPUT=$(bash "$GATE" "$FEATURE_DIR" 2>&1)
EXIT_CODE=$?
if [[ $EXIT_CODE -eq 2 ]] && echo "$OUTPUT" | grep -q "test-alpha.sh"; then
  ok "modified file detected: exit 2, stderr names file"
else
  not_ok "modified file detected: exit 2, stderr names file" "exit=$EXIT_CODE output=$OUTPUT"
fi
# Restore for next tests
cp "$FIXTURES/test-alpha.sh" "$FEATURE_DIR/tests/test-alpha.sh"
# Regenerate manifest with clean state
rm "$FEATURE_DIR/test-hashes.json"
bash "$GATE" "$FEATURE_DIR" >/dev/null 2>&1

# ---- Test 4: Deleted file detected — exit 2, stderr names file ----
rm "$FEATURE_DIR/tests/test-beta.sh"
OUTPUT=$(bash "$GATE" "$FEATURE_DIR" 2>&1)
EXIT_CODE=$?
if [[ $EXIT_CODE -eq 2 ]] && echo "$OUTPUT" | grep -q "test-beta.sh"; then
  ok "deleted file detected: exit 2, stderr names file"
else
  not_ok "deleted file detected: exit 2, stderr names file" "exit=$EXIT_CODE output=$OUTPUT"
fi
# Restore
cp "$FIXTURES/test-beta.sh" "$FEATURE_DIR/tests/test-beta.sh"
rm "$FEATURE_DIR/test-hashes.json"
bash "$GATE" "$FEATURE_DIR" >/dev/null 2>&1

# ---- Test 5: New file detected — exit 2, stderr names file ----
echo '#!/bin/bash' > "$FEATURE_DIR/tests/test-gamma.sh"
OUTPUT=$(bash "$GATE" "$FEATURE_DIR" 2>&1)
EXIT_CODE=$?
if [[ $EXIT_CODE -eq 2 ]] && echo "$OUTPUT" | grep -q "test-gamma.sh"; then
  ok "new file detected: exit 2, stderr names file"
else
  not_ok "new file detected: exit 2, stderr names file" "exit=$EXIT_CODE output=$OUTPUT"
fi
rm "$FEATURE_DIR/tests/test-gamma.sh"

# ---- Test 6: Manifest JSON structure uses relative paths ----
VALID=$(python3 -c "
import json, sys
m = json.load(open(sys.argv[1]))
files = m.get('files', {})
for path in files:
    assert not path.startswith('/'), f'absolute path found: {path}'
    assert 'tests/' in path, f'path missing tests/ prefix: {path}'
print('valid')
" "$FEATURE_DIR/test-hashes.json" 2>&1)
if [[ "$VALID" == "valid" ]]; then
  ok "manifest JSON structure uses relative paths"
else
  not_ok "manifest JSON structure uses relative paths" "$VALID"
fi

# ---- Test 7: Empty test directory handled gracefully ----
EMPTY_DIR="$TMPDIR_TEST/empty-feature"
mkdir -p "$EMPTY_DIR"
OUTPUT=$(bash "$GATE" "$EMPTY_DIR" 2>&1)
EXIT_CODE=$?
if [[ $EXIT_CODE -eq 0 ]]; then
  ok "empty test directory handled gracefully (exit 0)"
else
  not_ok "empty test directory handled gracefully (exit 0)" "exit=$EXIT_CODE output=$OUTPUT"
fi

# Summary
echo ""
echo "# Tests: $TESTS, Pass: $PASS, Fail: $FAIL"
exit $FAIL
