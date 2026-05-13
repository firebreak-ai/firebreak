---
id: task-02
type: implementation
wave: 2
covers: [AC-10]
files_to_modify:
  - tests/sdl-workflow/test-old-locations-empty.sh
test_tasks: [task-01]
completion_gate: "extended test compiles and includes new assertions for the three council leaves; task-01 assertion 56 passes after task-04/05/06 land the leaves; the extended test itself exits 0 once the leaves exist"
---

## 1. Objective

Extends `tests/sdl-workflow/test-old-locations-empty.sh` with assertions that `assets/fbk-docs/fbk-council/` exists and contains the three new conditional leaf files (`consensus-failure.md`, `compaction-recovery.md`, `ralph-integration.md`).

## 2. Context

The existing `test-old-locations-empty.sh` verifies that legacy hook/script/skill locations are emptied after the Python migration: it tests that no `.sh`/`.py` files remain in `assets/hooks/fbk-sdl-workflow/`, that `assets/scripts/` is empty, that no `.py` files remain under `assets/skills/fbk-council/`, and that `assets/skills/fbk-council/SKILL.md` is retained at the canonical path. It uses a TAP-like format with `ok`/`not_ok` helpers and exits non-zero on any failure.

The council-decomposition spec creates a new sibling location at `assets/fbk-docs/fbk-council/` holding three conditional leaves. The structural smoke test (task-01) verifies leaf existence individually; this test additionally verifies the **directory** exists (a pure-existence check that would fail with a clearer error if someone forgot to create the directory) and that all three files are present together — covering the "old locations + new locations" symmetry that this test file owns.

The existing five assertions stay unchanged. New assertions are appended after Test 5. Use the same `ok`/`not_ok` helpers and `PROJECT_ROOT` resolution already present in the file.

## 3. Instructions

1. Open `tests/sdl-workflow/test-old-locations-empty.sh`. Do not modify Tests 1–5; they remain in their current order.

2. After Test 5 (the SKILL.md retention check) and before the final `echo "$PASS/$TOTAL tests passed"` summary block, append these assertions:

   - **Test 6**: assert directory `$PROJECT_ROOT/assets/fbk-docs/fbk-council/` exists. Use `[ -d "$PROJECT_ROOT/assets/fbk-docs/fbk-council/" ]`. Pass message: `assets/fbk-docs/fbk-council/ directory exists`. Fail message: `directory missing`.
   - **Test 7**: assert file `$PROJECT_ROOT/assets/fbk-docs/fbk-council/consensus-failure.md` exists and is non-empty. Use `[ -s "$PROJECT_ROOT/assets/fbk-docs/fbk-council/consensus-failure.md" ]`. Pass: `consensus-failure.md exists`. Fail: `file missing or empty`.
   - **Test 8**: assert file `$PROJECT_ROOT/assets/fbk-docs/fbk-council/compaction-recovery.md` exists and is non-empty. Same idiom. Pass: `compaction-recovery.md exists`. Fail: `file missing or empty`.
   - **Test 9**: assert file `$PROJECT_ROOT/assets/fbk-docs/fbk-council/ralph-integration.md` exists and is non-empty. Same idiom. Pass: `ralph-integration.md exists`. Fail: `file missing or empty`.

3. Each assertion uses the existing `ok` and `not_ok` helpers already defined at lines 11–12. Do not introduce new helpers, new shell options, or change `set -uo pipefail`.

4. Do not change the final summary block (`echo "$PASS/$TOTAL tests passed"`) or the exit logic (`[[ $FAIL -eq 0 ]] && exit 0 || exit 1`).

5. Verify the completion gate: run `bash tests/sdl-workflow/test-old-locations-empty.sh`. Confirm Tests 1–5 pass (current behavior preserved) and Tests 6–9 fail (because the leaf directory and files do not exist on `main` yet). Do not create the directory or files to make Tests 6–9 pass — the implementation tasks will do that in a later wave.

## 4. Files to create/modify

- **Modify**: `tests/sdl-workflow/test-old-locations-empty.sh`

## 5. Test requirements

The four new assertions added to the existing file:

| # | Assertion | Method | AC |
|---|-----------|--------|----|
| 6 | `assets/fbk-docs/fbk-council/` directory exists | `[ -d ... ]` | AC-10 |
| 7 | `consensus-failure.md` exists and is non-empty | `[ -s ... ]` | AC-10 |
| 8 | `compaction-recovery.md` exists and is non-empty | `[ -s ... ]` | AC-10 |
| 9 | `ralph-integration.md` exists and is non-empty | `[ -s ... ]` | AC-10 |

Original Tests 1–5 remain unchanged and continue to assert the same conditions they assert today.

## 6. Acceptance criteria

- Tests 6, 7, 8, 9 are present in `tests/sdl-workflow/test-old-locations-empty.sh` immediately after Test 5 and before the summary block.
- Tests 1–5 are byte-identical to their current state on `main`.
- Running the test against current `main` exits non-zero with Tests 1–5 passing and Tests 6–9 failing.
- After the implementation tasks complete, all nine tests pass and the script exits 0.
- Covers AC-10 (the new-location side of the post-refactor verification).

## 7. Model

Haiku

## 8. Wave

Wave 1
