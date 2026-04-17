#!/usr/bin/env bash
set -uo pipefail

PASS=0
FAIL=0
TOTAL=0

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
PROJECT_ROOT="$(cd "$SCRIPT_DIR/../.." && pwd)"
PIPELINE="$PROJECT_ROOT/assets/scripts/pipeline.py"
FIXTURES="$PROJECT_ROOT/tests/fixtures/pipeline"

trap 'rm -f /tmp/test-integ-*.json /tmp/test-integ-*.md /tmp/test-integ-*-err.txt' EXIT

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

# --- Test 1: Full pipeline with behavioral-only preset produces expected count ---
uv run "$PIPELINE" run --preset behavioral-only --min-severity minor < "$FIXTURES/integration-input.json" > /tmp/test-integ-behavioral.json 2>/tmp/test-integ-behavioral-err.txt || true
if python3 -c "import json,sys; d=json.load(sys.stdin); assert len(d)==2, f'expected 2, got {len(d)}'" < /tmp/test-integ-behavioral.json 2>/dev/null; then
  ok "behavioral-only preset with minor threshold produces 2 sightings"
else
  actual=$(python3 -c "import json,sys; d=json.load(sys.stdin); print(len(d))" < /tmp/test-integ-behavioral.json 2>/dev/null || echo "error")
  not_ok "behavioral-only preset with minor threshold produces 2 sightings" "expected 2, got $actual"
fi

# --- Test 2: Surviving sightings have sequential S-NN IDs ---
if python3 -c "import json,sys; d=json.load(sys.stdin); ids=[s['id'] for s in d]; assert ids==['S-01','S-02'], f'got {ids}'" < /tmp/test-integ-behavioral.json 2>/dev/null; then
  ok "surviving sightings have sequential S-NN IDs"
else
  actual=$(python3 -c "import json,sys; d=json.load(sys.stdin); print([s['id'] for s in d])" < /tmp/test-integ-behavioral.json 2>/dev/null || echo "error")
  not_ok "surviving sightings have sequential S-NN IDs" "got $actual"
fi

# --- Test 3: Invalid matrix combination was rejected (stderr mentions it) ---
if grep -qi 'behavioral.*minor\|reject\|invalid' /tmp/test-integ-behavioral-err.txt 2>/dev/null; then
  ok "invalid matrix combination rejection reported in stderr"
else
  not_ok "invalid matrix combination rejection reported in stderr" "stderr did not mention rejection of behavioral+minor"
fi

# --- Test 4: Full pipeline with full preset and minor threshold produces expected count ---
uv run "$PIPELINE" run --preset full --min-severity minor < "$FIXTURES/integration-input.json" > /tmp/test-integ-full.json 2>/dev/null || true
if python3 -c "import json,sys; d=json.load(sys.stdin); assert len(d)==4, f'expected 4, got {len(d)}'" < /tmp/test-integ-full.json 2>/dev/null; then
  ok "full preset with minor threshold produces 4 sightings"
else
  actual=$(python3 -c "import json,sys; d=json.load(sys.stdin); print(len(d))" < /tmp/test-integ-full.json 2>/dev/null || echo "error")
  not_ok "full preset with minor threshold produces 4 sightings" "expected 4, got $actual"
fi

# --- Test 5: Full pipeline with full preset and info threshold keeps info sightings ---
uv run "$PIPELINE" run --preset full --min-severity info < "$FIXTURES/integration-input.json" > /tmp/test-integ-info.json 2>/dev/null || true
if python3 -c "import json,sys; d=json.load(sys.stdin); assert len(d)==5, f'expected 5, got {len(d)}'" < /tmp/test-integ-info.json 2>/dev/null; then
  ok "full preset with info threshold produces 5 sightings"
else
  actual=$(python3 -c "import json,sys; d=json.load(sys.stdin); print(len(d))" < /tmp/test-integ-info.json 2>/dev/null || echo "error")
  not_ok "full preset with info threshold produces 5 sightings" "expected 5, got $actual"
fi

# --- Test 6: Pipeline output converted to markdown is well-formed ---
uv run "$PIPELINE" run --preset behavioral-only --min-severity minor --output-markdown < "$FIXTURES/integration-input.json" > /tmp/test-integ-md.md 2>/dev/null || true
header_count=$(grep -c '### S-' /tmp/test-integ-md.md 2>/dev/null || true)
header_count="${header_count:-0}"
has_mechanism=0
grep -q 'Mechanism' /tmp/test-integ-md.md 2>/dev/null && has_mechanism=1 || true
if [ "${header_count}" -eq 2 ] 2>/dev/null && [ "$has_mechanism" -eq 1 ]; then
  ok "pipeline markdown output is well-formed with correct headers and sections"
else
  not_ok "pipeline markdown output is well-formed with correct headers and sections" "header_count=$header_count has_mechanism=$has_mechanism"
fi

# --- Test 7: Pipeline stderr does not warn about prompt drift below 30% threshold ---
if ! grep -qi 'prompt drift\|>30%\|warning.*rate' /tmp/test-integ-behavioral-err.txt 2>/dev/null; then
  ok "no false prompt drift warning when rejection rate is below 30%"
else
  not_ok "no false prompt drift warning when rejection rate is below 30%" "unexpected drift warning in stderr"
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
