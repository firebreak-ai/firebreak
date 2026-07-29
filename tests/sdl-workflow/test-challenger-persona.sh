#!/usr/bin/env bash
set -uo pipefail

PASS=0
FAIL=0
TOTAL=0

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
PROJECT_ROOT="$(cd "$SCRIPT_DIR/../.." && pwd)"
CHALLENGER="$PROJECT_ROOT/assets/agents/fbk-review-challenger.md"
REVIEW_LOOP="$PROJECT_ROOT/assets/fbk-docs/fbk-review-lenses/review-loop.md"

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

body=$(awk '/^---$/{c++; if(c==2){found=1; next}} found' "$CHALLENGER")

# retired: old code-review-challenger had a "mistrustful" persona label; the generic
# review-challenger describes the same discipline as "demands proof for every candidate"
# in the description field. The word "mistrustful" moved out of the architecture in the
# unified-review-shape consolidation.

# retired: old code-review-challenger required "reading the code yourself"; the generic
# review-challenger uses "read the artifact independently" — same discipline, different
# wording. unified-review-shape consolidation.

# --- Test 1: Challenger requires evidence in own words ---
if echo "$body" | grep -qiE 'your own words'; then
  ok "Challenger requires own words for verification evidence"
else
  not_ok "Challenger requires own words for verification evidence" "expected 'your own words' in body"
fi

# retired: "not the Detector" wording moved to "not a restatement of the researcher's" in
# the generic challenger. unified-review-shape consolidation.

# retired: "design intent" was a code-review-specific challenger discipline; the generic
# challenger does not carry this phrase. Code-review-specific disciplines live in code-lens.md.

# --- Test 2: Challenger traces callers for behavioral sightings ---
if echo "$body" | grep -qiE 'behavioral.*caller|behavioral.*trac|caller.*behavioral'; then
  ok "Challenger traces callers for behavioral sightings"
else
  not_ok "Challenger traces callers for behavioral sightings" "expected 'behavioral.*caller', 'caller.*behavioral', or 'behavioral.*trac' in body"
fi

# --- Test 3: Challenger reclassifies with matrix validation ---
if echo "$body" | grep -qi 'reclassif' && echo "$body" | grep -qi 'matrix'; then
  ok "Challenger reclassifies with matrix validation"
else
  not_ok "Challenger reclassifies with matrix validation" "expected both 'reclassif' and 'matrix' in body"
fi

# --- Test 4: Challenger rejects nits as functionally irrelevant ---
if echo "$body" | grep -qi 'nit' && (echo "$body" | grep -qi 'functionally irrelevant' || echo "$body" | grep -qiE 'naming.*formatting.*style'); then
  ok "Challenger rejects nits as functionally irrelevant"
else
  not_ok "Challenger rejects nits as functionally irrelevant" "expected 'nit' with 'functionally irrelevant' or 'naming.*formatting.*style' in body"
fi

# --- Test 5: Challenger description field contains evidence/proof language ---
fm=$(sed -n '2,/^---$/p' "$CHALLENGER" | sed '$d')
desc_val=$(echo "$fm" | grep '^description:' | sed 's/^description:[[:space:]]*//;s/[[:space:]]*$//')
if echo "$desc_val" | grep -qiE 'proof|evidence|demands'; then
  ok "Challenger description field contains evidence/proof language"
else
  not_ok "Challenger description field contains evidence/proof language" "desc_val='$desc_val'"
fi

# --- Test 6: Review loop defines Verified and Rejected outcomes ---
# The generic challenger body uses lowercase verdict tokens; the shared review-loop spine
# carries the prose definitions with capitalized forms.
if grep -q 'Verified' "$REVIEW_LOOP" && grep -q 'Rejected' "$REVIEW_LOOP"; then
  ok "Review loop defines Verified and Rejected outcomes"
else
  not_ok "Review loop defines Verified and Rejected outcomes" "expected both 'Verified' and 'Rejected' (case-sensitive) in $REVIEW_LOOP"
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
