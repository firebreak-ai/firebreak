#!/usr/bin/env bash
set -uo pipefail

PASS=0
FAIL=0
TOTAL=0

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
PROJECT_ROOT="$(cd "$SCRIPT_DIR/../.." && pwd)"

COUNCIL_AGENTS=(
  "$PROJECT_ROOT/assets/agents/fbk-council-architect.md"
  "$PROJECT_ROOT/assets/agents/fbk-council-analyst.md"
  "$PROJECT_ROOT/assets/agents/fbk-council-builder.md"
  "$PROJECT_ROOT/assets/agents/fbk-council-guardian.md"
  "$PROJECT_ROOT/assets/agents/fbk-council-security.md"
  "$PROJECT_ROOT/assets/agents/fbk-council-advocate.md"
)

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

# Helper: extract body (everything after the second --- line)
body_lines() {
  awk '/^---$/{c++; if(c==2){found=1; next}} found' "$1"
}

# Helper: count body lines
body_line_count() {
  body_lines "$1" | wc -l | tr -d ' '
}

echo "TAP version 13"

# Test each council agent
for FILE in "${COUNCIL_AGENTS[@]}"; do
  AGENT_NAME=$(basename "$FILE" .md)

  # Test A: File exists and is non-empty
  if [ -s "$FILE" ]; then
    ok "$AGENT_NAME exists and is non-empty"
  else
    not_ok "$AGENT_NAME exists and is non-empty" "file: $FILE"
  fi

  # Test B: Has valid YAML frontmatter
  first_line=$(head -1 "$FILE" 2>/dev/null || true)
  closing_count=$(grep -c '^---$' "$FILE" 2>/dev/null || true)
  if [ "$first_line" = "---" ] && [ "$closing_count" -ge 2 ]; then
    ok "$AGENT_NAME has valid YAML frontmatter"
  else
    not_ok "$AGENT_NAME has valid YAML frontmatter" "first_line='$first_line' closing_count=$closing_count"
  fi

  # Test C: Body at or below 40 lines
  line_count=$(body_line_count "$FILE")
  if [ "$line_count" -le 40 ]; then
    ok "$AGENT_NAME body at or below 40 lines"
  else
    not_ok "$AGENT_NAME body at or below 40 lines" "line_count=$line_count"
  fi

  # Test D: Body contains '## Output quality bars' heading
  body=$(body_lines "$FILE" 2>/dev/null || true)
  if echo "$body" | grep -q '^## Output quality bars$'; then
    ok "$AGENT_NAME body contains '## Output quality bars' heading"
  else
    not_ok "$AGENT_NAME body contains '## Output quality bars' heading"
  fi

  # Test E: Body contains no forbidden description-heavy headings
  forbidden_pattern='^## Your Identity$|^## Your Expertise$|^## How You Contribute$|^## Your Communication Style$|^## In Council Discussions$|^## Critical Behaviors$'
  if ! echo "$body" | grep -qE "$forbidden_pattern"; then
    ok "$AGENT_NAME body contains no forbidden description-heavy headings"
  else
    not_ok "$AGENT_NAME body contains no forbidden description-heavy headings" "found forbidden heading"
  fi
done

# Summary
echo ""
echo "1..$TOTAL"
echo "# tests $TOTAL"
echo "# pass  $PASS"
echo "# fail  $FAIL"
[ "$FAIL" -eq 0 ] || exit 1
