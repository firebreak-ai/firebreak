#!/usr/bin/env bash
set -uo pipefail

PASS=0
FAIL=0
TOTAL=0

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
PROJECT_ROOT="$(cd "$SCRIPT_DIR/../.." && pwd)"
LOADER="$PROJECT_ROOT/home/dot-claude/hooks/sdl-workflow/config-loader.py"
FIXTURES="$PROJECT_ROOT/tests/fixtures/config"

TMPDIR_BASE="$(mktemp -d)"
trap 'rm -rf "$TMPDIR_BASE"' EXIT

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

# Helper: create mock project root
make_project() {
  local d="$TMPDIR_BASE/$1"
  mkdir -p "$d/.claude/automation"
  echo "$d"
}

echo "TAP version 13"

# --- Test 1: defaults when no config files exist ---
PR=$(make_project t1)
OUTPUT=$(python3 "$LOADER" load "$PR" 2>&1)
RESULT=$(echo "$OUTPUT" | python3 -c "
import sys, json
d = json.load(sys.stdin)
assert d['token_budget'] is None
assert d['max_concurrent_agents'] == 1
assert d['replan_cap'] == 2
assert d['model'] == 'sonnet'
print('yes')
" 2>/dev/null)
if [ "$RESULT" = "yes" ]; then
  ok "defaults returned when no config files exist"
else
  not_ok "defaults returned when no config files exist" "$OUTPUT"
fi

# --- Test 2: project config.yml overrides defaults ---
PR=$(make_project t2)
cp "$FIXTURES/valid-config.yml" "$PR/.claude/automation/config.yml"
OUTPUT=$(python3 "$LOADER" load "$PR" 2>&1)
RESULT=$(echo "$OUTPUT" | python3 -c "
import sys, json
d = json.load(sys.stdin)
assert d['token_budget'] == 5000
assert d['max_concurrent_agents'] == 3
assert d['replan_cap'] == 5
assert d['model'] == 'sonnet'
print('yes')
" 2>/dev/null)
if [ "$RESULT" = "yes" ]; then
  ok "project config.yml overrides defaults"
else
  not_ok "project config.yml overrides defaults" "$OUTPUT"
fi

# --- Test 3: spec frontmatter overrides project config ---
PR=$(make_project t3)
cp "$FIXTURES/valid-config.yml" "$PR/.claude/automation/config.yml"
OUTPUT=$(python3 "$LOADER" load "$PR" "$FIXTURES/spec-with-frontmatter.md" 2>&1)
RESULT=$(echo "$OUTPUT" | python3 -c "
import sys, json
d = json.load(sys.stdin)
assert d['token_budget'] == 8000, f'token_budget={d[\"token_budget\"]}'
assert d['max_concurrent_agents'] == 3
assert d['model'] == 'haiku', f'model={d[\"model\"]}'
print('yes')
" 2>/dev/null)
if [ "$RESULT" = "yes" ]; then
  ok "spec frontmatter overrides project config"
else
  not_ok "spec frontmatter overrides project config" "$OUTPUT"
fi

# --- Test 4: spec without frontmatter returns defaults ---
PR=$(make_project t4)
SPEC="$TMPDIR_BASE/no-fm.md"
echo "## Problem" > "$SPEC"
echo "No frontmatter here." >> "$SPEC"
OUTPUT=$(python3 "$LOADER" load "$PR" "$SPEC" 2>&1)
RESULT=$(echo "$OUTPUT" | python3 -c "
import sys, json
d = json.load(sys.stdin)
assert d['token_budget'] is None
assert d['max_concurrent_agents'] == 1
print('yes')
" 2>/dev/null)
if [ "$RESULT" = "yes" ]; then
  ok "spec without frontmatter returns defaults"
else
  not_ok "spec without frontmatter returns defaults" "$OUTPUT"
fi

# --- Test 5: cold-start detects missing test runner ---
PR=$(make_project t5)
STDERR=$(python3 "$LOADER" cold-start-check "$PR" 2>&1 >/dev/null)
if echo "$STDERR" | grep -qi "test runner"; then
  ok "cold-start detects missing test runner"
else
  not_ok "cold-start detects missing test runner" "$STDERR"
fi

# --- Test 6: cold-start detects missing linting config ---
if echo "$STDERR" | grep -qi "linting"; then
  ok "cold-start detects missing linting config"
else
  not_ok "cold-start detects missing linting config" "$STDERR"
fi

# --- Test 7: cold-start detects missing CLAUDE.md ---
if echo "$STDERR" | grep -qi "CLAUDE.md"; then
  ok "cold-start detects missing CLAUDE.md"
else
  not_ok "cold-start detects missing CLAUDE.md" "$STDERR"
fi

# --- Test 8: cold-start passes when prerequisites exist ---
PR=$(make_project t8)
echo '{}' > "$PR/package.json"
echo '{}' > "$PR/.eslintrc.json"
echo "# Project" > "$PR/CLAUDE.md"
STDERR=$(python3 "$LOADER" cold-start-check "$PR" 2>&1 >/dev/null)
if [ -z "$STDERR" ]; then
  ok "cold-start passes when prerequisites exist"
else
  not_ok "cold-start passes when prerequisites exist" "stderr: $STDERR"
fi

# --- Test 9: verify.yml loads correctly ---
PR=$(make_project t9)
cp "$FIXTURES/valid-verify.yml" "$PR/.claude/automation/verify.yml"
OUTPUT=$(python3 "$LOADER" load-verify "$PR" 2>&1)
RESULT=$(echo "$OUTPUT" | python3 -c "
import sys, json
d = json.load(sys.stdin)
checks = d['checks']
assert len(checks) == 2
assert checks[0]['required'] is True
assert checks[1]['required'] is False
print('yes')
" 2>/dev/null)
if [ "$RESULT" = "yes" ]; then
  ok "verify.yml loads correctly"
else
  not_ok "verify.yml loads correctly" "$OUTPUT"
fi

# --- Test 10: malformed config.yml produces error ---
PR=$(make_project t10)
cp "$FIXTURES/malformed-config.yml" "$PR/.claude/automation/config.yml"
OUTPUT=$(python3 "$LOADER" load "$PR" 2>&1)
RC=$?
if [ $RC -ne 0 ]; then
  ok "malformed config.yml produces error"
else
  not_ok "malformed config.yml produces error" "exit $RC, output: $OUTPUT"
fi

# --- Summary ---
echo ""
echo "1..$TOTAL"
echo "# $PASS/$TOTAL tests passed"
if [ "$FAIL" -gt 0 ]; then
  exit 1
fi
exit 0
