#!/usr/bin/env bash
set -uo pipefail

PASS=0
FAIL=0
TOTAL=0

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
PROJECT_ROOT="$(cd "$SCRIPT_DIR/../.." && pwd)"

SKILL_FILE="$PROJECT_ROOT/assets/skills/fbk-improve/SKILL.md"

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

# --- File structure ---

# Test 1: Skill file exists at expected path
if [ -f "$SKILL_FILE" ]; then
  ok "skill file exists at expected path"
else
  not_ok "skill file exists at expected path" "file not found: $SKILL_FILE"
fi

# Test 2: Frontmatter contains description field
if grep -q '^description:' "$SKILL_FILE" 2>/dev/null; then
  ok "frontmatter contains description field"
else
  not_ok "frontmatter contains description field" "missing 'description:' in frontmatter"
fi

# Test 3: Frontmatter contains allowed-tools including required tools
if grep -q '^allowed-tools:' "$SKILL_FILE" 2>/dev/null; then
  tools_section=$(sed -n '/^allowed-tools:/,/^[a-z-]*:/p' "$SKILL_FILE" | head -20)
  if echo "$tools_section" | grep -q 'Read' && \
     echo "$tools_section" | grep -q 'Grep' && \
     echo "$tools_section" | grep -q 'Glob' && \
     echo "$tools_section" | grep -q 'Edit' && \
     echo "$tools_section" | grep -q 'Agent'; then
    ok "frontmatter allowed-tools includes Read, Grep, Glob, Edit, Agent"
  else
    not_ok "frontmatter allowed-tools includes required tools" "missing one or more required tools"
  fi
else
  not_ok "frontmatter contains allowed-tools field" "missing 'allowed-tools:' in frontmatter"
fi

# --- AC-01: Retrospective location ---

# Test 4: Body contains instruction to search ai-docs for *-retrospective.md
if grep -qiE 'ai-docs.*retrospective|retrospective.*ai-docs' "$SKILL_FILE"; then
  ok "body contains instruction to search ai-docs for retrospective files"
else
  not_ok "body contains instruction to search ai-docs for retrospective files" "missing ai-docs retrospective search language"
fi

# Test 5: Body contains instruction to report when no retrospective is found
if grep -qiE 'no retrospective|retrospective.*not found|not find.*retrospective' "$SKILL_FILE"; then
  ok "body contains instruction to report when no retrospective is found"
else
  not_ok "body contains instruction to report when no retrospective is found" "missing no-retrospective error handling"
fi

# --- AC-01, AC-02: Asset discovery ---

# Test 6: Body contains Glob-based discovery for .claude/skills/
if grep -qiE 'glob|\.claude/skills|skills/fbk-' "$SKILL_FILE"; then
  ok "body contains Glob-based discovery instruction for .claude/skills"
else
  not_ok "body contains Glob-based discovery instruction for .claude/skills" "missing Glob asset discovery language"
fi

# Test 7: Body contains instruction to search ~/.claude/skills/
if grep -qiE '~/.claude/skills|home.*skills|skills.*home' "$SKILL_FILE"; then
  ok "body contains instruction to search ~/.claude/skills/"
else
  not_ok "body contains instruction to search ~/.claude/skills/" "missing ~/.claude/skills search instruction"
fi

# Test 8: Body contains instruction to prefer project-level when both locations have results
if grep -qiE 'prefer|priorit|project.*over|precedence' "$SKILL_FILE"; then
  ok "body contains instruction to prefer project-level when both locations have results"
else
  not_ok "body contains instruction to prefer project-level" "missing project-level preference instruction"
fi

# Test 9: Body contains instruction to enumerate fbk-* prefixed files
if grep -qiE 'fbk-\*|fbk-[a-z]|enumerate.*fbk' "$SKILL_FILE"; then
  ok "body contains instruction to enumerate fbk-* prefixed files"
else
  not_ok "body contains instruction to enumerate fbk-* prefixed files" "missing fbk-* enumeration instruction"
fi

# --- AC-02: Agent isolation ---

# Test 10: Body references spawning fbk-improvement-analyst agent
if grep -qiE 'fbk-improvement-analyst|improvement.*analyst' "$SKILL_FILE"; then
  ok "body references spawning fbk-improvement-analyst agent"
else
  not_ok "body references spawning fbk-improvement-analyst agent" "missing fbk-improvement-analyst agent reference"
fi

# Test 11: Body specifies passing paths (not file contents) to the agent
if grep -qiE 'path|file.*path|location|pass.*path' "$SKILL_FILE"; then
  ok "body specifies passing paths to the agent"
else
  not_ok "body specifies passing paths to the agent" "missing path-passing instruction"
fi

# Test 12: Body specifies agent does NOT receive spec, implementation, or review content
if grep -qiE 'not.*receive|do not.*pass|no spec|no implementation|no review|exclude.*spec' "$SKILL_FILE"; then
  ok "body specifies agent does NOT receive spec, implementation, or review content"
else
  not_ok "body specifies agent does NOT receive spec, implementation, or review content" "missing agent content exclusion instruction"
fi

# --- AC-03, AC-04: Proposal format ---

# Test 13: Body contains proposal format with target, change, observation, necessity fields
proposal_check=0
if grep -qiE 'target' "$SKILL_FILE" && \
   grep -qiE 'change' "$SKILL_FILE" && \
   grep -qiE 'observation' "$SKILL_FILE" && \
   grep -qiE 'necessity' "$SKILL_FILE"; then
  proposal_check=1
fi
if [ "$proposal_check" -eq 1 ]; then
  ok "body contains proposal format with target, change, observation, necessity fields"
else
  not_ok "body contains proposal format fields" "missing one or more proposal fields (target, change, observation, necessity)"
fi

# --- AC-06: User interaction ---

# Test 14: Body contains accept/discuss/skip flow instructions
if grep -qiE 'accept|discuss|skip' "$SKILL_FILE"; then
  ok "body contains accept/discuss/skip flow instructions"
else
  not_ok "body contains accept/discuss/skip flow instructions" "missing flow instruction keywords"
fi

# Test 15: Body contains opt-out prompt (skip or proceed)
if grep -qiE 'skip|proceed|opt' "$SKILL_FILE"; then
  ok "body contains opt-out prompt (skip or proceed)"
else
  not_ok "body contains opt-out prompt" "missing skip/proceed opt-out language"
fi

# --- AC-07: Empty result ---

# Test 16: Body contains instruction for no-actionable-observations exit message
if grep -qiE 'no.*observation|no action|actionable|exit' "$SKILL_FILE"; then
  ok "body contains instruction for no-actionable-observations exit message"
else
  not_ok "body contains instruction for no-actionable-observations exit message" "missing no-observations exit instruction"
fi

# --- AC-08: Cross-cutting ---

# Test 17: Body contains instruction permitting proposals to target any Firebreak asset regardless of phase
if grep -qiE 'any.*asset|any.*phase|regardless.*phase|firebreak.*asset' "$SKILL_FILE"; then
  ok "body contains instruction permitting proposals to target any Firebreak asset regardless of phase"
else
  not_ok "body contains instruction for cross-phase asset targeting" "missing cross-phase targeting permission"
fi

# --- Summary ---
echo ""
echo "# $PASS/$TOTAL tests passed"
if [ "$FAIL" -eq 0 ]; then
  exit 0
fi
exit 1
