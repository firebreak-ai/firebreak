#!/usr/bin/env bash
set -uo pipefail

PASS=0
FAIL=0
TOTAL=0

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
PROJECT_ROOT="$(cd "$SCRIPT_DIR/../.." && pwd)"
PIPELINE="$PROJECT_ROOT/assets/scripts/pipeline.py"
FIXTURES="$PROJECT_ROOT/tests/fixtures/pipeline"

trap 'rm -f /tmp/test-domain-*.json /tmp/test-domain-*-err.txt' EXIT

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

# --- Test 1: behavioral-only preset passes only behavioral sightings ---
uv run "$PIPELINE" domain-filter --preset behavioral-only < "$FIXTURES/mixed-types.json" > /tmp/test-domain-behavioral.json 2>/dev/null || true
if python3 -c "import json,sys; d=json.load(sys.stdin); assert len(d)==1 and d[0]['type']=='behavioral', f'got {[(s[\"id\"],s[\"type\"]) for s in d]}'" < /tmp/test-domain-behavioral.json 2>/dev/null; then
  ok "behavioral-only preset passes only behavioral sightings"
else
  not_ok "behavioral-only preset passes only behavioral sightings" "expected 1 behavioral sighting"
fi

# --- Test 2: structural preset passes only structural sightings ---
uv run "$PIPELINE" domain-filter --preset structural < "$FIXTURES/mixed-types.json" > /tmp/test-domain-structural.json 2>/dev/null || true
if python3 -c "import json,sys; d=json.load(sys.stdin); assert len(d)==1 and d[0]['type']=='structural', f'got {[(s[\"id\"],s[\"type\"]) for s in d]}'" < /tmp/test-domain-structural.json 2>/dev/null; then
  ok "structural preset passes only structural sightings"
else
  not_ok "structural preset passes only structural sightings" "expected 1 structural sighting"
fi

# --- Test 3: test-only preset passes only test-integrity sightings ---
uv run "$PIPELINE" domain-filter --preset test-only < "$FIXTURES/mixed-types.json" > /tmp/test-domain-testonly.json 2>/dev/null || true
if python3 -c "import json,sys; d=json.load(sys.stdin); assert len(d)==1 and d[0]['type']=='test-integrity', f'got {[(s[\"id\"],s[\"type\"]) for s in d]}'" < /tmp/test-domain-testonly.json 2>/dev/null; then
  ok "test-only preset passes only test-integrity sightings"
else
  not_ok "test-only preset passes only test-integrity sightings" "expected 1 test-integrity sighting"
fi

# --- Test 4: full preset passes all sightings ---
uv run "$PIPELINE" domain-filter --preset full < "$FIXTURES/mixed-types.json" > /tmp/test-domain-full.json 2>/dev/null || true
if python3 -c "import json,sys; d=json.load(sys.stdin); assert len(d)==4, f'got {len(d)}'" < /tmp/test-domain-full.json 2>/dev/null; then
  ok "full preset passes all sightings"
else
  not_ok "full preset passes all sightings" "expected 4 sightings"
fi

# --- Test 5: domain-filter logs dropped sightings to stderr ---
uv run "$PIPELINE" domain-filter --preset behavioral-only < "$FIXTURES/mixed-types.json" > /dev/null 2>/tmp/test-domain-stderr.txt || true
if [ -s /tmp/test-domain-stderr.txt ] && grep -qE 'structural|test-integrity|fragile' /tmp/test-domain-stderr.txt 2>/dev/null; then
  ok "domain-filter logs dropped sightings to stderr"
else
  not_ok "domain-filter logs dropped sightings to stderr" "stderr empty or missing dropped type names"
fi

# --- Test 6: domain-filter with unknown preset exits non-zero ---
if ! uv run "$PIPELINE" domain-filter --preset nonexistent < "$FIXTURES/mixed-types.json" > /dev/null 2>/dev/null; then
  ok "domain-filter with unknown preset exits non-zero"
else
  not_ok "domain-filter with unknown preset exits non-zero" "expected non-zero exit for unknown preset"
fi

# --- Test 7: domain-filter on empty array outputs empty array ---
echo '[]' | uv run "$PIPELINE" domain-filter --preset behavioral-only > /tmp/test-domain-empty.json 2>/dev/null || true
if python3 -c "import json,sys; d=json.load(sys.stdin); assert d==[], f'got {d}'" < /tmp/test-domain-empty.json 2>/dev/null; then
  ok "domain-filter on empty array outputs empty array"
else
  not_ok "domain-filter on empty array outputs empty array" "expected empty array output"
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
