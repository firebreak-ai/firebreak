#!/usr/bin/env bash
set -uo pipefail

PASS=0
FAIL=0
TOTAL=0

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
PROJECT_ROOT="$(cd "$SCRIPT_DIR/../.." && pwd)"

SPEC_SKILL="$PROJECT_ROOT/assets/skills/fbk-spec/SKILL.md"
REVIEW_SKILL="$PROJECT_ROOT/assets/skills/fbk-spec-review/SKILL.md"
IMPL_SKILL="$PROJECT_ROOT/assets/skills/fbk-implement/SKILL.md"
SPEC_GUIDE="$PROJECT_ROOT/assets/fbk-docs/fbk-sdl-workflow/feature-spec-guide.md"
REVIEW_GUIDE="$PROJECT_ROOT/assets/fbk-docs/fbk-sdl-workflow/review-perspectives.md"
IMPL_GUIDE="$PROJECT_ROOT/assets/fbk-docs/fbk-sdl-workflow/implementation-guide.md"

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

# --- T1 (AC-01) — fbk-spec/SKILL.md does not contain duplicated gate-fail prose ---
if ! grep -qF 'If the gate fails:' "$SPEC_SKILL"; then
  ok "T1 (AC-01) — fbk-spec/SKILL.md does not contain 'If the gate fails:'"
else
  not_ok "T1 (AC-01) — fbk-spec/SKILL.md does not contain 'If the gate fails:'" "file: $SPEC_SKILL"
fi

# --- T1b (AC-01) — fbk-spec/SKILL.md does not contain duplicated gate-pass narrative ---
if ! grep -qF 'Verify that the testing strategy enumerates all callers' "$SPEC_SKILL"; then
  ok "T1b (AC-01) — fbk-spec/SKILL.md does not contain 'Verify that the testing strategy enumerates all callers'"
else
  not_ok "T1b (AC-01) — fbk-spec/SKILL.md does not contain 'Verify that the testing strategy enumerates all callers'" "file: $SPEC_SKILL"
fi

# --- T2 (AC-01) — fbk-spec/SKILL.md does not contain duplicated authoring-loop prose ---
if ! grep -qF 'Refuse to write code' "$SPEC_SKILL"; then
  ok "T2 (AC-01) — fbk-spec/SKILL.md does not contain 'Refuse to write code'"
else
  not_ok "T2 (AC-01) — fbk-spec/SKILL.md does not contain 'Refuse to write code'" "file: $SPEC_SKILL"
fi

# --- T3 (AC-02) — fbk-spec-review/SKILL.md does not contain duplicated threat-model decision flow ---
if ! grep -qF 'Does this feature need a threat model?' "$REVIEW_SKILL"; then
  ok "T3 (AC-02) — fbk-spec-review/SKILL.md does not contain 'Does this feature need a threat model?'"
else
  not_ok "T3 (AC-02) — fbk-spec-review/SKILL.md does not contain 'Does this feature need a threat model?'" "file: $REVIEW_SKILL"
fi

# --- T4 (AC-02) — fbk-spec-review/SKILL.md does not contain duplicated transition decision tree ---
if ! grep -qF 'There are N blocking findings' "$REVIEW_SKILL"; then
  ok "T4 (AC-02) — fbk-spec-review/SKILL.md does not contain 'There are N blocking findings'"
else
  not_ok "T4 (AC-02) — fbk-spec-review/SKILL.md does not contain 'There are N blocking findings'" "file: $REVIEW_SKILL"
fi

# --- T4b (AC-02) — fbk-spec-review/SKILL.md does not contain duplicated classification rationale-presentation prose ---
if ! grep -qF 'Present the selection with' "$REVIEW_SKILL"; then
  ok "T4b (AC-02) — fbk-spec-review/SKILL.md does not contain 'Present the selection with'"
else
  not_ok "T4b (AC-02) — fbk-spec-review/SKILL.md does not contain 'Present the selection with'" "file: $REVIEW_SKILL"
fi

# --- T5 (AC-03) — fbk-implement/SKILL.md does not contain duplicated wave-loop step headings (both must be absent) ---
if ! grep -qF 'Step 1 — Test tasks' "$IMPL_SKILL" && ! grep -qF 'Step 2 — Test compilation check' "$IMPL_SKILL"; then
  ok "T5 (AC-03) — fbk-implement/SKILL.md does not contain 'Step 1 — Test tasks' nor 'Step 2 — Test compilation check'"
else
  not_ok "T5 (AC-03) — fbk-implement/SKILL.md does not contain 'Step 1 — Test tasks' nor 'Step 2 — Test compilation check'" "file: $IMPL_SKILL"
fi

# --- T5b (AC-03) — fbk-implement/SKILL.md does not contain duplicated step-2 narrative ---
if ! grep -qF 'Tests are expected to fail' "$IMPL_SKILL"; then
  ok "T5b (AC-03) — fbk-implement/SKILL.md does not contain 'Tests are expected to fail'"
else
  not_ok "T5b (AC-03) — fbk-implement/SKILL.md does not contain 'Tests are expected to fail'" "file: $IMPL_SKILL"
fi

# --- T6 (AC-03) — fbk-implement/SKILL.md does not contain duplicated escalation cap ---
if ! grep -qF 'Cap: 2 escalation attempts per task' "$IMPL_SKILL"; then
  ok "T6 (AC-03) — fbk-implement/SKILL.md does not contain 'Cap: 2 escalation attempts per task'"
else
  not_ok "T6 (AC-03) — fbk-implement/SKILL.md does not contain 'Cap: 2 escalation attempts per task'" "file: $IMPL_SKILL"
fi

# --- T7 (AC-04) — fbk-implement/SKILL.md contains operational env-flag check ---
if grep -qF 'CLAUDE_CODE_EXPERIMENTAL_AGENT_TEAMS' "$IMPL_SKILL"; then
  ok "T7 (AC-04) — fbk-implement/SKILL.md contains 'CLAUDE_CODE_EXPERIMENTAL_AGENT_TEAMS'"
else
  not_ok "T7 (AC-04) — fbk-implement/SKILL.md contains 'CLAUDE_CODE_EXPERIMENTAL_AGENT_TEAMS'" "file: $IMPL_SKILL"
fi

# --- T8 (AC-04) — fbk-implement/SKILL.md contains operational spawn-prompt template marker ---
if grep -qF 'Task file:' "$IMPL_SKILL"; then
  ok "T8 (AC-04) — fbk-implement/SKILL.md contains 'Task file:'"
else
  not_ok "T8 (AC-04) — fbk-implement/SKILL.md contains 'Task file:'" "file: $IMPL_SKILL"
fi

# --- T9 (AC-04) — fbk-spec-review/SKILL.md contains three operational sentinels ---
if grep -qF '/fbk-council' "$REVIEW_SKILL" && grep -qF 'test-reviewer' "$REVIEW_SKILL" && grep -qF 'testing strategy' "$REVIEW_SKILL"; then
  ok "T9 (AC-04) — fbk-spec-review/SKILL.md contains '/fbk-council', 'test-reviewer', and 'testing strategy'"
else
  not_ok "T9 (AC-04) — fbk-spec-review/SKILL.md contains '/fbk-council', 'test-reviewer', and 'testing strategy'" "file: $REVIEW_SKILL"
fi

# --- T9b (AC-04) — fbk-implement/SKILL.md contains operational exit-prompt sentinel ---
if grep -qF 'review the implementation with /fbk-code-review' "$IMPL_SKILL"; then
  ok "T9b (AC-04) — fbk-implement/SKILL.md contains 'review the implementation with /fbk-code-review'"
else
  not_ok "T9b (AC-04) — fbk-implement/SKILL.md contains 'review the implementation with /fbk-code-review'" "file: $IMPL_SKILL"
fi

# --- T10 (AC-04) — each skill contains its respective gate-script command substring ---
if grep -qF 'spec-gate' "$SPEC_SKILL" && grep -qF 'review-gate' "$REVIEW_SKILL" && grep -qF 'breakdown-gate' "$IMPL_SKILL"; then
  ok "T10 (AC-04) — fbk-spec contains 'spec-gate', fbk-spec-review contains 'review-gate', fbk-implement contains 'breakdown-gate'"
else
  not_ok "T10 (AC-04) — fbk-spec contains 'spec-gate', fbk-spec-review contains 'review-gate', fbk-implement contains 'breakdown-gate'" "files: $SPEC_SKILL, $REVIEW_SKILL, $IMPL_SKILL"
fi

# --- T11a (AC-01) — feature-spec-guide.md contains four guide-side sentinels (incl. user-question) ---
if grep -qF 'If the gate fails:' "$SPEC_GUIDE" && grep -qF 'Refuse to write code' "$SPEC_GUIDE" && grep -qF 'Before invoking `/fbk-spec-review`' "$SPEC_GUIDE" && grep -qF 'Would you like to move to spec review?' "$SPEC_GUIDE"; then
  ok "T11a (AC-01) — feature-spec-guide.md contains 'If the gate fails:', 'Refuse to write code', 'Before invoking \`/fbk-spec-review\`', and 'Would you like to move to spec review?'"
else
  not_ok "T11a (AC-01) — feature-spec-guide.md contains 'If the gate fails:', 'Refuse to write code', 'Before invoking \`/fbk-spec-review\`', and 'Would you like to move to spec review?'" "file: $SPEC_GUIDE"
fi

# --- T11b (AC-02) — review-perspectives.md contains five guide-side sentinels (incl. user-question) ---
if grep -qF 'Does this feature need a threat model?' "$REVIEW_GUIDE" && grep -qF 'There are N blocking findings' "$REVIEW_GUIDE" && grep -qF 'Present the classification with' "$REVIEW_GUIDE" && grep -qF 'Before invoking `/fbk-breakdown`' "$REVIEW_GUIDE" && grep -qF 'Would you like to proceed to task breakdown?' "$REVIEW_GUIDE"; then
  ok "T11b (AC-02) — review-perspectives.md contains 'Does this feature need a threat model?', 'There are N blocking findings', 'Present the classification with', 'Before invoking \`/fbk-breakdown\`', and 'Would you like to proceed to task breakdown?'"
else
  not_ok "T11b (AC-02) — review-perspectives.md contains 'Does this feature need a threat model?', 'There are N blocking findings', 'Present the classification with', 'Before invoking \`/fbk-breakdown\`', and 'Would you like to proceed to task breakdown?'" "file: $REVIEW_GUIDE"
fi

# --- T11c (AC-03) — implementation-guide.md contains three guide-side sentinels ---
if grep -qF 'Step 1 — Test tasks' "$IMPL_GUIDE" && grep -qF 'Cap: 2 escalation attempts per task' "$IMPL_GUIDE" && grep -qF 'No dead code introduced' "$IMPL_GUIDE"; then
  ok "T11c (AC-03) — implementation-guide.md contains 'Step 1 — Test tasks', 'Cap: 2 escalation attempts per task', and 'No dead code introduced'"
else
  not_ok "T11c (AC-03) — implementation-guide.md contains 'Step 1 — Test tasks', 'Cap: 2 escalation attempts per task', and 'No dead code introduced'" "file: $IMPL_GUIDE"
fi

# --- T11d (AC-03 / AC-04) — implementation-guide.md does not contain the env-flag string ---
if ! grep -qF 'CLAUDE_CODE_EXPERIMENTAL_AGENT_TEAMS' "$IMPL_GUIDE"; then
  ok "T11d (AC-03/AC-04) — implementation-guide.md does not contain 'CLAUDE_CODE_EXPERIMENTAL_AGENT_TEAMS'"
else
  not_ok "T11d (AC-03/AC-04) — implementation-guide.md does not contain 'CLAUDE_CODE_EXPERIMENTAL_AGENT_TEAMS'" "file: $IMPL_GUIDE"
fi

# --- T12 (AC-04) — frontmatter operational glue preserved across all three skills ---
if [ "$(head -n 1 "$SPEC_SKILL")" = "---" ] && grep -qF 'description:' "$SPEC_SKILL" \
   && [ "$(head -n 1 "$REVIEW_SKILL")" = "---" ] && grep -qF 'description:' "$REVIEW_SKILL" \
   && [ "$(head -n 1 "$IMPL_SKILL")" = "---" ] && grep -qF 'description:' "$IMPL_SKILL"; then
  ok "T12 (AC-04) — frontmatter operational glue preserved across all three skills"
else
  not_ok "T12 (AC-04) — frontmatter operational glue preserved across all three skills" "files: $SPEC_SKILL, $REVIEW_SKILL, $IMPL_SKILL"
fi

# --- T13 (AC-04) — argument-resolution operational glue ---
if grep -qF '$ARGUMENTS' "$SPEC_SKILL" && grep -qF '$ARGUMENTS' "$REVIEW_SKILL" && grep -qF 'FEATURE=$ARGUMENTS' "$IMPL_SKILL"; then
  ok "T13 (AC-04) — fbk-spec and fbk-spec-review contain '\$ARGUMENTS'; fbk-implement contains 'FEATURE=\$ARGUMENTS'"
else
  not_ok "T13 (AC-04) — fbk-spec and fbk-spec-review contain '\$ARGUMENTS'; fbk-implement contains 'FEATURE=\$ARGUMENTS'" "files: $SPEC_SKILL, $REVIEW_SKILL, $IMPL_SKILL"
fi

# --- T14 (AC-04) — chained-skill invocation operational glue ---
if grep -qF '/fbk-spec-review $ARGUMENTS' "$SPEC_SKILL" && grep -qF '/fbk-breakdown' "$REVIEW_SKILL"; then
  ok "T14 (AC-04) — fbk-spec contains '/fbk-spec-review \$ARGUMENTS'; fbk-spec-review contains '/fbk-breakdown'"
else
  not_ok "T14 (AC-04) — fbk-spec contains '/fbk-spec-review \$ARGUMENTS'; fbk-spec-review contains '/fbk-breakdown'" "files: $SPEC_SKILL, $REVIEW_SKILL"
fi

# --- T15 (AC-01/AC-02) — user-question prose removed from skills (guide-only ownership) ---
if ! grep -qF 'Would you like to move to spec review?' "$SPEC_SKILL" && ! grep -qF 'Would you like to proceed to task breakdown?' "$REVIEW_SKILL"; then
  ok "T15 (AC-01/AC-02) — user-question prose absent from fbk-spec and fbk-spec-review skills (guide-side ownership)"
else
  not_ok "T15 (AC-01/AC-02) — user-question prose absent from fbk-spec and fbk-spec-review skills (guide-side ownership)" "files: $SPEC_SKILL, $REVIEW_SKILL"
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
