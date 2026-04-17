#!/usr/bin/env bash
set -uo pipefail

PASS=0
FAIL=0
TOTAL=0

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
PROJECT_ROOT="$(cd "$SCRIPT_DIR/../.." && pwd)"
PRESETS="$PROJECT_ROOT/assets/config/fbk-presets.json"

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

# --- Test 1: fbk-presets.json exists and is non-empty ---
if [ -s "$PRESETS" ]; then
  ok "fbk-presets.json exists and is non-empty"
else
  not_ok "fbk-presets.json exists and is non-empty" "file: $PRESETS"
fi

# --- Test 2: fbk-presets.json is valid JSON ---
if python3 -c "import json, sys; json.load(sys.stdin)" < "$PRESETS" 2>/dev/null; then
  ok "fbk-presets.json is valid JSON"
else
  not_ok "fbk-presets.json is valid JSON" "file failed JSON parse: $PRESETS"
fi

# --- Test 3: fbk-presets.json contains behavioral-only preset ---
if python3 -c "import json, sys; d=json.load(sys.stdin); assert 'behavioral-only' in d" < "$PRESETS" 2>/dev/null; then
  ok "fbk-presets.json contains behavioral-only preset"
else
  not_ok "fbk-presets.json contains behavioral-only preset" "key 'behavioral-only' not found"
fi

# --- Test 4: behavioral-only preset has allowed_types ["behavioral"] ---
if python3 -c "import json, sys; d=json.load(sys.stdin); assert d['behavioral-only']['allowed_types'] == ['behavioral']" < "$PRESETS" 2>/dev/null; then
  ok "behavioral-only preset has allowed_types [\"behavioral\"]"
else
  not_ok "behavioral-only preset has allowed_types [\"behavioral\"]" "allowed_types mismatch for behavioral-only"
fi

# --- Test 5: behavioral-only preset has default_severity_threshold "minor" ---
if python3 -c "import json, sys; d=json.load(sys.stdin); assert d['behavioral-only']['default_severity_threshold'] == 'minor'" < "$PRESETS" 2>/dev/null; then
  ok "behavioral-only preset has default_severity_threshold \"minor\""
else
  not_ok "behavioral-only preset has default_severity_threshold \"minor\"" "default_severity_threshold mismatch for behavioral-only"
fi

# --- Test 6: structural preset has allowed_types ["structural"] ---
if python3 -c "import json, sys; d=json.load(sys.stdin); assert d['structural']['allowed_types'] == ['structural']" < "$PRESETS" 2>/dev/null; then
  ok "structural preset has allowed_types [\"structural\"]"
else
  not_ok "structural preset has allowed_types [\"structural\"]" "allowed_types mismatch for structural"
fi

# --- Test 7: test-only preset has allowed_types ["test-integrity"] ---
if python3 -c "import json, sys; d=json.load(sys.stdin); assert d['test-only']['allowed_types'] == ['test-integrity']" < "$PRESETS" 2>/dev/null; then
  ok "test-only preset has allowed_types [\"test-integrity\"]"
else
  not_ok "test-only preset has allowed_types [\"test-integrity\"]" "allowed_types mismatch for test-only"
fi

# --- Test 8: full preset has all four types in allowed_types ---
if python3 -c "import json, sys; d=json.load(sys.stdin); assert set(d['full']['allowed_types']) == {'behavioral','structural','test-integrity','fragile'}" < "$PRESETS" 2>/dev/null; then
  ok "full preset has all four types in allowed_types"
else
  not_ok "full preset has all four types in allowed_types" "allowed_types mismatch for full"
fi

# --- Test 9: all four presets have default_severity_threshold "minor" ---
if python3 -c "import json, sys; d=json.load(sys.stdin); assert all(d[k]['default_severity_threshold']=='minor' for k in ['behavioral-only','structural','test-only','full'])" < "$PRESETS" 2>/dev/null; then
  ok "all four presets have default_severity_threshold \"minor\""
else
  not_ok "all four presets have default_severity_threshold \"minor\"" "default_severity_threshold mismatch in one or more presets"
fi

# --- Test 10: fbk-presets.json contains exactly four presets ---
if python3 -c "import json, sys; d=json.load(sys.stdin); assert len(d) == 4" < "$PRESETS" 2>/dev/null; then
  ok "fbk-presets.json contains exactly four presets"
else
  not_ok "fbk-presets.json contains exactly four presets" "expected 4 keys in fbk-presets.json"
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
