#!/usr/bin/env bash
set -uo pipefail

PASS=0
FAIL=0
TOTAL=0

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
PROJECT_ROOT="$(cd "$SCRIPT_DIR/../.." && pwd)"
SKILL="$PROJECT_ROOT/assets/skills/fbk-code-review/SKILL.md"

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

# --- Test 1: SKILL.md references pipeline.py ---
if grep -q 'pipeline.py' "$SKILL" 2>/dev/null; then
  ok "SKILL.md references pipeline.py"
else
  not_ok "SKILL.md references pipeline.py" "file: $SKILL"
fi

# --- Test 2: SKILL.md references uv run for pipeline invocation ---
if grep -q 'uv run' "$SKILL" 2>/dev/null; then
  ok "SKILL.md references uv run for pipeline invocation"
else
  not_ok "SKILL.md references uv run for pipeline invocation" "file: $SKILL"
fi

# --- Test 3: SKILL.md references JSON as the working format ---
if grep -qi 'JSON' "$SKILL" 2>/dev/null; then
  ok "SKILL.md references JSON as the working format"
else
  not_ok "SKILL.md references JSON as the working format" "file: $SKILL"
fi

# --- Test 4: SKILL.md references validate subcommand or run subcommand ---
if grep -qE 'validate|\.py run' "$SKILL" 2>/dev/null; then
  ok "SKILL.md references validate or run subcommand"
else
  not_ok "SKILL.md references validate or run subcommand" "file: $SKILL"
fi

# --- Test 5: SKILL.md references domain-filter or preset in pipeline context ---
if grep -qiE 'domain.filter|preset' "$SKILL" 2>/dev/null; then
  ok "SKILL.md references domain-filter or preset in pipeline context"
else
  not_ok "SKILL.md references domain-filter or preset in pipeline context" "file: $SKILL"
fi

# --- Test 6: SKILL.md references to-markdown for review report conversion ---
if grep -qiE 'to.markdown|to-markdown' "$SKILL" 2>/dev/null; then
  ok "SKILL.md references to-markdown for review report conversion"
else
  not_ok "SKILL.md references to-markdown for review report conversion" "file: $SKILL"
fi

# --- Test 7: SKILL.md specifies behavioral-only as default preset ---
if grep -qi 'behavioral-only' "$SKILL" 2>/dev/null; then
  ok "SKILL.md specifies behavioral-only as default preset"
else
  not_ok "SKILL.md specifies behavioral-only as default preset" "file: $SKILL"
fi

# --- Test 8: SKILL.md specifies minor as default severity threshold ---
section=$(sed -n '/## Detection-Verification Loop/,/^## /p' "$SKILL" 2>/dev/null || true)
if echo "$section" | grep -qiE 'minor|default.*severity' 2>/dev/null; then
  ok "SKILL.md specifies minor as default severity threshold"
else
  not_ok "SKILL.md specifies minor as default severity threshold" "minor not found in Detection-Verification Loop section"
fi

# --- Test 9: SKILL.md states preset and severity are overridable ---
if grep -qiE 'overrid|user.*instruction|user.*specify' "$SKILL" 2>/dev/null; then
  ok "SKILL.md states preset and severity are overridable"
else
  not_ok "SKILL.md states preset and severity are overridable" "file: $SKILL"
fi

# --- Test 10: SKILL.md Challenger receives JSON, not markdown ---
if grep -qiE 'Challenger.*JSON|filtered JSON|JSON sighting' "$SKILL" 2>/dev/null; then
  ok "SKILL.md Challenger receives JSON, not markdown"
else
  not_ok "SKILL.md Challenger receives JSON, not markdown" "file: $SKILL"
fi

# --- Test 11: SKILL.md markdown conversion happens once for review report ---
if grep -qiE 'markdown.*once|convert.*markdown.*report|to-markdown.*report' "$SKILL" 2>/dev/null; then
  ok "SKILL.md markdown conversion happens once for review report"
else
  not_ok "SKILL.md markdown conversion happens once for review report" "file: $SKILL"
fi

# --- Test 12: SKILL.md still contains stuck-agent recovery ---
if grep -qiE 'stuck.agent|unresponsive|relaunch' "$SKILL" 2>/dev/null; then
  ok "SKILL.md still contains stuck-agent recovery"
else
  not_ok "SKILL.md still contains stuck-agent recovery" "file: $SKILL"
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
