---
id: task-03
type: test
wave: 1
covers: [AC-08]
files_to_create:
  - tests/sdl-workflow/test-guide-precision-alignment.sh
completion_gate: "bash tests/sdl-workflow/test-guide-precision-alignment.sh exits 0"
---

## Objective

Create a TAP-style bash test that validates the code review guide contains consequence-based type definitions, observability-based severity definitions, JSON schema references, unified finding format with `reclassified_from`, and the updated orchestration protocol with pipeline.py integration.

## Context

The code review guide at `assets/fbk-docs/fbk-sdl-workflow/code-review-guide.md` is being updated to align with the new Detector/Challenger definitions. The updated guide must:
- Replace pattern-shape type definitions with consequence-based definitions from the Detector
- Replace subjective-risk severity definitions with observability-based definitions
- Reference the JSON sighting schema (replacing the markdown template)
- Document the unified finding format where findings are sightings with Challenger verdict fields added (status, verification_evidence, reclassified_from)
- Update the orchestration protocol to reflect JSON-throughout pipeline with `pipeline.py` invocation
- Document the type-severity validity matrix

## Instructions

Create `tests/sdl-workflow/test-guide-precision-alignment.sh` following the TAP pattern in `tests/sdl-workflow/test-code-review-structural.sh`.

Define variables:
```bash
SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
PROJECT_ROOT="$(cd "$SCRIPT_DIR/../.." && pwd)"
GUIDE="$PROJECT_ROOT/assets/fbk-docs/fbk-sdl-workflow/code-review-guide.md"
```

Implement these tests:

**Test 1: Guide type definitions use consequence-based language for behavioral**
Grep for `behavioral` combined with `concrete` or `constructible input` (case-insensitive). The old definition used "does something different from what its name, documentation, or spec says" — the new one must reference concrete constructible inputs.

**Test 2: Guide type definitions use consequence-based language for structural**
Grep for `structural` combined with `no wrong output` or `no.*observable output` (case-insensitive).

**Test 3: Guide type definitions use consequence-based language for fragile**
Grep for `fragile` combined with `specific.*change` or `plausible change` (case-insensitive).

**Test 4: Guide severity definitions use observability language for critical**
Grep for `critical` combined with `next user` or `primary path` (case-insensitive).

**Test 5: Guide severity definitions use observability language for major**
Grep for `major` combined with `write a test` or `demonstrates the failure` or `constructible` (case-insensitive).

**Test 6: Guide severity definitions use observability language for minor**
Grep for `minor` combined with `code reading` (case-insensitive).

**Test 7: Guide references JSON sighting schema**
Grep for `JSON` combined with `schema` or `sighting` (case-insensitive). The old guide had a markdown template block; the new one references JSON.

**Test 8: Guide documents reclassified_from field**
Grep for `reclassified_from` (exact string).

**Test 9: Guide documents verification_evidence field**
Grep for `verification_evidence` (exact string).

**Test 10: Guide documents type-severity validity matrix**
Grep for `matrix` or `validity matrix` (case-insensitive).

**Test 11: Guide orchestration protocol references pipeline.py**
Extract the Orchestration Protocol section using `sed -n '/## Orchestration Protocol/,/^## /p' "$GUIDE"`. Grep this section for `pipeline.py` or `uv run`.

**Test 12: Guide orchestration protocol references JSON as working format**
Grep the Orchestration Protocol section for `JSON` (case-sensitive).

**Test 13: Guide does not contain old pattern-shape type definition language**
Grep for the old definition `does something different from what its name` (case-insensitive). Test passes if this grep does NOT match.

**Test 14: Guide does not contain old severity definition "significant risk under realistic conditions"**
Grep for `significant risk under realistic conditions` (case-insensitive). Test passes if this grep does NOT match.

End with standard summary block.

## Files to create/modify

Create: `tests/sdl-workflow/test-guide-precision-alignment.sh` (make executable)

## Test requirements

Executable, exits 0/1. Grep-based only.

## Acceptance criteria

- 14 TAP tests: 3 consequence-based type definitions, 3 observability severity definitions, JSON schema reference, reclassified_from, verification_evidence, validity matrix, orchestration pipeline.py, orchestration JSON, 2 negative tests for old language removal
- Follows existing test suite conventions
- All tests grep against `assets/fbk-docs/fbk-sdl-workflow/code-review-guide.md`

## Model

sonnet

## Wave

1
