---
id: task-01
type: test
wave: 1
covers: [AC-02, AC-04, AC-05, AC-07]
files_to_create:
  - tests/sdl-workflow/test-detector-persona.sh
completion_gate: "bash tests/sdl-workflow/test-detector-persona.sh exits 0"
---

## Objective

Create a TAP-style bash test that validates the Detector agent definition contains the persona, output quality bar, consequence-based type definitions, observability-based severity definitions, and mechanism-first wording instruction.

## Context

The Detector agent at `assets/agents/fbk-code-review-detector.md` is being rewritten from a procedural definition to a persona-driven definition. The new definition must contain:
- A staff engineer persona identity
- An output quality bar requiring mechanism, concrete failing input, and caller impact
- Consequence-based type definitions (behavioral, structural, test-integrity, fragile)
- Observability-based severity definitions (critical, major, minor, info)
- A reference to the type-severity validity matrix
- Mechanism-first wording embedded in the output quality bar (not a separate instruction)

## Instructions

Create `tests/sdl-workflow/test-detector-persona.sh` following the TAP test pattern used in existing tests (see `tests/sdl-workflow/test-code-review-structural.sh` for the exact boilerplate: `set -uo pipefail`, PASS/FAIL/TOTAL counters, `ok()`/`not_ok()` helpers, `echo "TAP version 13"` header, summary block with `1..$TOTAL` and exit code).

Define these variables at the top:
```bash
SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
PROJECT_ROOT="$(cd "$SCRIPT_DIR/../.." && pwd)"
DETECTOR="$PROJECT_ROOT/assets/agents/fbk-code-review-detector.md"
```

Extract the Detector body (everything after the second `---` line) into a variable using:
```bash
body=$(awk '/^---$/{c++; if(c==2){found=1; next}} found' "$DETECTOR")
```

Implement these tests:

**Test 1: Detector contains staff engineer persona identity**
Grep the body for `staff engineer` (case-insensitive). This confirms the persona activates the senior engineering review distribution.

**Test 2: Detector output quality bar requires mechanism**
Grep the body for `mechanism` (case-insensitive). The quality bar must require each sighting to demonstrate the mechanism.

**Test 3: Detector output quality bar requires concrete failing input**
Grep the body for `failing input` (case-insensitive). The quality bar must require a concrete failing input for each sighting.

**Test 4: Detector output quality bar requires caller impact**
Grep the body for `caller impact` (case-insensitive). The quality bar must require caller impact for each sighting.

**Test 5: Detector contains behavioral type definition with concrete input language**
Grep the body for a pattern matching `behavioral` near `concrete` or `constructible` (case-insensitive, within 200 chars). Use: `echo "$body" | grep -qiP 'behavioral.*(?:concrete|constructible)|(?:concrete|constructible).*behavioral'`. If `grep -P` is unavailable, grep separately for `behavioral` and `constructible input` in the body, requiring both.

**Test 6: Detector contains structural type definition**
Grep the body for `structural` combined with `no wrong output` or `maintain` (case-insensitive). Use: `echo "$body" | grep -qiE 'structural.*(no wrong output|maintain)|maintain.*structural'`. Accept if either pair matches.

**Test 7: Detector contains test-integrity type definition**
Grep the body for `test-integrity` combined with `passes but` or `does not verify` or `claims` (case-insensitive).

**Test 8: Detector contains fragile type definition with specific change language**
Grep the body for `fragile` combined with `specific.*change` or `plausible change` (case-insensitive).

**Test 9: Detector contains critical severity definition with observability language**
Grep the body for `critical` combined with `next user` or `primary path` (case-insensitive).

**Test 10: Detector contains major severity definition with observability language**
Grep the body for `major` combined with `write a test` or `demonstrates the failure` or `constructible` (case-insensitive).

**Test 11: Detector contains minor severity definition with code-reading-only language**
Grep the body for `minor` combined with `code reading` (case-insensitive).

**Test 12: Detector references type-severity validity matrix**
Grep the body for `matrix` or `type-severity` (case-insensitive).

**Test 13: Detector does not contain separate mechanism-first wording instruction**
Confirm mechanism-first is embedded in the quality bar, not a separate section. Grep the body for a `## Mechanism` section heading: `echo "$body" | grep -q '^## Mechanism'`. The test passes if this grep does NOT match (exit code != 0). This confirms mechanism-first wording is embedded in the persona, not separated.

**Test 14: Detector contains nit exclusion instruction**
Grep the body for `exclude nits` or `Exclude nits` (case-insensitive).

End with the standard summary block.

## Files to create/modify

Create: `tests/sdl-workflow/test-detector-persona.sh` (make executable with `chmod +x`)

## Test requirements

The test file must be executable (`chmod +x`). It must exit 0 when all tests pass and exit 1 when any test fails. All tests use grep against the file content — no LLM involvement, no network calls.

## Acceptance criteria

- 14 TAP tests covering persona identity, output quality bar (3 elements), 4 type definitions with consequence-based language, 4 severity definitions with observability-based language, matrix reference, mechanism-first embedding confirmation, and nit exclusion
- Test file follows existing test suite conventions exactly (boilerplate, helpers, summary)
- All tests are grep-based content validation against `assets/agents/fbk-code-review-detector.md`

## Model

sonnet

## Wave

1
