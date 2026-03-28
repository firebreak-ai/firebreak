#!/usr/bin/env bash
set -uo pipefail

PASS=0
FAIL=0
TOTAL=0

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
PROJECT_ROOT="$(cd "$SCRIPT_DIR/../.." && pwd)"

AGENT_FILE="$PROJECT_ROOT/assets/agents/fbk-improvement-analyst.md"

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

# Test 1: Agent file exists at expected path
if [ -f "$AGENT_FILE" ]; then
  ok "agent file exists at expected path"
else
  not_ok "agent file exists at expected path" "file not found: $AGENT_FILE"
fi

# Test 2: Frontmatter contains name field (improvement-analyst or fbk-improvement-analyst)
if grep -qE '^name:\s+(improvement-analyst|fbk-improvement-analyst)' "$AGENT_FILE"; then
  ok "frontmatter contains name: improvement-analyst or fbk-improvement-analyst"
else
  not_ok "frontmatter contains name: improvement-analyst or fbk-improvement-analyst" "name field missing or incorrect"
fi

# Test 3: Frontmatter contains description field
if grep -q '^description:' "$AGENT_FILE"; then
  ok "frontmatter contains description field"
else
  not_ok "frontmatter contains description field" "description field missing"
fi

# Test 4: Frontmatter contains tools field with only read-only tools (Read, Grep, Glob)
if grep -q '^tools:' "$AGENT_FILE"; then
  # Check that only read-only tools are listed
  if grep -E '^tools:' -A 20 "$AGENT_FILE" | grep -qE 'Read|Grep|Glob' && \
     ! grep -E '^tools:' -A 20 "$AGENT_FILE" | grep -qE 'Write|Edit|Bash|SendMessage|Skill|Bash'; then
    ok "tools field lists only read-only tools (Read, Grep, Glob)"
  else
    not_ok "tools field lists only read-only tools" "contains restricted tools (Write, Edit, Bash, etc)"
  fi
else
  not_ok "tools field lists only read-only tools" "tools field missing"
fi

# Test 5: Body contains instruction referencing authoring rules (fbk-context-assets)
if grep -qi 'fbk-context-assets' "$AGENT_FILE"; then
  ok "body contains instruction referencing authoring rules (fbk-context-assets)"
else
  not_ok "body contains instruction referencing authoring rules" "missing fbk-context-assets reference"
fi

# Test 6: Body contains instruction about sub-agent spawning for per-asset analysis
if grep -qiE 'sub-agent|sub agent|spawn.*agent|per-asset|per asset' "$AGENT_FILE"; then
  ok "body contains instruction about sub-agent spawning for per-asset analysis"
else
  not_ok "body contains instruction about sub-agent spawning for per-asset analysis" "missing sub-agent/spawning language"
fi

# Test 7: Body contains scope discipline section restricting to read-only analysis and proposal output
if grep -qiE 'scope|read-only|read only|proposal output' "$AGENT_FILE"; then
  ok "body contains scope discipline restricting to read-only analysis and proposal output"
else
  not_ok "body contains scope discipline restricting to read-only analysis and proposal output" "missing scope/read-only/proposal output language"
fi

# Test 8: Body contains proposal output format specification (target, change type, diff, observation, necessity)
if grep -qiE 'proposal|target|change type|diff|observation|necessity' "$AGENT_FILE"; then
  ok "body contains proposal output format specification"
else
  not_ok "body contains proposal output format specification" "missing proposal format fields"
fi

# Test 9: Body contains instruction prohibiting speculative improvements disconnected from observations
if grep -qiE 'speculative|disconnect|observation|anchor|grounded' "$AGENT_FILE"; then
  ok "body prohibits speculative improvements disconnected from retrospective observations"
else
  not_ok "body prohibits speculative improvements disconnected from observations" "missing prohibition on speculative improvements"
fi

# Test 10: Body contains instruction about cross-cutting proposals
if grep -qiE 'cross-cutting|cross cutting|any.*asset|phase' "$AGENT_FILE"; then
  ok "body contains instruction about cross-cutting proposals"
else
  not_ok "body contains instruction about cross-cutting proposals" "missing cross-cutting proposal language"
fi

# Test 11: Body does NOT contain references to receiving spec, implementation, or review conversation content
if grep -qiE 'spec content|implementation content|review content|receive.*spec|receive.*implementation|receive.*review' "$AGENT_FILE"; then
  not_ok "body does not contain references to spec/impl/review content" "contains prohibited references to conversation content"
else
  ok "body does not contain references to spec/impl/review content"
fi

# --- Summary ---
echo ""
echo "# $PASS/$TOTAL tests passed"
if [ "$FAIL" -eq 0 ]; then
  exit 0
fi
exit 1
