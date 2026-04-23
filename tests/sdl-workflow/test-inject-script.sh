#!/usr/bin/env bash
set -uo pipefail

PASS=0
FAIL=0
TOTAL=0

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
PROJECT_ROOT="$(cd "$SCRIPT_DIR/../.." && pwd)"
INJECT="$PROJECT_ROOT/ai-docs/detection-accuracy/martian-benchmark/inject_results.py"
FIXTURES="$PROJECT_ROOT/tests/fixtures/pipeline"

# Prefer the fbk-scripts venv python (parity with other tests); fall back to
# system python3. inject_results.py is stdlib-only so either works — this
# pattern just avoids needing `uv` on the CI runner.
VENV_PY="$PROJECT_ROOT/assets/fbk-scripts/.venv/bin/python3"
if [[ -x "$VENV_PY" ]]; then
  PYTHON="$VENV_PY"
else
  PYTHON="python3"
fi

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

trap 'rm -f /tmp/test-inject-*.json' EXIT

echo "TAP version 13"

# --- Test 1: inject_results.py exists and is non-empty ---
if [ -s "$INJECT" ]; then
  ok "inject_results.py exists and is non-empty"
else
  not_ok "inject_results.py exists and is non-empty" "file: $INJECT"
fi

# --- Run dry-run once and reuse output for tests 2-8 ---
"$PYTHON" "$INJECT" --dry-run --input "$FIXTURES/verified-findings.json" --tool-name firebreak \
  > /tmp/test-inject-out.json 2>/dev/null || true

# --- Test 2: inject script maps location.file to path field ---
if python3 -c "import json,sys; d=json.load(sys.stdin); assert d[0]['path']=='src/handler.ts'" \
     < /tmp/test-inject-out.json 2>/dev/null; then
  ok "inject script maps location.file to path field"
else
  not_ok "inject script maps location.file to path field" "expected path='src/handler.ts' in first finding"
fi

# --- Test 3: inject script maps location.start_line to line field ---
if python3 -c "import json,sys; d=json.load(sys.stdin); assert d[0]['line']==42" \
     < /tmp/test-inject-out.json 2>/dev/null; then
  ok "inject script maps location.start_line to line field"
else
  not_ok "inject script maps location.start_line to line field" "expected line=42 in first finding"
fi

# --- Test 4: inject script maps mechanism+consequence to body field ---
if python3 -c "
import json,sys
d=json.load(sys.stdin)
b=d[0]['body']
assert 'forEach' in b and 'Callbacks execute' in b
" < /tmp/test-inject-out.json 2>/dev/null; then
  ok "inject script maps mechanism+consequence to body field"
else
  not_ok "inject script maps mechanism+consequence to body field" "body field missing mechanism or consequence content"
fi

# --- Test 5: inject script maps severity field directly ---
if python3 -c "import json,sys; d=json.load(sys.stdin); assert d[0]['severity']=='critical'" \
     < /tmp/test-inject-out.json 2>/dev/null; then
  ok "inject script maps severity field directly"
else
  not_ok "inject script maps severity field directly" "expected severity='critical' in first finding"
fi

# --- Test 6: inject script passes type field through ---
if python3 -c "import json,sys; d=json.load(sys.stdin); assert d[0]['type']=='behavioral'" \
     < /tmp/test-inject-out.json 2>/dev/null; then
  ok "inject script passes type field through"
else
  not_ok "inject script passes type field through" "expected type='behavioral' in first finding"
fi

# --- Test 7: inject script passes origin field through ---
if python3 -c "import json,sys; d=json.load(sys.stdin); assert d[0].get('origin')=='introduced'" \
     < /tmp/test-inject-out.json 2>/dev/null; then
  ok "inject script passes origin field through"
else
  not_ok "inject script passes origin field through" "expected origin='introduced' in first finding"
fi

# --- Test 8: inject script passes reclassified_from through ---
if python3 -c "
import json,sys
d=json.load(sys.stdin)
rf=d[1].get('reclassified_from',{})
assert rf.get('type')=='fragile', f'reclassified_from={rf}'
" < /tmp/test-inject-out.json 2>/dev/null; then
  ok "inject script passes reclassified_from through"
else
  not_ok "inject script passes reclassified_from through" "expected reclassified_from.type='fragile' in second finding"
fi

# --- Test 9: inject script --min-severity filters output ---
"$PYTHON" "$INJECT" --dry-run --input "$FIXTURES/verified-findings.json" \
  --tool-name firebreak --min-severity major \
  > /tmp/test-inject-filtered.json 2>/dev/null || true
if python3 -c "
import json,sys
d=json.load(sys.stdin)
assert len(d)==2, f'expected 2, got {len(d)}'
" < /tmp/test-inject-filtered.json 2>/dev/null; then
  ok "inject script --min-severity filters output"
else
  not_ok "inject script --min-severity filters output" "expected 2 findings after --min-severity major filter"
fi

# --- Test 10: inject script does not use regex-based markdown parsing ---
if ! grep -qE 're\.compile|re\.search|re\.findall|_is_metadata_line|parse_findings_flat' "$INJECT" 2>/dev/null; then
  ok "inject script does not use regex-based markdown parsing"
else
  not_ok "inject script does not use regex-based markdown parsing" "found legacy regex parsing patterns in script"
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
