---
id: task-01
type: test
wave: 1
covers: [AC-01, AC-02, AC-03, AC-04, AC-05, AC-06]
files_to_create:
  - tests/sdl-workflow/test-skill-guide-dedup.sh
completion_gate: "test file exists, is syntactically valid bash (passes shellcheck or bash -n), and at least one assertion fails before implementation begins (proves the test is not vacuously passing)"
---

## Objective

Produce `tests/sdl-workflow/test-skill-guide-dedup.sh`, a TAP-format shell test with 22 numbered assertions (T1, T1b, T2, T3, T4, T4b, T5, T5b, T6, T7, T8, T9, T9b, T10, T11a, T11b, T11c, T11d, T12, T13, T14, T15) that grep three SDL skill files and three SDL workflow guide files for sentinel phrases. The test asserts duplicated workflow prose has been removed from the skills, operational glue remains in the skills, and the equivalent prose lives in the guides.

## Context

This is the sole structural verification artifact for the SDL skill/guide dedup refactor. The refactor removes duplicated workflow prose from three skill files (`assets/skills/fbk-spec/SKILL.md`, `assets/skills/fbk-spec-review/SKILL.md`, `assets/skills/fbk-implement/SKILL.md`), adds two transition steps to two guides (`feature-spec-guide.md` §"Transition", `review-perspectives.md` §"Transition"), and removes one env-flag prerequisite line from `implementation-guide.md`.

The test is auto-discovered by CI via the existing `tests/sdl-workflow/test-*.sh` glob. Each assertion fits in a single shell line using `grep -q` (positive) or `! grep -q` (negative) and emits a TAP `ok` / `not ok` line. The assertions are independent and fast (<1 second total).

**Negative assertions (T1, T1b, T2, T3, T4, T4b, T5, T5b, T6, T11d) MUST FAIL on the current codebase before the refactor implementation lands** — the duplicated prose is still present in the skills and the env-flag line is still present in the guide. This is the gate that proves the test is not vacuously passing.

**Positive assertions for guide-side additive transition steps (the `Before invoking ` substrings inside T11a and T11b) will also fail before the refactor**, because those transition steps do not yet exist in the guides; they are added as part of the refactor. This is correct: the test fails before the refactor and passes after.

Other positive assertions (T7, T8, T9, T9b, T10, T12, T13, T14, T15, the non-additive parts of T11a/T11b/T11c) verify operational glue and existing guide content; they should pass on the current codebase as well as post-refactor.

Use `tests/sdl-workflow/test-implementation-pipeline.sh` as the boilerplate template — it sets `set -uo pipefail`, declares `PASS`, `FAIL`, `TOTAL`, defines `ok()` and `not_ok()` helpers, prints `TAP version 13`, and ends with `1..$TOTAL` plus a summary that exits 1 on any failure.

Resolve all file paths relative to `PROJECT_ROOT` computed as `"$(cd "$(dirname "$0")/../.." && pwd)"`. Do not use `cd` inside the test — pass full paths to grep.

## Instructions

1. Create the file `tests/sdl-workflow/test-skill-guide-dedup.sh` with execute permission (`chmod +x` after creation; if your environment cannot chmod, add a note in the task summary — the CI runner may handle this).

2. Open with the canonical TAP boilerplate matching `test-implementation-pipeline.sh`:

   ```bash
   #!/usr/bin/env bash
   set -uo pipefail

   PASS=0
   FAIL=0
   TOTAL=0

   SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
   PROJECT_ROOT="$(cd "$SCRIPT_DIR/../.." && pwd)"

   SPEC_SKILL="$PROJECT_ROOT/assets/skills/fbk-spec/SKILL.md"
   REVIEW_SKILL="$PROJECT_ROOT/assets/skills/fbk-spec-review/SKILL.md"
   IMPL_SKILL="$PROJECT_ROOT/assets/skills/fbk-implement/SKILL.md"
   SPEC_GUIDE="$PROJECT_ROOT/assets/fbk-docs/fbk-sdl-workflow/feature-spec-guide.md"
   REVIEW_GUIDE="$PROJECT_ROOT/assets/fbk-docs/fbk-sdl-workflow/review-perspectives.md"
   IMPL_GUIDE="$PROJECT_ROOT/assets/fbk-docs/fbk-sdl-workflow/implementation-guide.md"

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
   ```

3. Emit each of the 22 assertions below, in order, as an `if ... then ok ... else not_ok ... fi` block. Each block uses `grep -q` (or `grep -qF` for fixed-string matching when the phrase contains shell metacharacters such as backticks) against the variable for the target file. Use `grep -F` (fixed-string) for every assertion below — none of these are regexes, and `-F` avoids accidental metacharacter interpretation in phrases like `Step 1 — Test tasks`, `/spec-review $ARGUMENTS`, and the backtick-wrapped `` `/spec-review` ``.

   Assertion list (each entry: T-id, AC, semantic intent, target file, grep argument literal, assertion direction):

   - **T1 (AC-01)** — skill does NOT contain duplicated gate-fail prose.
     File: `$SPEC_SKILL`. Pattern: `If the gate fails:`. Direction: negative — assertion passes when `grep -qF 'If the gate fails:' "$SPEC_SKILL"` returns non-zero.

   - **T1b (AC-01)** — skill does NOT contain duplicated gate-pass narrative.
     File: `$SPEC_SKILL`. Pattern: `Verify that the testing strategy enumerates all callers`. Direction: negative.

   - **T2 (AC-01)** — skill does NOT contain duplicated authoring-loop prose.
     File: `$SPEC_SKILL`. Pattern: `Refuse to write code`. Direction: negative.

   - **T3 (AC-02)** — skill does NOT contain duplicated threat-model decision flow.
     File: `$REVIEW_SKILL`. Pattern: `Does this feature need a threat model?`. Direction: negative.

   - **T4 (AC-02)** — skill does NOT contain duplicated transition decision tree.
     File: `$REVIEW_SKILL`. Pattern: `There are N blocking findings`. Direction: negative.

   - **T4b (AC-02)** — skill does NOT contain duplicated classification rationale-presentation prose.
     File: `$REVIEW_SKILL`. Pattern: `Present the selection with`. Direction: negative.

   - **T5 (AC-03)** — skill does NOT contain duplicated wave-loop step headings. Two sub-checks; assertion passes only if BOTH are absent.
     File: `$IMPL_SKILL`. Patterns (both must be absent): `Step 1 — Test tasks` AND `Step 2 — Test compilation check`. Direction: negative for both. Implement as a compound test: `if ! grep -qF '...' && ! grep -qF '...'; then ok ... else not_ok ... fi`.

   - **T5b (AC-03)** — skill does NOT contain duplicated step-2 narrative.
     File: `$IMPL_SKILL`. Pattern: `Tests are expected to fail`. Direction: negative.

   - **T6 (AC-03)** — skill does NOT contain duplicated escalation cap.
     File: `$IMPL_SKILL`. Pattern: `Cap: 2 escalation attempts per task`. Direction: negative.

   - **T7 (AC-04)** — skill DOES contain operational env-flag check.
     File: `$IMPL_SKILL`. Pattern: `CLAUDE_CODE_EXPERIMENTAL_AGENT_TEAMS`. Direction: positive.

   - **T8 (AC-04)** — skill DOES contain operational spawn-prompt template marker.
     File: `$IMPL_SKILL`. Pattern: `Task file:`. Direction: positive.

   - **T9 (AC-04)** — review skill DOES contain three operational sentinels (council invocation, test-reviewer spawn, finding-synthesis testing-strategy keyword). All three must be present; assertion passes only if all three greps succeed.
     File: `$REVIEW_SKILL`. Patterns (all must be present): `/fbk-council` AND `test-reviewer` AND `testing strategy`. Direction: positive for all three. Implement as a compound test: `if grep -qF '/fbk-council' && grep -qF 'test-reviewer' && grep -qF 'testing strategy'; then ok ... else not_ok ... fi`.

   - **T9b (AC-04)** — implement skill DOES contain operational exit-prompt sentinel (load-bearing for `test-code-review-skill.sh` Tests 15-16).
     File: `$IMPL_SKILL`. Pattern: `review the implementation with /code-review`. Direction: positive.

   - **T10 (AC-04)** — each skill DOES contain its respective gate-script command substring. Three sub-checks.
     File `$SPEC_SKILL`: pattern `spec-gate`. File `$REVIEW_SKILL`: pattern `review-gate`. File `$IMPL_SKILL`: pattern `breakdown-gate`. All positive. Implement as a compound test: `if grep -qF 'spec-gate' "$SPEC_SKILL" && grep -qF 'review-gate' "$REVIEW_SKILL" && grep -qF 'breakdown-gate' "$IMPL_SKILL"; then ok ... else not_ok ... fi`.

   - **T11a (AC-01)** — feature-spec-guide DOES contain three guide-side sentinels paired with T1, T2, and the §4.3a additive transition step.
     File: `$SPEC_GUIDE`. Patterns (all must be present): `If the gate fails:` AND `Refuse to write code` AND `` Before invoking `/spec-review` ``. Direction: positive for all three. The third pattern includes literal backticks; use `grep -qF` with single quotes around the pattern (e.g., `grep -qF 'Before invoking `/spec-review`' "$SPEC_GUIDE"`). Implement as a compound test.

   - **T11b (AC-02)** — review-perspectives guide DOES contain four guide-side sentinels paired with T3, T4, T4b, and the §4.3a additive transition step.
     File: `$REVIEW_GUIDE`. Patterns (all must be present): `Does this feature need a threat model?` AND `There are N blocking findings` AND `Present the classification with` AND `` Before invoking `/breakdown` ``. Direction: positive for all four. Use `grep -qF` with single quotes for each. Implement as a compound test.

   - **T11c (AC-03)** — implementation-guide DOES contain three guide-side sentinels paired with T5, T6, and the final-verification structural list.
     File: `$IMPL_GUIDE`. Patterns (all must be present): `Step 1 — Test tasks` AND `Cap: 2 escalation attempts per task` AND `No dead code introduced`. Direction: positive for all three. Implement as a compound test.

   - **T11d (AC-03 / AC-04)** — implementation-guide does NOT contain the env-flag string (consolidated to skill-side per §4.3a).
     File: `$IMPL_GUIDE`. Pattern: `CLAUDE_CODE_EXPERIMENTAL_AGENT_TEAMS`. Direction: negative.

   - **T12 (AC-04)** — each skill opens with `---` and contains a `description:` field within frontmatter. Six sub-checks.
     For each of `$SPEC_SKILL`, `$REVIEW_SKILL`, `$IMPL_SKILL`: assert that the first line is exactly `---` (use `head -n 1 "$FILE"` and string-compare to `---`) AND that the file contains `description:` (use `grep -qF 'description:' "$FILE"`). Implement as one compound test that ANDs all six conditions; emit a single ok/not_ok with label "T12 — frontmatter operational glue preserved across all three skills".

   - **T13 (AC-04)** — argument-resolution operational glue. Three sub-checks.
     File `$SPEC_SKILL`: pattern `$ARGUMENTS` (use `grep -qF '$ARGUMENTS' "$SPEC_SKILL"` — single quotes prevent shell expansion of `$ARGUMENTS`). File `$REVIEW_SKILL`: pattern `$ARGUMENTS`. File `$IMPL_SKILL`: pattern `FEATURE=$ARGUMENTS`. All positive. Implement as a compound test.

   - **T14 (AC-04)** — chained-skill invocation operational glue. Two sub-checks.
     File `$SPEC_SKILL`: pattern `/spec-review $ARGUMENTS` (use `grep -qF` with single quotes). File `$REVIEW_SKILL`: pattern `/breakdown`. Both positive. Implement as a compound test.

   - **T15 (AC-04)** — exit-prompt operational glue. Two sub-checks.
     File `$SPEC_SKILL`: pattern `Would you like to move to spec review?`. File `$REVIEW_SKILL`: pattern `Would you like to proceed to task breakdown?`. Both positive. Implement as a compound test.

4. Use a stable, descriptive label for each `ok` / `not_ok` line so failures are diagnosable. Recommended label format: `T<id> (AC-NN) — <one-line description>`. Example: `ok 1 - T1 (AC-01) — fbk-spec/SKILL.md does not contain 'If the gate fails:'`.

5. After all 22 assertion blocks, emit the summary footer matching `test-implementation-pipeline.sh`:

   ```bash
   echo ""
   echo "1..$TOTAL"
   echo "# $PASS/$TOTAL tests passed"
   if [ "$FAIL" -gt 0 ]; then
     echo "# FAIL $FAIL"
     exit 1
   fi
   exit 0
   ```

6. Verify the file is syntactically valid bash with `bash -n tests/sdl-workflow/test-skill-guide-dedup.sh`. The command must exit 0.

7. Run the test against the current (unrefactored) tree: `bash tests/sdl-workflow/test-skill-guide-dedup.sh`. Confirm it exits 1 (some assertions fail). The expected pre-refactor failure set includes at minimum: T1, T1b, T2, T3, T4, T4b, T5, T5b, T6, T11d, and the `Before invoking` substrings inside T11a and T11b. Confirm at least one of these reports `not ok`. This proves the test is not vacuously passing.

8. Mark the task complete only after both bash-syntax check and pre-refactor-fail check succeed.

## Files to create/modify

- `tests/sdl-workflow/test-skill-guide-dedup.sh` (create)

Do not modify any other file. Do not edit `assets/skills/`, `assets/fbk-docs/`, or any other test file.

## Test requirements

The new test file `tests/sdl-workflow/test-skill-guide-dedup.sh` declares 22 TAP assertions. Each assertion's T identifier and the AC it covers:

| T-id | AC | Direction | File | Sentinel phrase |
|------|-----|-----------|------|-----------------|
| T1 | AC-01 | absent | fbk-spec/SKILL.md | `If the gate fails:` |
| T1b | AC-01 | absent | fbk-spec/SKILL.md | `Verify that the testing strategy enumerates all callers` |
| T2 | AC-01 | absent | fbk-spec/SKILL.md | `Refuse to write code` |
| T3 | AC-02 | absent | fbk-spec-review/SKILL.md | `Does this feature need a threat model?` |
| T4 | AC-02 | absent | fbk-spec-review/SKILL.md | `There are N blocking findings` |
| T4b | AC-02 | absent | fbk-spec-review/SKILL.md | `Present the selection with` |
| T5 | AC-03 | absent | fbk-implement/SKILL.md | `Step 1 — Test tasks` AND `Step 2 — Test compilation check` |
| T5b | AC-03 | absent | fbk-implement/SKILL.md | `Tests are expected to fail` |
| T6 | AC-03 | absent | fbk-implement/SKILL.md | `Cap: 2 escalation attempts per task` |
| T7 | AC-04 | present | fbk-implement/SKILL.md | `CLAUDE_CODE_EXPERIMENTAL_AGENT_TEAMS` |
| T8 | AC-04 | present | fbk-implement/SKILL.md | `Task file:` |
| T9 | AC-04 | present | fbk-spec-review/SKILL.md | `/fbk-council` AND `test-reviewer` AND `testing strategy` |
| T9b | AC-04 | present | fbk-implement/SKILL.md | `review the implementation with /code-review` |
| T10 | AC-04 | present | three skills | `spec-gate` / `review-gate` / `breakdown-gate` (per skill) |
| T11a | AC-01 | present | feature-spec-guide.md | `If the gate fails:` AND `Refuse to write code` AND `` Before invoking `/spec-review` `` |
| T11b | AC-02 | present | review-perspectives.md | `Does this feature need a threat model?` AND `There are N blocking findings` AND `Present the classification with` AND `` Before invoking `/breakdown` `` |
| T11c | AC-03 | present | implementation-guide.md | `Step 1 — Test tasks` AND `Cap: 2 escalation attempts per task` AND `No dead code introduced` |
| T11d | AC-03 / AC-04 | absent | implementation-guide.md | `CLAUDE_CODE_EXPERIMENTAL_AGENT_TEAMS` |
| T12 | AC-04 | present | three skills | first line `---` AND contains `description:` (each skill) |
| T13 | AC-04 | present | three skills | `$ARGUMENTS` (fbk-spec, fbk-spec-review) AND `FEATURE=$ARGUMENTS` (fbk-implement) |
| T14 | AC-04 | present | two skills | `/spec-review $ARGUMENTS` (fbk-spec) AND `/breakdown` (fbk-spec-review) |
| T15 | AC-04 | present | two skills | `Would you like to move to spec review?` (fbk-spec) AND `Would you like to proceed to task breakdown?` (fbk-spec-review) |

The test exits 0 only when all 22 assertions pass, and exits 1 otherwise.

## Acceptance criteria

- AC-01, AC-02, AC-03, AC-06: covered structurally by T1/T1b/T2/T11a (AC-01), T3/T4/T4b/T11b (AC-02), T5/T5b/T6/T11c/T11d (AC-03), test file existence + auto-discovery + all-22-pass (AC-06).
- AC-04: covered by T7, T8, T9, T9b, T10, T12, T13, T14, T15, T11d.
- AC-05 is verified procedurally by re-running the existing test suite post-refactor; no assertion in this file covers AC-05.
- The test file is syntactically valid bash (`bash -n` exits 0).
- Running the test on the current (unrefactored) tree exits 1 with at least one `not ok` line — proves the test is not vacuously passing.

## Model

Haiku

## Wave

Wave 1
