#!/usr/bin/env bash
set -uo pipefail

PASS=0
FAIL=0
TOTAL=0

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
PROJECT_ROOT="$(cd "$SCRIPT_DIR/../.." && pwd)"

SKILL_FILE="$PROJECT_ROOT/home/dot-claude/skills/code-review/SKILL.md"
EXISTING_REF="$PROJECT_ROOT/home/dot-claude/skills/code-review/references/existing-code-review.md"
POSTIMPL_REF="$PROJECT_ROOT/home/dot-claude/skills/code-review/references/post-impl-review.md"
IMPLEMENT_SKILL="$PROJECT_ROOT/home/dot-claude/skills/implement/SKILL.md"

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

# Helper: extract body (everything after second ---)
body_lines() {
  awk 'BEGIN{c=0} /^---$/{c++; next} c>=2{print}' "$1"
}

echo "TAP version 13"

# --- Test 1: SKILL.md exists and is non-empty ---
if [ -s "$SKILL_FILE" ]; then
  ok "SKILL.md exists and is non-empty"
else
  not_ok "SKILL.md exists and is non-empty" "file: $SKILL_FILE"
fi

# --- Test 2: SKILL.md has valid YAML frontmatter ---
first_line=$(head -1 "$SKILL_FILE" 2>/dev/null)
closing_count=$(grep -c '^---$' "$SKILL_FILE" 2>/dev/null)
fm_has_desc=$(frontmatter "$SKILL_FILE" | grep -c '^description:' 2>/dev/null)
if [ "$first_line" = "---" ] && [ "$closing_count" -ge 2 ] && [ "$fm_has_desc" -gt 0 ]; then
  ok "SKILL.md has valid YAML frontmatter with description"
else
  not_ok "SKILL.md has valid YAML frontmatter with description" "first_line='$first_line' closing_count=$closing_count desc_found=$fm_has_desc"
fi

# --- Test 3: SKILL.md frontmatter contains allowed-tools field ---
fm=$(frontmatter "$SKILL_FILE")
has_allowed_tools=$(echo "$fm" | grep -c '^allowed-tools:' 2>/dev/null)
if [ "$has_allowed_tools" -gt 0 ]; then
  ok "SKILL.md frontmatter contains allowed-tools field"
else
  not_ok "SKILL.md frontmatter contains allowed-tools field"
fi

# --- Test 4: SKILL.md allowed-tools includes Agent ---
allowed_tools_line=$(echo "$fm" | grep '^allowed-tools:' 2>/dev/null)
has_agent=$(echo "$allowed_tools_line" | grep -ci 'Agent' 2>/dev/null)
if [ "$has_agent" -gt 0 ]; then
  ok "SKILL.md allowed-tools includes Agent"
else
  not_ok "SKILL.md allowed-tools includes Agent" "allowed_tools_line: $allowed_tools_line"
fi

# --- Test 5: SKILL.md references existing-code-review reference ---
body=$(body_lines "$SKILL_FILE")
has_existing_ref=$(echo "$body" | grep -ci 'existing-code-review\|existing code review' 2>/dev/null)
if [ "$has_existing_ref" -gt 0 ]; then
  ok "SKILL.md references existing-code-review reference file"
else
  not_ok "SKILL.md references existing-code-review reference file"
fi

# --- Test 6: SKILL.md references post-impl-review reference ---
has_postimpl_ref=$(echo "$body" | grep -ci 'post-impl-review\|post-impl review\|post-implementation review' 2>/dev/null)
if [ "$has_postimpl_ref" -gt 0 ]; then
  ok "SKILL.md references post-impl-review reference file"
else
  not_ok "SKILL.md references post-impl-review reference file"
fi

# --- Test 7: SKILL.md loads shared code-review-guide ---
has_guide=$(echo "$body" | grep -ci 'code-review-guide\|code review guide' 2>/dev/null)
if [ "$has_guide" -gt 0 ]; then
  ok "SKILL.md loads shared code-review-guide"
else
  not_ok "SKILL.md loads shared code-review-guide"
fi

# --- Test 8: SKILL.md loads shared ai-failure-modes checklist ---
has_failmodes=$(echo "$body" | grep -ci 'ai-failure-modes\|ai failure modes\|failure mode' 2>/dev/null)
if [ "$has_failmodes" -gt 0 ]; then
  ok "SKILL.md loads shared ai-failure-modes checklist"
else
  not_ok "SKILL.md loads shared ai-failure-modes checklist"
fi

# --- Test 9: SKILL.md implements path routing ---
has_routing=$(echo "$body" | grep -ciE '(invocation context|standalone|post-implementation|path|route|mode)' 2>/dev/null)
if [ "$has_routing" -gt 0 ]; then
  ok "SKILL.md implements path routing between modes"
else
  not_ok "SKILL.md implements path routing between modes"
fi

# --- Test 10: existing-code-review.md reference exists and is non-empty ---
if [ -s "$EXISTING_REF" ]; then
  ok "existing-code-review.md reference file exists and is non-empty"
else
  not_ok "existing-code-review.md reference file exists and is non-empty" "file: $EXISTING_REF"
fi

# --- Test 11: existing-code-review.md contains conversational review guidance ---
existing_body=$(body_lines "$EXISTING_REF")
has_conversational=$(echo "$existing_body" | grep -ci 'conversation\|conversational\|user' 2>/dev/null)
has_spec=$(echo "$existing_body" | grep -ci 'spec\|co-author\|draft' 2>/dev/null)
if [ "$has_conversational" -gt 0 ] && [ "$has_spec" -gt 0 ]; then
  ok "existing-code-review.md contains conversational review guidance"
else
  not_ok "existing-code-review.md contains conversational review guidance" "conversational=$has_conversational spec=$has_spec"
fi

# --- Test 12: post-impl-review.md reference exists and is non-empty ---
if [ -s "$POSTIMPL_REF" ]; then
  ok "post-impl-review.md reference file exists and is non-empty"
else
  not_ok "post-impl-review.md reference file exists and is non-empty" "file: $POSTIMPL_REF"
fi

# --- Test 13: post-impl-review.md contains findings-only guidance ---
postimpl_body=$(body_lines "$POSTIMPL_REF")
has_findings=$(echo "$postimpl_body" | grep -ci 'findings\|findings-only\|non-interactive' 2>/dev/null)
if [ "$has_findings" -gt 0 ]; then
  ok "post-impl-review.md contains findings-only guidance"
else
  not_ok "post-impl-review.md contains findings-only guidance"
fi

# --- Test 14: post-impl-review.md excludes spec co-authoring ---
has_coauthor=$(echo "$postimpl_body" | grep -ci 'co-author\|spec draft\|draft spec' 2>/dev/null)
if [ "$has_coauthor" -eq 0 ]; then
  ok "post-impl-review.md excludes spec co-authoring"
else
  not_ok "post-impl-review.md excludes spec co-authoring" "found spec co-authoring references: $has_coauthor"
fi

# --- Test 15: /implement skill contains post-implementation review prompt ---
impl_body=$(body_lines "$IMPLEMENT_SKILL")
has_review_prompt=$(echo "$impl_body" | grep -ci 'review the implementation\|code review\|code-review' 2>/dev/null)
if [ "$has_review_prompt" -gt 0 ]; then
  ok "/implement skill contains post-implementation review prompt"
else
  not_ok "/implement skill contains post-implementation review prompt" "file: $IMPLEMENT_SKILL"
fi

# --- Test 16: /implement skill's review prompt follows stage-transition pattern ---
has_stage_transition=$(echo "$impl_body" | grep -ci 'would you like\|ask.*review' 2>/dev/null)
if [ "$has_stage_transition" -gt 0 ]; then
  ok "/implement skill's review prompt follows stage-transition pattern"
else
  not_ok "/implement skill's review prompt follows stage-transition pattern"
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
