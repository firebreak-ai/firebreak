#!/usr/bin/env bash
set -uo pipefail

PASS=0
FAIL=0
TOTAL=0

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
PROJECT_ROOT="$(cd "$SCRIPT_DIR/../.." && pwd)"
CHALLENGER="$PROJECT_ROOT/assets/agents/fbk-code-review-challenger.md"

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

# --- Test 1: Challenger contains mistrustful persona language ---
if echo "$body" | grep -qi 'mistrustful'; then
  ok "Challenger contains mistrustful persona language"
else
  not_ok "Challenger contains mistrustful persona language" "expected 'mistrustful' in body"
fi

# --- Test 2: Challenger requires independent code reading ---
if echo "$body" | grep -qiE 'reading the code yourself|read.*code.*yourself'; then
  ok "Challenger requires independent code reading"
else
  not_ok "Challenger requires independent code reading" "expected 'reading the code yourself' or 'read.*code.*yourself' in body"
fi

# --- Test 3: Challenger requires own words, not Detector's ---
if echo "$body" | grep -qiE 'your own words|not the Detector'; then
  ok "Challenger requires own words, not Detector's"
else
  not_ok "Challenger requires own words, not Detector's" "expected 'your own words' or 'not the Detector' in body"
fi

# --- Test 4: Challenger cannot reproduce reasoning means reject ---
if echo "$body" | grep -qiE 'cannot.*reproduce.*reject|cannot independently reproduce'; then
  ok "Challenger cannot reproduce reasoning means reject"
else
  not_ok "Challenger cannot reproduce reasoning means reject" "expected 'cannot.*reproduce.*reject' or 'cannot independently reproduce' in body"
fi

# --- Test 5: Challenger keeps design intent in mind ---
if echo "$body" | grep -qi 'design intent'; then
  ok "Challenger keeps design intent in mind"
else
  not_ok "Challenger keeps design intent in mind" "expected 'design intent' in body"
fi

# --- Test 6: Challenger traces callers for behavioral sightings ---
if echo "$body" | grep -qiE 'behavioral.*caller|caller.*behavioral|trace.*caller'; then
  ok "Challenger traces callers for behavioral sightings"
else
  not_ok "Challenger traces callers for behavioral sightings" "expected 'behavioral.*caller', 'caller.*behavioral', or 'trace.*caller' in body"
fi

# --- Test 7: Challenger reclassifies with matrix validation ---
if echo "$body" | grep -qi 'reclassif' && echo "$body" | grep -qi 'matrix'; then
  ok "Challenger reclassifies with matrix validation"
else
  not_ok "Challenger reclassifies with matrix validation" "expected both 'reclassif' and 'matrix' in body"
fi

# --- Test 8: Challenger rejects nits as functionally irrelevant ---
if echo "$body" | grep -qi 'nit' && (echo "$body" | grep -qi 'functionally irrelevant' || echo "$body" | grep -qiE 'naming.*formatting.*style'); then
  ok "Challenger rejects nits as functionally irrelevant"
else
  not_ok "Challenger rejects nits as functionally irrelevant" "expected 'nit' with 'functionally irrelevant' or 'naming.*formatting.*style' in body"
fi

# --- Test 9: Challenger description field contains evidence/proof language ---
fm=$(sed -n '2,/^---$/p' "$CHALLENGER" | sed '$d')
desc_val=$(echo "$fm" | grep '^description:' | sed 's/^description:[[:space:]]*//;s/[[:space:]]*$//')
if echo "$desc_val" | grep -qiE 'proof|evidence|demands'; then
  ok "Challenger description field contains evidence/proof language"
else
  not_ok "Challenger description field contains evidence/proof language" "desc_val='$desc_val'"
fi

# --- Test 10: Challenger body references Verified and Rejected outcomes ---
if echo "$body" | grep -q 'Verified' && echo "$body" | grep -q 'Rejected'; then
  ok "Challenger body references Verified and Rejected outcomes"
else
  not_ok "Challenger body references Verified and Rejected outcomes" "expected both 'Verified' and 'Rejected' (case-sensitive) in body"
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
