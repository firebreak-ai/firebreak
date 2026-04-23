#!/usr/bin/env bash
set -uo pipefail

PASS=0
FAIL=0
TOTAL=0

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
PROJECT_ROOT="$(cd "$SCRIPT_DIR/../.." && pwd)"
SPEC_AUTHOR="$PROJECT_ROOT/assets/agents/fbk-spec-author.md"
TASK_COMPILER="$PROJECT_ROOT/assets/agents/fbk-task-compiler.md"
IMPLEMENTER="$PROJECT_ROOT/assets/agents/fbk-implementer.md"

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

# Helper: count body lines
body_line_count() {
  body_lines "$1" | wc -l | tr -d ' '
}

echo "TAP version 13"

# ============================================================================
# fbk-spec-author.md Tests (A-F)
# ============================================================================

# Test 1A: fbk-spec-author.md exists and is non-empty
if [ -s "$SPEC_AUTHOR" ]; then
  ok "fbk-spec-author.md exists and is non-empty"
else
  not_ok "fbk-spec-author.md exists and is non-empty" "file: $SPEC_AUTHOR"
fi

# Test 2B: fbk-spec-author.md has valid YAML frontmatter
first_line=$(head -1 "$SPEC_AUTHOR" 2>/dev/null || true)
closing_count=$(grep -c '^---$' "$SPEC_AUTHOR" 2>/dev/null || true)
if [ "$first_line" = "---" ] && [ "$closing_count" -ge 2 ]; then
  ok "fbk-spec-author.md has valid YAML frontmatter"
else
  not_ok "fbk-spec-author.md has valid YAML frontmatter" "first_line='$first_line' closing_count=$closing_count"
fi

# Test 3C: fbk-spec-author.md body at or below 40 lines
body_count=$(body_line_count "$SPEC_AUTHOR" 2>/dev/null)
body_count=${body_count:-999}
if [ "$body_count" -le 40 ]; then
  ok "fbk-spec-author.md body at or below 40 lines"
else
  not_ok "fbk-spec-author.md body at or below 40 lines" "body_count=$body_count"
fi

# Test 4D: fbk-spec-author.md body contains '## Output quality bars' heading
if body_lines "$SPEC_AUTHOR" 2>/dev/null | grep -q '^## Output quality bars$'; then
  ok "fbk-spec-author.md body contains '## Output quality bars' heading"
else
  not_ok "fbk-spec-author.md body contains '## Output quality bars' heading"
fi

# Test 5E: fbk-spec-author.md frontmatter has non-empty name and description
fm=$(frontmatter "$SPEC_AUTHOR" 2>/dev/null || true)
has_name=$(echo "$fm" | grep -q '^name:.*[^[:space:]]' && echo 1 || echo 0)
has_desc=$(echo "$fm" | grep -q '^description:.*[^[:space:]]' && echo 1 || echo 0)
if [ "$has_name" -eq 1 ] && [ "$has_desc" -eq 1 ]; then
  ok "fbk-spec-author.md frontmatter has non-empty name and description"
else
  not_ok "fbk-spec-author.md frontmatter has non-empty name and description" "has_name=$has_name has_desc=$has_desc"
fi

# Test 6F: fbk-spec-author.md tools field matches spec allowlist (Read, Grep, Glob; no Edit, Write, Bash)
tools_line=$(echo "$fm" | grep '^tools:')
has_read=$(echo "$tools_line" | grep -q 'Read' && echo 1 || echo 0)
has_grep=$(echo "$tools_line" | grep -q 'Grep' && echo 1 || echo 0)
has_glob=$(echo "$tools_line" | grep -q 'Glob' && echo 1 || echo 0)
has_edit=$(echo "$tools_line" | grep -q 'Edit' && echo 1 || echo 0)
has_write=$(echo "$tools_line" | grep -q 'Write' && echo 1 || echo 0)
has_bash=$(echo "$tools_line" | grep -q 'Bash' && echo 1 || echo 0)
if [ "$has_read" -eq 1 ] && [ "$has_grep" -eq 1 ] && [ "$has_glob" -eq 1 ] && [ "$has_edit" -eq 0 ] && [ "$has_write" -eq 0 ] && [ "$has_bash" -eq 0 ]; then
  ok "fbk-spec-author.md tools field matches allowlist (Read, Grep, Glob; no Edit, Write, Bash)"
else
  not_ok "fbk-spec-author.md tools field matches allowlist (Read, Grep, Glob; no Edit, Write, Bash)" "read=$has_read grep=$has_grep glob=$has_glob edit=$has_edit write=$has_write bash=$has_bash"
fi

# Test 7: fbk-spec-author.md body contains 'principal engineer' (role activation)
if body_lines "$SPEC_AUTHOR" 2>/dev/null | grep -qi 'principal engineer'; then
  ok "fbk-spec-author.md body contains 'principal engineer' (role activation)"
else
  not_ok "fbk-spec-author.md body contains 'principal engineer' (role activation)"
fi

# ============================================================================
# fbk-task-compiler.md Tests (A-F)
# ============================================================================

# Test 8A: fbk-task-compiler.md exists and is non-empty
if [ -s "$TASK_COMPILER" ]; then
  ok "fbk-task-compiler.md exists and is non-empty"
else
  not_ok "fbk-task-compiler.md exists and is non-empty" "file: $TASK_COMPILER"
fi

# Test 9B: fbk-task-compiler.md has valid YAML frontmatter
first_line=$(head -1 "$TASK_COMPILER" 2>/dev/null || true)
closing_count=$(grep -c '^---$' "$TASK_COMPILER" 2>/dev/null || true)
if [ "$first_line" = "---" ] && [ "$closing_count" -ge 2 ]; then
  ok "fbk-task-compiler.md has valid YAML frontmatter"
else
  not_ok "fbk-task-compiler.md has valid YAML frontmatter" "first_line='$first_line' closing_count=$closing_count"
fi

# Test 10C: fbk-task-compiler.md body at or below 40 lines
body_count=$(body_line_count "$TASK_COMPILER" 2>/dev/null)
body_count=${body_count:-999}
if [ "$body_count" -le 40 ]; then
  ok "fbk-task-compiler.md body at or below 40 lines"
else
  not_ok "fbk-task-compiler.md body at or below 40 lines" "body_count=$body_count"
fi

# Test 11D: fbk-task-compiler.md body contains '## Output quality bars' heading
if body_lines "$TASK_COMPILER" 2>/dev/null | grep -q '^## Output quality bars$'; then
  ok "fbk-task-compiler.md body contains '## Output quality bars' heading"
else
  not_ok "fbk-task-compiler.md body contains '## Output quality bars' heading"
fi

# Test 12E: fbk-task-compiler.md frontmatter has non-empty name and description
fm=$(frontmatter "$TASK_COMPILER" 2>/dev/null || true)
has_name=$(echo "$fm" | grep -q '^name:.*[^[:space:]]' && echo 1 || echo 0)
has_desc=$(echo "$fm" | grep -q '^description:.*[^[:space:]]' && echo 1 || echo 0)
if [ "$has_name" -eq 1 ] && [ "$has_desc" -eq 1 ]; then
  ok "fbk-task-compiler.md frontmatter has non-empty name and description"
else
  not_ok "fbk-task-compiler.md frontmatter has non-empty name and description" "has_name=$has_name has_desc=$has_desc"
fi

# Test 13F: fbk-task-compiler.md tools field matches spec allowlist (Read, Grep, Glob; no Edit, Write, Bash)
tools_line=$(echo "$fm" | grep '^tools:')
has_read=$(echo "$tools_line" | grep -q 'Read' && echo 1 || echo 0)
has_grep=$(echo "$tools_line" | grep -q 'Grep' && echo 1 || echo 0)
has_glob=$(echo "$tools_line" | grep -q 'Glob' && echo 1 || echo 0)
has_edit=$(echo "$tools_line" | grep -q 'Edit' && echo 1 || echo 0)
has_write=$(echo "$tools_line" | grep -q 'Write' && echo 1 || echo 0)
has_bash=$(echo "$tools_line" | grep -q 'Bash' && echo 1 || echo 0)
if [ "$has_read" -eq 1 ] && [ "$has_grep" -eq 1 ] && [ "$has_glob" -eq 1 ] && [ "$has_edit" -eq 0 ] && [ "$has_write" -eq 0 ] && [ "$has_bash" -eq 0 ]; then
  ok "fbk-task-compiler.md tools field matches allowlist (Read, Grep, Glob; no Edit, Write, Bash)"
else
  not_ok "fbk-task-compiler.md tools field matches allowlist (Read, Grep, Glob; no Edit, Write, Bash)" "read=$has_read grep=$has_grep glob=$has_glob edit=$has_edit write=$has_write bash=$has_bash"
fi

# Test 14: fbk-task-compiler.md body contains 'tech lead' (role activation)
if body_lines "$TASK_COMPILER" 2>/dev/null | grep -qi 'tech lead'; then
  ok "fbk-task-compiler.md body contains 'tech lead' (role activation)"
else
  not_ok "fbk-task-compiler.md body contains 'tech lead' (role activation)"
fi

# ============================================================================
# fbk-implementer.md Tests (A-F)
# ============================================================================

# Test 15A: fbk-implementer.md exists and is non-empty
if [ -s "$IMPLEMENTER" ]; then
  ok "fbk-implementer.md exists and is non-empty"
else
  not_ok "fbk-implementer.md exists and is non-empty" "file: $IMPLEMENTER"
fi

# Test 16B: fbk-implementer.md has valid YAML frontmatter
first_line=$(head -1 "$IMPLEMENTER" 2>/dev/null || true)
closing_count=$(grep -c '^---$' "$IMPLEMENTER" 2>/dev/null || true)
if [ "$first_line" = "---" ] && [ "$closing_count" -ge 2 ]; then
  ok "fbk-implementer.md has valid YAML frontmatter"
else
  not_ok "fbk-implementer.md has valid YAML frontmatter" "first_line='$first_line' closing_count=$closing_count"
fi

# Test 17C: fbk-implementer.md body at or below 40 lines
body_count=$(body_line_count "$IMPLEMENTER" 2>/dev/null)
body_count=${body_count:-999}
if [ "$body_count" -le 40 ]; then
  ok "fbk-implementer.md body at or below 40 lines"
else
  not_ok "fbk-implementer.md body at or below 40 lines" "body_count=$body_count"
fi

# Test 18D: fbk-implementer.md body contains '## Output quality bars' heading
if body_lines "$IMPLEMENTER" 2>/dev/null | grep -q '^## Output quality bars$'; then
  ok "fbk-implementer.md body contains '## Output quality bars' heading"
else
  not_ok "fbk-implementer.md body contains '## Output quality bars' heading"
fi

# Test 19E: fbk-implementer.md frontmatter has non-empty name and description
fm=$(frontmatter "$IMPLEMENTER" 2>/dev/null || true)
has_name=$(echo "$fm" | grep -q '^name:.*[^[:space:]]' && echo 1 || echo 0)
has_desc=$(echo "$fm" | grep -q '^description:.*[^[:space:]]' && echo 1 || echo 0)
if [ "$has_name" -eq 1 ] && [ "$has_desc" -eq 1 ]; then
  ok "fbk-implementer.md frontmatter has non-empty name and description"
else
  not_ok "fbk-implementer.md frontmatter has non-empty name and description" "has_name=$has_name has_desc=$has_desc"
fi

# Test 20F: fbk-implementer.md tools field matches spec allowlist (all six: Read, Grep, Glob, Edit, Write, Bash)
tools_line=$(echo "$fm" | grep '^tools:')
has_read=$(echo "$tools_line" | grep -q 'Read' && echo 1 || echo 0)
has_grep=$(echo "$tools_line" | grep -q 'Grep' && echo 1 || echo 0)
has_glob=$(echo "$tools_line" | grep -q 'Glob' && echo 1 || echo 0)
has_edit=$(echo "$tools_line" | grep -q 'Edit' && echo 1 || echo 0)
has_write=$(echo "$tools_line" | grep -q 'Write' && echo 1 || echo 0)
has_bash=$(echo "$tools_line" | grep -q 'Bash' && echo 1 || echo 0)
if [ "$has_read" -eq 1 ] && [ "$has_grep" -eq 1 ] && [ "$has_glob" -eq 1 ] && [ "$has_edit" -eq 1 ] && [ "$has_write" -eq 1 ] && [ "$has_bash" -eq 1 ]; then
  ok "fbk-implementer.md tools field matches allowlist (all six: Read, Grep, Glob, Edit, Write, Bash)"
else
  not_ok "fbk-implementer.md tools field matches allowlist (all six: Read, Grep, Glob, Edit, Write, Bash)" "read=$has_read grep=$has_grep glob=$has_glob edit=$has_edit write=$has_write bash=$has_bash"
fi

# Test 21: fbk-implementer.md body contains 'senior engineer' (role activation)
if body_lines "$IMPLEMENTER" 2>/dev/null | grep -qi 'senior engineer'; then
  ok "fbk-implementer.md body contains 'senior engineer' (role activation)"
else
  not_ok "fbk-implementer.md body contains 'senior engineer' (role activation)"
fi

# ============================================================================
# Summary
# ============================================================================
echo ""
echo "1..$TOTAL"
echo "# $PASS/$TOTAL tests passed"
if [ "$FAIL" -gt 0 ]; then
  echo "# FAIL $FAIL"
  exit 1
fi
exit 0
