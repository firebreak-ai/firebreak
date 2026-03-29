#!/usr/bin/env bash
set -uo pipefail

PASS=0
FAIL=0
TOTAL=0

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
PROJECT_ROOT="$(cd "$SCRIPT_DIR/../.." && pwd)"
ASSETS_DIR="$PROJECT_ROOT/assets"
SKILLS_DIR="$ASSETS_DIR/skills"

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

# --- Part 1: Execution path completeness ---
#
# Convention: skills with a references/ directory use execution handoffs.
# The LAST ## section in SKILL.md is the terminal/finalization section.
# Every reference file must contain that section heading and any skill
# invocations (/fbk-*) within it.
#
# This catches dead-end reference files that terminate before finalization.

found_skills=0

while IFS= read -r refdir; do
  found_skills=1
  skill_dir="$(dirname "$refdir")"
  skill_md="$skill_dir/SKILL.md"
  skill_rel="${skill_dir#$ASSETS_DIR/}"

  # Verify SKILL.md exists
  if [ ! -f "$skill_md" ]; then
    not_ok "SKILL.md exists for $skill_rel" "references/ dir exists but no SKILL.md"
    continue
  fi

  # Verify SKILL.md routes to the references/ directory
  if ! grep -q 'references/' "$skill_md"; then
    not_ok "SKILL.md routes to references/ in $skill_rel" \
      "references/ dir exists but SKILL.md does not reference it"
    continue
  fi
  ok "SKILL.md routes to references/ in $skill_rel"

  # Extract the last ## heading (terminal section)
  terminal_heading=$(grep '^## ' "$skill_md" | tail -1 | sed 's/^## //')

  if [ -z "$terminal_heading" ]; then
    not_ok "terminal section found in $skill_rel/SKILL.md" "no ## headings found"
    continue
  fi

  # Extract the terminal section body (from last ## heading to EOF)
  terminal_line=$(grep -n "^## ${terminal_heading}$" "$skill_md" | tail -1 | cut -d: -f1)
  terminal_body=$(tail -n +"$terminal_line" "$skill_md")

  # Find skill invocations (/fbk-*) in the terminal section
  skill_invocations=$(echo "$terminal_body" | grep -oE '/fbk-[a-z-]+' | sort -u)

  # Check each reference file
  while IFS= read -r ref_file; do
    ref_rel="${ref_file#$ASSETS_DIR/}"

    # Check 1: terminal section heading appears in the reference file
    if grep -qi "^## .*${terminal_heading}" "$ref_file"; then
      ok "terminal section '${terminal_heading}' present in $ref_rel"
    else
      not_ok "terminal section '${terminal_heading}' missing from $ref_rel" \
        "$skill_rel/SKILL.md requires a '${terminal_heading}' section in all execution paths"
    fi

    # Check 2: skill invocations from terminal section appear in the reference file
    if [ -n "$skill_invocations" ]; then
      while IFS= read -r invocation; do
        if grep -q "$invocation" "$ref_file"; then
          ok "skill invocation '$invocation' present in $ref_rel"
        else
          not_ok "skill invocation '$invocation' missing from $ref_rel" \
            "$skill_rel/SKILL.md terminal section invokes $invocation — reference file must too"
        fi
      done <<< "$skill_invocations"
    fi
  done < <(find "$refdir" -name "*.md" -type f | sort)

done < <(find "$SKILLS_DIR" -type d -name "references" 2>/dev/null | sort)

if [ "$found_skills" -eq 0 ]; then
  ok "no skills with references/ directories found — nothing to check"
fi

# --- Summary ---
echo ""
echo "# $PASS/$TOTAL tests passed"
if [ "$FAIL" -eq 0 ]; then
  exit 0
fi
exit 1
