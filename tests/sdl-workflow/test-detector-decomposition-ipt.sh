#!/usr/bin/env bash
set -uo pipefail

PASS=0
FAIL=0
TOTAL=0

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
PROJECT_ROOT="$(cd "$SCRIPT_DIR/../.." && pwd)"
IPT="$PROJECT_ROOT/assets/agents/fbk-intent-path-tracer.md"

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

# Helper: extract frontmatter (lines between first --- and second ---)
frontmatter() {
  sed -n '2,/^---$/p' "$1" | sed '$d'
}

echo "TAP version 13"

# --- Test 1: Intent Path Tracer agent file exists and is non-empty ---
if [ -s "$IPT" ]; then
  ok "Intent Path Tracer agent file exists and is non-empty"
else
  not_ok "Intent Path Tracer agent file exists and is non-empty" "file: $IPT"
fi

# --- Test 2: Frontmatter name field is non-empty ---
fm=$(frontmatter "$IPT" 2>/dev/null || true)
name_val=$(echo "$fm" | grep '^name:' | sed 's/^name:[[:space:]]*//;s/[[:space:]]*$//')
if [ -n "$name_val" ]; then
  ok "Frontmatter name field is non-empty"
else
  not_ok "Frontmatter name field is non-empty" "name_val='$name_val'"
fi

# --- Test 3: Frontmatter tools field lists Read, Grep, Glob ---
tools_line=$(echo "$fm" | grep '^tools:')
has_read=$(echo "$tools_line" | grep -c 'Read')
has_grep=$(echo "$tools_line" | grep -c 'Grep')
has_glob=$(echo "$tools_line" | grep -c 'Glob')
if [ "$has_read" -gt 0 ] && [ "$has_grep" -gt 0 ] && [ "$has_glob" -gt 0 ]; then
  ok "Frontmatter tools field lists Read, Grep, Glob"
else
  not_ok "Frontmatter tools field lists Read, Grep, Glob" "tools_line='$tools_line'"
fi

# --- Test 4: Body contains path-tracing mandate language (trace and path/execution path) ---
body=$(sed '1,/^---$/d' "$IPT" 2>/dev/null || true)
has_trace=$(echo "$body" | grep -c 'trace')
has_path=$(echo "$body" | grep -ciE 'path|execution path')
if [ "$has_trace" -gt 0 ] && [ "$has_path" -gt 0 ]; then
  ok "Body contains path-tracing mandate language (trace and path/execution path)"
else
  not_ok "Body contains path-tracing mandate language (trace and path/execution path)" "has_trace=$has_trace has_path=$has_path"
fi

# --- Test 5: Body references architectural mismatch or no entry point ---
has_arch=$(echo "$body" | grep -ci 'architectural mismatch')
has_entry=$(echo "$body" | grep -ci 'no entry point')
if [ "$has_arch" -gt 0 ] || [ "$has_entry" -gt 0 ]; then
  ok "Body references architectural mismatch or no entry point"
else
  not_ok "Body references architectural mismatch or no entry point" "has_arch=$has_arch has_entry=$has_entry"
fi

# --- Test 6: Body references intent drift or diverges from intent ---
has_drift=$(echo "$body" | grep -ci 'intent drift')
has_diverge=$(echo "$body" | grep -ci 'diverges from.*intent')
if [ "$has_drift" -gt 0 ] || [ "$has_diverge" -gt 0 ]; then
  ok "Body references intent drift or diverges from intent"
else
  not_ok "Body references intent drift or diverges from intent" "has_drift=$has_drift has_diverge=$has_diverge"
fi

# --- Test 7: Body references unreachable or no reachable implementation ---
has_unreachable=$(echo "$body" | grep -ci 'unreachable')
has_no_reach=$(echo "$body" | grep -ci 'no reachable implementation')
if [ "$has_unreachable" -gt 0 ] || [ "$has_no_reach" -gt 0 ]; then
  ok "Body references unreachable or no reachable implementation"
else
  not_ok "Body references unreachable or no reachable implementation" "has_unreachable=$has_unreachable has_no_reach=$has_no_reach"
fi

# --- Test 8: Body references workflow completeness, inverse, or undo ---
has_workflow=$(echo "$body" | grep -ci 'workflow completeness')
has_inverse=$(echo "$body" | grep -ci 'inverse')
has_undo=$(echo "$body" | grep -ci 'undo')
if [ "$has_workflow" -gt 0 ] || [ "$has_inverse" -gt 0 ] || [ "$has_undo" -gt 0 ]; then
  ok "Body references workflow completeness, inverse, or undo"
else
  not_ok "Body references workflow completeness, inverse, or undo" "has_workflow=$has_workflow has_inverse=$has_inverse has_undo=$has_undo"
fi

# --- Test 9: Body contains sighting output format reference (sighting and S- or IPT-S-) ---
has_sighting=$(echo "$body" | grep -ci 'sighting')
has_format=$(echo "$body" | grep -ciE 'S-|IPT-S-')
if [ "$has_sighting" -gt 0 ] && [ "$has_format" -gt 0 ]; then
  ok "Body contains sighting output format reference (sighting and S- or IPT-S-)"
else
  not_ok "Body contains sighting output format reference (sighting and S- or IPT-S-)" "has_sighting=$has_sighting has_format=$has_format"
fi

# --- Test 10: Body contains detection source intent ---
has_intent=$(echo "$body" | grep -ciE 'detection source.*intent|intent')
if [ "$has_intent" -gt 0 ]; then
  ok "Body contains detection source intent"
else
  not_ok "Body contains detection source intent" "has_intent=$has_intent"
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
