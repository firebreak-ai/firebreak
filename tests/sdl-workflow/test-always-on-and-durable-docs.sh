#!/usr/bin/env bash
set -uo pipefail

PASS=0
FAIL=0
TOTAL=0

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
PROJECT_ROOT="$(cd "$SCRIPT_DIR/../.." && pwd)"

CLAUDE_MD="$PROJECT_ROOT/.claude/CLAUDE.md"
AUTHORING_RULES="$PROJECT_ROOT/assets/fbk-docs/fbk-context-assets.md"
DECISIONS_LOG="$PROJECT_ROOT/docs/decisions-log.md"
ARCH_OVERVIEW="$PROJECT_ROOT/docs/architecture-overview.md"

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

# --- AC-17: Test 1-6: Five disciplines present in .claude/CLAUDE.md ---
# T1: simple language
if grep -qiF 'simple language' "$CLAUDE_MD"; then
  ok "Discipline 'simple language' present in .claude/CLAUDE.md"
else
  not_ok "Discipline 'simple language' present in .claude/CLAUDE.md" "file: $CLAUDE_MD"
fi

# T2: descriptions over identifiers
if grep -qiF 'descriptions over identifiers' "$CLAUDE_MD"; then
  ok "Discipline 'descriptions over identifiers' present in .claude/CLAUDE.md"
else
  not_ok "Discipline 'descriptions over identifiers' present in .claude/CLAUDE.md" "file: $CLAUDE_MD"
fi

# T3: capability framing
if grep -qiF 'capability framing' "$CLAUDE_MD"; then
  ok "Discipline 'capability framing' present in .claude/CLAUDE.md"
else
  not_ok "Discipline 'capability framing' present in .claude/CLAUDE.md" "file: $CLAUDE_MD"
fi

# T4: interview before drafting
if grep -qiF 'interview before drafting' "$CLAUDE_MD"; then
  ok "Discipline 'interview before drafting' present in .claude/CLAUDE.md"
else
  not_ok "Discipline 'interview before drafting' present in .claude/CLAUDE.md" "file: $CLAUDE_MD"
fi

# T5: structural-principles awareness
if grep -qiF 'structural-principles awareness' "$CLAUDE_MD"; then
  ok "Discipline 'structural-principles awareness' present in .claude/CLAUDE.md"
else
  not_ok "Discipline 'structural-principles awareness' present in .claude/CLAUDE.md" "file: $CLAUDE_MD"
fi

# T6: .claude/CLAUDE.md routes to authoring rules (fbk-context-assets or always-on)
if grep -qE 'fbk-context-assets|always-on' "$CLAUDE_MD"; then
  ok ".claude/CLAUDE.md routes to authoring rules"
else
  not_ok ".claude/CLAUDE.md routes to authoring rules" "file: $CLAUDE_MD"
fi

# --- AC-18: Test 7-11: Five disciplines present in authoring rules ---
# T7: simple language
if grep -qiF 'simple language' "$AUTHORING_RULES"; then
  ok "Discipline 'simple language' present in authoring rules"
else
  not_ok "Discipline 'simple language' present in authoring rules" "file: $AUTHORING_RULES"
fi

# T8: descriptions over identifiers
if grep -qiF 'descriptions over identifiers' "$AUTHORING_RULES"; then
  ok "Discipline 'descriptions over identifiers' present in authoring rules"
else
  not_ok "Discipline 'descriptions over identifiers' present in authoring rules" "file: $AUTHORING_RULES"
fi

# T9: capability framing
if grep -qiF 'capability framing' "$AUTHORING_RULES"; then
  ok "Discipline 'capability framing' present in authoring rules"
else
  not_ok "Discipline 'capability framing' present in authoring rules" "file: $AUTHORING_RULES"
fi

# T10: interview before drafting
if grep -qiF 'interview before drafting' "$AUTHORING_RULES"; then
  ok "Discipline 'interview before drafting' present in authoring rules"
else
  not_ok "Discipline 'interview before drafting' present in authoring rules" "file: $AUTHORING_RULES"
fi

# T11: structural-principles awareness
if grep -qiF 'structural-principles awareness' "$AUTHORING_RULES"; then
  ok "Discipline 'structural-principles awareness' present in authoring rules"
else
  not_ok "Discipline 'structural-principles awareness' present in authoring rules" "file: $AUTHORING_RULES"
fi

# --- AC-19: Test 12-15: Durable docs exist and are properly seeded ---
# T12: decisions-log.md exists
if [ -f "$DECISIONS_LOG" ]; then
  ok "docs/decisions-log.md exists"
else
  not_ok "docs/decisions-log.md exists" "file: $DECISIONS_LOG"
fi

# T13: architecture-overview.md exists
if [ -f "$ARCH_OVERVIEW" ]; then
  ok "docs/architecture-overview.md exists"
else
  not_ok "docs/architecture-overview.md exists" "file: $ARCH_OVERVIEW"
fi

# T14: architecture-overview.md is non-empty
if [ -s "$ARCH_OVERVIEW" ]; then
  ok "docs/architecture-overview.md is non-empty"
else
  not_ok "docs/architecture-overview.md is non-empty" "file: $ARCH_OVERVIEW"
fi

# T15: architecture-overview.md contains at least one governing convention phrase
if grep -qiE 'plain markdown|bounded length|in-branch' "$ARCH_OVERVIEW"; then
  ok "docs/architecture-overview.md contains governing convention phrases"
else
  not_ok "docs/architecture-overview.md contains governing convention phrases" "file: $ARCH_OVERVIEW"
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
