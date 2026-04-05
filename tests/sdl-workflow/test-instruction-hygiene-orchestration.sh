#!/usr/bin/env bash
set -uo pipefail

TESTS=0
PASS=0
FAIL=0

ok() {
  TESTS=$((TESTS + 1))
  PASS=$((PASS + 1))
  echo "ok $TESTS - $1"
}

not_ok() {
  TESTS=$((TESTS + 1))
  FAIL=$((FAIL + 1))
  echo "not ok $TESTS - $1"
  [ -n "${2:-}" ] && echo "# $2"
}

# Setup
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(cd "$SCRIPT_DIR/../.." && pwd)"
SKILL="$PROJECT_ROOT/assets/skills/fbk-code-review/SKILL.md"
GUIDE="$PROJECT_ROOT/assets/fbk-docs/fbk-sdl-workflow/code-review-guide.md"

echo "TAP version 13"
echo "1..6"

# ---- Test 1: AC-07 SKILL.md step 1 contains content-first ordering language ----
if grep -qiE 'contents? first|code.*first.*then.*instructions|file contents first' "$SKILL"; then
  ok "AC-07 SKILL.md step 1 contains content-first ordering language"
else
  not_ok "AC-07 SKILL.md step 1 contains content-first ordering language" "grep did not find content-first language in step 1"
fi

# ---- Test 2: AC-07 SKILL.md step 3 (Spawn Challenger) contains content-first ordering language ----
if grep -A3 'Spawn Challenger' "$SKILL" | grep -qiE 'contents? first|code.*first|file contents first'; then
  ok "AC-07 SKILL.md step 3 (Spawn Challenger) contains content-first ordering language"
else
  not_ok "AC-07 SKILL.md step 3 (Spawn Challenger) contains content-first ordering language" "grep did not find content-first language in Spawn Challenger section"
fi

# ---- Test 3: AC-12 SKILL.md initial read instructions reference ai-failure-modes ----
if head -20 "$SKILL" | grep -qi 'ai-failure-modes'; then
  ok "AC-12 SKILL.md initial read instructions reference ai-failure-modes"
else
  not_ok "AC-12 SKILL.md initial read instructions reference ai-failure-modes" "ai-failure-modes not found in initial read instructions"
fi

# ---- Test 4: AC-12 SKILL.md initial read instructions reference quality-detection ----
if head -20 "$SKILL" | grep -qi 'quality-detection'; then
  ok "AC-12 SKILL.md initial read instructions reference quality-detection"
else
  not_ok "AC-12 SKILL.md initial read instructions reference quality-detection" "quality-detection not found in initial read instructions"
fi

# ---- Test 5: AC-13 code-review-guide.md Source of Truth Handling does NOT contain "Supplement with" language ----
if ! grep -qi 'supplement with' "$GUIDE"; then
  ok "AC-13 code-review-guide.md Source of Truth Handling does NOT contain 'Supplement with' hierarchy language"
else
  not_ok "AC-13 code-review-guide.md Source of Truth Handling does NOT contain 'Supplement with' hierarchy language" "'Supplement with' language still exists in guide"
fi

# ---- Test 6: AC-13 code-review-guide.md Orchestration Protocol step 1 contains content-first ordering language ----
if sed -n '/## Orchestration Protocol/,/^## /p' "$GUIDE" | grep -qiE 'contents? first|code.*first|file contents first'; then
  ok "AC-13 code-review-guide.md Orchestration Protocol step 1 contains content-first ordering language"
else
  not_ok "AC-13 code-review-guide.md Orchestration Protocol step 1 contains content-first ordering language" "content-first language not found in Orchestration Protocol"
fi

# Summary
echo ""
echo "# Tests: $TESTS, Pass: $PASS, Fail: $FAIL"
exit $FAIL
