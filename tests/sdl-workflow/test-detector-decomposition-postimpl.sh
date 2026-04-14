#!/usr/bin/env bash
set -uo pipefail

PASS=0
FAIL=0
TOTAL=0

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
PROJECT_ROOT="$(cd "$SCRIPT_DIR/../.." && pwd)"
POSTIMPL="$PROJECT_ROOT/assets/skills/fbk-code-review/references/post-impl-review.md"

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

# --- Test 1: post-impl-review.md exists and is non-empty (AC-13) ---
if [ -s "$POSTIMPL" ]; then
  ok "post-impl-review.md exists and is non-empty"
else
  not_ok "post-impl-review.md exists and is non-empty" "file: $POSTIMPL"
fi

# --- Test 2: Step 2 does not reference single Detector without multi-agent context (AC-13) ---
if grep -q 'Spawn Detector' "$POSTIMPL"; then
  # Check if the line with "Spawn Detector" also contains multi-agent language
  if grep 'Spawn Detector' "$POSTIMPL" | grep -qi 'multi-agent\|multiple.*agent\|per-group\|tier 1'; then
    ok "Step 2 references single Detector with multi-agent context"
  else
    not_ok "Step 2 does not reference single Detector without multi-agent context" "file: $POSTIMPL"
  fi
else
  ok "Step 2 does not reference single Detector without multi-agent context"
fi

# --- Test 3: post-impl-review.md contains multi-agent or per-group language (AC-13) ---
if grep -qiE 'per-group|tier 1|named agent|preset' "$POSTIMPL"; then
  ok "post-impl-review.md contains multi-agent or per-group language"
else
  not_ok "post-impl-review.md contains multi-agent or per-group language" "file: $POSTIMPL"
fi

# --- Test 4: post-impl-review.md contains Tier 1 group name or multi-agent spawn language (AC-13) ---
if grep -qiE 'value-abstraction|dead-code|signal-loss|behavioral-drift|function-boundaries|cross-boundary|missing-safeguards|multi-agent|multiple.*agent' "$POSTIMPL"; then
  ok "post-impl-review.md contains Tier 1 group name or multi-agent spawn language"
else
  not_ok "post-impl-review.md contains Tier 1 group name or multi-agent spawn language" "file: $POSTIMPL"
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
