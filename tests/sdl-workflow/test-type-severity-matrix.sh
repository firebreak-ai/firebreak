#!/usr/bin/env bash
set -uo pipefail

PASS=0
FAIL=0
TOTAL=0

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
PROJECT_ROOT="$(cd "$SCRIPT_DIR/../.." && pwd)"
DISPATCHER="$PROJECT_ROOT/assets/fbk-scripts/fbk.py"

trap 'rm -f /tmp/test-matrix-*.json' EXIT

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

test_combination() {
  local type_val="$1"
  local sev_val="$2"
  local expect="$3"  # "valid" or "invalid"
  local desc="$type_val+$sev_val should be $expect"

  cat > /tmp/test-matrix-input.json <<EOJSON
[{
  "id": "S-01",
  "title": "Test sighting for matrix validation check",
  "location": {"file": "src/test.ts", "start_line": 1},
  "type": "$type_val",
  "severity": "$sev_val",
  "mechanism": "Test mechanism for matrix validation exhaustive check",
  "consequence": "Test consequence for matrix validation exhaustive check",
  "evidence": "Lines 1-5"
}]
EOJSON

  local out
  out=$(python3 "$DISPATCHER" pipeline validate < /tmp/test-matrix-input.json 2>/dev/null)
  local count
  count=$(echo "$out" | python3 -c "import json,sys; print(len(json.load(sys.stdin)))" 2>/dev/null || echo "error")

  if [ "$expect" = "valid" ]; then
    if [ "$count" = "1" ]; then
      ok "$desc"
    else
      not_ok "$desc" "expected 1 valid sighting, got $count"
    fi
  else
    if [ "$count" = "0" ]; then
      ok "$desc"
    else
      not_ok "$desc" "expected 0 valid sightings (rejected), got $count"
    fi
  fi
}

# Valid combinations (9)
test_combination "behavioral" "critical" "valid"
test_combination "behavioral" "major" "valid"
test_combination "structural" "minor" "valid"
test_combination "structural" "info" "valid"
test_combination "test-integrity" "critical" "valid"
test_combination "test-integrity" "major" "valid"
test_combination "test-integrity" "minor" "valid"
test_combination "fragile" "major" "valid"
test_combination "fragile" "minor" "valid"

# Invalid combinations (7)
test_combination "behavioral" "minor" "invalid"
test_combination "behavioral" "info" "invalid"
test_combination "structural" "critical" "invalid"
test_combination "structural" "major" "invalid"
test_combination "test-integrity" "info" "invalid"
test_combination "fragile" "critical" "invalid"
test_combination "fragile" "info" "invalid"

# --- Summary ---
echo ""
echo "1..$TOTAL"
echo "# $PASS/$TOTAL tests passed"
if [ "$FAIL" -gt 0 ]; then
  echo "# FAIL $FAIL"
  exit 1
fi
exit 0
