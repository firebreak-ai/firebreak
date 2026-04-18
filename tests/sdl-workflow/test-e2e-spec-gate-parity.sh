#!/usr/bin/env bash
set -uo pipefail

PASS=0
FAIL=0
TOTAL=0

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
PROJECT_ROOT="$(cd "$SCRIPT_DIR/../.." && pwd)"
DISPATCHER="$PROJECT_ROOT/assets/fbk-scripts/fbk.py"
GOLDEN="$PROJECT_ROOT/tests/fixtures/specs"

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

# --- Test 1: valid spec — same result value as golden ---
GOLDEN_RESULT="$(python3 -c "import json,sys; d=json.load(open('$GOLDEN/golden-spec-gate-valid.json')); print(d['result'])")"
STDOUT=$(python3 "$DISPATCHER" spec-gate "$GOLDEN/../specs/valid-spec.md" 2>/tmp/parity-stderr)
RC=$?
PY_RESULT="$(echo "$STDOUT" | python3 -c "import json,sys; d=json.load(sys.stdin); print(d['result'])" 2>/dev/null || true)"
if [ "$RC" -eq 0 ] && [ "$PY_RESULT" = "$GOLDEN_RESULT" ]; then
  ok "valid spec: exit 0 and result matches golden ($PY_RESULT)"
else
  not_ok "valid spec: exit 0 and result matches golden" "rc=$RC py_result='$PY_RESULT' golden_result='$GOLDEN_RESULT'"
fi

# --- Test 2: missing sections — exit 2 and contains same key phrases as golden ---
STDOUT=$(python3 "$DISPATCHER" spec-gate "$GOLDEN/../specs/missing-sections-spec.md" 2>/tmp/parity-stderr)
RC=$?
STDERR=$(cat /tmp/parity-stderr)
GOLDEN_PHRASES="$(grep -oE 'Missing section: [^$]+' "$GOLDEN/golden-spec-gate-missing.txt" | sort || true)"
PY_PHRASES="$(echo "$STDERR" | grep -oE 'Missing section: [^$]+' | sort || true)"
if [ "$RC" -eq 2 ] && echo "$STDERR" | grep -q "Missing section" && [ "$PY_PHRASES" = "$GOLDEN_PHRASES" ]; then
  ok "missing sections: exit 2 and 'Missing section' phrases match golden"
else
  not_ok "missing sections: exit 2 and 'Missing section' phrases match golden" "rc=$RC py_phrases='$PY_PHRASES' golden_phrases='$GOLDEN_PHRASES'"
fi

# --- Test 3: injection markers — exit 0 and WARNING count matches golden ---
GOLDEN_WARN_COUNT="$(grep -c "^WARNING:" "$GOLDEN/golden-spec-gate-injection.txt" || true)"
STDOUT=$(python3 "$DISPATCHER" spec-gate "$GOLDEN/../specs/injection-attempt-spec.md" 2>/tmp/parity-stderr)
RC=$?
STDERR=$(cat /tmp/parity-stderr)
PY_WARN_COUNT="$(echo "$STDERR" | grep -c "^WARNING:" || true)"
if [ "$RC" -eq 0 ] && [ "$PY_WARN_COUNT" -eq "$GOLDEN_WARN_COUNT" ]; then
  ok "injection markers: exit 0 and WARNING count matches golden ($PY_WARN_COUNT/$GOLDEN_WARN_COUNT)"
else
  not_ok "injection markers: exit 0 and WARNING count matches golden" "rc=$RC py_warnings=$PY_WARN_COUNT golden_warnings=$GOLDEN_WARN_COUNT"
fi

# --- Summary ---
rm -f /tmp/parity-stderr
echo ""
echo "# $PASS/$TOTAL tests passed"
if [ "$FAIL" -gt 0 ]; then
  exit 1
fi
exit 0
