#!/usr/bin/env bash
set -uo pipefail

PASS=0
FAIL=0
TOTAL=0

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
PROJECT_ROOT="$(cd "$SCRIPT_DIR/../.." && pwd)"
DISPATCHER="$PROJECT_ROOT/assets/fbk-scripts/fbk.py"
FIXTURES="$PROJECT_ROOT/tests/fixtures/pipeline"

trap 'rm -f /tmp/test-md-*.md /tmp/test-md-sighting-input.json' EXIT

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

# Generate inline sighting fixture
cat > /tmp/test-md-sighting-input.json <<'EOJSON'
[{"id":"S-01","title":"forEach(async) drops return value silently","location":{"file":"src/handler.ts","start_line":42,"end_line":55},"type":"behavioral","severity":"critical","origin":"introduced","detection_source":"intent","pattern":"async-in-sync-iterator","mechanism":"forEach(async callback) discards the Promise returned by each iteration","consequence":"Callbacks execute concurrently with no error propagation to the caller","evidence":"Lines 42-48: bookingHandler.forEach(async (booking) => ...)","remediation":"Replace forEach(async) with for...of loop"}]
EOJSON

python3 "$DISPATCHER" pipeline to-markdown < /tmp/test-md-sighting-input.json > /tmp/test-md-sighting.md 2>/dev/null || true
python3 "$DISPATCHER" pipeline to-markdown < "$FIXTURES/finding-for-markdown.json" > /tmp/test-md-finding.md 2>/dev/null || true

# --- Test 1: to-markdown converts sighting to markdown with S-NN header ---
if grep -q '### S-01' /tmp/test-md-sighting.md 2>/dev/null; then
  ok "to-markdown converts sighting to markdown with S-NN header"
else
  not_ok "to-markdown converts sighting to markdown with S-NN header" "### S-01 not found in output"
fi

# --- Test 2: to-markdown sighting output contains mechanism field ---
if grep -q 'Mechanism' /tmp/test-md-sighting.md 2>/dev/null; then
  ok "to-markdown sighting output contains mechanism field"
else
  not_ok "to-markdown sighting output contains mechanism field" "Mechanism not found in sighting output"
fi

# --- Test 3: to-markdown sighting output contains consequence field ---
if grep -q 'Consequence' /tmp/test-md-sighting.md 2>/dev/null; then
  ok "to-markdown sighting output contains consequence field"
else
  not_ok "to-markdown sighting output contains consequence field" "Consequence not found in sighting output"
fi

# --- Test 4: to-markdown sighting output contains location with file and lines ---
if grep -q 'src/handler.ts' /tmp/test-md-sighting.md 2>/dev/null; then
  ok "to-markdown sighting output contains location with file and lines"
else
  not_ok "to-markdown sighting output contains location with file and lines" "src/handler.ts not found in sighting output"
fi

# --- Test 5: to-markdown sighting output contains type and severity ---
if grep -q 'behavioral' /tmp/test-md-sighting.md 2>/dev/null && grep -q 'critical' /tmp/test-md-sighting.md 2>/dev/null; then
  ok "to-markdown sighting output contains type and severity"
else
  not_ok "to-markdown sighting output contains type and severity" "behavioral or critical not found in sighting output"
fi

# --- Test 6: to-markdown converts finding to markdown with F-NN header ---
if grep -q '### F-01' /tmp/test-md-finding.md 2>/dev/null; then
  ok "to-markdown converts finding to markdown with F-NN header"
else
  not_ok "to-markdown converts finding to markdown with F-NN header" "### F-01 not found in finding output"
fi

# --- Test 7: to-markdown finding output contains verification evidence ---
if grep -q 'Verification' /tmp/test-md-finding.md 2>/dev/null && grep -q 'Traced caller chain' /tmp/test-md-finding.md 2>/dev/null; then
  ok "to-markdown finding output contains verification evidence"
else
  not_ok "to-markdown finding output contains verification evidence" "Verification or 'Traced caller chain' not found in finding output"
fi

# --- Test 8: to-markdown finding output contains reclassification note ---
if grep -qiE 'reclassif|originally' /tmp/test-md-finding.md 2>/dev/null; then
  ok "to-markdown finding output contains reclassification note"
else
  not_ok "to-markdown finding output contains reclassification note" "reclassification language not found in finding output"
fi

# --- Test 9: to-markdown excludes rejected-as-nit findings from output ---
if ! grep -q 'Style nit' /tmp/test-md-finding.md 2>/dev/null; then
  ok "to-markdown excludes rejected-as-nit findings from output"
else
  not_ok "to-markdown excludes rejected-as-nit findings from output" "rejected-as-nit finding appeared in output"
fi

# --- Test 10: to-markdown on empty array produces empty or minimal output ---
if echo '[]' | python3 "$DISPATCHER" pipeline to-markdown > /tmp/test-md-empty.md 2>/dev/null; then
  if ! grep -q '### ' /tmp/test-md-empty.md 2>/dev/null; then
    ok "to-markdown on empty array produces empty or minimal output"
  else
    not_ok "to-markdown on empty array produces empty or minimal output" "unexpected headers found in empty output"
  fi
else
  not_ok "to-markdown on empty array produces empty or minimal output" "pipeline to-markdown exited non-zero on empty input"
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
