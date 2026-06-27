#!/usr/bin/env bash
set -uo pipefail

PASS=0
FAIL=0
TOTAL=0

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
PROJECT_ROOT="$(cd "$SCRIPT_DIR/../.." && pwd)"

SKILL="$PROJECT_ROOT/assets/skills/fbk-council/SKILL.md"
LEAF_DIR="$PROJECT_ROOT/assets/fbk-docs/fbk-council"
CONSENSUS="$LEAF_DIR/consensus-failure.md"
RECOVERY="$LEAF_DIR/compaction-recovery.md"
RALPH="$LEAF_DIR/ralph-integration.md"

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

# ── SKILL existence and frontmatter (AC-01) ──────────────────────────────────

# 1: SKILL exists and is non-empty
if [ -s "$SKILL" ]; then
  ok "SKILL.md exists and is non-empty"
else
  not_ok "SKILL.md exists and is non-empty"
fi

# 2: SKILL frontmatter contains name: fbk-council
if grep -F 'name: fbk-council' "$SKILL" >/dev/null 2>&1; then
  ok "SKILL frontmatter contains name: fbk-council"
else
  not_ok "SKILL frontmatter contains name: fbk-council"
fi

# 3: SKILL description contains 'selected per task'
if grep -F 'selected per task' "$SKILL" >/dev/null 2>&1; then
  ok "SKILL description contains 'selected per task'"
else
  not_ok "SKILL description contains 'selected per task'"
fi

# 4: SKILL description contains agent-role list
if grep -F 'architect, builder, guardian, security, advocate, analyst' "$SKILL" >/dev/null 2>&1; then
  ok "SKILL description contains agent-role list"
else
  not_ok "SKILL description contains agent-role list"
fi

# 5: SKILL does NOT contain 'team of 6' (literal removed)
if ! grep -F 'team of 6' "$SKILL" >/dev/null 2>&1; then
  ok "SKILL does not contain banned phrase 'team of 6'"
else
  not_ok "SKILL does not contain banned phrase 'team of 6'"
fi

# ── Trigger phrases verbatim (AC-11) ─────────────────────────────────────────

# 6: SKILL contains /fbk-council
if grep -F '/fbk-council' "$SKILL" >/dev/null 2>&1; then
  ok "SKILL contains trigger /fbk-council"
else
  not_ok "SKILL contains trigger /fbk-council"
fi

# 7: SKILL contains /fbk-council quick
if grep -F '/fbk-council quick' "$SKILL" >/dev/null 2>&1; then
  ok "SKILL contains trigger /fbk-council quick"
else
  not_ok "SKILL contains trigger /fbk-council quick"
fi

# 8: SKILL contains /fbk-qcouncil
if grep -F '/fbk-qcouncil' "$SKILL" >/dev/null 2>&1; then
  ok "SKILL contains trigger /fbk-qcouncil"
else
  not_ok "SKILL contains trigger /fbk-qcouncil"
fi

# 9: SKILL contains /fbk-council --no-log
if grep -F '/fbk-council --no-log' "$SKILL" >/dev/null 2>&1; then
  ok "SKILL contains trigger /fbk-council --no-log"
else
  not_ok "SKILL contains trigger /fbk-council --no-log"
fi

# 10: SKILL contains /fbk-council quick --no-log
if grep -F '/fbk-council quick --no-log' "$SKILL" >/dev/null 2>&1; then
  ok "SKILL contains trigger /fbk-council quick --no-log"
else
  not_ok "SKILL contains trigger /fbk-council quick --no-log"
fi

# 11: SKILL contains /fbk-assemble
if grep -F '/fbk-assemble' "$SKILL" >/dev/null 2>&1; then
  ok "SKILL contains trigger /fbk-assemble"
else
  not_ok "SKILL contains trigger /fbk-assemble"
fi

# 12: SKILL contains 'assemble the team'
if grep -F 'assemble the team' "$SKILL" >/dev/null 2>&1; then
  ok "SKILL contains trigger phrase 'assemble the team'"
else
  not_ok "SKILL contains trigger phrase 'assemble the team'"
fi

# 13: SKILL contains 'convene the council'
if grep -F 'convene the council' "$SKILL" >/dev/null 2>&1; then
  ok "SKILL contains trigger phrase 'convene the council'"
else
  not_ok "SKILL contains trigger phrase 'convene the council'"
fi

# 14: SKILL contains 'quick council'
if grep -F 'quick council' "$SKILL" >/dev/null 2>&1; then
  ok "SKILL contains trigger phrase 'quick council'"
else
  not_ok "SKILL contains trigger phrase 'quick council'"
fi

# ── Default-dispatcher references (AC-01 part (h)) ───────────────────────────

# 15: SKILL contains literal 'session-manager'
if grep -F 'session-manager' "$SKILL" >/dev/null 2>&1; then
  ok "SKILL contains dispatcher ref: session-manager"
else
  not_ok "SKILL contains dispatcher ref: session-manager"
fi

# 16: SKILL contains literal 'session-logger'
if grep -F 'session-logger' "$SKILL" >/dev/null 2>&1; then
  ok "SKILL contains dispatcher ref: session-logger"
else
  not_ok "SKILL contains dispatcher ref: session-logger"
fi

# 17: SKILL contains literal '--no-log' (FIND-013 anti-typo guard; AC-01 part (i))
if grep -F -- '--no-log' "$SKILL" >/dev/null 2>&1; then
  ok "SKILL contains '--no-log' flag literal"
else
  not_ok "SKILL contains '--no-log' flag literal"
fi

# 18: SKILL contains 'session-state checkpoint' (AC-01 part (j); FIND-002)
if grep -F 'session-state checkpoint' "$SKILL" >/dev/null 2>&1; then
  ok "SKILL contains 'session-state checkpoint' per-phase trigger"
else
  not_ok "SKILL contains 'session-state checkpoint' per-phase trigger"
fi

# ── Required section headers (AC-01 parts (c)–(g)) ───────────────────────────

# 19: SKILL contains header 'Council Members'
if grep -F 'Council Members' "$SKILL" >/dev/null 2>&1; then
  ok "SKILL contains header 'Council Members'"
else
  not_ok "SKILL contains header 'Council Members'"
fi

# 20: SKILL contains header 'Phase 5: Consensus Output'
if grep -F 'Phase 5: Consensus Output' "$SKILL" >/dev/null 2>&1; then
  ok "SKILL contains header 'Phase 5: Consensus Output'"
else
  not_ok "SKILL contains header 'Phase 5: Consensus Output'"
fi

# 21: SKILL contains header 'Phase 5.5'
if grep -F 'Phase 5.5' "$SKILL" >/dev/null 2>&1; then
  ok "SKILL contains header 'Phase 5.5'"
else
  not_ok "SKILL contains header 'Phase 5.5'"
fi

# 22: SKILL contains header 'Immutable Core'
if grep -F 'Immutable Core' "$SKILL" >/dev/null 2>&1; then
  ok "SKILL contains header 'Immutable Core'"
else
  not_ok "SKILL contains header 'Immutable Core'"
fi

# 23: SKILL contains header 'Trigger Phrases'
if grep -F 'Trigger Phrases' "$SKILL" >/dev/null 2>&1; then
  ok "SKILL contains header 'Trigger Phrases'"
else
  not_ok "SKILL contains header 'Trigger Phrases'"
fi

# ── Banned headers absent (AC-02) ────────────────────────────────────────────

# 24: SKILL does NOT contain header 'Quick Council'
if ! grep -F 'Quick Council' "$SKILL" >/dev/null 2>&1; then
  ok "SKILL does not contain banned header 'Quick Council'"
else
  not_ok "SKILL does not contain banned header 'Quick Council'"
fi

# 25: SKILL does NOT contain header 'Full Council'
if ! grep -F 'Full Council' "$SKILL" >/dev/null 2>&1; then
  ok "SKILL does not contain banned header 'Full Council'"
else
  not_ok "SKILL does not contain banned header 'Full Council'"
fi

# 26: SKILL does NOT contain header 'Tier Selection Heuristics'
if ! grep -F 'Tier Selection Heuristics' "$SKILL" >/dev/null 2>&1; then
  ok "SKILL does not contain banned header 'Tier Selection Heuristics'"
else
  not_ok "SKILL does not contain banned header 'Tier Selection Heuristics'"
fi

# 27: SKILL does NOT contain header 'Auto-escalation'
if ! grep -F 'Auto-escalation' "$SKILL" >/dev/null 2>&1; then
  ok "SKILL does not contain banned header 'Auto-escalation'"
else
  not_ok "SKILL does not contain banned header 'Auto-escalation'"
fi

# ── Dispatch references to each conditional leaf (AC-09 reachability) ─────────

# 28: SKILL contains dispatch path for consensus-failure.md
if grep -F '.claude/fbk-docs/fbk-council/consensus-failure.md' "$SKILL" >/dev/null 2>&1; then
  ok "SKILL contains dispatch path for consensus-failure.md"
else
  not_ok "SKILL contains dispatch path for consensus-failure.md"
fi

# 29: SKILL contains dispatch path for compaction-recovery.md
if grep -F '.claude/fbk-docs/fbk-council/compaction-recovery.md' "$SKILL" >/dev/null 2>&1; then
  ok "SKILL contains dispatch path for compaction-recovery.md"
else
  not_ok "SKILL contains dispatch path for compaction-recovery.md"
fi

# 30: SKILL contains dispatch path for ralph-integration.md
if grep -F '.claude/fbk-docs/fbk-council/ralph-integration.md' "$SKILL" >/dev/null 2>&1; then
  ok "SKILL contains dispatch path for ralph-integration.md"
else
  not_ok "SKILL contains dispatch path for ralph-integration.md"
fi

# ── Leaf files exist at expected paths (AC-09 link resolution) ────────────────

# 31: consensus-failure.md exists and is non-empty
if [ -s "$CONSENSUS" ]; then
  ok "consensus-failure.md exists and is non-empty"
else
  not_ok "consensus-failure.md exists and is non-empty"
fi

# 32: compaction-recovery.md exists and is non-empty
if [ -s "$RECOVERY" ]; then
  ok "compaction-recovery.md exists and is non-empty"
else
  not_ok "compaction-recovery.md exists and is non-empty"
fi

# 33: ralph-integration.md exists and is non-empty
if [ -s "$RALPH" ]; then
  ok "ralph-integration.md exists and is non-empty"
else
  not_ok "ralph-integration.md exists and is non-empty"
fi

# ── consensus-failure.md content (AC-04) ──────────────────────────────────────

# 34: contains 'Weighted Voting'
if grep -F 'Weighted Voting' "$CONSENSUS" >/dev/null 2>&1; then
  ok "consensus-failure.md contains 'Weighted Voting'"
else
  not_ok "consensus-failure.md contains 'Weighted Voting'"
fi

# 35: contains 'Evidence-Based Consensus'
if grep -F 'Evidence-Based Consensus' "$CONSENSUS" >/dev/null 2>&1; then
  ok "consensus-failure.md contains 'Evidence-Based Consensus'"
else
  not_ok "consensus-failure.md contains 'Evidence-Based Consensus'"
fi

# 36: contains 'Reasoning'
if grep -F 'Reasoning' "$CONSENSUS" >/dev/null 2>&1; then
  ok "consensus-failure.md contains 'Reasoning'"
else
  not_ok "consensus-failure.md contains 'Reasoning'"
fi

# 37: contains 'Knowledge'
if grep -F 'Knowledge' "$CONSENSUS" >/dev/null 2>&1; then
  ok "consensus-failure.md contains 'Knowledge'"
else
  not_ok "consensus-failure.md contains 'Knowledge'"
fi

# 38: contains 'Technical Disagreement'
if grep -F 'Technical Disagreement' "$CONSENSUS" >/dev/null 2>&1; then
  ok "consensus-failure.md contains 'Technical Disagreement'"
else
  not_ok "consensus-failure.md contains 'Technical Disagreement'"
fi

# 39: contains 'Security vs Usability'
if grep -F 'Security vs Usability' "$CONSENSUS" >/dev/null 2>&1; then
  ok "consensus-failure.md contains 'Security vs Usability'"
else
  not_ok "consensus-failure.md contains 'Security vs Usability'"
fi

# 40: contains 'Quality vs Speed'
if grep -F 'Quality vs Speed' "$CONSENSUS" >/dev/null 2>&1; then
  ok "consensus-failure.md contains 'Quality vs Speed'"
else
  not_ok "consensus-failure.md contains 'Quality vs Speed'"
fi

# 41: contains 'Feature Scope'
if grep -F 'Feature Scope' "$CONSENSUS" >/dev/null 2>&1; then
  ok "consensus-failure.md contains 'Feature Scope'"
else
  not_ok "consensus-failure.md contains 'Feature Scope'"
fi

# 42: contains 'Deadlock'
if grep -F 'Deadlock' "$CONSENSUS" >/dev/null 2>&1; then
  ok "consensus-failure.md contains 'Deadlock'"
else
  not_ok "consensus-failure.md contains 'Deadlock'"
fi

# ── compaction-recovery.md content (AC-06 partial — see 69-71 for remainder) ──

# 43: contains 'Recovery Protocol'
if grep -F 'Recovery Protocol' "$RECOVERY" >/dev/null 2>&1; then
  ok "compaction-recovery.md contains 'Recovery Protocol'"
else
  not_ok "compaction-recovery.md contains 'Recovery Protocol'"
fi

# ── Session State Footer in SKILL (AC-01(l) — moved inline per F-02 fix) ──────
# Footer templates moved from compaction-recovery.md to SKILL.md so non-recovering
# sessions have access to the mandatory-every-session footer template.

# 44: SKILL contains 'Session State Footer' section
if grep -F 'Session State Footer' "$SKILL" >/dev/null 2>&1; then
  ok "SKILL contains 'Session State Footer' section"
else
  not_ok "SKILL contains 'Session State Footer' section"
fi

# 45: SKILL contains 'COUNCIL_STATUS: CONTINUE' template
if grep -F 'COUNCIL_STATUS: CONTINUE' "$SKILL" >/dev/null 2>&1; then
  ok "SKILL contains 'COUNCIL_STATUS: CONTINUE' template"
else
  not_ok "SKILL contains 'COUNCIL_STATUS: CONTINUE' template"
fi

# 46: SKILL contains 'COUNCIL_STATUS: COUNCIL_COMPLETE' template
if grep -F 'COUNCIL_STATUS: COUNCIL_COMPLETE' "$SKILL" >/dev/null 2>&1; then
  ok "SKILL contains 'COUNCIL_STATUS: COUNCIL_COMPLETE' template"
else
  not_ok "SKILL contains 'COUNCIL_STATUS: COUNCIL_COMPLETE' template"
fi

# ── ralph-integration.md content (AC-07) ──────────────────────────────────────

# 47: contains 'What is Ralph Wiggum'
if grep -F 'What is Ralph Wiggum' "$RALPH" >/dev/null 2>&1; then
  ok "ralph-integration.md contains 'What is Ralph Wiggum'"
else
  not_ok "ralph-integration.md contains 'What is Ralph Wiggum'"
fi

# 48: contains 'Guardrails'
if grep -F 'Guardrails' "$RALPH" >/dev/null 2>&1; then
  ok "ralph-integration.md contains 'Guardrails'"
else
  not_ok "ralph-integration.md contains 'Guardrails'"
fi

# 49: contains 'Escape Hatches'
if grep -F 'Escape Hatches' "$RALPH" >/dev/null 2>&1; then
  ok "ralph-integration.md contains 'Escape Hatches'"
else
  not_ok "ralph-integration.md contains 'Escape Hatches'"
fi

# 50: contains 'When to Use Ralph'
if grep -F 'When to Use Ralph' "$RALPH" >/dev/null 2>&1; then
  ok "ralph-integration.md contains 'When to Use Ralph'"
else
  not_ok "ralph-integration.md contains 'When to Use Ralph'"
fi

# ── Sizing-instruction soft-default phrases (AC-03 + AC-13) ──────────────────

# 51: SKILL contains 'Architect + Builder + Guardian'
if grep -F 'Architect + Builder + Guardian' "$SKILL" >/dev/null 2>&1; then
  ok "SKILL contains soft-default composition 'Architect + Builder + Guardian'"
else
  not_ok "SKILL contains soft-default composition 'Architect + Builder + Guardian'"
fi

# 52: SKILL contains 'substitute Security'
if grep -F 'substitute Security' "$SKILL" >/dev/null 2>&1; then
  ok "SKILL contains substitute instruction 'substitute Security'"
else
  not_ok "SKILL contains substitute instruction 'substitute Security'"
fi

# 53: SKILL contains 'substitute Advocate'
if grep -F 'substitute Advocate' "$SKILL" >/dev/null 2>&1; then
  ok "SKILL contains substitute instruction 'substitute Advocate'"
else
  not_ok "SKILL contains substitute instruction 'substitute Advocate'"
fi

# 54: SKILL contains 'substitute Analyst'
if grep -F 'substitute Analyst' "$SKILL" >/dev/null 2>&1; then
  ok "SKILL contains substitute instruction 'substitute Analyst'"
else
  not_ok "SKILL contains substitute instruction 'substitute Analyst'"
fi

# 55: SKILL contains 'skipping the Phase 1 alignment round'
if grep -F 'skipping the Phase 1 alignment round' "$SKILL" >/dev/null 2>&1; then
  ok "SKILL contains 'skipping the Phase 1 alignment round'"
else
  not_ok "SKILL contains 'skipping the Phase 1 alignment round'"
fi

# ── Modified existing tests + deleted reference test (AC-10) ──────────────────

# 56: test-old-locations-empty.sh references assets/fbk-docs/fbk-council
if grep -F 'assets/fbk-docs/fbk-council' "$PROJECT_ROOT/tests/sdl-workflow/test-old-locations-empty.sh" >/dev/null 2>&1; then
  ok "test-old-locations-empty.sh references assets/fbk-docs/fbk-council"
else
  not_ok "test-old-locations-empty.sh references assets/fbk-docs/fbk-council"
fi

# 57: test-no-old-path-patterns.sh contains consensus-failure.md path
if grep -F 'fbk-council/consensus-failure.md' "$PROJECT_ROOT/tests/sdl-workflow/test-no-old-path-patterns.sh" >/dev/null 2>&1; then
  ok "test-no-old-path-patterns.sh contains consensus-failure.md path"
else
  not_ok "test-no-old-path-patterns.sh contains consensus-failure.md path"
fi

# 58: test-no-old-path-patterns.sh contains compaction-recovery.md path
if grep -F 'fbk-council/compaction-recovery.md' "$PROJECT_ROOT/tests/sdl-workflow/test-no-old-path-patterns.sh" >/dev/null 2>&1; then
  ok "test-no-old-path-patterns.sh contains compaction-recovery.md path"
else
  not_ok "test-no-old-path-patterns.sh contains compaction-recovery.md path"
fi

# 59: test-no-old-path-patterns.sh contains ralph-integration.md path
if grep -F 'fbk-council/ralph-integration.md' "$PROJECT_ROOT/tests/sdl-workflow/test-no-old-path-patterns.sh" >/dev/null 2>&1; then
  ok "test-no-old-path-patterns.sh contains ralph-integration.md path"
else
  not_ok "test-no-old-path-patterns.sh contains ralph-integration.md path"
fi

# 60: test-council-skill-references.sh does NOT exist (deleted by task-03)
if ! [ -e "$PROJECT_ROOT/tests/sdl-workflow/test-council-skill-references.sh" ]; then
  ok "test-council-skill-references.sh does not exist (deleted)"
else
  not_ok "test-council-skill-references.sh does not exist (deleted)"
fi

# ── Downstream caller integrity (AC-12) ──────────────────────────────────────

# 61: fbk-spec-review SKILL.md still references /fbk-council
if grep -F '/fbk-council' "$PROJECT_ROOT/assets/skills/fbk-spec-review/SKILL.md" >/dev/null 2>&1; then
  ok "fbk-spec-review SKILL.md references /fbk-council"
else
  not_ok "fbk-spec-review SKILL.md references /fbk-council"
fi

# 62: review-perspectives.md references /fbk-council
if grep -F '/fbk-council' "$PROJECT_ROOT/assets/fbk-docs/fbk-sdl-workflow/review-perspectives.md" >/dev/null 2>&1; then
  ok "review-perspectives.md references /fbk-council"
else
  not_ok "review-perspectives.md references /fbk-council"
fi

# Note: README.md and CHANGELOG.md are human-facing narrative that nothing in the
# pipeline reads at runtime, so their prose is not asserted here. Wiring contracts
# in executable assets (skills/agents/docs the pipeline consumes) are tested above.

# ── Ralph stale-state guard (AC-07 reinforcement; closes CP2 Finding 1) ───────

# 67: SKILL contains 'does NOT activate Ralph mode' (§4.2 item 16 stale-state exclusion)
if grep -F 'does NOT activate Ralph mode' "$SKILL" >/dev/null 2>&1; then
  ok "SKILL contains Ralph stale-state exclusion guard 'does NOT activate Ralph mode'"
else
  not_ok "SKILL contains Ralph stale-state exclusion guard 'does NOT activate Ralph mode'"
fi

# ── Tier argument value (AC-01 reinforcement; closes CP2 Finding 3) ───────────

# 68: SKILL contains '--tier full' (literal tier argument per §4.2 item 17 and §4.7)
if grep -F -- '--tier full' "$SKILL" >/dev/null 2>&1; then
  ok "SKILL contains '--tier full' literal tier argument"
else
  not_ok "SKILL contains '--tier full' literal tier argument"
fi

# ── compaction-recovery.md remaining AC-06 items (post-F-04 remediation) ──────
# AC-06 was amended during code-review remediation to drop "Phase-Level Checkpointing
# command reference" (the WRITE side lives inline in SKILL §4.2 item 5a per the
# WRITE/READ split designed in Stage 2). Remaining 4 AC-06 items: recovery protocol
# steps, recovery acknowledgment phrase, State Persistence schema, Session Cleanup.
# Assertion 43 covers Recovery Protocol header. Assertions below cover the rest.

# 69: compaction-recovery.md contains recovery acknowledgment phrase
if grep -F 'Resumed from checkpoint after context compaction' "$RECOVERY" >/dev/null 2>&1; then
  ok "compaction-recovery.md contains recovery acknowledgment phrase"
else
  not_ok "compaction-recovery.md contains recovery acknowledgment phrase"
fi

# 70: compaction-recovery.md references State Persistence (council-state.json schema)
if grep -F 'council-state.json' "$RECOVERY" >/dev/null 2>&1; then
  ok "compaction-recovery.md references State Persistence (council-state.json schema)"
else
  not_ok "compaction-recovery.md references State Persistence (council-state.json schema)"
fi

# 71: compaction-recovery.md contains Session Cleanup commands
if grep -F 'session-manager unregister' "$RECOVERY" >/dev/null 2>&1; then
  ok "compaction-recovery.md contains Session Cleanup (session-manager unregister)"
else
  not_ok "compaction-recovery.md contains Session Cleanup (session-manager unregister)"
fi

# ── Summary ───────────────────────────────────────────────────────────────────

echo "1..$TOTAL"

if [ "$FAIL" -gt 0 ]; then
  exit 1
fi
exit 0
