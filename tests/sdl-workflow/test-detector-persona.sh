#!/usr/bin/env bash
set -uo pipefail

PASS=0
FAIL=0
TOTAL=0

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
PROJECT_ROOT="$(cd "$SCRIPT_DIR/../.." && pwd)"
# Code-review-specific content (finding types, severities, matrix) moved from the old
# fbk-code-review-detector.md into the per-type lens in the unified-review-shape
# consolidation. The generic researcher (fbk-review-researcher.md) carries the role;
# the lens carries the code-review-specific knowledge.
DETECTOR="$PROJECT_ROOT/assets/fbk-docs/fbk-review-lenses/code-lens.md"

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

# code-lens.md is a plain markdown file (no YAML frontmatter), so read it in full.
body=$(cat "$DETECTOR")

# retired: "senior software validation engineer" was the old code-review-detector persona
# label. The generic review-researcher uses "senior evaluator". unified-review-shape.

# --- Test 1: Lens defines the mechanism field ---
if echo "$body" | grep -qi 'mechanism'; then
  ok "Lens defines the mechanism field"
else
  not_ok "Lens defines the mechanism field" "expected 'mechanism' in code-lens body"
fi

# retired: "caller impact" was old-specific wording in the detector output quality bar.
# The generic researcher uses "consequence" for downstream impact. unified-review-shape.

# --- Test 2: Lens defines the behavioral finding type ---
if echo "$body" | grep -qiE 'behavioral'; then
  ok "Lens defines the behavioral finding type"
else
  not_ok "Lens defines the behavioral finding type" "expected 'behavioral' in code-lens body"
fi

# --- Test 3: Lens defines the structural finding type ---
if echo "$body" | grep -qiE 'structural.*(maintain|wrong|organization)|maintain.*structural'; then
  ok "Lens defines the structural finding type"
else
  not_ok "Lens defines the structural finding type" "expected structural with 'maintain', 'wrong', or 'organization' in body"
fi

# --- Test 4: Lens defines the test-integrity finding type ---
if echo "$body" | grep -qiE 'test-integrity'; then
  ok "Lens defines the test-integrity finding type"
else
  not_ok "Lens defines the test-integrity finding type" "expected 'test-integrity' in code-lens body"
fi

# --- Test 5: Lens defines critical severity with observability language ---
if echo "$body" | grep -qiE 'critical.*(observe|actor|user|realistic)|(observe|actor|user|realistic).*critical'; then
  ok "Lens defines critical severity with observability language"
else
  not_ok "Lens defines critical severity with observability language" "expected critical with observability language in body"
fi

# --- Test 6: Lens defines major severity with reachability language ---
if echo "$body" | grep -qiE 'major.*(reachable|requires|specific)|(reachable|requires|specific).*major'; then
  ok "Lens defines major severity with reachability language"
else
  not_ok "Lens defines major severity with reachability language" "expected major with reachability language in body"
fi

# --- Test 7: Lens defines minor severity ---
if echo "$body" | grep -qiE 'minor.*(narrow|transient|impact)|(narrow|transient|impact).*minor'; then
  ok "Lens defines minor severity with impact language"
else
  not_ok "Lens defines minor severity with impact language" "expected minor with 'narrow', 'transient', or 'impact' in body"
fi

# --- Test 8: Lens contains a type-severity validity matrix ---
if echo "$body" | grep -qiE 'matrix|type-severity'; then
  ok "Lens contains type-severity validity matrix"
else
  not_ok "Lens contains type-severity validity matrix" "expected 'matrix' or 'type-severity' in body"
fi

# --- Test 9: Lens does not contain a separate Mechanism section heading ---
if echo "$body" | grep -q '^## Mechanism'; then
  not_ok "Lens does not contain separate Mechanism section heading" "found '## Mechanism' section heading"
else
  ok "Lens does not contain separate Mechanism section heading"
fi

# retired: "exclude nits" was a researcher-level instruction in the old code-review-detector.
# Nit filtering moved to the challenger's rejected-as-nit verdict in the unified-review-shape
# consolidation. Covered by test-challenger-persona.sh.

# --- Summary ---
echo ""
echo "1..$TOTAL"
echo "# $PASS/$TOTAL tests passed"
if [ "$FAIL" -gt 0 ]; then
  echo "# FAIL $FAIL"
  exit 1
fi
exit 0
