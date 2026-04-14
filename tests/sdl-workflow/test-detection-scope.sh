#!/usr/bin/env bash
set -uo pipefail

PASS=0
FAIL=0
TOTAL=0

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
PROJECT_ROOT="$(cd "$SCRIPT_DIR/../.." && pwd)"
CHECKLIST="$PROJECT_ROOT/assets/fbk-docs/fbk-sdl-workflow/ai-failure-modes.md"
QUALITY="$PROJECT_ROOT/assets/fbk-docs/fbk-design-guidelines/quality-detection.md"
EXISTING="$PROJECT_ROOT/assets/skills/fbk-code-review/references/existing-code-review.md"

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

# --- Test 1: ai-failure-modes.md checklist item count >= 14 (AC-36 through AC-42) ---
numbered=$(grep -cE '^[0-9]+\.' "$CHECKLIST" 2>/dev/null || true)
if [ "$numbered" -ge 14 ]; then
  ok "ai-failure-modes.md checklist item count >= 14"
else
  not_ok "ai-failure-modes.md checklist item count >= 14" "numbered=$numbered"
fi

# --- Test 2: ai-failure-modes.md contains "bare literal" keyword (AC-36) ---
if grep -qi 'bare literal' "$CHECKLIST"; then
  ok "ai-failure-modes.md contains \"bare literal\" keyword"
else
  not_ok "ai-failure-modes.md contains \"bare literal\" keyword"
fi

# --- Test 3: ai-failure-modes.md contains "dead infrastructure" keyword (AC-37) ---
if grep -qi 'dead infrastructure' "$CHECKLIST"; then
  ok "ai-failure-modes.md contains \"dead infrastructure\" keyword"
else
  not_ok "ai-failure-modes.md contains \"dead infrastructure\" keyword"
fi

# --- Test 4: ai-failure-modes.md contains "non-enforcing" keyword (AC-38) ---
if grep -qi 'non-enforcing' "$CHECKLIST"; then
  ok "ai-failure-modes.md contains \"non-enforcing\" keyword"
else
  not_ok "ai-failure-modes.md contains \"non-enforcing\" keyword"
fi

# --- Test 5: ai-failure-modes.md contains "comment-code drift" keyword (AC-39) ---
if grep -qiE 'comment.*(code|behavior).*drift|drift.*(comment|code)' "$CHECKLIST"; then
  ok "ai-failure-modes.md contains \"comment-code drift\" keyword"
else
  not_ok "ai-failure-modes.md contains \"comment-code drift\" keyword"
fi

# --- Test 6: ai-failure-modes.md contains "sentinel" keyword (AC-40) ---
if grep -qi 'sentinel' "$CHECKLIST"; then
  ok "ai-failure-modes.md contains \"sentinel\" keyword"
else
  not_ok "ai-failure-modes.md contains \"sentinel\" keyword"
fi

# --- Test 7: ai-failure-modes.md contains "context bypass" keyword (AC-41) ---
if grep -qi 'context bypass' "$CHECKLIST"; then
  ok "ai-failure-modes.md contains \"context bypass\" keyword"
else
  not_ok "ai-failure-modes.md contains \"context bypass\" keyword"
fi

# --- Test 8: ai-failure-modes.md contains "string-based error" keyword (AC-42) ---
if grep -qi 'string-based error' "$CHECKLIST"; then
  ok "ai-failure-modes.md contains \"string-based error\" keyword"
else
  not_ok "ai-failure-modes.md contains \"string-based error\" keyword"
fi

# --- Test 9: quality-detection.md detection target count >= 15 (AC-31 through AC-35) ---
headings=$(grep -cE '^## ' "$QUALITY" 2>/dev/null || true)
if [ "$headings" -ge 15 ]; then
  ok "quality-detection.md detection target count >= 15"
else
  not_ok "quality-detection.md detection target count >= 15" "headings=$headings"
fi

# --- Test 10: quality-detection.md contains "parallel collection" keyword (AC-31) ---
if grep -qi 'parallel collection' "$QUALITY"; then
  ok "quality-detection.md contains \"parallel collection\" keyword"
else
  not_ok "quality-detection.md contains \"parallel collection\" keyword"
fi

# --- Test 11: quality-detection.md contains "dead infrastructure" keyword (AC-32) ---
if grep -qi 'dead infrastructure' "$QUALITY"; then
  ok "quality-detection.md contains \"dead infrastructure\" keyword"
else
  not_ok "quality-detection.md contains \"dead infrastructure\" keyword"
fi

# --- Test 12: quality-detection.md contains "semantic drift" keyword (AC-33) ---
if grep -qi 'semantic drift' "$QUALITY"; then
  ok "quality-detection.md contains \"semantic drift\" keyword"
else
  not_ok "quality-detection.md contains \"semantic drift\" keyword"
fi

# --- Test 13: quality-detection.md contains "silent error" or "context discard" keyword (AC-34) ---
if grep -qiE 'silent error|context discard' "$QUALITY"; then
  ok "quality-detection.md contains \"silent error\" or \"context discard\" keyword"
else
  not_ok "quality-detection.md contains \"silent error\" or \"context discard\" keyword"
fi

# --- Test 14: quality-detection.md contains "string-based type" keyword (AC-35) ---
if grep -qi 'string-based type' "$QUALITY"; then
  ok "quality-detection.md contains \"string-based type\" keyword"
else
  not_ok "quality-detection.md contains \"string-based type\" keyword"
fi

# --- Test 15: quality-detection.md contains "dual-path" keyword (AC-43) ---
if grep -qiE 'dual.path' "$QUALITY"; then
  ok "quality-detection.md contains \"dual-path\" keyword"
else
  not_ok "quality-detection.md contains \"dual-path\" keyword"
fi

# --- Test 16: quality-detection.md contains "string alignment" or "test-production" keyword (AC-45) ---
if grep -qiE 'string alignment|test.production' "$QUALITY"; then
  ok "quality-detection.md contains \"string alignment\" or \"test-production\" keyword"
else
  not_ok "quality-detection.md contains \"string alignment\" or \"test-production\" keyword"
fi

# --- Test 17: existing-code-review.md contains severity ordering keyword (AC-48) ---
if grep -qiE 'severity|critical first' "$EXISTING"; then
  ok "existing-code-review.md contains severity ordering keyword"
else
  not_ok "existing-code-review.md contains severity ordering keyword"
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
