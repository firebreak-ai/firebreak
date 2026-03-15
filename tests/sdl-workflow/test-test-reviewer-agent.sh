#!/usr/bin/env bash
set -uo pipefail

PASS=0
FAIL=0
TOTAL=0

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
PROJECT_ROOT="$(cd "$SCRIPT_DIR/../.." && pwd)"
AGENT_FILE="$PROJECT_ROOT/home/.claude/agents/test-reviewer.md"

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
  sed -n '2,/^---$/p' "$AGENT_FILE" | sed '$d'
}

# Helper: extract body (everything after second ---)
body() {
  sed -n '/^---$/,/^---$/!p; /^---$/{ x; s/^/x/; /^xx/{ x; q; }; x; }' "$AGENT_FILE" | tail -n +1
}

# More reliable body extraction: skip frontmatter, return the rest
body_lines() {
  awk 'BEGIN{c=0} /^---$/{c++; next} c>=2{print}' "$AGENT_FILE"
}

echo "TAP version 13"

# --- Test 1: Agent file exists and is non-empty ---
if [ -s "$AGENT_FILE" ]; then
  ok "agent file exists and is non-empty"
else
  not_ok "agent file exists and is non-empty" "file: $AGENT_FILE"
fi

# --- Test 2: File has YAML frontmatter ---
first_line=$(head -1 "$AGENT_FILE" 2>/dev/null)
closing_count=$(grep -c '^---$' "$AGENT_FILE" 2>/dev/null)
if [ "$first_line" = "---" ] && [ "$closing_count" -ge 2 ]; then
  ok "file has YAML frontmatter"
else
  not_ok "file has YAML frontmatter" "first_line='$first_line' closing_count=$closing_count"
fi

# --- Test 3: Frontmatter contains name: with non-empty value ---
fm=$(frontmatter)
name_val=$(echo "$fm" | grep '^name:' | sed 's/^name:[[:space:]]*//')
if [ -n "$name_val" ]; then
  ok "frontmatter contains name: with non-empty value"
else
  not_ok "frontmatter contains name: with non-empty value" "name_val='$name_val'"
fi

# --- Test 4: Frontmatter contains description: with non-empty value ---
desc_val=$(echo "$fm" | grep '^description:' | sed 's/^description:[[:space:]]*//')
if [ -n "$desc_val" ]; then
  ok "frontmatter contains description: with non-empty value"
else
  not_ok "frontmatter contains description: with non-empty value" "desc_val='$desc_val'"
fi

# --- Test 5: Body contains agent role ---
first_10=$(body_lines | head -10)
has_test=$(echo "$first_10" | grep -ci 'test')
has_review=$(echo "$first_10" | grep -ciE 'reviewer|review|validate')
if [ "$has_test" -gt 0 ] && [ "$has_review" -gt 0 ]; then
  ok "body contains agent role (test + review/validate)"
else
  not_ok "body contains agent role (test + review/validate)" "test=$has_test review=$has_review"
fi

# --- Test 6: Checkpoint 1 (spec review) ---
cp1=$(awk '/^## .*[Cc]heckpoint 1/,/^## .*[Cc]heckpoint 2/' "$AGENT_FILE")
cp1_spec=$(echo "$cp1" | grep -ciE 'spec')
cp1_schema=$(echo "$cp1" | grep -ciE 'schema')
cp1_strat=$(echo "$cp1" | grep -ciE 'testing strategy|AC|acceptance criteria')
if [ "$cp1_spec" -gt 0 ] && [ "$cp1_schema" -gt 0 ] && [ "$cp1_strat" -gt 0 ]; then
  ok "checkpoint 1 mentions spec, schema, and testing strategy/AC"
else
  not_ok "checkpoint 1 mentions spec, schema, and testing strategy/AC" "spec=$cp1_spec schema=$cp1_schema strat=$cp1_strat"
fi

# --- Test 7: Checkpoint 2 (task review) ---
cp2=$(awk '/^## .*[Cc]heckpoint 2/,/^## .*[Cc]heckpoint 3/' "$AGENT_FILE")
cp2_task=$(echo "$cp2" | grep -ciE 'task files')
cp2_strat=$(echo "$cp2" | grep -ciE 'testing strategy|breakdown')
if [ "$cp2_task" -gt 0 ] && [ "$cp2_strat" -gt 0 ]; then
  ok "checkpoint 2 mentions task files and testing strategy/breakdown"
else
  not_ok "checkpoint 2 mentions task files and testing strategy/breakdown" "task=$cp2_task strat=$cp2_strat"
fi

# --- Test 8: Checkpoint 3 (test code review) ---
cp3=$(awk '/^## .*[Cc]heckpoint 3/,/^## .*[Cc]heckpoint 4/' "$AGENT_FILE")
cp3_code=$(echo "$cp3" | grep -ciE 'test code')
cp3_fail=$(echo "$cp3" | grep -ciE 'compile|fail|trace')
if [ "$cp3_code" -gt 0 ] && [ "$cp3_fail" -gt 0 ]; then
  ok "checkpoint 3 mentions test code and compile/fail/trace"
else
  not_ok "checkpoint 3 mentions test code and compile/fail/trace" "code=$cp3_code fail=$cp3_fail"
fi

# --- Test 9: Checkpoint 4 (test integrity) ---
cp4=$(awk '/^## .*[Cc]heckpoint 4/,/^## .*[Cc]heckpoint 5/' "$AGENT_FILE")
cp4_impl=$(echo "$cp4" | grep -ciE 'implementation|implemented')
cp4_qual=$(echo "$cp4" | grep -ciE 'weaken|coverage|trivial|quality|regression|adequate')
if [ "$cp4_impl" -gt 0 ] && [ "$cp4_qual" -gt 0 ]; then
  ok "checkpoint 4 mentions implementation and quality/coverage/weaken"
else
  not_ok "checkpoint 4 mentions implementation and quality/coverage/weaken" "impl=$cp4_impl qual=$cp4_qual"
fi

# --- Test 10: Checkpoint 5 (mutation testing) ---
cp5=$(awk '/^## .*[Cc]heckpoint 5/,/^## [^C]/' "$AGENT_FILE")
cp5_impl=$(echo "$cp5" | grep -ciE 'implemented code|implementation')
cp5_mut=$(echo "$cp5" | grep -ciE 'mutation')
cp5_det=$(echo "$cp5" | grep -ciE 'detection rate|hash|verified|kill|survive')
cp5_no_test_input=$(echo "$cp5" | grep -ciE 'does not receive test code|no test code as input|without.*test code input|not receive test code')
# Check it does NOT indicate it receives test code as input (negative check)
cp5_receives_test=$(echo "$cp5" | grep -ciE 'receives test code|test code as input')
if [ "$cp5_impl" -gt 0 ] && [ "$cp5_mut" -gt 0 ] && [ "$cp5_det" -gt 0 ] && [ "$cp5_receives_test" -eq 0 ]; then
  ok "checkpoint 5 mentions implementation, mutation, detection/hash/kill, no test code input"
else
  not_ok "checkpoint 5 mentions implementation, mutation, detection/hash/kill, no test code input" "impl=$cp5_impl mut=$cp5_mut det=$cp5_det receives_test=$cp5_receives_test"
fi

# --- Test 11: Pipeline-blocking authority specified ---
blocking=$(grep -ciE 'pipeline.blocking|blocking authority' "$AGENT_FILE")
if [ "$blocking" -gt 0 ]; then
  ok "pipeline-blocking authority specified"
else
  not_ok "pipeline-blocking authority specified"
fi

# --- Test 12: Context isolation specified ---
isolation=$(grep -ciE 'context isolation|isolated context|isolation' "$AGENT_FILE")
if [ "$isolation" -gt 0 ]; then
  ok "context isolation specified"
else
  not_ok "context isolation specified"
fi

# --- Test 13: Output format specified (pass/fail with findings) ---
output_pass=$(grep -ciE 'pass' "$AGENT_FILE")
output_fail=$(grep -ciE 'fail' "$AGENT_FILE")
output_findings=$(grep -ciE 'finding' "$AGENT_FILE")
if [ "$output_pass" -gt 0 ] && [ "$output_fail" -gt 0 ] && [ "$output_findings" -gt 0 ]; then
  ok "output format specifies pass/fail with findings"
else
  not_ok "output format specifies pass/fail with findings" "pass=$output_pass fail=$output_fail findings=$output_findings"
fi

# --- Test 14: Each checkpoint specifies artifact set ---
artifacts_ok=true
for i in 1 2 3 4 5; do
  next=$((i + 1))
  if [ "$i" -eq 5 ]; then
    cp_section=$(awk "/^## .*[Cc]heckpoint $i/,/^## [^C]/" "$AGENT_FILE")
  else
    cp_section=$(awk "/^## .*[Cc]heckpoint $i/,/^## .*[Cc]heckpoint $next/" "$AGENT_FILE")
  fi
  art_count=$(echo "$cp_section" | grep -ciE 'artifact|receives|input')
  if [ "$art_count" -eq 0 ]; then
    artifacts_ok=false
  fi
done
if $artifacts_ok; then
  ok "each checkpoint specifies artifact set"
else
  not_ok "each checkpoint specifies artifact set"
fi

# --- Test 15: Brownfield mode mentioned ---
brownfield=$(grep -ciE 'brownfield' "$AGENT_FILE")
if [ "$brownfield" -gt 0 ]; then
  ok "brownfield mode mentioned"
else
  not_ok "brownfield mode mentioned"
fi

# --- Test 16: On-demand invocation pattern (test-review) ---
invocation=$(grep -ciE 'test-review' "$AGENT_FILE")
if [ "$invocation" -gt 0 ]; then
  ok "on-demand invocation pattern (test-review) mentioned"
else
  not_ok "on-demand invocation pattern (test-review) mentioned"
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
