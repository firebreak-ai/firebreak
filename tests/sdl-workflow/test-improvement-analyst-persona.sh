#!/usr/bin/env bash
set -uo pipefail

PASS=0
FAIL=0
TOTAL=0

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
PROJECT_ROOT="$(cd "$SCRIPT_DIR/../.." && pwd)"
AGENT="$PROJECT_ROOT/assets/agents/fbk-improvement-analyst.md"

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

# Helper: extract body after second ---
body_lines() { awk '/^---$/{c++; if(c==2){found=1; next}} found' "$1"; }

# Helper: extract persona section (body start to first ## heading)
persona_section() { body_lines "$1" | awk '/^## /{exit} {print}'; }

echo "TAP version 13"

# --- Test 1: file exists and is non-empty ---
if [ -s "$AGENT" ]; then
  ok "Agent file exists and is non-empty"
else
  not_ok "Agent file exists and is non-empty" "file: $AGENT"
fi

# --- Test 2: has valid YAML frontmatter ---
first_line=$(head -1 "$AGENT" 2>/dev/null || true)
closing_count=$(grep -c '^---$' "$AGENT" 2>/dev/null || true)
if [ "$first_line" = "---" ] && [ "$closing_count" -ge 2 ]; then
  ok "Agent has valid YAML frontmatter"
else
  not_ok "Agent has valid YAML frontmatter" "first_line='$first_line' closing_count=$closing_count"
fi

# --- Test 3: persona section contains at least 5 lines ---
persona_line_count=$(persona_section "$AGENT" | wc -l | tr -d ' ')
if [ "$persona_line_count" -ge 5 ]; then
  ok "Persona section contains at least 5 lines"
else
  not_ok "Persona section contains at least 5 lines" "persona_line_count=$persona_line_count"
fi

# --- Test 4: persona section at or below 40 lines ---
if [ "$persona_line_count" -le 40 ]; then
  ok "Persona section at or below 40 lines"
else
  not_ok "Persona section at or below 40 lines" "persona_line_count=$persona_line_count"
fi

# --- Test 5: persona contains role-activation language ---
if persona_section "$AGENT" | grep -qi 'process improvement engineer'; then
  ok "Persona contains role-activation language"
else
  not_ok "Persona contains role-activation language" "grep for 'process improvement engineer' failed"
fi

# --- Test 6: persona contains Output quality bars heading ---
if body_lines "$AGENT" | grep -q '^## Output quality bars$'; then
  ok "Persona contains Output quality bars heading"
else
  not_ok "Persona contains Output quality bars heading" "grep for '^## Output quality bars$' failed"
fi

# --- Test 7: existing task-logic section Input contract preserved ---
if body_lines "$AGENT" | grep -q '^## Input contract$'; then
  ok "Existing task-logic section Input contract preserved"
else
  not_ok "Existing task-logic section Input contract preserved" "grep for '^## Input contract$' failed"
fi

# --- Test 8: existing task-logic section Workflow preserved ---
if body_lines "$AGENT" | grep -q '^## Workflow$'; then
  ok "Existing task-logic section Workflow preserved"
else
  not_ok "Existing task-logic section Workflow preserved" "grep for '^## Workflow$' failed"
fi

# --- Test 9: existing task-logic section Proposal output format preserved ---
if body_lines "$AGENT" | grep -q '^## Proposal output format$'; then
  ok "Existing task-logic section Proposal output format preserved"
else
  not_ok "Existing task-logic section Proposal output format preserved" "grep for '^## Proposal output format$' failed"
fi

# --- Test 10: existing task-logic section Scope discipline preserved ---
if body_lines "$AGENT" | grep -q '^## Scope discipline$'; then
  ok "Existing task-logic section Scope discipline preserved"
else
  not_ok "Existing task-logic section Scope discipline preserved" "grep for '^## Scope discipline$' failed"
fi

# --- Test 11: retrospective-observation grounding preserved ---
if body_lines "$AGENT" | grep -qi 'retrospective observation'; then
  ok "Retrospective-observation grounding preserved"
else
  not_ok "Retrospective-observation grounding preserved" "grep for 'retrospective observation' failed"
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
