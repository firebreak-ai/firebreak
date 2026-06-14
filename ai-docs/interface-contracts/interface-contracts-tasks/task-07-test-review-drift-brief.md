---
id: task-07
type: test
wave: 1
covers: [AC-16]
files_to_create:
  - tests/sdl-workflow/test-review-drift-brief.sh
completion_gate: "tests compile and fail before implementation (red phase before the review-perspectives.md architecture-reviewer brief edit exists)"
---

# task-07 — Test the architecture-reviewer contract-drift brief

## 1. Objective

Produces `tests/sdl-workflow/test-review-drift-brief.sh`: a TAP-style shell test verifying that `review-perspectives.md`'s architecture-reviewer brief carries the three contract-drift conditions as informational findings.

## 2. Context

Test task for the `review-drift-brief` slice (new-contract discipline). The paired implementation task (task-08) edits `assets/fbk-docs/fbk-sdl-workflow/review-perspectives.md` to extend the architecture reviewer's brief. The edit does not exist yet — this test compiles and FAILS (red phase) until it does.

The three drift conditions the brief must carry, reported as informational findings (disposition left to the operator):

1. A spec-added `IF-S-NN` contract that is absent from design.
2. An `IF-D-NN` entry whose identifier is preserved but whose name or signature has materially changed.
3. A count/name mismatch between the design page's `IF-D-NN` entries and what the spec carries or excludes.

These are reviewer *behaviors*, not deterministic interfaces — so the test checks the brief carries the conditions, not that drift is detected. Per test-authoring discipline, assert on anchored structural markers and the load-bearing identifier tokens (`IF-S-`, `IF-D-`, and "informational"), not on incidental body vocabulary.

Convention to follow: `tests/sdl-workflow/test-instruction-hygiene-coverage.sh` — PROJECT_ROOT from `BASH_SOURCE`, `ok`/`not_ok` helpers, `grep -q`, `1..$TOTAL`, non-zero exit on failure.

## 3. Instructions

1. Create `tests/sdl-workflow/test-review-drift-brief.sh`, `chmod +x`, `set -euo pipefail`.
2. `PROJECT_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"`.
3. Define `BRIEF="$PROJECT_ROOT/assets/fbk-docs/fbk-sdl-workflow/review-perspectives.md"`.
4. Copy the `ok`/`not_ok` TAP helpers.
5. Write the assertions in §5. Let them fail naturally when the brief edit is absent (red phase).
6. Emit `echo "1..$TOTAL"`; `exit 1` when `FAIL > 0`.
7. Run the test and confirm it FAILS (the brief edit is not yet made) — red phase.

## 4. Files to create/modify

- Create: `tests/sdl-workflow/test-review-drift-brief.sh`

Do not modify any other file. (The brief edit is made by task-08.)

## 5. Test requirements

Shell integration test, TAP style, asserting against the source file `assets/fbk-docs/fbk-sdl-workflow/review-perspectives.md`.

Instruction-hygiene (AC-16):

- The brief carries the spec-added-contract-absent-from-design condition — grep for the `IF-S-` token together with a structural marker placing it in the architecture-reviewer brief (e.g. an anchored heading or list-item for contract drift). Pair with a presence check.
- The brief carries the preserved-identifier-but-changed-name/signature condition — grep for the `IF-D-` token alongside a marker for name/signature change.
- The brief carries the count/name mismatch condition — grep for a mismatch marker between the design page's entries and what the spec carries or excludes.
- The brief frames all three as informational — grep for the literal `informational` (the conditions are reported informationally, with disposition left to the operator). Pair with a presence check.

Use three distinct assertions for the three conditions plus one for the informational framing, so a partial edit (one condition added, two missing) fails. Prefer anchored structural markers (the drift-brief heading or bullet structure) over loose body vocabulary where the brief provides one.

## 6. Acceptance criteria

- Covers AC-16.
- Three drift conditions each have their own assertion; the informational framing has its own assertion.
- Test FAILS before task-08 edits the brief (red phase).

## 7. Model

Haiku

## 8. Wave

Wave 1
