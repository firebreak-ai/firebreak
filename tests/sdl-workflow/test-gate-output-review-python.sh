#!/usr/bin/env bash
set -uo pipefail

PASS=0
FAIL=0
TOTAL=0

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
PROJECT_ROOT="$(cd "$SCRIPT_DIR/../.." && pwd)"
DISPATCHER="$PROJECT_ROOT/assets/fbk-scripts/fbk.py"

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

# --- Test 1: valid review with all perspectives passes ---
REVIEW_FIXTURE=$(mktemp /tmp/review-valid-XXXX.md)
cat > "$REVIEW_FIXTURE" << 'EOF'
# Security Review

## Security Perspective

This is a blocking security concern that needs attention.

Important: All interfaces validated.

### New tests needed
Existing tests impacted.
Test infrastructure changes required.

## Architecture Perspective

This is an informational architecture note.

## Threat Model

The threat model requires yes decision and substantial rationale to justify the approach taken and to explain the reasoning behind accepting or mitigating identified risks.

## Testing Strategy

New tests needed for the feature.
Existing tests impacted by changes.
Test infrastructure changes to support the new validation.
EOF

STDOUT=$(python3 "$DISPATCHER" review-gate "$REVIEW_FIXTURE" "Security,Architecture" 2>/tmp/review-gate-stderr)
RC=$?
STDERR=$(cat /tmp/review-gate-stderr)
if [ $RC -eq 0 ] && echo "$STDOUT" | grep -q '"result": "pass"'; then
  ok "valid review with all perspectives passes exit 0"
else
  not_ok "valid review with all perspectives passes exit 0" "rc=$RC stdout=$STDOUT stderr=$STDERR"
fi
rm -f "$REVIEW_FIXTURE"

# --- Test 2: review missing perspective fails ---
REVIEW_FIXTURE=$(mktemp /tmp/review-missing-perspective-XXXX.md)
cat > "$REVIEW_FIXTURE" << 'EOF'
# Security Review

## Security Perspective

This is a blocking security concern.

## Threat Model

The threat model requires yes decision and substantial rationale to justify the approach.

## Testing Strategy

New tests needed for the feature.
Existing tests impacted by changes.
Test infrastructure changes to support the new validation.
EOF

STDOUT=$(python3 "$DISPATCHER" review-gate "$REVIEW_FIXTURE" "Security,Architecture" 2>/tmp/review-gate-stderr)
RC=$?
STDERR=$(cat /tmp/review-gate-stderr)
if [ $RC -eq 2 ] && echo "$STDERR" | grep -q "Missing perspective"; then
  ok "review missing perspective fails exit 2"
else
  not_ok "review missing perspective fails exit 2" "rc=$RC stderr=$STDERR"
fi
rm -f "$REVIEW_FIXTURE"

# --- Test 3: missing arguments exits 2 ---
STDOUT=$(python3 "$DISPATCHER" review-gate 2>/tmp/review-gate-stderr)
RC=$?
STDERR=$(cat /tmp/review-gate-stderr)
if [ $RC -eq 2 ]; then
  ok "missing arguments exits 2"
else
  not_ok "missing arguments exits 2" "rc=$RC stderr=$STDERR"
fi

# --- Summary ---
rm -f /tmp/review-gate-stderr
echo ""
echo "# $PASS/$TOTAL tests passed"
if [ "$FAIL" -gt 0 ]; then
  exit 1
fi
exit 0
