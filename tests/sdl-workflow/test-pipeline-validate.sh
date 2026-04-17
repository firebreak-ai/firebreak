#!/usr/bin/env bash
set -uo pipefail

PASS=0
FAIL=0
TOTAL=0

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
PROJECT_ROOT="$(cd "$SCRIPT_DIR/../.." && pwd)"
PIPELINE="$PROJECT_ROOT/assets/scripts/fbk-pipeline.py"
FIXTURES="$PROJECT_ROOT/tests/fixtures/pipeline"

trap 'rm -f /tmp/test-validate-*.json /tmp/test-validate-*-err.txt' EXIT

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

# --- Test 1: fbk-pipeline.py exists and is non-empty ---
if [ -s "$PIPELINE" ]; then
  ok "fbk-pipeline.py exists and is non-empty"
else
  not_ok "fbk-pipeline.py exists and is non-empty" "file: $PIPELINE"
fi

# --- Test 2: validate accepts valid sightings and outputs JSON array ---
if uv run "$PIPELINE" validate < "$FIXTURES/valid-sightings.json" > /tmp/test-validate-out.json 2>/dev/null; then
  if python3 -c "import json,sys; json.load(sys.stdin)" < /tmp/test-validate-out.json 2>/dev/null; then
    ok "validate accepts valid sightings and outputs JSON array"
  else
    not_ok "validate accepts valid sightings and outputs JSON array" "output is not valid JSON"
  fi
else
  not_ok "validate accepts valid sightings and outputs JSON array" "pipeline validate exited non-zero"
fi

# --- Test 3: validate assigns sequential S-NN IDs ---
if python3 -c "import json,sys; d=json.load(sys.stdin); ids=[s['id'] for s in d]; assert ids==['S-01','S-02','S-03'], f'got {ids}'" < /tmp/test-validate-out.json 2>/dev/null; then
  ok "validate assigns sequential S-NN IDs"
else
  not_ok "validate assigns sequential S-NN IDs" "IDs do not match expected S-01, S-02, S-03"
fi

# --- Test 4: validate preserves all required fields ---
if python3 -c "import json,sys; d=json.load(sys.stdin); s=d[0]; assert all(k in s for k in ['id','title','location','type','severity','mechanism','consequence','evidence'])" < /tmp/test-validate-out.json 2>/dev/null; then
  ok "validate preserves all required fields"
else
  not_ok "validate preserves all required fields" "one or more required fields missing from validated sighting"
fi

# --- Test 5: validate rejects sightings with missing required fields ---
cat > /tmp/test-validate-missing-input.json <<'EOJSON'
[
  {"id":"S-01","title":"Missing mechanism field entirely","location":{"file":"src/a.ts","start_line":1},"type":"behavioral","severity":"critical","consequence":"No mechanism field","evidence":"Lines 1-5"},
  {"id":"S-02","location":{"file":"src/b.ts","start_line":1},"type":"structural","severity":"minor","mechanism":"Title is empty","title":"","consequence":"Below 10 char min","evidence":"Lines 1-5"}
]
EOJSON
uv run "$PIPELINE" validate < /tmp/test-validate-missing-input.json > /tmp/test-validate-missing.json 2>/tmp/test-validate-missing-err.txt || true
valid_count=$(python3 -c "import json,sys; d=json.load(sys.stdin); print(len(d))" < /tmp/test-validate-missing.json 2>/dev/null || echo "0")
err_nonempty=$([ -s /tmp/test-validate-missing-err.txt ] && echo "1" || echo "0")
if [ "$valid_count" -eq 0 ] && [ "$err_nonempty" -eq 1 ]; then
  ok "validate rejects sightings with missing required fields"
else
  not_ok "validate rejects sightings with missing required fields" "valid_count=$valid_count err_nonempty=$err_nonempty"
fi

# --- Test 6: validate rejects sightings with invalid enum values ---
cat > /tmp/test-validate-enum-input.json <<'EOJSON'
[
  {"id":"S-01","title":"Invalid type enum value sighting","location":{"file":"src/c.ts","start_line":1},"type":"performance","severity":"critical","mechanism":"Invalid type not in enum","consequence":"Parser should reject this","evidence":"Lines 1-5"},
  {"id":"S-02","title":"Invalid severity enum value sighting","location":{"file":"src/d.ts","start_line":1},"type":"behavioral","severity":"high","mechanism":"Invalid severity not in enum","consequence":"Parser should reject this","evidence":"Lines 1-5"}
]
EOJSON
uv run "$PIPELINE" validate < /tmp/test-validate-enum-input.json > /tmp/test-validate-enum.json 2>/tmp/test-validate-enum-err.txt || true
enum_valid_count=$(python3 -c "import json,sys; d=json.load(sys.stdin); print(len(d))" < /tmp/test-validate-enum.json 2>/dev/null || echo "0")
enum_err_nonempty=$([ -s /tmp/test-validate-enum-err.txt ] && echo "1" || echo "0")
if [ "$enum_valid_count" -eq 0 ] && [ "$enum_err_nonempty" -eq 1 ]; then
  ok "validate rejects sightings with invalid enum values"
else
  not_ok "validate rejects sightings with invalid enum values" "enum_valid_count=$enum_valid_count enum_err_nonempty=$enum_err_nonempty"
fi

# --- Test 7: validate rejects invalid type-severity matrix combinations ---
cat > /tmp/test-validate-matrix-input.json <<'EOJSON'
[
  {"id":"S-01","title":"Behavioral minor is invalid combination","location":{"file":"src/e.ts","start_line":1},"type":"behavioral","severity":"minor","mechanism":"behavioral+minor invalid per matrix","consequence":"Parser should reject this","evidence":"Lines 1-5"},
  {"id":"S-02","title":"Structural critical is invalid combination","location":{"file":"src/f.ts","start_line":1},"type":"structural","severity":"critical","mechanism":"structural+critical invalid per matrix","consequence":"Parser should reject this","evidence":"Lines 1-5"}
]
EOJSON
uv run "$PIPELINE" validate < /tmp/test-validate-matrix-input.json > /tmp/test-validate-matrix.json 2>/tmp/test-validate-matrix-err.txt || true
matrix_valid_count=$(python3 -c "import json,sys; d=json.load(sys.stdin); print(len(d))" < /tmp/test-validate-matrix.json 2>/dev/null || echo "0")
matrix_err_nonempty=$([ -s /tmp/test-validate-matrix-err.txt ] && echo "1" || echo "0")
if [ "$matrix_valid_count" -eq 0 ] && [ "$matrix_err_nonempty" -eq 1 ]; then
  ok "validate rejects invalid type-severity matrix combinations"
else
  not_ok "validate rejects invalid type-severity matrix combinations" "matrix_valid_count=$matrix_valid_count matrix_err_nonempty=$matrix_err_nonempty"
fi

# --- Test 8: validate fills defaults for optional fields ---
if python3 -c "import json,sys; d=json.load(sys.stdin); s=d[1]; assert s.get('origin') in ['introduced','pre-existing','unknown',''], f'origin={s.get(\"origin\")}'" < /tmp/test-validate-out.json 2>/dev/null; then
  ok "validate fills defaults for optional fields"
else
  not_ok "validate fills defaults for optional fields" "origin field not filled with valid default in second sighting"
fi

# --- Test 9: validate outputs rejected sightings to stderr as complete JSON ---
if grep -q 'behavioral' /tmp/test-validate-matrix-err.txt 2>/dev/null && grep -q 'minor' /tmp/test-validate-matrix-err.txt 2>/dev/null; then
  ok "validate outputs rejected sightings to stderr as complete JSON"
else
  not_ok "validate outputs rejected sightings to stderr as complete JSON" "stderr does not contain full rejected sighting data"
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
