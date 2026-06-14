#!/usr/bin/env bash
# End-to-end dogfood test for the wired contracts gate (task-11, covers AC-17).
#
# Drives the assembled, real spec gate through six user-verification steps using
# throwaway sample feature directories built under a temp working area.
#
# Invocation: python3 "$DISPATCHER" spec-gate "$SPEC_PATH"
#   Exit 0 = pass, Exit 2 = fail, failures printed to stderr.
#
# Red-phase expectation (before Wave 1 module + Wave 2 wiring land):
#   UV-2, UV-3, and UV-5 would exit 0 instead of 2 — the gate would not yet
#   run the contract checks, so those fail steps would appear to pass.
#   Once the gate is assembled and wired, all six UV assertions should be green.

set -uo pipefail

PASS=0
FAIL=0
TOTAL=0

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
PROJECT_ROOT="$(cd "$SCRIPT_DIR/../.." && pwd)"
DISPATCHER="$PROJECT_ROOT/assets/fbk-scripts/fbk.py"

WORK="$(mktemp -d)"
LOG_DIR="$(mktemp -d)"
export LOG_DIR
trap 'rm -rf "$WORK" "$LOG_DIR"' EXIT

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

# ---------------------------------------------------------------------------
# run_gate STEP SPEC_BODY CONTRACTS_PAGE_BODY
#   Writes the sample-spec.md and design/contracts.md into $WORK/uv-STEP/,
#   runs the real gate, and sets RC and STDERR for the caller to inspect.
# ---------------------------------------------------------------------------
run_gate() {
  local step="$1"
  local spec_body="$2"
  local page_body="$3"

  local dir="$WORK/uv-${step}"
  mkdir -p "$dir/design"
  printf '%s' "$spec_body" > "$dir/sample-spec.md"
  printf '%s' "$page_body" > "$dir/design/contracts.md"

  STDERR="$(python3 "$DISPATCHER" spec-gate "$dir/sample-spec.md" 2>&1 >/dev/null)"
  RC=$?
}

# ---------------------------------------------------------------------------
# Reusable spec bodies — built as shell here-doc strings.
# All specs pass the existing gate checks (nine required sections, AC format,
# testing-strategy traceability, Slices block) so the only failure exercised
# per UV step is the contract check under test.
# ---------------------------------------------------------------------------

# Minimal valid spec body shared across UV steps (with one AC, one contract).
# Used as the "good" baseline for UV-1 and as the base for UV-2/3/5/6.
GOOD_SPEC_WITH_CONTRACT='# Sample Feature

## Problem

This sample feature exercises the contracts gate end-to-end in a throwaway temp directory.

## Goals

- Validate the contracts gate checks against real sample fixtures.

## User-facing behavior

Users can trigger the sample action from the dashboard toolbar.

## Technical approach

The feature adds a new validation endpoint consumed by the dashboard.

## Testing strategy

Unit tests cover the validation logic (AC-01).

## Documentation impact

No documentation changes required.

## Acceptance criteria

- **AC-01**: The validation endpoint accepts a token and returns a result.

## Dependencies

None.

## Open questions

- Should we support batch validation in a later release? Deferring keeps scope manageable.

## Slices

- name: new-contract-slice
  test-discipline: new-contract
  covers: [AC-01]

## Interface contracts

- id: IF-D-01
  name: Token validation endpoint
  signature: POST /validate
  invariants: Returns valid=true on success; returns valid=false when the token is expired or invalid.
  covers: [AC-01]
  design-ref: design/contracts.md#if-d-01
'

# Design page that carries IF-D-01 (used alongside GOOD_SPEC_WITH_CONTRACT).
DESIGN_WITH_CONTRACT='# Interface contracts

## IF-D-01 — Token validation endpoint

The token validation endpoint accepts a token and returns a boolean result.
'

# Design page with no contracts (no-contracts form).
DESIGN_NO_CONTRACT='# Interface contracts

No new or changed contracts in this feature.
'

# ---------------------------------------------------------------------------
# UV-1: real entry + matching design page → gate passes (exit 0)
# ---------------------------------------------------------------------------
run_gate "1" "$GOOD_SPEC_WITH_CONTRACT" "$DESIGN_WITH_CONTRACT"
if [ "$RC" -eq 0 ]; then
  ok "UV-1: real contract entry + matching design/contracts.md → exit 0"
else
  not_ok "UV-1: real contract entry + matching design/contracts.md → exit 0" "rc=$RC stderr=$STDERR"
fi

# ---------------------------------------------------------------------------
# UV-2: dropped contract (no exclusion) → exit 2, naming IF-D-01 and the
#        "listed in design but not carried" message with both resolution paths.
#
# Setup: use the no-contracts sentence in ## Interface contracts so the
# structure check vacuously passes, but the design anchor check sees IF-D-01
# in the design page without a matching carried or excluded entry → fails.
# ---------------------------------------------------------------------------
SPEC_UV2='# Sample Feature

## Problem

This sample feature exercises the contracts gate end-to-end in a throwaway temp directory.

## Goals

- Validate the contracts gate checks against real sample fixtures.

## User-facing behavior

Users can trigger the sample action from the dashboard toolbar.

## Technical approach

The feature adds a new validation endpoint consumed by the dashboard.

## Testing strategy

Unit tests cover the validation logic (AC-01).

## Documentation impact

No documentation changes required.

## Acceptance criteria

- **AC-01**: The validation endpoint accepts a token and returns a result.

## Dependencies

None.

## Open questions

- Should we support batch validation in a later release? Deferring keeps scope manageable.

## Slices

- name: new-contract-slice
  test-discipline: new-contract
  covers: [AC-01]

## Interface contracts

No new or changed contracts in this feature.
'

run_gate "2" "$SPEC_UV2" "$DESIGN_WITH_CONTRACT"
WANTED_SUBSTR_UV2="is listed in design/contracts.md but is not carried into ## Interface contracts"
if [ "$RC" -eq 2 ] && echo "$STDERR" | grep -qF "IF-D-01" && echo "$STDERR" | grep -qF "$WANTED_SUBSTR_UV2"; then
  ok "UV-2: dropped contract without exclusion → exit 2, names IF-D-01, carries both resolution paths"
else
  not_ok "UV-2: dropped contract without exclusion → exit 2, names IF-D-01, carries both resolution paths" "rc=$RC stderr=$STDERR"
fi

# ---------------------------------------------------------------------------
# UV-3: uncovered AC → exit 2, naming AC-02 and both resolution paths.
#
# Setup: two ACs in the spec — AC-01 covered by IF-D-01, AC-02 not covered
# and not in ## Uncovered acceptance criteria.
# ---------------------------------------------------------------------------
SPEC_UV3='# Sample Feature

## Problem

This sample feature exercises the contracts gate end-to-end in a throwaway temp directory.

## Goals

- Validate the contracts gate checks against real sample fixtures.

## User-facing behavior

Users can trigger the sample action from the dashboard toolbar.

## Technical approach

The feature adds a new validation endpoint consumed by the dashboard.

## Testing strategy

Unit tests cover the validation logic (AC-01, AC-02).

## Documentation impact

No documentation changes required.

## Acceptance criteria

- **AC-01**: The validation endpoint accepts a token and returns a result.
- **AC-02**: The endpoint logs every validation attempt.

## Dependencies

None.

## Open questions

- Should we support batch validation in a later release? Deferring keeps scope manageable.

## Slices

- name: new-contract-slice
  test-discipline: new-contract
  covers: [AC-01]

## Interface contracts

- id: IF-D-01
  name: Token validation endpoint
  signature: POST /validate
  invariants: Returns valid=true on success; returns valid=false when the token is expired or invalid.
  covers: [AC-01]
  design-ref: design/contracts.md#if-d-01
'

run_gate "3" "$SPEC_UV3" "$DESIGN_WITH_CONTRACT"
WANTED_SUBSTR_UV3="is not covered by any contract's covers: list and has no entry in ## Uncovered acceptance criteria"
if [ "$RC" -eq 2 ] && echo "$STDERR" | grep -qF "AC-02" && echo "$STDERR" | grep -qF "$WANTED_SUBSTR_UV3"; then
  ok "UV-3: uncovered AC with no Uncovered acceptance criteria entry → exit 2, names AC-02, carries both resolution paths"
else
  not_ok "UV-3: uncovered AC with no Uncovered acceptance criteria entry → exit 2, names AC-02, carries both resolution paths" "rc=$RC stderr=$STDERR"
fi

# ---------------------------------------------------------------------------
# UV-4: no-contracts sentence in spec + no-contracts design page → exit 0.
#
# The no-contracts form exempts AC coverage — even if ACs are present and
# uncovered, the gate passes vacuously (check_ac_coverage short-circuits on
# the no-contracts sentence). The design anchor check finds no IF-D-NN entries
# in the page, so there is nothing to carry or exclude.
# ---------------------------------------------------------------------------
SPEC_UV4='# Sample Feature

## Problem

This sample feature exercises the contracts gate end-to-end in a throwaway temp directory.

## Goals

- Validate the contracts gate checks against real sample fixtures.

## User-facing behavior

Users can trigger the sample action from the dashboard toolbar.

## Technical approach

The feature adds a new validation endpoint consumed by the dashboard.

## Testing strategy

Unit tests cover the validation logic (AC-01).

## Documentation impact

No documentation changes required.

## Acceptance criteria

- **AC-01**: The validation endpoint accepts a token and returns a result.

## Dependencies

None.

## Open questions

- Should we support batch validation in a later release? Deferring keeps scope manageable.

## Slices

- name: new-contract-slice
  test-discipline: new-contract
  covers: [AC-01]

## Interface contracts

No new or changed contracts in this feature.
'

run_gate "4" "$SPEC_UV4" "$DESIGN_NO_CONTRACT"
if [ "$RC" -eq 0 ]; then
  ok "UV-4: no-contracts sentence + no-contracts design page → exit 0 (vacuous pass, AC coverage exempted)"
else
  not_ok "UV-4: no-contracts sentence + no-contracts design page → exit 0 (vacuous pass, AC coverage exempted)" "rc=$RC stderr=$STDERR"
fi

# ---------------------------------------------------------------------------
# UV-5: un-named integration seam → exit 2 with heuristic seam message naming
#        both component names.
#
# Setup: ## Technical approach declares a seam "TokenValidator → AuditLogger:"
# (using the Unicode U+2192 arrow in a - [ ] checklist line). The spec's
# ## Interface contracts carries IF-D-01 but its body does not mention
# "TokenValidator" or "AuditLogger", so the heuristic seam check fires.
# ---------------------------------------------------------------------------
SPEC_UV5='# Sample Feature

## Problem

This sample feature exercises the contracts gate end-to-end in a throwaway temp directory.

## Goals

- Validate the contracts gate checks against real sample fixtures.

## User-facing behavior

Users can trigger the sample action from the dashboard toolbar.

## Technical approach

The feature integrates two internal components:

- [ ] TokenValidator → AuditLogger: every validated token triggers an audit log entry.

## Testing strategy

Unit tests cover the validation logic (AC-01).

## Documentation impact

No documentation changes required.

## Acceptance criteria

- **AC-01**: The validation endpoint accepts a token and returns a result.

## Dependencies

None.

## Open questions

- Should we support batch validation in a later release? Deferring keeps scope manageable.

## Slices

- name: new-contract-slice
  test-discipline: new-contract
  covers: [AC-01]

## Interface contracts

- id: IF-D-01
  name: Token validation endpoint
  signature: POST /validate
  invariants: Returns valid=true on success; returns valid=false when the token is expired or invalid.
  covers: [AC-01]
  design-ref: design/contracts.md#if-d-01
'

run_gate "5" "$SPEC_UV5" "$DESIGN_WITH_CONTRACT"
WANTED_SUBSTR_UV5="This is a heuristic check"
if [ "$RC" -eq 2 ] && echo "$STDERR" | grep -qF "$WANTED_SUBSTR_UV5" && echo "$STDERR" | grep -qF "TokenValidator" && echo "$STDERR" | grep -qF "AuditLogger"; then
  ok "UV-5: un-named integration seam → exit 2 with heuristic message naming both components"
else
  not_ok "UV-5: un-named integration seam → exit 2 with heuristic message naming both components" "rc=$RC stderr=$STDERR"
fi

# ---------------------------------------------------------------------------
# UV-6: dropped contract moved to ## Excluded contracts with rationale → exit 0.
#
# Same setup as UV-2 (no IF-D-01 in ## Interface contracts, no-contracts
# sentence used) but now ## Excluded contracts carries an IF-D-01 entry with
# a non-empty rationale. The design anchor check sees IF-D-01 in excluded →
# not missing → passes.
# ---------------------------------------------------------------------------
SPEC_UV6='# Sample Feature

## Problem

This sample feature exercises the contracts gate end-to-end in a throwaway temp directory.

## Goals

- Validate the contracts gate checks against real sample fixtures.

## User-facing behavior

Users can trigger the sample action from the dashboard toolbar.

## Technical approach

The feature adds a new validation endpoint consumed by the dashboard.

## Testing strategy

Unit tests cover the validation logic (AC-01).

## Documentation impact

No documentation changes required.

## Acceptance criteria

- **AC-01**: The validation endpoint accepts a token and returns a result.

## Dependencies

None.

## Open questions

- Should we support batch validation in a later release? Deferring keeps scope manageable.

## Slices

- name: new-contract-slice
  test-discipline: new-contract
  covers: [AC-01]

## Interface contracts

No new or changed contracts in this feature.

## Excluded contracts

- id: IF-D-01
  rationale: Deferred to a later release; the token validation boundary is not in scope for this feature.
'

run_gate "6" "$SPEC_UV6" "$DESIGN_WITH_CONTRACT"
if [ "$RC" -eq 0 ]; then
  ok "UV-6: dropped contract moved to Excluded contracts with rationale → exit 0"
else
  not_ok "UV-6: dropped contract moved to Excluded contracts with rationale → exit 0" "rc=$RC stderr=$STDERR"
fi

# ---------------------------------------------------------------------------
# Summary
# ---------------------------------------------------------------------------
echo ""
echo "# $PASS/$TOTAL tests passed"
echo "1..$TOTAL"
[ "$FAIL" -gt 0 ] && exit 1
exit 0
