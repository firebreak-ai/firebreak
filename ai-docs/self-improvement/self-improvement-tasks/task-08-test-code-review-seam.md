---
id: T-08
type: test
wave: 3
covers: [AC-01]
depends_on: [T-04]
files_to_modify: [tests/sdl-workflow/test-code-review-integration.sh]
completion_gate: "Test script runs with new assertion; assertion fails until T-06 applies the transition instruction"
---

## Objective

Adds an assertion to the existing code review integration test validating that the code review skill contains the `/fbk-improve` transition instruction, completing the automatic invocation seam contract.

## Context

`tests/sdl-workflow/test-code-review-integration.sh` validates structural integrity of the code review skill and its referenced assets. The self-improvement feature adds a transition instruction to the code review skill's Retrospective section. This task adds the assertion that validates the transition exists.

The spec's "Existing tests impacted" section identifies this change. Follow the existing assertion pattern in the test file.

## Instructions

1. Read `tests/sdl-workflow/test-code-review-integration.sh` to understand the existing assertion pattern.
2. Add an assertion after the existing assertions that validates:
   - The code review skill file contains a reference to `/fbk-improve` or `fbk-improve`
   - The reference appears in the context of retrospective finalization (search for the pattern near "retrospective" content)
3. Use the same `grep -q` + `ok`/`not_ok` pattern as existing assertions.
4. Update the expected test count if the file tracks it.

## Files to create/modify

- Modify: `tests/sdl-workflow/test-code-review-integration.sh`

## Test requirements

This IS the test task. It validates:
- AC-01: The automatic invocation seam — code review skill transitions to `/fbk-improve` after retrospective finalization

## Acceptance criteria

- AC-01: Existing code review integration test includes assertion for `/fbk-improve` transition

## Model

Haiku

## Wave

Wave 3
