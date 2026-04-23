#!/usr/bin/env bash
set -uo pipefail

PASS=0
FAIL=0
TOTAL=0

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
PROJECT_ROOT="$(cd "$SCRIPT_DIR/../.." && pwd)"
DOC="$PROJECT_ROOT/assets/fbk-docs/fbk-context-assets/agents.md"

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

# --- Test 1: file exists and is non-empty ---
if [ -s "$DOC" ]; then
  ok "agents.md exists and is non-empty"
else
  not_ok "agents.md exists and is non-empty" "file: $DOC"
fi

# --- Test 2: contains a top-level persona authoring guidance section ---
if grep -qE '^## .*[Pp]ersona' "$DOC" 2>/dev/null; then
  ok "agents.md contains a top-level persona authoring guidance section"
else
  not_ok "agents.md contains a top-level persona authoring guidance section"
fi

# --- Test 3: enterprise activation baseline coverage ---
if grep -qi 'enterprise' "$DOC" 2>/dev/null && grep -qi 'activation' "$DOC" 2>/dev/null; then
  ok "agents.md covers enterprise activation baseline"
else
  not_ok "agents.md covers enterprise activation baseline" "Anchor phrase: 'enterprise activation'"
fi

# --- Test 4: correctness-vs-maintainability rationale ---
if grep -qi 'maintainability' "$DOC" 2>/dev/null && grep -qi 'correctness' "$DOC" 2>/dev/null; then
  ok "agents.md covers correctness-vs-maintainability rationale"
else
  not_ok "agents.md covers correctness-vs-maintainability rationale"
fi

# --- Test 5: persona structure — role activation ---
if grep -qi 'role activation' "$DOC" 2>/dev/null; then
  ok "agents.md covers persona structure - role activation"
else
  not_ok "agents.md covers persona structure - role activation"
fi

# --- Test 6: persona structure — output quality bars ---
if grep -qi 'output quality bars' "$DOC" 2>/dev/null; then
  ok "agents.md covers persona structure - output quality bars"
else
  not_ok "agents.md covers persona structure - output quality bars"
fi

# --- Test 7: persona structure — anti-defaults ---
if grep -qi 'anti-default' "$DOC" 2>/dev/null; then
  ok "agents.md covers persona structure - anti-defaults"
else
  not_ok "agents.md covers persona structure - anti-defaults"
fi

# --- Test 8: personas and spawn prompts precedence ---
if grep -qi 'spawn prompt' "$DOC" 2>/dev/null; then
  ok "agents.md covers personas and spawn prompts precedence"
else
  not_ok "agents.md covers personas and spawn prompts precedence"
fi

# --- Test 9: reference implementations — Detector and Challenger named ---
if grep -q 'Detector' "$DOC" 2>/dev/null && grep -q 'Challenger' "$DOC" 2>/dev/null; then
  ok "agents.md references Detector and Challenger implementations"
else
  not_ok "agents.md references Detector and Challenger implementations"
fi

# --- Test 10: what not to include ---
if grep -qiE 'what not to include|not to include' "$DOC" 2>/dev/null; then
  ok "agents.md covers what not to include"
else
  not_ok "agents.md covers what not to include"
fi

# --- Test 11: when personas are unnecessary ---
if grep -qi 'unnecessary' "$DOC" 2>/dev/null; then
  ok "agents.md covers when personas are unnecessary"
else
  not_ok "agents.md covers when personas are unnecessary"
fi

# --- Test 12: mechanical-task example named ---
if grep -qi 'mechanical' "$DOC" 2>/dev/null; then
  ok "agents.md names mechanical tasks as persona-unnecessary"
else
  not_ok "agents.md names mechanical tasks as persona-unnecessary"
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
