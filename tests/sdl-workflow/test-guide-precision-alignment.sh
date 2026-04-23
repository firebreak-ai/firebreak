#!/usr/bin/env bash
set -uo pipefail

PASS=0
FAIL=0
TOTAL=0

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
PROJECT_ROOT="$(cd "$SCRIPT_DIR/../.." && pwd)"
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

echo "TAP version 13"

# --- Test 1: Guide type definitions use consequence-based language for behavioral ---
behavioral_consequence=$(grep -ciE 'behavioral.*(concrete|constructible input)|constructible input.*behavioral' "$GUIDE" 2>/dev/null || true)
if [ "$behavioral_consequence" -gt 0 ]; then
  ok "Guide type definitions use consequence-based language for behavioral"
else
  not_ok "Guide type definitions use consequence-based language for behavioral" "count=$behavioral_consequence"
fi

# --- Test 2: Guide type definitions use consequence-based language for structural ---
structural_consequence=$(grep -ciE 'structural.*(no path to user-visible failure|no.*user-visible failure)|(no path to user-visible failure|no.*user-visible failure).*structural' "$GUIDE" 2>/dev/null || true)
if [ "$structural_consequence" -gt 0 ]; then
  ok "Guide type definitions use consequence-based language for structural"
else
  not_ok "Guide type definitions use consequence-based language for structural" "count=$structural_consequence"
fi

# --- Test 4: Guide severity definitions use observability language for critical ---
critical_obs=$(grep -ciE 'critical.*(next user|primary path)|(next user|primary path).*critical' "$GUIDE" 2>/dev/null || true)
if [ "$critical_obs" -gt 0 ]; then
  ok "Guide severity definitions use observability language for critical"
else
  not_ok "Guide severity definitions use observability language for critical" "count=$critical_obs"
fi

# --- Test 5: Guide severity definitions use observability language for major ---
major_obs=$(grep -ciE 'major.*(write a test|demonstrates the failure|constructible)|(write a test|demonstrates the failure|constructible).*major' "$GUIDE" 2>/dev/null || true)
if [ "$major_obs" -gt 0 ]; then
  ok "Guide severity definitions use observability language for major"
else
  not_ok "Guide severity definitions use observability language for major" "count=$major_obs"
fi

# --- Test 6: Guide severity definitions use observability language for minor ---
minor_obs=$(grep -ciE 'minor.*code reading|code reading.*minor' "$GUIDE" 2>/dev/null || true)
if [ "$minor_obs" -gt 0 ]; then
  ok "Guide severity definitions use observability language for minor"
else
  not_ok "Guide severity definitions use observability language for minor" "count=$minor_obs"
fi

# --- Test 7: Guide references JSON sighting schema ---
json_schema=$(grep -ciE 'JSON.*(schema|sighting)|(schema|sighting).*JSON' "$GUIDE" 2>/dev/null || true)
if [ "$json_schema" -gt 0 ]; then
  ok "Guide references JSON sighting schema"
else
  not_ok "Guide references JSON sighting schema" "count=$json_schema"
fi

# --- Test 8: Guide documents reclassified_from field ---
reclassified=$(grep -c 'reclassified_from' "$GUIDE" 2>/dev/null || true)
if [ "$reclassified" -gt 0 ]; then
  ok "Guide documents reclassified_from field"
else
  not_ok "Guide documents reclassified_from field" "count=$reclassified"
fi

# --- Test 9: Guide documents verification_evidence field ---
verification_evidence=$(grep -c 'verification_evidence' "$GUIDE" 2>/dev/null || true)
if [ "$verification_evidence" -gt 0 ]; then
  ok "Guide documents verification_evidence field"
else
  not_ok "Guide documents verification_evidence field" "count=$verification_evidence"
fi

# --- Test 10: Guide documents type-severity validity matrix ---
validity_matrix=$(grep -ciE 'matrix|validity matrix' "$GUIDE" 2>/dev/null || true)
if [ "$validity_matrix" -gt 0 ]; then
  ok "Guide documents type-severity validity matrix"
else
  not_ok "Guide documents type-severity validity matrix" "count=$validity_matrix"
fi

# --- Test 11: Guide orchestration protocol references fbk-pipeline.py ---
orch_section=$(sed -n '/## Orchestration Protocol/,/^## /p' "$GUIDE" 2>/dev/null || true)
pipeline_ref=$(echo "$orch_section" | grep -ciE 'fbk\.py.*pipeline|python3.*pipeline' 2>/dev/null || true)
if [ "$pipeline_ref" -gt 0 ]; then
  ok "Guide orchestration protocol references fbk-pipeline.py"
else
  not_ok "Guide orchestration protocol references fbk-pipeline.py" "count=$pipeline_ref"
fi

# --- Test 12: Guide orchestration protocol references JSON as working format ---
json_orch=$(echo "$orch_section" | grep -c 'JSON' 2>/dev/null || true)
if [ "$json_orch" -gt 0 ]; then
  ok "Guide orchestration protocol references JSON as working format"
else
  not_ok "Guide orchestration protocol references JSON as working format" "count=$json_orch"
fi

# --- Test 13: Guide does not contain old pattern-shape type definition language ---
old_type_def=$(grep -ci 'does something different from what its name' "$GUIDE" 2>/dev/null || true)
if [ "$old_type_def" -eq 0 ]; then
  ok "Guide does not contain old pattern-shape type definition language"
else
  not_ok "Guide does not contain old pattern-shape type definition language" "old_type_def=$old_type_def"
fi

# --- Test 14: Guide does not contain old severity definition language ---
old_severity=$(grep -ci 'significant risk under realistic conditions' "$GUIDE" 2>/dev/null || true)
if [ "$old_severity" -eq 0 ]; then
  ok "Guide does not contain old severity definition 'significant risk under realistic conditions'"
else
  not_ok "Guide does not contain old severity definition 'significant risk under realistic conditions'" "old_severity=$old_severity"
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
