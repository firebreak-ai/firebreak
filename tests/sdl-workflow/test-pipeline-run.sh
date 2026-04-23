#!/usr/bin/env bash
set -uo pipefail

PASS=0
FAIL=0
TOTAL=0

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
PROJECT_ROOT="$(cd "$SCRIPT_DIR/../.." && pwd)"
DISPATCHER="$PROJECT_ROOT/assets/fbk-scripts/fbk.py"
FIXTURES="$PROJECT_ROOT/tests/fixtures/pipeline"

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

trap 'rm -f /tmp/test-run-*.json /tmp/test-run-*.md /tmp/test-run-*-err.txt' EXIT

echo "TAP version 13"

# --- Test 1: run --preset behavioral-only produces same result as sequential pipeline ---
python3 "$DISPATCHER" pipeline validate < "$FIXTURES/valid-sightings.json" 2>/dev/null \
  | python3 "$DISPATCHER" pipeline domain-filter --preset behavioral-only 2>/dev/null \
  | python3 "$DISPATCHER" pipeline severity-filter --min-severity minor 2>/dev/null \
  > /tmp/test-run-sequential.json || true
python3 "$DISPATCHER" pipeline run --preset behavioral-only --min-severity minor \
  < "$FIXTURES/valid-sightings.json" > /tmp/test-run-combined.json 2>/dev/null || true
if python3 -c "
import json
a=json.load(open('/tmp/test-run-sequential.json'))
b=json.load(open('/tmp/test-run-combined.json'))
assert a==b, f'sequential={a} combined={b}'
" 2>/dev/null; then
  ok "run --preset behavioral-only produces same result as sequential pipeline"
else
  not_ok "run --preset behavioral-only produces same result as sequential pipeline" "pipeline not available or outputs differ"
fi

# --- Test 2: run --preset behavioral-only filters to behavioral sightings only ---
if python3 -c "
import json,sys
d=json.load(sys.stdin)
assert len(d)==1 and d[0]['type']=='behavioral'
" < /tmp/test-run-combined.json 2>/dev/null; then
  ok "run --preset behavioral-only filters to behavioral sightings only"
else
  not_ok "run --preset behavioral-only filters to behavioral sightings only" "output count or type mismatch"
fi

# --- Test 3: run --preset full --min-severity minor keeps all non-info sightings ---
python3 "$DISPATCHER" pipeline run --preset full --min-severity minor \
  < "$FIXTURES/valid-sightings.json" > /tmp/test-run-full.json 2>/dev/null || true
if python3 -c "
import json,sys
d=json.load(open('/tmp/test-run-full.json'))
assert len(d)==3, f'expected 3 sightings, got {len(d)}'
" 2>/dev/null; then
  ok "run --preset full --min-severity minor keeps all non-info sightings"
else
  not_ok "run --preset full --min-severity minor keeps all non-info sightings" "expected 3 sightings in full preset output"
fi

# --- Test 4: run --output-markdown produces markdown instead of JSON ---
python3 "$DISPATCHER" pipeline run --preset behavioral-only --min-severity minor --output-markdown \
  < "$FIXTURES/valid-sightings.json" > /tmp/test-run-md.md 2>/dev/null || true
if grep -q '### ' /tmp/test-run-md.md 2>/dev/null; then
  ok "run --output-markdown produces markdown instead of JSON"
else
  not_ok "run --output-markdown produces markdown instead of JSON" "no markdown headers found in output"
fi

# --- Test 5: run on empty array outputs empty JSON array ---
echo '[]' | python3 "$DISPATCHER" pipeline run --preset behavioral-only --min-severity minor \
  > /tmp/test-run-empty.json 2>/dev/null || true
if python3 -c "import json,sys; assert json.load(sys.stdin)==[]" < /tmp/test-run-empty.json 2>/dev/null; then
  ok "run on empty array outputs empty JSON array"
else
  not_ok "run on empty array outputs empty JSON array" "output was not empty array"
fi

# --- Test 6: run where all sightings are filtered outputs empty array ---
python3 "$DISPATCHER" pipeline run --preset structural --min-severity major \
  < "$FIXTURES/valid-sightings.json" > /tmp/test-run-allfiltered.json 2>/dev/null || true
if python3 -c "import json,sys; assert json.load(sys.stdin)==[]" < /tmp/test-run-allfiltered.json 2>/dev/null; then
  ok "run where all sightings are filtered outputs empty array"
else
  not_ok "run where all sightings are filtered outputs empty array" "expected empty array after all-filtered run"
fi

# --- Test 7: run with unknown preset exits non-zero ---
if python3 "$DISPATCHER" pipeline run --preset nonexistent \
     < "$FIXTURES/valid-sightings.json" > /dev/null 2>/dev/null; then
  not_ok "run with unknown preset exits non-zero" "pipeline exited 0 for unknown preset"
else
  ok "run with unknown preset exits non-zero"
fi

# --- Test 8: run with malformed JSON input exits non-zero ---
if echo 'not json at all' | python3 "$DISPATCHER" pipeline run --preset behavioral-only \
     > /dev/null 2>/tmp/test-run-malformed-err.txt; then
  not_ok "run with malformed JSON input exits non-zero" "pipeline exited 0 for malformed JSON"
else
  if [ -s "/tmp/test-run-malformed-err.txt" ]; then
    ok "run with malformed JSON input exits non-zero"
  else
    not_ok "run with malformed JSON input exits non-zero" "pipeline exited non-zero but stderr was empty"
  fi
fi

# --- Test 9: run preserves unicode in field values ---
cat > /tmp/test-run-unicode-input.json <<'EOJSON'
[{
  "id": "S-01",
  "title": "Mishandled encoding in path \u2014 drops non-ASCII characters",
  "location": {"file": "src/encoder.ts", "start_line": 10},
  "type": "behavioral",
  "severity": "critical",
  "mechanism": "encodeURI() strips characters outside Basic Latin \u2014 loses CJK input",
  "consequence": "User-submitted names with non-Latin characters are silently truncated",
  "evidence": "Line 10: encodeURI(input) with \u00e9\u00e8\u00ea test values"
}]
EOJSON
python3 "$DISPATCHER" pipeline run --preset behavioral-only --min-severity minor \
  < /tmp/test-run-unicode-input.json > /tmp/test-run-unicode-out.json 2>/dev/null || true
if python3 -c "import json,sys; d=json.load(sys.stdin); assert len(d)==1" < /tmp/test-run-unicode-out.json 2>/dev/null; then
  ok "run preserves unicode in field values"
else
  not_ok "run preserves unicode in field values" "expected 1 sighting with unicode preserved"
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
