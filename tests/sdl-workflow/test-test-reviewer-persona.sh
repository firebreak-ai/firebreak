#!/usr/bin/env bash
set -uo pipefail

PASS=0
FAIL=0
TOTAL=0

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
PROJECT_ROOT="$(cd "$SCRIPT_DIR/../.." && pwd)"
# fbk-test-reviewer.md was deleted in the unified-review-shape consolidation.
# The monolithic agent's persona and structural sections have been split across:
#   - fbk-test-review/SKILL.md (orchestration, mode routing)
#   - test-lens.md (detection targets, challenger instructions, verdict contract)
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
  ok "Skill file exists and is non-empty"
else
  not_ok "Skill file exists and is non-empty" "file: $SKILL"
fi

# --- Test 2: Skill has valid YAML frontmatter ---
first_line=$(head -1 "$SKILL" 2>/dev/null || true)
closing_count=$(grep -c '^---$' "$SKILL" 2>/dev/null || true)
if [ "$first_line" = "---" ] && [ "$closing_count" -ge 2 ]; then
  ok "Skill has valid YAML frontmatter"
else
  not_ok "Skill has valid YAML frontmatter" "first_line='$first_line' closing_count=$closing_count"
fi

# --- Test 3: Skill body is at least 5 lines ---
skill_body=$(awk '/^---$/{c++; if(c==2){found=1; next}} found' "$SKILL")
body_line_count=$(echo "$skill_body" | wc -l | tr -d ' ')
if [ "$body_line_count" -ge 5 ]; then
  ok "Skill body is at least 5 lines ($body_line_count)"
else
  not_ok "Skill body is at least 5 lines" "body_line_count=$body_line_count (need >= 5)"
fi

# --- Test 4: Skill body is reasonably concise (under 200 lines) ---
if [ "$body_line_count" -le 200 ]; then
  ok "Skill body is reasonably concise ($body_line_count lines)"
else
  not_ok "Skill body is reasonably concise" "body_line_count=$body_line_count (need <= 200)"
fi

# retired: "QA engineer" was the role-activation phrase in the old fbk-test-reviewer.md persona.
# The generic review-researcher provides the evaluator role; test-review-specific
# framing lives in the skill and test-lens. unified-review-shape consolidation.

# retired: "## Output quality bars", "## Evaluation criteria", "## Context isolation",
# "## Override mechanism" were section headings specific to fbk-test-reviewer.md.
# In the unified architecture these concepts are handled generically by review-loop.md
# (isolation invariant, verdict contract) and test-lens.md (evaluation criteria).
# unified-review-shape consolidation.

# retired: "pipeline-blocking" was an explicit authority statement in fbk-test-reviewer.md.
# The new skill expresses the same concept via "Only an accepted ... verdict lets the ...
# gate pass". unified-review-shape consolidation.

# --- Test 5: Skill expresses blocking authority via gate language ---
if grep -qiE 'gate|block|accepted.*verdict|verdict.*accepted' "$SKILL"; then
  ok "Skill expresses blocking authority via gate language"
else
  not_ok "Skill expresses blocking authority via gate language"
fi

# --- Test 6: Lens exists and is non-empty ---
if [ -s "$LENS" ]; then
  ok "Test-lens file exists and is non-empty"
else
  not_ok "Test-lens file exists and is non-empty" "file: $LENS"
fi

# --- Test 7: Lens contains finding types for test review ---
if grep -qiE 'weakened-assertion|untested-behavior|trivially-passing|manifest-drift' "$LENS"; then
  ok "Lens contains test-review finding types"
else
  not_ok "Lens contains test-review finding types"
fi

# --- Test 8: Lens contains challenger instructions ---
if grep -qiE 'challenger|reclassif|provenance' "$LENS"; then
  ok "Lens contains challenger instructions"
else
  not_ok "Lens contains challenger instructions"
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
