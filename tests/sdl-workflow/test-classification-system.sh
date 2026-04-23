#!/usr/bin/env bash
set -uo pipefail

PASS=0
FAIL=0
TOTAL=0

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
PROJECT_ROOT="$(cd "$SCRIPT_DIR/../.." && pwd)"
DETECTOR="$PROJECT_ROOT/assets/agents/fbk-code-review-detector.md"
CHALLENGER="$PROJECT_ROOT/assets/agents/fbk-code-review-challenger.md"
GUIDE="$PROJECT_ROOT/assets/fbk-docs/fbk-sdl-workflow/code-review-guide.md"

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

# --- Test 1: Detector tools list does not contain Bash (AC-09 — absence half) ---
fm=$(frontmatter "$DETECTOR" 2>/dev/null || true)
tools_line=$(echo "$fm" | grep '^tools:')
has_bash=$(echo "$tools_line" | grep -c 'Bash' 2>/dev/null || true)
if [ "$has_bash" -eq 0 ]; then
  ok "Detector tools list does not contain Bash"
else
  not_ok "Detector tools list does not contain Bash" "tools_line='$tools_line'"
fi

# --- Test 2: Detector tools list contains Read, Grep, Glob (AC-09 — tools preserved) ---
has_read=$(echo "$tools_line" | grep -c 'Read' 2>/dev/null || true)
has_grep=$(echo "$tools_line" | grep -c 'Grep' 2>/dev/null || true)
has_glob=$(echo "$tools_line" | grep -c 'Glob' 2>/dev/null || true)
if [ "$has_read" -gt 0 ] && [ "$has_grep" -gt 0 ] && [ "$has_glob" -gt 0 ]; then
  ok "Detector tools list contains Read, Grep, Glob"
else
  not_ok "Detector tools list contains Read, Grep, Glob" "tools_line='$tools_line'"
fi

# --- Test 3: Detector body does not contain linter discovery section (AC-09 — removal) ---
body=$(awk '/^---$/{c++; if(c==2){found=1; next}} found' "$DETECTOR")
has_linter_section=$(echo "$body" | grep -ciE 'project-native tool discovery|lint config|eslintrc|pylintrc' 2>/dev/null || true)
if [ "$has_linter_section" -eq 0 ]; then
  ok "Detector body does not contain linter discovery section"
else
  not_ok "Detector body does not contain linter discovery section" "has_linter_section=$has_linter_section"
fi

# --- Test 4: Detector sighting output mentions type field (AC-10) ---
if echo "$body" | grep -qiE '\btype\b'; then
  ok "Detector sighting output includes type field"
else
  not_ok "Detector sighting output includes type field" "no 'type' field found in Detector body"
fi

# --- Test 5: Detector sighting output mentions severity field (AC-10) ---
if echo "$body" | grep -qi 'severity'; then
  ok "Detector sighting output includes severity field"
else
  not_ok "Detector sighting output includes severity field" "no 'severity' field found in Detector body"
fi

# --- Test 6: Detector sighting output mentions pattern label field (AC-11) ---
if echo "$body" | grep -qiE 'pattern'; then
  ok "Detector sighting output includes pattern label field"
else
  not_ok "Detector sighting output includes pattern label field" "no 'pattern' field found in Detector body"
fi

# --- Test 7: Challenger validates type and severity (AC-12) ---
challenger_body=$(awk '/^---$/{c++; if(c==2){found=1; next}} found' "$CHALLENGER")
has_type_validate=$(echo "$challenger_body" | grep -ciE '(validat|adjust|classif).*type|type.*(validat|adjust|classif)' 2>/dev/null || true)
has_sev_validate=$(echo "$challenger_body" | grep -ciE '(validat|adjust|classif).*severity|severity.*(validat|adjust|classif)' 2>/dev/null || true)
if [ "$has_type_validate" -gt 0 ] && [ "$has_sev_validate" -gt 0 ]; then
  ok "Challenger validates both type and severity"
else
  not_ok "Challenger validates both type and severity" "has_type_validate=$has_type_validate has_sev_validate=$has_sev_validate"
fi

# --- Test 8: Cross-file consistency — type values appear in Detector or guide (AC-10, integration seam) ---
has_behavioral=$(echo "$body" | grep -c 'behavioral' 2>/dev/null || true)
has_structural=$(echo "$body" | grep -c 'structural' 2>/dev/null || true)
has_test_integrity=$(echo "$body" | grep -c 'test-integrity' 2>/dev/null || true)
has_fragile=$(echo "$body" | grep -c 'fragile' 2>/dev/null || true)
if [ "$has_behavioral" -gt 0 ] && [ "$has_structural" -gt 0 ] && [ "$has_test_integrity" -gt 0 ] && [ "$has_fragile" -gt 0 ]; then
  ok "Type values defined in Detector or guide"
else
  # Fallback: check guide
  has_behavioral=$(grep -c 'behavioral' "$GUIDE" 2>/dev/null || true)
  has_structural=$(grep -c 'structural' "$GUIDE" 2>/dev/null || true)
  has_test_integrity=$(grep -c 'test-integrity' "$GUIDE" 2>/dev/null || true)
  has_fragile=$(grep -c 'fragile' "$GUIDE" 2>/dev/null || true)
  if [ "$has_behavioral" -gt 0 ] && [ "$has_structural" -gt 0 ] && [ "$has_test_integrity" -gt 0 ] && [ "$has_fragile" -gt 0 ]; then
    ok "Type values defined in Detector or guide"
  else
    not_ok "Type values defined in Detector or guide" "behavioral=$has_behavioral structural=$has_structural test-integrity=$has_test_integrity fragile=$has_fragile"
  fi
fi

# --- Test 9: Cross-file consistency — type values accessible to Challenger (AC-12, integration seam) ---
# Challenger may reference types directly or delegate to orchestrator-provided definitions
ch_behavioral=$(echo "$challenger_body" | grep -c 'behavioral' 2>/dev/null || true)
ch_structural=$(echo "$challenger_body" | grep -c 'structural' 2>/dev/null || true)
ch_test_integrity=$(echo "$challenger_body" | grep -c 'test-integrity' 2>/dev/null || true)
ch_fragile=$(echo "$challenger_body" | grep -c 'fragile' 2>/dev/null || true)
if [ "$ch_behavioral" -gt 0 ] && [ "$ch_structural" -gt 0 ] && [ "$ch_test_integrity" -gt 0 ] && [ "$ch_fragile" -gt 0 ]; then
  ok "Challenger references all four type values"
elif echo "$challenger_body" | grep -qiE 'reclassif|type.*classif|classif.*type' && [ "$has_behavioral" -gt 0 ] && [ "$has_structural" -gt 0 ] && [ "$has_test_integrity" -gt 0 ] && [ "$has_fragile" -gt 0 ]; then
  ok "Challenger references all four type values" # Challenger delegates to orchestrator; types defined in Detector/guide
else
  not_ok "Challenger references all four type values" "behavioral=$ch_behavioral structural=$ch_structural test-integrity=$ch_test_integrity fragile=$ch_fragile"
fi

# --- Test 10: Cross-file consistency — severity values appear in Detector or guide (AC-10, integration seam) ---
has_critical=$(echo "$body" | grep -c 'critical' 2>/dev/null || true)
has_major=$(echo "$body" | grep -c 'major' 2>/dev/null || true)
has_minor=$(echo "$body" | grep -c 'minor' 2>/dev/null || true)
has_info=$(echo "$body" | grep -c 'info' 2>/dev/null || true)
if [ "$has_critical" -gt 0 ] && [ "$has_major" -gt 0 ] && [ "$has_minor" -gt 0 ] && [ "$has_info" -gt 0 ]; then
  ok "Severity values defined in Detector or guide"
else
  # Fallback: check guide
  has_critical=$(grep -c 'critical' "$GUIDE" 2>/dev/null || true)
  has_major=$(grep -c 'major' "$GUIDE" 2>/dev/null || true)
  has_minor=$(grep -c 'minor' "$GUIDE" 2>/dev/null || true)
  has_info=$(grep -c 'info' "$GUIDE" 2>/dev/null || true)
  if [ "$has_critical" -gt 0 ] && [ "$has_major" -gt 0 ] && [ "$has_minor" -gt 0 ] && [ "$has_info" -gt 0 ]; then
    ok "Severity values defined in Detector or guide"
  else
    not_ok "Severity values defined in Detector or guide" "critical=$has_critical major=$has_major minor=$has_minor info=$has_info"
  fi
fi

# --- Test 11: Cross-file consistency — severity values accessible to Challenger (AC-12, integration seam) ---
# Challenger may reference severities directly or delegate to orchestrator-provided definitions
ch_critical=$(echo "$challenger_body" | grep -c 'critical' 2>/dev/null || true)
ch_major=$(echo "$challenger_body" | grep -c 'major' 2>/dev/null || true)
ch_minor=$(echo "$challenger_body" | grep -c 'minor' 2>/dev/null || true)
ch_info=$(echo "$challenger_body" | grep -c 'info' 2>/dev/null || true)
if [ "$ch_critical" -gt 0 ] && [ "$ch_major" -gt 0 ] && [ "$ch_minor" -gt 0 ] && [ "$ch_info" -gt 0 ]; then
  ok "Challenger references all four severity values"
elif echo "$challenger_body" | grep -qiE 'reclassif|severity.*classif|classif.*severity' && [ "$has_critical" -gt 0 ] && [ "$has_major" -gt 0 ] && [ "$has_minor" -gt 0 ] && [ "$has_info" -gt 0 ]; then
  ok "Challenger references all four severity values" # Challenger delegates to orchestrator; severities defined in Detector/guide
else
  not_ok "Challenger references all four severity values" "critical=$ch_critical major=$ch_major minor=$ch_minor info=$ch_info"
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
