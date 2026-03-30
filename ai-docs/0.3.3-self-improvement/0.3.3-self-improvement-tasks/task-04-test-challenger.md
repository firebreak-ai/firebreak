---
id: task-04
type: test
wave: 1
covers: [AC-13, AC-14, AC-15]
files_to_create:
  - tests/sdl-workflow/test-challenger-extensions.sh
completion_gate: "tests compile and fail before implementation"
---

## Objective

Creates `tests/sdl-workflow/test-challenger-extensions.sh` — a structural test suite validating the Challenger agent's new capabilities: adjacent observation channel, caller tracing requirement, and verified-pending-execution status.

## Context

Three new capabilities are added to `fbk-code-review-challenger.md`:

- AC-13: "Adjacent observation" channel — related issues the Challenger notes without generating new sightings. The orchestrator appends them to the retrospective as informational items. They do not feed back into the detection loop or surface as findings.
- AC-14: Cross-reference caller tracing requirement for `behavioral` type sightings — the Challenger must trace callers to verify behavioral claims.
- AC-15: `verified-pending-execution` status for `test-integrity` type sightings that require test execution to confirm — the Challenger cannot verify them from code reading alone.

Current state of `fbk-code-review-challenger.md`: The file has three sections after frontmatter — verification protocol, "Downgrade to nit" (being replaced by AC-59 in task-02), and scope discipline. None of the three new capabilities exist yet.

Follow the TAP format from existing test files.

## Instructions

1. Create `tests/sdl-workflow/test-challenger-extensions.sh` with shebang and `set -uo pipefail`.

2. Add standard boilerplate. Define:
   - `CHALLENGER="$PROJECT_ROOT/assets/agents/fbk-code-review-challenger.md"`

3. Add the following tests:

   **Test 1: Challenger contains "adjacent observation" keyword (AC-13)**
   Grep case-insensitively for `adjacent observation` in `$CHALLENGER`. Use: `grep -qi 'adjacent observation' "$CHALLENGER"`. Test name: "Challenger includes adjacent observation channel".

   **Test 2: Adjacent observations do not surface as findings (AC-13)**
   Grep for language indicating adjacent observations are informational and excluded from findings. Use: `grep -qiE 'informational|do not.*finding|not.*surface|not.*detection loop|exclude.*finding' "$CHALLENGER"`. Test name: "Adjacent observations documented as informational".

   **Test 3: Challenger contains caller tracing requirement (AC-14)**
   Grep case-insensitively for `caller trac` or `cross-reference.*caller` or `trace.*caller` in `$CHALLENGER`. Use: `grep -qiE 'caller.trac|trace.*caller|cross.reference.*caller' "$CHALLENGER"`. Test name: "Challenger includes caller tracing requirement".

   **Test 4: Caller tracing applies to behavioral type (AC-14)**
   Grep for `behavioral` appearing near `caller` or `trac` in `$CHALLENGER`. Use: `grep -qiE 'behavioral.*caller|behavioral.*trac|caller.*behavioral' "$CHALLENGER"`. Test name: "Caller tracing scoped to behavioral type".

   **Test 5: Challenger contains verified-pending-execution status (AC-15)**
   Grep case-insensitively for `verified-pending-execution` or `verified.pending.execution` in `$CHALLENGER`. Use: `grep -qiE 'verified.pending.execution' "$CHALLENGER"`. Test name: "Challenger includes verified-pending-execution status".

   **Test 6: Verified-pending-execution applies to test-integrity type (AC-15)**
   Grep for `test-integrity` appearing near `pending` or `execution` in `$CHALLENGER`. Use: `grep -qiE 'test.integrity.*pending|test.integrity.*execution|pending.*test.integrity' "$CHALLENGER"`. Test name: "Verified-pending-execution scoped to test-integrity type".

4. Add standard summary footer.

5. Make the file executable.

## Files to create/modify

- `tests/sdl-workflow/test-challenger-extensions.sh` (create)

## Test requirements

6 structural tests covering AC-13, AC-14, AC-15. Each AC gets two tests: one for keyword presence and one for correct scoping. Tests must fail before implementation.

## Acceptance criteria

- AC-13: Tests 1-2 verify adjacent observation channel exists and is documented as informational.
- AC-14: Tests 3-4 verify caller tracing exists and is scoped to behavioral type.
- AC-15: Tests 5-6 verify verified-pending-execution status exists and is scoped to test-integrity type.

## Model

Haiku

## Wave

Wave 1
