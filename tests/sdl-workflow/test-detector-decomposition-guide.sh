#!/usr/bin/env bash
set -uo pipefail

PASS=0
FAIL=0
TOTAL=0

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
PROJECT_ROOT="$(cd "$SCRIPT_DIR/../.." && pwd)"
GUIDE="$PROJECT_ROOT/assets/fbk-docs/fbk-sdl-workflow/code-review-guide.md"

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

# Helper: extract section from heading to next heading
extract_section() {
  local heading="$1"
  sed -n "/^## $heading/,/^## /p" "$2" | head -n -1
}

echo "TAP version 13"

# --- Test 1: Guide contains preset or Tier 1 reference ---
if grep -qiE 'preset|tier 1' "$GUIDE"; then
  ok "Guide contains preset or Tier 1 reference"
else
  not_ok "Guide contains preset or Tier 1 reference"
fi

# --- Test 2: Guide contains Deduplicator or dedup reference ---
if grep -qiE 'deduplicat|dedup' "$GUIDE"; then
  ok "Guide contains Deduplicator or dedup reference"
else
  not_ok "Guide contains Deduplicator or dedup reference"
fi

# --- Test 3: Orchestration Protocol section contains multi-agent spawn language ---
orch_section=$(extract_section "Orchestration Protocol" "$GUIDE" 2>/dev/null || true)
if echo "$orch_section" | grep -qE 'per-group|named agent|Tier 1'; then
  ok "Orchestration Protocol section contains multi-agent spawn language"
else
  not_ok "Orchestration Protocol section contains multi-agent spawn language"
fi

# --- Test 4: Retrospective Fields section contains enumeration compliance ---
retro_section=$(extract_section "Retrospective Fields" "$GUIDE" 2>/dev/null || true)
if echo "$retro_section" | grep -qi 'enumeration compliance'; then
  ok "Retrospective Fields section contains enumeration compliance"
else
  not_ok "Retrospective Fields section contains enumeration compliance"
fi

# --- Test 5: Retrospective Fields section contains survival rate ---
if echo "$retro_section" | grep -qiE 'survival rate|sighting survival'; then
  ok "Retrospective Fields section contains survival rate"
else
  not_ok "Retrospective Fields section contains survival rate"
fi

# --- Test 6: Retrospective Fields section contains phase attribution ---
if echo "$retro_section" | grep -qi 'phase attribution'; then
  ok "Retrospective Fields section contains phase attribution"
else
  not_ok "Retrospective Fields section contains phase attribution"
fi

# --- Test 7: Retrospective Fields section contains instruction trace or prompt composition ---
if echo "$retro_section" | grep -qiE 'instruction trace|prompt composition'; then
  ok "Retrospective Fields section contains instruction trace or prompt composition"
else
  not_ok "Retrospective Fields section contains instruction trace or prompt composition"
fi

# --- Test 8: Retrospective Fields section contains merge count, merged pairs, or dedup ---
if echo "$retro_section" | grep -qiE 'merge count|merged pairs|dedup'; then
  ok "Retrospective Fields section contains merge count, merged pairs, or dedup"
else
  not_ok "Retrospective Fields section contains merge count, merged pairs, or dedup"
fi

# --- Test 9: Orchestration Protocol section contains Challenger batching language ---
if echo "$orch_section" | grep -qiE 'batch|1 per 5|challenger.*per.*sighting'; then
  ok "Orchestration Protocol section contains Challenger batching language"
else
  not_ok "Orchestration Protocol section contains Challenger batching language"
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
