---
id: task-02
type: test
wave: 1
covers: [AC-03]
files_to_create:
  - tests/sdl-workflow/test-challenger-persona.sh
completion_gate: "bash tests/sdl-workflow/test-challenger-persona.sh exits 0"
---

## Objective

Create a TAP-style bash test that validates the Challenger agent definition contains the mistrustful persona, independent verification requirement, design intent awareness, reclassification with matrix validation, and nit rejection.

## Context

The Challenger agent at `assets/agents/fbk-code-review-challenger.md` is being rewritten to a persona-driven definition. The new definition must contain:
- A senior engineer persona that is mistrustful of secondhand descriptions
- Independent verification: reads code itself, traces values, checks caller expectations
- Requirement to describe failing input in the Challenger's own words, not the Detector's
- Design intent awareness for verification and rejection decisions
- Reclassification with type-severity matrix validation
- Nit rejection as a distinct outcome (rejected-as-nit)
- JSON verdict fields: status, verification_evidence, rejection_reason, reclassified_from

## Instructions

Create `tests/sdl-workflow/test-challenger-persona.sh` following the TAP test pattern in `tests/sdl-workflow/test-code-review-structural.sh` (boilerplate, helpers, TAP header, summary).

Define variables:
```bash
SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
PROJECT_ROOT="$(cd "$SCRIPT_DIR/../.." && pwd)"
CHALLENGER="$PROJECT_ROOT/assets/agents/fbk-code-review-challenger.md"
```

Extract the body:
```bash
body=$(awk '/^---$/{c++; if(c==2){found=1; next}} found' "$CHALLENGER")
```

Implement these tests:

**Test 1: Challenger contains mistrustful persona language**
Grep body for `mistrustful` (case-insensitive).

**Test 2: Challenger requires independent code reading**
Grep body for `reading the code yourself` or `read.*code.*yourself` (case-insensitive).

**Test 3: Challenger requires own words, not Detector's**
Grep body for `your own words` or `not the Detector` (case-insensitive).

**Test 4: Challenger cannot reproduce reasoning means reject**
Grep body for `cannot.*reproduce.*reject` or `cannot independently reproduce` (case-insensitive).

**Test 5: Challenger keeps design intent in mind**
Grep body for `design intent` (case-insensitive).

**Test 6: Challenger traces callers for behavioral sightings**
Grep body for `behavioral.*caller` or `caller.*behavioral` or `trace.*caller` (case-insensitive).

**Test 7: Challenger reclassifies with matrix validation**
Grep body for `reclassif` combined with `matrix` in the body (both must appear, not necessarily on the same line). Test: `echo "$body" | grep -qi 'reclassif' && echo "$body" | grep -qi 'matrix'`.

**Test 8: Challenger rejects nits as functionally irrelevant**
Grep body for `nit` combined with `functionally irrelevant` or `naming.*formatting.*style` (case-insensitive).

**Test 9: Challenger description field contains evidence/proof language**
Extract frontmatter description. Grep for `proof` or `evidence` or `demands` (case-insensitive).

**Test 10: Challenger body references verified and rejected outcomes**
Grep body for both `Verified` and `Rejected` (case-sensitive, as section headers or bold items).

End with the standard summary block.

## Files to create/modify

Create: `tests/sdl-workflow/test-challenger-persona.sh` (make executable)

## Test requirements

Executable, exits 0 on all pass / 1 on any fail. Grep-based only.

## Acceptance criteria

- 10 TAP tests covering mistrustful persona, independent verification (3 tests), design intent, caller tracing, reclassification + matrix, nit rejection, description field, verified/rejected outcomes
- Follows existing test suite conventions exactly
- All tests grep against `assets/agents/fbk-code-review-challenger.md`

## Model

sonnet

## Wave

1
