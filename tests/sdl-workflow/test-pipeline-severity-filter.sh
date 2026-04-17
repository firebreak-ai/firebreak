#!/usr/bin/env bash
set -uo pipefail

PASS=0
FAIL=0
TOTAL=0

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
PROJECT_ROOT="$(cd "$SCRIPT_DIR/../.." && pwd)"
PIPELINE="$PROJECT_ROOT/assets/scripts/fbk-pipeline.py"
FIXTURES="$PROJECT_ROOT/tests/fixtures/pipeline"

trap 'rm -f /tmp/test-severity-*.json /tmp/test-severity-*-err.txt' EXIT

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

# --- Test 1: --min-severity minor drops info, keeps minor+major+critical ---
uv run "$PIPELINE" severity-filter --min-severity minor < "$FIXTURES/mixed-severities.json" > /tmp/test-severity-minor.json 2>/dev/null || true
if python3 -c "import json,sys; d=json.load(sys.stdin); assert len(d)==3, f'expected 3, got {len(d)}'" < /tmp/test-severity-minor.json 2>/dev/null; then
  ok "--min-severity minor drops info, keeps minor+major+critical"
else
  count=$(python3 -c "import json,sys; print(len(json.load(sys.stdin)))" < /tmp/test-severity-minor.json 2>/dev/null || echo "error")
  not_ok "--min-severity minor drops info, keeps minor+major+critical" "expected 3, got $count"
fi

# --- Test 2: --min-severity major drops info+minor, keeps major+critical ---
uv run "$PIPELINE" severity-filter --min-severity major < "$FIXTURES/mixed-severities.json" > /tmp/test-severity-major.json 2>/dev/null || true
if python3 -c "import json,sys; d=json.load(sys.stdin); assert len(d)==2, f'expected 2, got {len(d)}'" < /tmp/test-severity-major.json 2>/dev/null; then
  ok "--min-severity major drops info+minor, keeps major+critical"
else
  count=$(python3 -c "import json,sys; print(len(json.load(sys.stdin)))" < /tmp/test-severity-major.json 2>/dev/null || echo "error")
  not_ok "--min-severity major drops info+minor, keeps major+critical" "expected 2, got $count"
fi

# --- Test 3: --min-severity critical drops everything below critical ---
uv run "$PIPELINE" severity-filter --min-severity critical < "$FIXTURES/mixed-severities.json" > /tmp/test-severity-critical.json 2>/dev/null || true
if python3 -c "import json,sys; d=json.load(sys.stdin); assert len(d)==1 and d[0]['severity']=='critical', f'expected 1 critical, got {d}'" < /tmp/test-severity-critical.json 2>/dev/null; then
  ok "--min-severity critical drops everything below critical"
else
  result=$(python3 -c "import json,sys; d=json.load(sys.stdin); print(len(d), [s['severity'] for s in d])" < /tmp/test-severity-critical.json 2>/dev/null || echo "error")
  not_ok "--min-severity critical drops everything below critical" "result: $result"
fi

# --- Test 4: --min-severity info keeps all sightings ---
uv run "$PIPELINE" severity-filter --min-severity info < "$FIXTURES/mixed-severities.json" > /tmp/test-severity-info.json 2>/dev/null || true
if python3 -c "import json,sys; d=json.load(sys.stdin); assert len(d)==4, f'expected 4, got {len(d)}'" < /tmp/test-severity-info.json 2>/dev/null; then
  ok "--min-severity info keeps all sightings"
else
  count=$(python3 -c "import json,sys; print(len(json.load(sys.stdin)))" < /tmp/test-severity-info.json 2>/dev/null || echo "error")
  not_ok "--min-severity info keeps all sightings" "expected 4, got $count"
fi

# --- Test 5: severity-filter logs dropped sightings to stderr ---
uv run "$PIPELINE" severity-filter --min-severity major < "$FIXTURES/mixed-severities.json" > /dev/null 2>/tmp/test-severity-stderr.txt || true
stderr_size=$(wc -c < /tmp/test-severity-stderr.txt 2>/dev/null || echo "0")
if [ "$stderr_size" -gt 0 ]; then
  ok "severity-filter logs dropped sightings to stderr"
else
  not_ok "severity-filter logs dropped sightings to stderr" "stderr was empty"
fi

# --- Test 6: severity-filter on empty array outputs empty array ---
echo '[]' | uv run "$PIPELINE" severity-filter --min-severity minor > /tmp/test-severity-empty.json 2>/dev/null || true
if python3 -c "import json,sys; d=json.load(sys.stdin); assert d==[], f'expected [], got {d}'" < /tmp/test-severity-empty.json 2>/dev/null; then
  ok "severity-filter on empty array outputs empty array"
else
  result=$(python3 -c "import json,sys; print(json.load(sys.stdin))" < /tmp/test-severity-empty.json 2>/dev/null || echo "error")
  not_ok "severity-filter on empty array outputs empty array" "got: $result"
fi

# --- Test 7: severity-filter preserves sighting field content ---
uv run "$PIPELINE" severity-filter --min-severity critical < "$FIXTURES/mixed-severities.json" > /tmp/test-severity-fields.json 2>/dev/null || true
if python3 -c "import json,sys; d=json.load(sys.stdin); s=d[0]; assert s['title']=='forEach(async) drops return value silently' and s['type']=='behavioral'" < /tmp/test-severity-fields.json 2>/dev/null; then
  ok "severity-filter preserves sighting field content"
else
  result=$(python3 -c "import json,sys; d=json.load(sys.stdin); print(d[0].get('title','') if d else 'empty')" < /tmp/test-severity-fields.json 2>/dev/null || echo "error")
  not_ok "severity-filter preserves sighting field content" "title: $result"
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
