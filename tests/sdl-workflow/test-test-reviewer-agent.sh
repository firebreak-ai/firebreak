#!/usr/bin/env bash
set -uo pipefail

PASS=0
FAIL=0
TOTAL=0

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
PROJECT_ROOT="$(cd "$SCRIPT_DIR/../.." && pwd)"
# fbk-test-reviewer.md was deleted in the unified-review-shape consolidation.
# Test-review behavior now lives in two places:
#   - the fbk-test-review skill (orchestration, mode routing, verdict format)
#   - test-lens.md (finding types, severities, matrix, researcher/challenger instructions)
SKILL="$PROJECT_ROOT/assets/skills/fbk-test-review/SKILL.md"
LENS="$PROJECT_ROOT/assets/fbk-docs/fbk-review-lenses/test-lens.md"

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

# --- Test 1: Skill file exists and is non-empty ---
if [ -s "$SKILL" ]; then
  ok "skill file exists and is non-empty"
else
  not_ok "skill file exists and is non-empty" "file: $SKILL"
fi

# --- Test 2: Skill has YAML frontmatter ---
first_line=$(head -1 "$SKILL" 2>/dev/null || true)
closing_count=$(grep -c '^---$' "$SKILL" 2>/dev/null || true)
if [ "$first_line" = "---" ] && [ "$closing_count" -ge 2 ]; then
  ok "skill has YAML frontmatter"
else
  not_ok "skill has YAML frontmatter" "first_line='$first_line' closing_count=$closing_count"
fi

# --- Test 3: Skill description is non-empty ---
fm=$(sed -n '2,/^---$/p' "$SKILL" | sed '$d')
desc_val=$(echo "$fm" | grep '^description:' | sed 's/^description:[[:space:]]*//' | tr -d '"')
if [ -n "$desc_val" ]; then
  ok "skill description is non-empty"
else
  not_ok "skill description is non-empty" "desc_val='$desc_val'"
fi

# --- Test 4: Skill body contains test + review language ---
skill_body=$(awk '/^---$/{c++; if(c==2){found=1; next}} found' "$SKILL")
has_test=$(echo "$skill_body" | grep -ci 'test')
has_review=$(echo "$skill_body" | grep -ciE 'review|validate|evaluate')
if [ "$has_test" -gt 0 ] && [ "$has_review" -gt 0 ]; then
  ok "skill body contains agent role (test + review/validate)"
else
  not_ok "skill body contains agent role (test + review/validate)" "test=$has_test review=$has_review"
fi

# --- Test 5: Skill defines pre-lock mode ---
if grep -qi 'pre-lock' "$SKILL"; then
  ok "skill defines pre-lock mode"
else
  not_ok "skill defines pre-lock mode"
fi

# --- Test 6: Skill defines final mode ---
if grep -qi 'final mode\|final pass\|Final mode' "$SKILL"; then
  ok "skill defines final mode"
else
  not_ok "skill defines final mode"
fi

# --- Test 7: Pre-lock mentions fail before implementation ---
if grep -qiE 'fail before implementation|red before implementation' "$SKILL" || \
   grep -qiE 'fail before implementation|red before implementation' "$LENS"; then
  ok "pre-lock mode mentions fail before implementation"
else
  not_ok "pre-lock mode mentions fail before implementation"
fi

# retired: old test-reviewer named four specific catching-power criteria
# (implementation-embedding, assertion-strength, coverage-versus-claim, mocking and contradiction).
# The test-lens pre-lock pass uses "Faithful translation", "AC trace",
# "Red before implementation", "Assertion strength" — same concepts, different labels.
# unified-review-shape consolidation.

# --- Test 8: Pre-lock verdict format present in skill ---
if grep -qE 'accepted \| needs-revision|accepted|needs-revision' "$SKILL"; then
  ok "pre-lock verdict format present in skill"
else
  not_ok "pre-lock verdict format present in skill"
fi

# retired: "verify_manifest" was a specific function name in the old fbk-test-reviewer.md.
# The concept survives as "Manifest drift" in test-lens.md and
# "drift from the locked manifest" in the skill. unified-review-shape consolidation.

# --- Test 9: Final mode mentions drift ---
if grep -qi 'drift' "$SKILL" || grep -qi 'drift' "$LENS"; then
  ok "final mode mentions drift"
else
  not_ok "final mode mentions drift"
fi

# --- Test 10: Final verdict format present in skill ---
if grep -qE 'accepted \| needs-revision|Verdict:' "$SKILL"; then
  ok "final mode contains verdict format"
else
  not_ok "final mode contains verdict format"
fi

# retired: "pipeline-blocking authority" was a specific concept in fbk-test-reviewer.md.
# The new architecture expresses blocking via "Only an accepted ... verdict lets the ...
# gate pass" language in the skill. unified-review-shape consolidation.

# retired: "context isolation" was a section heading in the old fbk-test-reviewer.md.
# Context isolation is enforced by the shared review-loop spine's isolation invariant
# (review-loop.md), not re-stated in the skill. unified-review-shape consolidation.

# --- Test 11: Output format specifies pass/fail with findings ---
has_pass=$(grep -ciE 'accepted' "$SKILL" || true)
has_fail=$(grep -ciE 'needs-revision' "$SKILL" || true)
has_findings=$(grep -ciE 'finding' "$SKILL" || true)
if [ "$has_pass" -gt 0 ] && [ "$has_fail" -gt 0 ] && [ "$has_findings" -gt 0 ]; then
  ok "output format specifies pass/fail with findings"
else
  not_ok "output format specifies pass/fail with findings" "accepted=$has_pass needs-revision=$has_fail findings=$has_findings"
fi

# --- Test 12: Each mode specifies artifact ---
if grep -qi 'artifact' "$SKILL"; then
  ok "skill specifies artifact paths"
else
  not_ok "skill specifies artifact paths"
fi

# retired: "brownfield mode" was a specific section in the old fbk-test-reviewer.md.
# The unified architecture handles brownfield via the shared code-review skill's
# brownfield reference. unified-review-shape consolidation.

# --- Test 13: Test-review invocation pattern mentioned ---
if grep -qiE 'test-review|test review' "$SKILL"; then
  ok "test-review invocation pattern mentioned"
else
  not_ok "test-review invocation pattern mentioned"
fi

# --- Test 14: Lens file exists and is non-empty ---
if [ -s "$LENS" ]; then
  ok "test-lens file exists and is non-empty"
else
  not_ok "test-lens file exists and is non-empty" "file: $LENS"
fi

# --- Test 15: Lens defines manifest-drift finding type ---
if grep -qi 'manifest-drift' "$LENS"; then
  ok "lens defines manifest-drift finding type"
else
  not_ok "lens defines manifest-drift finding type"
fi

# --- Test 16: Lens defines weakened-assertion finding type ---
if grep -qi 'weakened-assertion' "$LENS"; then
  ok "lens defines weakened-assertion finding type"
else
  not_ok "lens defines weakened-assertion finding type"
fi

# --- Test 17: Lens defines trivially-passing finding type ---
if grep -qi 'trivially-passing' "$LENS"; then
  ok "lens defines trivially-passing finding type"
else
  not_ok "lens defines trivially-passing finding type"
fi

# --- Test 18: Lens contains a type-severity validity matrix ---
if grep -qi 'matrix\|type-severity' "$LENS"; then
  ok "lens contains type-severity validity matrix"
else
  not_ok "lens contains type-severity validity matrix"
fi

# --- Test 19: Lens defines verdict contract ---
if grep -qi 'verdict' "$LENS"; then
  ok "lens defines verdict contract"
else
  not_ok "lens defines verdict contract"
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
