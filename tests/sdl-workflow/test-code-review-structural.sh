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
CHECKLIST="$PROJECT_ROOT/assets/fbk-docs/fbk-sdl-workflow/ai-failure-modes.md"

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

# --- Test 1: Detector agent file exists and is non-empty ---
if [ -s "$DETECTOR" ]; then
  ok "Detector agent file exists and is non-empty"
else
  not_ok "Detector agent file exists and is non-empty" "file: $DETECTOR"
fi

# --- Test 2: Detector has YAML frontmatter ---
first_line=$(head -1 "$DETECTOR" 2>/dev/null || true)
closing_count=$(grep -c '^---$' "$DETECTOR" 2>/dev/null || true)
if [ "$first_line" = "---" ] && [ "$closing_count" -ge 2 ]; then
  ok "Detector has YAML frontmatter"
else
  not_ok "Detector has YAML frontmatter" "first_line='$first_line' closing_count=$closing_count"
fi

# --- Test 3: Detector name field contains "detector" ---
fm=$(frontmatter "$DETECTOR" 2>/dev/null || true)
name_val=$(echo "$fm" | grep '^name:' | sed 's/^name:[[:space:]]*//;s/[[:space:]]*$//')
if echo "$name_val" | grep -qi 'detector'; then
  ok "Detector name field contains 'detector'"
else
  not_ok "Detector name field contains 'detector'" "name_val='$name_val'"
fi

# --- Test 4: Detector description field is non-empty ---
desc_val=$(echo "$fm" | grep '^description:' | sed 's/^description:[[:space:]]*//;s/[[:space:]]*$//')
if [ -n "$desc_val" ]; then
  ok "Detector description field is non-empty"
else
  not_ok "Detector description field is non-empty" "desc_val='$desc_val'"
fi

# --- Test 5: Detector tools field lists Read, Grep, Glob without Bash ---
tools_line=$(echo "$fm" | grep '^tools:')
has_read=$(echo "$tools_line" | grep -c 'Read')
has_grep=$(echo "$tools_line" | grep -c 'Grep')
has_glob=$(echo "$tools_line" | grep -c 'Glob')
has_bash=$(echo "$tools_line" | grep -c 'Bash')
if [ "$has_read" -gt 0 ] && [ "$has_grep" -gt 0 ] && [ "$has_glob" -gt 0 ] && [ "$has_bash" -eq 0 ]; then
  ok "Detector tools field lists Read, Grep, Glob without Bash"
else
  not_ok "Detector tools field lists Read, Grep, Glob without Bash" "tools_line='$tools_line'"
fi

# --- Test 6: Detector tools field excludes Write and Edit ---
has_write=$(echo "$tools_line" | grep -c 'Write')
has_edit=$(echo "$tools_line" | grep -c 'Edit')
if [ "$has_write" -eq 0 ] && [ "$has_edit" -eq 0 ]; then
  ok "Detector tools field excludes Write and Edit"
else
  not_ok "Detector tools field excludes Write and Edit" "has_write=$has_write has_edit=$has_edit"
fi

# --- Test 7: Detector description contains code analysis language ---
if echo "$desc_val" | grep -qiE 'analysis|analyz|detect|code review|pattern'; then
  ok "Detector description contains code analysis language"
else
  not_ok "Detector description contains code analysis language" "desc_val='$desc_val'"
fi

# --- Test 8: Challenger agent file exists and is non-empty ---
if [ -s "$CHALLENGER" ]; then
  ok "Challenger agent file exists and is non-empty"
else
  not_ok "Challenger agent file exists and is non-empty" "file: $CHALLENGER"
fi

# --- Test 9: Challenger has YAML frontmatter ---
first_line=$(head -1 "$CHALLENGER" 2>/dev/null || true)
closing_count=$(grep -c '^---$' "$CHALLENGER" 2>/dev/null || true)
if [ "$first_line" = "---" ] && [ "$closing_count" -ge 2 ]; then
  ok "Challenger has YAML frontmatter"
else
  not_ok "Challenger has YAML frontmatter" "first_line='$first_line' closing_count=$closing_count"
fi

# --- Test 10: Challenger name field contains "challenger" ---
fm=$(frontmatter "$CHALLENGER" 2>/dev/null || true)
name_val=$(echo "$fm" | grep '^name:' | sed 's/^name:[[:space:]]*//;s/[[:space:]]*$//')
if echo "$name_val" | grep -qi 'challenger'; then
  ok "Challenger name field contains 'challenger'"
else
  not_ok "Challenger name field contains 'challenger'" "name_val='$name_val'"
fi

# --- Test 11: Challenger description field is non-empty ---
desc_val=$(echo "$fm" | grep '^description:' | sed 's/^description:[[:space:]]*//;s/[[:space:]]*$//')
if [ -n "$desc_val" ]; then
  ok "Challenger description field is non-empty"
else
  not_ok "Challenger description field is non-empty" "desc_val='$desc_val'"
fi

# --- Test 12: Challenger tools field lists exactly Read, Grep, Glob ---
tools_line=$(echo "$fm" | grep '^tools:')
has_read=$(echo "$tools_line" | grep -c 'Read')
has_grep=$(echo "$tools_line" | grep -c 'Grep')
has_glob=$(echo "$tools_line" | grep -c 'Glob')
has_bash=$(echo "$tools_line" | grep -c 'Bash')
has_write=$(echo "$tools_line" | grep -c 'Write')
has_edit=$(echo "$tools_line" | grep -c 'Edit')
if [ "$has_read" -gt 0 ] && [ "$has_grep" -gt 0 ] && [ "$has_glob" -gt 0 ] && [ "$has_bash" -eq 0 ] && [ "$has_write" -eq 0 ] && [ "$has_edit" -eq 0 ]; then
  ok "Challenger tools field lists exactly Read, Grep, Glob"
else
  not_ok "Challenger tools field lists exactly Read, Grep, Glob" "tools_line='$tools_line'"
fi

# --- Test 13: Challenger tools field excludes Bash, Write, and Edit ---
has_bash=$(echo "$tools_line" | grep -c 'Bash')
has_write=$(echo "$tools_line" | grep -c 'Write')
has_edit=$(echo "$tools_line" | grep -c 'Edit')
if [ "$has_bash" -eq 0 ] && [ "$has_write" -eq 0 ] && [ "$has_edit" -eq 0 ]; then
  ok "Challenger tools field excludes Bash, Write, and Edit"
else
  not_ok "Challenger tools field excludes Bash, Write, and Edit" "has_bash=$has_bash has_write=$has_write has_edit=$has_edit"
fi

# --- Test 14: Challenger description contains adversarial verification language ---
desc_val=$(echo "$fm" | grep '^description:' | sed 's/^description:[[:space:]]*//;s/[[:space:]]*$//')
if echo "$desc_val" | grep -qiE 'adversarial|verif|challenger|skeptic|evidence'; then
  ok "Challenger description contains adversarial verification language"
else
  not_ok "Challenger description contains adversarial verification language" "desc_val='$desc_val'"
fi

# --- Test 15: Code review guide exists and is non-empty ---
if [ -s "$GUIDE" ]; then
  ok "Code review guide exists and is non-empty"
else
  not_ok "Code review guide exists and is non-empty" "file: $GUIDE"
fi

# --- Test 16: Guide documents finding format with all required fields ---
finding_id=$(grep -ci 'finding id' "$GUIDE" 2>/dev/null || true)
sighting=$(grep -ci 'sighting' "$GUIDE" 2>/dev/null || true)
location=$(grep -ci 'location' "$GUIDE" 2>/dev/null || true)
type_field=$(grep -ci 'Type:' "$GUIDE" 2>/dev/null || true)
current=$(grep -ci 'current behavior' "$GUIDE" 2>/dev/null || true)
expected=$(grep -ci 'expected behavior' "$GUIDE" 2>/dev/null || true)
source=$(grep -ci 'source of truth' "$GUIDE" 2>/dev/null || true)
evidence=$(grep -ci 'evidence' "$GUIDE" 2>/dev/null || true)
if [ "$finding_id" -gt 0 ] && [ "$sighting" -gt 0 ] && [ "$location" -gt 0 ] && [ "$type_field" -gt 0 ] && [ "$current" -gt 0 ] && [ "$expected" -gt 0 ] && [ "$source" -gt 0 ] && [ "$evidence" -gt 0 ]; then
  ok "Guide documents finding format with all 8 required fields"
else
  not_ok "Guide documents finding format with all 8 required fields" "finding_id=$finding_id sighting=$sighting location=$location type_field=$type_field current=$current expected=$expected source=$source evidence=$evidence"
fi

# --- Test 17: Guide documents all 4 type values ---
behavioral=$(grep -c 'behavioral' "$GUIDE" 2>/dev/null || true)
structural=$(grep -c 'structural' "$GUIDE" 2>/dev/null || true)
test_integrity=$(grep -c 'test-integrity' "$GUIDE" 2>/dev/null || true)
fragile=$(grep -c 'fragile' "$GUIDE" 2>/dev/null || true)
if [ "$behavioral" -gt 0 ] && [ "$structural" -gt 0 ] && [ "$test_integrity" -gt 0 ] && [ "$fragile" -gt 0 ]; then
  ok "Guide documents all 4 type values"
else
  not_ok "Guide documents all 4 type values" "behavioral=$behavioral structural=$structural test_integrity=$test_integrity fragile=$fragile"
fi

# --- Test 18: Guide documents sighting format with required fields ---
sighting_id=$(grep -ci 'sighting id' "$GUIDE" 2>/dev/null || true)
sighting_location=$(grep -ci 'location' "$GUIDE" 2>/dev/null || true)
sighting_type=$(grep -ci 'Type:' "$GUIDE" 2>/dev/null || true)
observation=$(grep -ci 'observation' "$GUIDE" 2>/dev/null || true)
sighting_expected=$(grep -ci 'expected' "$GUIDE" 2>/dev/null || true)
sighting_source=$(grep -ci 'source of truth' "$GUIDE" 2>/dev/null || true)
if [ "$sighting_id" -gt 0 ] && [ "$sighting_location" -gt 0 ] && [ "$sighting_type" -gt 0 ] && [ "$observation" -gt 0 ] && [ "$sighting_expected" -gt 0 ] && [ "$sighting_source" -gt 0 ]; then
  ok "Guide documents sighting format with required fields"
else
  not_ok "Guide documents sighting format with required fields" "sighting_id=$sighting_id sighting_location=$sighting_location sighting_type=$sighting_type observation=$observation sighting_expected=$sighting_expected sighting_source=$sighting_source"
fi

# --- Test 19: Guide documents behavioral comparison methodology ---
behavioral=$(grep -ci 'behavioral comparison' "$GUIDE" 2>/dev/null || true)
describe_compare=$(grep -ciE 'describe.*compare|compare.*describe' "$GUIDE" 2>/dev/null || true)
if [ "$behavioral" -gt 0 ] || [ "$describe_compare" -gt 0 ]; then
  ok "Guide documents behavioral comparison methodology"
else
  not_ok "Guide documents behavioral comparison methodology" "behavioral=$behavioral describe_compare=$describe_compare"
fi

# --- Test 20: Guide does not use defect-detection framing as instructions ---
find_bugs_total=$(grep -c 'find bugs' "$GUIDE" 2>/dev/null || true)
find_bugs_negated=$(grep 'find bugs' "$GUIDE" 2>/dev/null | grep -cE "don't|not|never|avoid" || true)
if [ "$find_bugs_total" -eq 0 ] || [ "$find_bugs_total" -eq "$find_bugs_negated" ]; then
  ok "Guide does not use defect-detection framing as instructions"
else
  not_ok "Guide does not use defect-detection framing as instructions" "find_bugs_total=$find_bugs_total find_bugs_negated=$find_bugs_negated"
fi

# --- Test 21: Guide documents all required retrospective fields ---
sighting_counts=$(grep -ci 'sighting counts' "$GUIDE" 2>/dev/null || true)
verification=$(grep -ci 'verification rounds' "$GUIDE" 2>/dev/null || true)
scope=$(grep -ci 'scope assessment' "$GUIDE" 2>/dev/null || true)
context_health=$(grep -ci 'context health' "$GUIDE" 2>/dev/null || true)
tool_usage=$(grep -ci 'tool usage' "$GUIDE" 2>/dev/null || true)
finding_quality=$(grep -ci 'finding quality' "$GUIDE" 2>/dev/null || true)
if [ "$sighting_counts" -gt 0 ] && [ "$verification" -gt 0 ] && [ "$scope" -gt 0 ] && [ "$context_health" -gt 0 ] && [ "$tool_usage" -gt 0 ] && [ "$finding_quality" -gt 0 ]; then
  ok "Guide documents all required retrospective fields"
else
  not_ok "Guide documents all required retrospective fields" "sighting_counts=$sighting_counts verification=$verification scope=$scope context_health=$context_health tool_usage=$tool_usage finding_quality=$finding_quality"
fi

# --- Test 22: AI failure mode checklist exists and is non-empty ---
if [ -s "$CHECKLIST" ]; then
  ok "AI failure mode checklist exists and is non-empty"
else
  not_ok "AI failure mode checklist exists and is non-empty" "file: $CHECKLIST"
fi

# --- Test 23: Checklist contains at least 14 numbered items ---
numbered=$(grep -cE '^[0-9]+\.|^[0-9]+\)|^- \*\*[0-9]+' "$CHECKLIST" 2>/dev/null || true)
if [ "$numbered" -ge 14 ]; then
  ok "Checklist contains at least 14 numbered items"
else
  not_ok "Checklist contains at least 14 numbered items" "numbered=$numbered"
fi

# --- Test 24: Checklist contains key failure mode keywords (updated for 0.3.3) ---
reimplement=$(grep -ci 're-implement' "$CHECKLIST" 2>/dev/null || true)
duplication=$(grep -ci 'duplication' "$CHECKLIST" 2>/dev/null || true)
bare_literal=$(grep -ci 'bare literal' "$CHECKLIST" 2>/dev/null || true)
dead=$(grep -ci 'dead code' "$CHECKLIST" 2>/dev/null || true)
hardcoded=$(grep -ci 'hardcoded' "$CHECKLIST" 2>/dev/null || true)
inconsistent=$(grep -ci 'inconsistent' "$CHECKLIST" 2>/dev/null || true)
middleware=$(grep -ci 'middleware' "$CHECKLIST" 2>/dev/null || true)
trivial=$(grep -ci 'trivially-true' "$CHECKLIST" 2>/dev/null || true)
nonenforcing=$(grep -ci 'non-enforcing' "$CHECKLIST" 2>/dev/null || true)
surface=$(grep -ci 'surface-level' "$CHECKLIST" 2>/dev/null || true)
keyword_count=$((reimplement + duplication + bare_literal + dead + hardcoded + inconsistent + middleware + trivial + nonenforcing + surface))
if [ "$keyword_count" -ge 5 ]; then
  ok "Checklist contains key failure mode keywords (updated for 0.3.3)"
else
  not_ok "Checklist contains key failure mode keywords (updated for 0.3.3)" "keyword_count=$keyword_count"
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
