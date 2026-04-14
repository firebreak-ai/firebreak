#!/usr/bin/env bash
set -uo pipefail

PASS=0
FAIL=0
TOTAL=0

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
PROJECT_ROOT="$(cd "$SCRIPT_DIR/../.." && pwd)"
TR="$PROJECT_ROOT/assets/agents/fbk-cr-test-reviewer.md"

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

# --- Test 1: Test Reviewer agent file exists and is non-empty ---
if [ -s "$TR" ]; then
  ok "Test Reviewer agent file exists and is non-empty"
else
  not_ok "Test Reviewer agent file exists and is non-empty" "file: $TR"
fi

# --- Test 2: Test Reviewer frontmatter has non-empty name field ---
fm=$(frontmatter "$TR" 2>/dev/null || true)
name_val=$(echo "$fm" | grep '^name:' | sed 's/^name:[[:space:]]*//;s/[[:space:]]*$//')
if [ -n "$name_val" ]; then
  ok "Test Reviewer frontmatter has non-empty name field"
else
  not_ok "Test Reviewer frontmatter has non-empty name field" "name_val='$name_val'"
fi

# --- Test 3: Test Reviewer frontmatter tools field lists Read, Grep, Glob ---
tools_line=$(echo "$fm" | grep '^tools:')
has_read=$(echo "$tools_line" | grep -c 'Read')
has_grep=$(echo "$tools_line" | grep -c 'Grep')
has_glob=$(echo "$tools_line" | grep -c 'Glob')
if [ "$has_read" -gt 0 ] && [ "$has_grep" -gt 0 ] && [ "$has_glob" -gt 0 ]; then
  ok "Test Reviewer frontmatter tools field lists Read, Grep, Glob"
else
  not_ok "Test Reviewer frontmatter tools field lists Read, Grep, Glob" "tools_line='$tools_line'"
fi

# --- Test 4: Body contains test-intent alignment ---
body=$(sed '1,/^---$/d' "$TR" 2>/dev/null | tail -n +2)
if echo "$body" | grep -qiE 'test-intent alignment|test.*intent.*alignment'; then
  ok "Body contains test-intent alignment"
else
  not_ok "Body contains test-intent alignment"
fi

# --- Test 5: Body contains tests protecting bugs ---
if echo "$body" | grep -qi 'protecting bugs\|tests protecting bugs'; then
  ok "Body contains tests protecting bugs"
else
  not_ok "Body contains tests protecting bugs"
fi

# --- Test 6: Body contains Name-assertion mismatch ---
if echo "$body" | grep -qi 'name-assertion mismatch'; then
  ok "Body contains Name-assertion mismatch"
else
  not_ok "Body contains Name-assertion mismatch"
fi

# --- Test 7: Body contains Non-enforcing test ---
if echo "$body" | grep -qi 'non-enforcing test'; then
  ok "Body contains Non-enforcing test"
else
  not_ok "Body contains Non-enforcing test"
fi

# --- Test 8: Body contains Semantically incoherent fixtures ---
if echo "$body" | grep -qi 'semantically incoherent'; then
  ok "Body contains Semantically incoherent fixtures"
else
  not_ok "Body contains Semantically incoherent fixtures"
fi

# --- Test 9: Body contains Mock permissiveness ---
if echo "$body" | grep -qi 'mock permissiveness'; then
  ok "Body contains Mock permissiveness"
else
  not_ok "Body contains Mock permissiveness"
fi

# --- Test 10: Body contains Test-production string alignment ---
if echo "$body" | grep -qi 'test-production string\|test-production'; then
  ok "Body contains Test-production string alignment"
else
  not_ok "Body contains Test-production string alignment"
fi

# --- Test 11: Body contains sighting output reference ---
if echo "$body" | grep -q 'sighting' && echo "$body" | grep -qE 'TR-S-|[^a-zA-Z]S-'; then
  ok "Body contains sighting output reference"
else
  not_ok "Body contains sighting output reference"
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
