#!/usr/bin/env bash
set -uo pipefail

PASS=0
FAIL=0
TOTAL=0

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
PROJECT_ROOT="$(cd "$SCRIPT_DIR/../.." && pwd)"
AGENT="$PROJECT_ROOT/assets/agents/fbk-test-reviewer.md"

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

# Helper: extract body (lines after second ---)
body_lines() {
  awk '/^---$/{c++; if(c==2){found=1; next}} found' "$1"
}

# Helper: extract persona section (from body start to first ## heading)
persona_section() {
  body_lines "$1" | awk '/^## /{exit} {print}'
}

echo "TAP version 13"

# --- Test 1: Agent file exists and is non-empty ---
if [ -s "$AGENT" ]; then
  ok "Agent file exists and is non-empty"
else
  not_ok "Agent file exists and is non-empty" "file: $AGENT"
fi

# --- Test 2: Agent has valid YAML frontmatter ---
first_line=$(head -1 "$AGENT" 2>/dev/null || true)
closing_count=$(grep -c '^---$' "$AGENT" 2>/dev/null || true)
if [ "$first_line" = "---" ] && [ "$closing_count" -ge 2 ]; then
  ok "Agent has valid YAML frontmatter"
else
  not_ok "Agent has valid YAML frontmatter" "first_line='$first_line' closing_count=$closing_count"
fi

# --- Test 3: Persona section contains at least 5 lines ---
persona_line_count=$(persona_section "$AGENT" | wc -l | tr -d ' ')
if [ "$persona_line_count" -ge 5 ]; then
  ok "Persona section contains at least 5 lines"
else
  not_ok "Persona section contains at least 5 lines" "persona_line_count=$persona_line_count (need >= 5)"
fi

# --- Test 4: Persona section at or below 40 lines ---
persona_line_count=$(persona_section "$AGENT" | wc -l | tr -d ' ')
if [ "$persona_line_count" -le 40 ]; then
  ok "Persona section at or below 40 lines"
else
  not_ok "Persona section at or below 40 lines" "persona_line_count=$persona_line_count (need <= 40)"
fi

# --- Test 5: Persona section contains role-activation language (QA engineer) ---
body=$(body_lines "$AGENT")
if echo "$body" | grep -qi 'QA engineer'; then
  ok "Persona section contains role-activation language (QA engineer)"
else
  not_ok "Persona section contains role-activation language (QA engineer)" "QA engineer phrase not found"
fi

# --- Test 6: Persona section contains ## Output quality bars heading ---
if echo "$body" | grep -q '^## Output quality bars$'; then
  ok "Persona section contains ## Output quality bars heading"
else
  not_ok "Persona section contains ## Output quality bars heading" "heading not found in body"
fi

# --- Test 7: Existing task-logic section ## Evaluation criteria preserved ---
if echo "$body" | grep -q '^## Evaluation criteria$'; then
  ok "Existing task-logic section ## Evaluation criteria preserved"
else
  not_ok "Existing task-logic section ## Evaluation criteria preserved" "section not found in body"
fi

# --- Test 8: Existing task-logic section ## Context isolation preserved ---
if echo "$body" | grep -q '^## Context isolation$'; then
  ok "Existing task-logic section ## Context isolation preserved"
else
  not_ok "Existing task-logic section ## Context isolation preserved" "section not found in body"
fi

# --- Test 9: Existing task-logic section ## Override mechanism preserved ---
if echo "$body" | grep -q '^## Override mechanism$'; then
  ok "Existing task-logic section ## Override mechanism preserved"
else
  not_ok "Existing task-logic section ## Override mechanism preserved" "section not found in body"
fi

# --- Test 10: Pipeline-blocking authority reference preserved ---
if echo "$body" | grep -qi 'pipeline-blocking'; then
  ok "Pipeline-blocking authority reference preserved"
else
  not_ok "Pipeline-blocking authority reference preserved" "pipeline-blocking phrase not found"
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
