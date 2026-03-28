#!/usr/bin/env bash
set -uo pipefail

PASS=0
FAIL=0
TOTAL=0

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
PROJECT_ROOT="$(cd "$SCRIPT_DIR/../.." && pwd)"

CODE_REVIEW_SKILL="$PROJECT_ROOT/assets/skills/fbk-code-review/SKILL.md"
SDL_WORKFLOW="$PROJECT_ROOT/assets/fbk-docs/fbk-sdl-workflow.md"
IMPROVE_SKILL="$PROJECT_ROOT/assets/skills/fbk-improve/SKILL.md"
IMPROVE_AGENT="$PROJECT_ROOT/assets/agents/fbk-improvement-analyst.md"

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

# --- AC-01: Code review transition seam ---

# Test 1: Code review skill's Retrospective section contains instruction to invoke /fbk-improve
if grep -qiE 'Retrospective|retrospective' "$CODE_REVIEW_SKILL" && \
   grep -q '/fbk-improve' "$CODE_REVIEW_SKILL"; then
  ok "code review skill retrospective section invokes /fbk-improve"
else
  not_ok "code review skill retrospective section invokes /fbk-improve" "missing Retrospective section or /fbk-improve invocation"
fi

# Test 2: Code review skill invocation passes <feature-name> as argument
if grep -qE '/fbk-improve.*<feature-name>|<feature-name>.*fbk-improve' "$CODE_REVIEW_SKILL"; then
  ok "code review skill passes <feature-name> argument to /fbk-improve"
else
  not_ok "code review skill passes <feature-name> argument to /fbk-improve" "invocation missing <feature-name> argument"
fi

# --- SDL workflow doc references ---

# Test 3: SDL workflow doc references self-improvement concept
if grep -qiE '/fbk-improve|fbk-improve|self-improvement' "$SDL_WORKFLOW"; then
  ok "SDL workflow doc references /fbk-improve or fbk-improve or self-improvement"
else
  not_ok "SDL workflow doc references /fbk-improve or fbk-improve or self-improvement" "no self-improvement reference found"
fi

# Test 4: SDL workflow doc reference appears after code review stage reference
code_review_line=$(grep -in 'code.review\|fbk-code-review' "$SDL_WORKFLOW" | head -1 | cut -d: -f1)
improve_line=$(grep -in '/fbk-improve\|fbk-improve\|self-improvement' "$SDL_WORKFLOW" | head -1 | cut -d: -f1)
if [ -n "$code_review_line" ] && [ -n "$improve_line" ] && [ "$improve_line" -gt "$code_review_line" ]; then
  ok "self-improvement reference appears after code review stage reference"
else
  not_ok "self-improvement reference appears after code review stage reference" "code-review line: $code_review_line, improve line: $improve_line"
fi

# --- Cross-asset file existence ---

# Test 5: Improve skill file exists
if [ -f "$IMPROVE_SKILL" ]; then
  ok "improve skill file exists"
else
  not_ok "improve skill file exists" "file not found: $IMPROVE_SKILL"
fi

# Test 6: Improve agent file exists
if [ -f "$IMPROVE_AGENT" ]; then
  ok "improve agent file exists"
else
  not_ok "improve agent file exists" "file not found: $IMPROVE_AGENT"
fi

# --- Cross-asset references ---

# Test 7: Improve skill references agent name fbk-improvement-analyst
if grep -q 'fbk-improvement-analyst' "$IMPROVE_SKILL"; then
  ok "improve skill references agent name fbk-improvement-analyst"
else
  not_ok "improve skill references agent name fbk-improvement-analyst" "agent name reference missing"
fi

# Test 8: Improve agent references authoring rules path fbk-context-assets
if grep -qiE 'fbk-context-assets|fbk-docs/fbk-context-assets' "$IMPROVE_AGENT"; then
  ok "improve agent references authoring rules path fbk-context-assets"
else
  not_ok "improve agent references authoring rules path fbk-context-assets" "authoring rules reference missing"
fi

# Test 9: Improve skill references Glob-based asset discovery
if grep -qi 'glob' "$IMPROVE_SKILL"; then
  ok "improve skill references Glob-based asset discovery"
else
  not_ok "improve skill references Glob-based asset discovery" "Glob reference missing"
fi

# Test 10: Code review skill references /fbk-improve
if grep -q '/fbk-improve' "$CODE_REVIEW_SKILL"; then
  ok "code review skill references /fbk-improve"
else
  not_ok "code review skill references /fbk-improve" "reference missing"
fi

# --- AC-06: Selective application ---

# Test 11: Improve skill contains Edit in its allowed-tools
if grep -qiE 'allowed-tools.*Edit|Edit.*allowed-tools' "$IMPROVE_SKILL" || \
   grep -qE 'allowed.*[Ee]dit|Edit' "$IMPROVE_SKILL"; then
  ok "improve skill contains Edit in allowed-tools (needed to apply diffs)"
else
  not_ok "improve skill contains Edit in allowed-tools (needed to apply diffs)" "Edit tool not found in allowed-tools"
fi

# --- Summary ---
echo ""
echo "# $PASS/$TOTAL tests passed"
if [ "$FAIL" -eq 0 ]; then
  exit 0
fi
exit 1
