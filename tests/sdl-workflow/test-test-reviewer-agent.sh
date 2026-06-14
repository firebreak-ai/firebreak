#!/usr/bin/env bash
set -uo pipefail

PASS=0
FAIL=0
TOTAL=0

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
PROJECT_ROOT="$(cd "$SCRIPT_DIR/../.." && pwd)"
AGENT_FILE="$PROJECT_ROOT/assets/agents/fbk-test-reviewer.md"

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
has_review=$(echo "$first_10" | grep -ciE 'reviewer|review|validate|evaluate')
if [ "$has_test" -gt 0 ] && [ "$has_review" -gt 0 ]; then
  ok "body contains agent role (test + review/validate)"
else
  not_ok "body contains agent role (test + review/validate)" "test=$has_test review=$has_review"
fi

# --- Test 6: Pre-lock mode section exists ---
if grep -q '^## Pre-lock mode' "$AGENT_FILE"; then
  ok "Pre-lock mode section exists"
else
  not_ok "Pre-lock mode section exists"
fi

# --- Test 7: Final mode section exists ---
if grep -q '^## Final mode' "$AGENT_FILE"; then
  ok "Final mode section exists"
else
  not_ok "Final mode section exists"
fi

# --- Test 8: Pre-lock mode — fail before implementation discipline ---
prelock=$(awk '/^## Pre-lock mode/,/^## Final mode/' "$AGENT_FILE")
if echo "$prelock" | grep -qE 'fail before implementation|red before implementation'; then
  ok "pre-lock mode mentions fail before implementation"
else
  not_ok "pre-lock mode mentions fail before implementation"
fi

# --- Test 9: Pre-lock mode — four catching-power criteria present ---
prelock_impl=$(echo "$prelock" | grep -ci 'implementation-embedding')
prelock_assert=$(echo "$prelock" | grep -ci 'assertion strength')
prelock_cov=$(echo "$prelock" | grep -ci 'coverage-versus-claim')
prelock_mock=$(echo "$prelock" | grep -ci 'mocking and contradiction')
if [ "$prelock_impl" -gt 0 ] && [ "$prelock_assert" -gt 0 ] && [ "$prelock_cov" -gt 0 ] && [ "$prelock_mock" -gt 0 ]; then
  ok "pre-lock mode names all four catching-power criteria"
else
  not_ok "pre-lock mode names all four catching-power criteria" "impl=$prelock_impl assert=$prelock_assert cov=$prelock_cov mock=$prelock_mock"
fi

# --- Test 10: Pre-lock mode — verdict line present ---
if echo "$prelock" | grep -qE 'accepted \| needs-revision'; then
  ok "pre-lock mode contains accepted | needs-revision verdict line"
else
  not_ok "pre-lock mode contains accepted | needs-revision verdict line"
fi

# --- Test 11: Final mode — verify_manifest present ---
final=$(awk '/^## Final mode/,/^## Output format/' "$AGENT_FILE")
if echo "$final" | grep -q 'verify_manifest'; then
  ok "final mode mentions verify_manifest"
else
  not_ok "final mode mentions verify_manifest"
fi

# --- Test 12: Final mode — drift check present ---
if echo "$final" | grep -qi 'drift'; then
  ok "final mode mentions drift"
else
  not_ok "final mode mentions drift"
fi

# --- Test 13: Final mode — verdict line present ---
if echo "$final" | grep -qE 'accepted \| needs-revision'; then
  ok "final mode contains accepted | needs-revision verdict line"
else
  not_ok "final mode contains accepted | needs-revision verdict line"
fi

# --- Test 14: Pipeline-blocking authority specified ---
blocking=$(grep -ciE 'pipeline.blocking|blocking authority' "$AGENT_FILE")
if [ "$blocking" -gt 0 ]; then
  ok "pipeline-blocking authority specified"
else
  not_ok "pipeline-blocking authority specified"
fi

# --- Test 15: Context isolation specified ---
isolation=$(grep -ciE 'context isolation|isolated context|isolation' "$AGENT_FILE")
if [ "$isolation" -gt 0 ]; then
  ok "context isolation specified"
else
  not_ok "context isolation specified"
fi

# --- Test 16: Output format specified (pass/fail with findings) ---
output_pass=$(grep -ciE 'pass' "$AGENT_FILE")
output_fail=$(grep -ciE 'fail' "$AGENT_FILE")
output_findings=$(grep -ciE 'finding' "$AGENT_FILE")
if [ "$output_pass" -gt 0 ] && [ "$output_fail" -gt 0 ] && [ "$output_findings" -gt 0 ]; then
  ok "output format specifies pass/fail with findings"
else
  not_ok "output format specifies pass/fail with findings" "pass=$output_pass fail=$output_fail findings=$output_findings"
fi

# --- Test 17: Each mode specifies artifact set ---
prelock_art=$(echo "$prelock" | grep -ciE 'artifact|receives|input')
final_art=$(echo "$final" | grep -ciE 'artifact|receives|input')
if [ "$prelock_art" -gt 0 ] && [ "$final_art" -gt 0 ]; then
  ok "each mode specifies artifact set"
else
  not_ok "each mode specifies artifact set" "prelock=$prelock_art final=$final_art"
fi

# --- Test 18: Brownfield mode mentioned ---
brownfield=$(grep -ciE 'brownfield' "$AGENT_FILE")
if [ "$brownfield" -gt 0 ]; then
  ok "brownfield mode mentioned"
else
  not_ok "brownfield mode mentioned"
fi

# --- Test 19: On-demand invocation pattern (test-review) ---
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
