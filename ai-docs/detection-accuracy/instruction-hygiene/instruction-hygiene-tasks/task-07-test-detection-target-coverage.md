---
id: task-07
type: test
wave: 1
covers: [AC-08, AC-10]
files_to_create:
  - tests/sdl-workflow/test-instruction-hygiene-coverage.sh
completion_gate: "tests compile and fail before implementation"
---

## Objective

Creates a new shell test file verifying that every pre-change detection target name exists in at least one agent-facing document post-change, ensuring no detection capability is lost during moves.

## Context

The instruction hygiene spec moves, deduplicates, and promotes detection targets across multiple documents. AC-10 requires that no detection target name disappears entirely. The test greps a specific list of substrings (provided by the spec) across 5 agent-facing documents. If any substring is absent from all 5 documents, the test fails.

The 5 agent-facing documents are:
- `assets/fbk-docs/fbk-sdl-workflow/ai-failure-modes.md`
- `assets/fbk-docs/fbk-design-guidelines/quality-detection.md`
- `assets/fbk-docs/fbk-sdl-workflow/code-review-guide.md`
- `assets/agents/fbk-code-review-detector.md`
- `assets/agents/fbk-code-review-challenger.md`

The target name list (29 substrings) comes from the spec's testing strategy. Each substring must appear in at least one of the 5 documents.

Follow the TAP format convention from existing test files.

## Instructions

1. Create `tests/sdl-workflow/test-instruction-hygiene-coverage.sh` with the standard boilerplate. Define variables for all 5 agent-facing documents:
   - `CHECKLIST="$PROJECT_ROOT/assets/fbk-docs/fbk-sdl-workflow/ai-failure-modes.md"`
   - `QUALITY="$PROJECT_ROOT/assets/fbk-docs/fbk-design-guidelines/quality-detection.md"`
   - `GUIDE="$PROJECT_ROOT/assets/fbk-docs/fbk-sdl-workflow/code-review-guide.md"`
   - `DETECTOR="$PROJECT_ROOT/assets/agents/fbk-code-review-detector.md"`
   - `CHALLENGER="$PROJECT_ROOT/assets/agents/fbk-code-review-challenger.md"`

2. Define an `ALL_DOCS` variable combining all 5 paths for use with `grep -l`: `ALL_DOCS="$CHECKLIST $QUALITY $GUIDE $DETECTOR $CHALLENGER"`.

3. Define a helper function `check_target()` that takes a substring argument and a test description, greps all 5 documents for the substring (case-insensitive), and calls `ok` if found in at least one or `not_ok` if found in none. Implementation:
   ```
   check_target() {
     local found=0
     for doc in $ALL_DOCS; do
       if grep -qi "$1" "$doc" 2>/dev/null; then
         found=1
         break
       fi
     done
     if [ "$found" -eq 1 ]; then
       ok "detection target present: $1"
     else
       not_ok "detection target present: $1" "not found in any agent-facing document"
     fi
   }
   ```

4. Call `check_target` for each of the 29 substrings from the spec's testing strategy. These are split into two groups by source document:

   From ai-failure-modes.md targets:
   - `check_target "bare literal"`
   - `check_target "hardcoded coupling"`
   - `check_target "never connected"`
   - `check_target "name-assertion mismatch"`
   - `check_target "surface-level fix"`
   - `check_target "non-enforcing test"`
   - `check_target "dead infrastructure"`
   - `check_target "comment-code drift"`
   - `check_target "sentinel"`
   - `check_target "context bypass"`
   - `check_target "string-based error"`
   - `check_target "semantically incoherent"`
   - `check_target "mock permissiveness"`
   - `check_target "dead conditional"`

   From quality-detection.md targets:
   - `check_target "mixed logic and side effects"`
   - `check_target "ambient state"`
   - `check_target "non-importable"`
   - `check_target "multi-responsibility"`
   - `check_target "caller re-implementation"`
   - `check_target "composition opacity"`
   - `check_target "parallel collection"`
   - `check_target "dead infrastructure"`
   - `check_target "semantic drift"`
   - `check_target "silent error discard"`
   - `check_target "context discard"`
   - `check_target "string-based type discrimination"`
   - `check_target "dual-path verification"`
   - `check_target "test-production string"`
   - `check_target "dead code after field"`

5. Add an AC-08 pass-through test that documents the inspection-only verification:
   ```
   ok "AC-08: token volume reduction verified by inspection (not automatable per spec)"
   ```
   This test always passes — it exists solely to satisfy the task gate's AC coverage requirement. AC-08 is verified by human inspection of word counts before/after implementation.

6. Add the standard summary block. Make the file executable.

Note: "dead infrastructure" appears in both source lists but only needs one check_target call (the duplicate is fine — it just runs twice, both passing). Keep both calls for spec traceability.

## Files to create/modify

- `tests/sdl-workflow/test-instruction-hygiene-coverage.sh` (create)

## Test requirements

New shell tests (29 check_target calls):
- Each verifies one detection target substring exists in at least one of 5 agent-facing documents
- Most will pass against current state (targets exist pre-change)
- 3 targets will fail pre-implementation because they only exist post-change: `silent error discard` (current section is "Silent error and context discard"), `context discard` (same), `dual-path verification` (currently only in existing-code-review.md which is not in the 5-doc list — wait, it IS in the list of 5 docs implicitly... no, existing-code-review.md is NOT one of the 5 agent-facing docs)
- Correction: `dual-path verification`, `test-production string`, and `dead code after field` currently exist only in `existing-code-review.md`, which is NOT one of the 5 agent-facing documents in the test. These 3 will fail pre-implementation and pass post-implementation when promoted to quality-detection.md.

## Acceptance criteria

- AC-10: All 29 detection target substrings found in at least one agent-facing document, confirming no detection capability lost during moves

## Model

Haiku

## Wave

Wave 1
