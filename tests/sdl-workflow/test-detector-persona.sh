#!/usr/bin/env bash
set -uo pipefail

PASS=0
FAIL=0
TOTAL=0

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
PROJECT_ROOT="$(cd "$SCRIPT_DIR/../.." && pwd)"
DETECTOR="$PROJECT_ROOT/assets/agents/fbk-code-review-detector.md"

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

# Extract body (everything after second --- line)
body=$(awk '/^---$/{c++; if(c==2){found=1; next}} found' "$DETECTOR")

# --- Test 1: Detector contains staff engineer persona identity ---
if echo "$body" | grep -qi 'staff engineer'; then
  ok "Detector contains staff engineer persona identity"
else
  not_ok "Detector contains staff engineer persona identity" "expected 'staff engineer' in body"
fi

# --- Test 2: Detector output quality bar requires mechanism ---
if echo "$body" | grep -qi 'mechanism'; then
  ok "Detector output quality bar requires mechanism"
else
  not_ok "Detector output quality bar requires mechanism" "expected 'mechanism' in body"
fi

# --- Test 3: Detector output quality bar requires concrete failing input ---
if echo "$body" | grep -qi 'failing input'; then
  ok "Detector output quality bar requires concrete failing input"
else
  not_ok "Detector output quality bar requires concrete failing input" "expected 'failing input' in body"
fi

# --- Test 4: Detector output quality bar requires caller impact ---
if echo "$body" | grep -qi 'caller impact'; then
  ok "Detector output quality bar requires caller impact"
else
  not_ok "Detector output quality bar requires caller impact" "expected 'caller impact' in body"
fi

# --- Test 5: Detector contains behavioral type definition with concrete input language ---
if echo "$body" | grep -qiP 'behavioral.*(?:concrete|constructible)|(?:concrete|constructible).*behavioral' 2>/dev/null; then
  ok "Detector contains behavioral type definition with concrete input language"
else
  has_behavioral=$(echo "$body" | grep -ci 'behavioral' || true)
  has_constructible=$(echo "$body" | grep -ci 'constructible input' || true)
  if [ "$has_behavioral" -gt 0 ] && [ "$has_constructible" -gt 0 ]; then
    ok "Detector contains behavioral type definition with concrete input language"
  else
    not_ok "Detector contains behavioral type definition with concrete input language" "behavioral=$has_behavioral constructible_input=$has_constructible"
  fi
fi

# --- Test 6: Detector contains structural type definition ---
if echo "$body" | grep -qiE 'structural.*(no wrong output|maintain)|maintain.*structural'; then
  ok "Detector contains structural type definition"
else
  not_ok "Detector contains structural type definition" "expected structural with 'no wrong output' or 'maintain' in body"
fi

# --- Test 7: Detector contains test-integrity type definition ---
if echo "$body" | grep -qiE 'test-integrity.*(passes but|does not verify|claims)|(passes but|does not verify|claims).*test-integrity'; then
  ok "Detector contains test-integrity type definition"
else
  not_ok "Detector contains test-integrity type definition" "expected test-integrity with 'passes but', 'does not verify', or 'claims' in body"
fi

# --- Test 8: Detector contains fragile type definition with specific change language ---
if echo "$body" | grep -qiE 'fragile.*(specific.*change|plausible change)|(specific.*change|plausible change).*fragile'; then
  ok "Detector contains fragile type definition with specific change language"
else
  not_ok "Detector contains fragile type definition with specific change language" "expected fragile with 'specific change' or 'plausible change' in body"
fi

# --- Test 9: Detector contains critical severity definition with observability language ---
if echo "$body" | grep -qiE 'critical.*(next user|primary path)|(next user|primary path).*critical'; then
  ok "Detector contains critical severity definition with observability language"
else
  not_ok "Detector contains critical severity definition with observability language" "expected critical with 'next user' or 'primary path' in body"
fi

# --- Test 10: Detector contains major severity definition with observability language ---
if echo "$body" | grep -qiE 'major.*(write a test|demonstrates the failure|constructible)|(write a test|demonstrates the failure|constructible).*major'; then
  ok "Detector contains major severity definition with observability language"
else
  not_ok "Detector contains major severity definition with observability language" "expected major with 'write a test', 'demonstrates the failure', or 'constructible' in body"
fi

# --- Test 11: Detector contains minor severity definition with code-reading-only language ---
if echo "$body" | grep -qiE 'minor.*code reading|code reading.*minor'; then
  ok "Detector contains minor severity definition with code-reading-only language"
else
  not_ok "Detector contains minor severity definition with code-reading-only language" "expected minor with 'code reading' in body"
fi

# --- Test 12: Detector references type-severity validity matrix ---
if echo "$body" | grep -qiE 'matrix|type-severity'; then
  ok "Detector references type-severity validity matrix"
else
  not_ok "Detector references type-severity validity matrix" "expected 'matrix' or 'type-severity' in body"
fi

# --- Test 13: Detector does not contain separate mechanism-first wording instruction ---
if echo "$body" | grep -q '^## Mechanism'; then
  not_ok "Detector does not contain separate mechanism-first wording instruction" "found '## Mechanism' section heading — mechanism-first should be embedded in quality bar"
else
  ok "Detector does not contain separate mechanism-first wording instruction"
fi

# --- Test 14: Detector contains nit exclusion instruction ---
if echo "$body" | grep -qiE 'exclude nits'; then
  ok "Detector contains nit exclusion instruction"
else
  not_ok "Detector contains nit exclusion instruction" "expected 'exclude nits' or 'Exclude nits' in body"
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
