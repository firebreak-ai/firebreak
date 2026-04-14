#!/usr/bin/env bash
set -uo pipefail

PASS=0
FAIL=0
TOTAL=0

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
PROJECT_ROOT="$(cd "$SCRIPT_DIR/../.." && pwd)"
DEDUP="$PROJECT_ROOT/assets/agents/fbk-sighting-deduplicator.md"
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

# Helper: extract frontmatter (lines between first --- and second ---)
frontmatter() {
  sed -n '2,/^---$/p' "$1" | sed '$d'
}

echo "TAP version 13"

# --- Test 1: Deduplicator file exists and is non-empty ---
if [ -s "$DEDUP" ]; then
  ok "Deduplicator file exists and is non-empty"
else
  not_ok "Deduplicator file exists and is non-empty" "file: $DEDUP"
fi

# --- Test 2: Deduplicator frontmatter name field is non-empty ---
fm=$(frontmatter "$DEDUP" 2>/dev/null || true)
name_val=$(echo "$fm" | grep '^name:' | sed 's/^name:[[:space:]]*//;s/[[:space:]]*$//')
if [ -n "$name_val" ]; then
  ok "Deduplicator frontmatter name field is non-empty"
else
  not_ok "Deduplicator frontmatter name field is non-empty" "name_val='$name_val'"
fi

# --- Test 3: Deduplicator tools field does NOT contain Read, Grep, Glob, or Bash ---
tools_line=$(echo "$fm" | grep '^tools:')
has_read=$(echo "$tools_line" | grep -c 'Read' || true)
has_grep=$(echo "$tools_line" | grep -c 'Grep' || true)
has_glob=$(echo "$tools_line" | grep -c 'Glob' || true)
has_bash=$(echo "$tools_line" | grep -c 'Bash' || true)
if [ "$has_read" -eq 0 ] && [ "$has_grep" -eq 0 ] && [ "$has_glob" -eq 0 ] && [ "$has_bash" -eq 0 ]; then
  ok "Deduplicator tools field does NOT contain Read, Grep, Glob, or Bash"
else
  not_ok "Deduplicator tools field does NOT contain Read, Grep, Glob, or Bash" "tools_line='$tools_line'"
fi

# --- Test 4: Deduplicator body contains merge mandate language ---
if grep -qi 'merge' "$DEDUP" 2>/dev/null; then
  ok "Deduplicator body contains merge mandate language"
else
  not_ok "Deduplicator body contains merge mandate language" "file: $DEDUP"
fi

# --- Test 5: Deduplicator body contains merge log or merged output reference ---
if grep -qiE 'merge log|merged' "$DEDUP" 2>/dev/null; then
  ok "Deduplicator body contains merge log or merged output reference"
else
  not_ok "Deduplicator body contains merge log or merged output reference" "file: $DEDUP"
fi

# --- Test 6: Deduplicator body contains pattern label preservation rule ---
if grep -qi 'pattern label' "$DEDUP" 2>/dev/null; then
  ok "Deduplicator body contains pattern label preservation rule"
else
  not_ok "Deduplicator body contains pattern label preservation rule" "file: $DEDUP"
fi

# --- Test 7: SKILL.md contains deduplicat or dedup reference ---
if grep -qi 'deduplicat\|dedup' "$SKILL" 2>/dev/null; then
  ok "SKILL.md contains deduplicat or dedup reference"
else
  not_ok "SKILL.md contains deduplicat or dedup reference" "file: $SKILL"
fi

# --- Test 8: SKILL.md contains step 1a or 1a reference near dedup context ---
if grep -qE 'step 1a|[[:space:]]1a[[:space:]]|^1a[[:space:]]|1a\.' "$SKILL" 2>/dev/null; then
  ok "SKILL.md contains step 1a or 1a reference"
else
  not_ok "SKILL.md contains step 1a or 1a reference" "file: $SKILL"
fi

# --- Test 9: SKILL.md contains single-agent bypass language ---
if grep -qiE 'single agent|skip.*dedup|bypass' "$SKILL" 2>/dev/null; then
  ok "SKILL.md contains single-agent bypass language"
else
  not_ok "SKILL.md contains single-agent bypass language" "file: $SKILL"
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
