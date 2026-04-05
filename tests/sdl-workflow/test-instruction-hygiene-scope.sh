#!/bin/bash
set -uo pipefail

# TAP test: instruction hygiene scope resolution, dedup references, item split
PASS=0
FAIL=0
TOTAL=0

PROJECT_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
CHECKLIST="$PROJECT_ROOT/assets/fbk-docs/fbk-sdl-workflow/ai-failure-modes.md"
QUALITY="$PROJECT_ROOT/assets/fbk-docs/fbk-design-guidelines/quality-detection.md"

# Helper functions
ok() {
  TOTAL=$((TOTAL + 1))
  PASS=$((PASS + 1))
  echo "ok $TOTAL - $1"
}

not_ok() {
  TOTAL=$((TOTAL + 1))
  FAIL=$((FAIL + 1))
  echo "not_ok $TOTAL - $1"
}

echo "TAP version 13"

# Test 1: AC-03 positive - assert line 1 contains "Apply these detection targets"
if grep -qi 'Apply these detection targets' "$CHECKLIST"; then
  ok "AC-03: ai-failure-modes.md line 1 contains 'Apply these detection targets'"
else
  not_ok "AC-03: ai-failure-modes.md line 1 contains 'Apply these detection targets'"
fi

# Test 2: AC-03 negative - assert does NOT contain conditional scope instruction
if ! grep -qi 'When specs are available, use quality-detection.md instead' "$CHECKLIST"; then
  ok "AC-03: ai-failure-modes.md does NOT contain conditional scope instruction"
else
  not_ok "AC-03: ai-failure-modes.md does NOT contain conditional scope instruction"
fi

# Test 3: AC-01 - assert item 7 references quality-detection.md
if grep -A2 '^7\.' "$CHECKLIST" | grep -qi 'quality-detection'; then
  ok "AC-01: ai-failure-modes.md item 7 references quality-detection.md"
else
  not_ok "AC-01: ai-failure-modes.md item 7 references quality-detection.md"
fi

# Test 4: AC-02 - assert item 11 references quality-detection.md
if grep -A2 '^11\.' "$CHECKLIST" | grep -qi 'quality-detection'; then
  ok "AC-02: ai-failure-modes.md item 11 references quality-detection.md"
else
  not_ok "AC-02: ai-failure-modes.md item 11 references quality-detection.md"
fi

# Test 5: AC-11 dedup - assert item 10 references quality-detection.md
if grep -A2 '^10\.' "$CHECKLIST" | grep -qi 'quality-detection'; then
  ok "AC-11: ai-failure-modes.md item 10 references quality-detection.md"
else
  not_ok "AC-11: ai-failure-modes.md item 10 references quality-detection.md"
fi

# Test 6: AC-09 count - assert exactly 14 numbered items
count=$(grep -cE '^[0-9]+\.' "$CHECKLIST")
if [ "$count" -eq 14 ]; then
  ok "AC-09: ai-failure-modes.md contains exactly 14 numbered items"
else
  not_ok "AC-09: ai-failure-modes.md contains exactly 14 numbered items (found $count)"
fi

# Test 7: AC-09 item 12 - assert contains "Semantically incoherent"
if grep -A1 '^12\.' "$CHECKLIST" | grep -qi 'semantically incoherent'; then
  ok "AC-09: ai-failure-modes.md item 12 contains 'Semantically incoherent'"
else
  not_ok "AC-09: ai-failure-modes.md item 12 contains 'Semantically incoherent'"
fi

# Test 8: AC-09 item 13 - assert contains "Mock permissiveness"
if grep -A1 '^13\.' "$CHECKLIST" | grep -qi 'mock permissiveness'; then
  ok "AC-09: ai-failure-modes.md item 13 contains 'Mock permissiveness'"
else
  not_ok "AC-09: ai-failure-modes.md item 13 contains 'Mock permissiveness'"
fi

# Test 9: AC-11 split - assert quality-detection.md has "Silent error discard" section
if grep -qi '## Silent error discard' "$QUALITY"; then
  ok "AC-11: quality-detection.md contains 'Silent error discard' section"
else
  not_ok "AC-11: quality-detection.md contains 'Silent error discard' section"
fi

# Test 10: AC-11 split - assert quality-detection.md has "Context discard" section
if grep -qi '## Context discard' "$QUALITY"; then
  ok "AC-11: quality-detection.md contains 'Context discard' section"
else
  not_ok "AC-11: quality-detection.md contains 'Context discard' section"
fi

# Summary
echo ""
echo "# Tests: $TOTAL | Passed: $PASS | Failed: $FAIL"
[ "$FAIL" -eq 0 ]
