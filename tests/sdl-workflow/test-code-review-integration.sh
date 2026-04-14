#!/usr/bin/env bash
set -uo pipefail

PASS=0
FAIL=0
TOTAL=0

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
PROJECT_ROOT="$(cd "$SCRIPT_DIR/../.." && pwd)"

SKILL_FILE="$PROJECT_ROOT/assets/skills/fbk-code-review/SKILL.md"
EXISTING_REF="$PROJECT_ROOT/assets/skills/fbk-code-review/references/existing-code-review.md"
POSTIMPL_REF="$PROJECT_ROOT/assets/skills/fbk-code-review/references/post-impl-review.md"
DETECTOR="$PROJECT_ROOT/assets/agents/fbk-t1-value-abstraction-detector.md"
CHALLENGER="$PROJECT_ROOT/assets/agents/fbk-code-review-challenger.md"
GUIDE="$PROJECT_ROOT/assets/fbk-docs/fbk-sdl-workflow/code-review-guide.md"
CHECKLIST="$PROJECT_ROOT/assets/fbk-docs/fbk-sdl-workflow/ai-failure-modes.md"
FIXTURE_DIR="$PROJECT_ROOT/tests/fixtures/code-review"

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

# --- Test 1: All fixture files exist ---
all_fixtures=1
for f in \
  "$FIXTURE_DIR/auth-spec.md" \
  "$FIXTURE_DIR/src/auth/session.ts" \
  "$FIXTURE_DIR/src/auth/tokens.ts" \
  "$FIXTURE_DIR/src/orders/checkout.ts" \
  "$FIXTURE_DIR/src/orders/returns.ts" \
  "$FIXTURE_DIR/tests/auth.test.ts"; do
  if [ ! -f "$f" ]; then
    all_fixtures=0
    break
  fi
done
if [ "$all_fixtures" -eq 1 ]; then
  ok "all fixture files exist"
else
  not_ok "all fixture files exist" "one or more fixture files missing"
fi

# --- AC-01/AC-02 --- Detection-verification round trip ---

# Test 2: Skill defines the detection-verification loop
if grep -qi 'detect' "$SKILL_FILE" && grep -qiE 'verif|challenge' "$SKILL_FILE"; then
  ok "skill defines the detection-verification loop"
else
  not_ok "skill defines the detection-verification loop" "skill missing 'detect' and 'verif'/'challenge' language"
fi

# Test 3: Detector agent defines sighting output
if grep -qi 'sighting' "$DETECTOR"; then
  ok "tier 1 agent defines sighting output"
else
  not_ok "tier 1 agent defines sighting output" "tier 1 agent missing 'sighting' keyword"
fi

# Test 4: Challenger agent defines verification output
if grep -qi 'verif' "$CHALLENGER" && grep -qiE 'reject|disprove|counter-evidence' "$CHALLENGER"; then
  ok "challenger agent defines verification output"
else
  not_ok "challenger agent defines verification output" "challenger missing 'verif' combined with reject/disprove/counter-evidence"
fi

# Test 5: Challenger agent includes rejection capability (AC-02 false positive filtering)
if grep -qiE 'reject|disprove|dismissed' "$CHALLENGER"; then
  ok "challenger agent includes rejection capability"
else
  not_ok "challenger agent includes rejection capability" "challenger missing reject/disprove/dismissed language"
fi

# Test 6: Fixture spec contains intentional deviation deferral note (UV-6 false positive plant)
if grep -qiE 'defer|intentional|future phase' "$FIXTURE_DIR/auth-spec.md"; then
  ok "fixture spec contains intentional deviation deferral note"
else
  not_ok "fixture spec contains intentional deviation deferral note" "auth-spec.md missing defer/intentional/future phase language"
fi

# Test 7: Detector -> Challenger sighting handoff format (structural proxy)
if grep -q 'S-' "$DETECTOR" && grep -q 'S-' "$CHALLENGER"; then
  ok "tier 1 agent and challenger both reference sighting ID format (S-)"
else
  not_ok "tier 1 agent and challenger both reference sighting ID format (S-)" "one or both agents missing 'S-' sighting ID reference"
fi

# Test 8: Guide defines the orchestration loop protocol
if grep -qiE 'loop|iteration|round' "$GUIDE" && grep -qiE 'sighting|finding|terminat' "$GUIDE"; then
  ok "guide defines the orchestration loop protocol"
else
  not_ok "guide defines the orchestration loop protocol" "guide missing loop/iteration/round combined with sighting/finding/terminat"
fi

# --- AC-05 --- Spec output from review ---

# Test 9: Existing-code-review reference includes spec drafting guidance
if grep -qi 'spec' "$EXISTING_REF" && grep -qiE 'draft|co-author|section' "$EXISTING_REF"; then
  ok "existing-code-review reference includes spec drafting guidance"
else
  not_ok "existing-code-review reference includes spec drafting guidance" "existing-code-review.md missing spec draft/co-author/section language"
fi

# Test 10: Existing-code-review reference references spec-gate
if grep -qiE 'spec-gate|spec gate' "$EXISTING_REF"; then
  ok "existing-code-review reference references spec-gate"
else
  not_ok "existing-code-review reference references spec-gate" "existing-code-review.md missing spec-gate reference"
fi

# Test 11: Existing-code-review reference references the 9-section template
if grep -qiE '9-section|nine-section|feature-spec-guide' "$EXISTING_REF"; then
  ok "existing-code-review reference references the 9-section template"
else
  not_ok "existing-code-review reference references the 9-section template" "existing-code-review.md missing 9-section/feature-spec-guide reference"
fi

# --- AC-06 --- Cleanup mode ---

# Test 12: Skill handles the no-spec scenario
if grep -qiE 'no spec|without spec|no existing spec' "$SKILL_FILE"; then
  ok "skill handles the no-spec scenario"
else
  not_ok "skill handles the no-spec scenario" "skill missing no-spec routing language"
fi

# Test 13: Skill references checklist for no-spec mode
if grep -qiE 'ai-failure-modes|failure mode checklist' "$SKILL_FILE" || \
   (grep -qi 'checklist' "$SKILL_FILE" && grep -qiE 'no spec|structural' "$SKILL_FILE"); then
  ok "skill references AI failure mode checklist for no-spec mode"
else
  not_ok "skill references AI failure mode checklist for no-spec mode" "skill missing checklist reference in no-spec path"
fi

# Test 14: Checklist items contain detection heuristics
match_count=$(grep -ciE 'detect|look for|check|heuristic' "$CHECKLIST")
if [ "$match_count" -ge 3 ]; then
  ok "checklist items contain detection heuristics ($match_count matches)"
else
  not_ok "checklist items contain detection heuristics" "only $match_count matches, need at least 3"
fi

# Test 15: Checklist items are numbered and referenceable (UV-5 structural proxy)
numbered_count=$(grep -cE '^[0-9]+\.' "$CHECKLIST")
if [ "$numbered_count" -ge 5 ]; then
  ok "checklist items are numbered and referenceable ($numbered_count items)"
else
  not_ok "checklist items are numbered and referenceable" "only $numbered_count numbered items, need at least 5"
fi

# --- E2e --- Full code review cycle (UV-1 through UV-4) ---

# Test 16: All 13 context assets exist
all_assets=1
for f in \
  "$SKILL_FILE" \
  "$EXISTING_REF" \
  "$POSTIMPL_REF" \
  "$PROJECT_ROOT/assets/agents/fbk-t1-value-abstraction-detector.md" \
  "$PROJECT_ROOT/assets/agents/fbk-t1-dead-code-detector.md" \
  "$PROJECT_ROOT/assets/agents/fbk-t1-signal-loss-detector.md" \
  "$PROJECT_ROOT/assets/agents/fbk-t1-behavioral-drift-detector.md" \
  "$PROJECT_ROOT/assets/agents/fbk-t1-function-boundaries-detector.md" \
  "$PROJECT_ROOT/assets/agents/fbk-t1-cross-boundary-structure-detector.md" \
  "$PROJECT_ROOT/assets/agents/fbk-t1-missing-safeguards-detector.md" \
  "$CHALLENGER" \
  "$GUIDE" \
  "$CHECKLIST"; do
  if [ ! -f "$f" ]; then
    all_assets=0
    break
  fi
done
if [ "$all_assets" -eq 1 ]; then
  ok "all 13 context assets exist"
else
  not_ok "all 13 context assets exist" "one or more context asset files missing"
fi

# Test 17: Cross-file reference: Skill references tier 1 agents by correct name
challenger_name=$(grep '^name:' "$CHALLENGER" | head -1 | sed 's/name:[[:space:]]*//' | tr -d '"')
if (grep -qi 'value-abstraction' "$SKILL_FILE" || grep -qi 'code-review-detector' "$SKILL_FILE") && grep -qF "$challenger_name" "$SKILL_FILE"; then
  ok "skill references tier 1 agents by correct name"
else
  not_ok "skill references tier 1 agents by correct name" "skill missing agent references or '$challenger_name'"
fi

# Test 18: Cross-file reference: Skill references guide by correct path
if grep -qiE 'docs/sdl-workflow/code-review-guide|code-review-guide\.md' "$SKILL_FILE"; then
  ok "skill references guide by correct path"
else
  not_ok "skill references guide by correct path" "skill missing code-review-guide path reference"
fi

# Test 19: Cross-file reference: Skill references checklist by correct path
if grep -qiE 'docs/sdl-workflow/ai-failure-modes|ai-failure-modes\.md' "$SKILL_FILE"; then
  ok "skill references checklist by correct path"
else
  not_ok "skill references checklist by correct path" "skill missing ai-failure-modes path reference"
fi

# Test 20: Finding format consistency between guide and agents (sighting/finding IDs)
if grep -q 'S-' "$DETECTOR" && grep -q 'F-' "$CHALLENGER"; then
  ok "finding format consistency: detector uses S- sighting IDs, challenger uses F- finding IDs"
else
  not_ok "finding format consistency between guide and agents" "detector missing 'S-' or challenger missing 'F-'"
fi

# Test 21: Skill includes /fbk-improve transition instruction (AC-01 automatic invocation seam)
if grep -qE '/fbk-improve|fbk-improve' "$SKILL_FILE"; then
  ok "skill includes /fbk-improve transition instruction"
else
  not_ok "skill includes /fbk-improve transition instruction" "skill missing /fbk-improve or fbk-improve reference"
fi

# --- Summary ---
echo ""
echo "# $PASS/$TOTAL tests passed"
if [ "$FAIL" -eq 0 ]; then
  exit 0
fi
exit 1
