---
id: task-03
type: implementation
wave: 2
covers: [AC-10]
files_to_modify:
  - tests/sdl-workflow/test-no-old-path-patterns.sh
test_tasks: [task-01]
completion_gate: "extended path-pattern test includes the three new leaf paths in its files=() array; the deleted reference test (test-council-skill-references.sh) is removed; task-01 assertions 57–60 pass after this task lands"
---

## 1. Objective

Extends `tests/sdl-workflow/test-no-old-path-patterns.sh` to cover the three new council leaf paths under `assets/fbk-docs/fbk-council/`, absorbs assertions (3) and (4) from `tests/sdl-workflow/test-council-skill-references.sh`, and deletes that now-obsolete file from the repository.

## 2. Context

`test-no-old-path-patterns.sh` greps a curated `files=()` array of 11 context-asset files for legacy path substrings (`hooks/fbk-sdl-workflow`, `scripts/fbk-pipeline`, `uv run`, `~/.claude/skills/fbk-council/`). The council-decomposition refactor adds three new context assets under `assets/fbk-docs/fbk-council/`. Those leaves must be scanned by the same detector so that no future edit reintroduces a legacy path pattern there.

`test-council-skill-references.sh` is being deleted as part of this spec (per spec §4.5). It currently has four assertions:

1. SKILL contains a `session-manager` dispatcher reference.
2. SKILL contains a `session-logger` dispatcher reference.
3. SKILL contains zero `~/.claude/skills/fbk-council/session-` substrings.
4. SKILL contains zero `~/.claude/skills/fbk-council/ralph-` substrings.

Assertions (1) and (2) are absorbed by task-01 (the structural smoke test) as its assertions 15 and 16. Assertions (3) and (4) are absorbed here. Once both migrations land, the original file is deleted to satisfy AC-10.

This task uses the bundled approach: the path-pattern extension and the deletion of `test-council-skill-references.sh` happen in the same task. The assertion-(1)/(2) migration is owned by task-01. The deletion runs at the end of this task; sequencing within the wave is enforced by ordering — the deletion step appears after both migration steps land. The implementing agent verifies task-01's file exists with the migrated assertions before deleting `test-council-skill-references.sh`.

The existing `test-no-old-path-patterns.sh` already has Test 4 (`~/.claude/skills/fbk-council/` substring check) which covers a superset of assertions (3) and (4) from the deleted file — but for the curated `files=()` array, not for `assets/skills/fbk-council/SKILL.md` specifically. Once the new leaves are added to the array AND the SKILL is already in the array (it is, at line 19), Test 4's coverage subsumes the migrated assertions naturally. No new test cases are required for assertions (3) and (4) beyond ensuring SKILL.md and the new leaves remain in the scanned `files=()` array.

## 3. Instructions

1. Open `tests/sdl-workflow/test-no-old-path-patterns.sh`. The existing `files=()` array is at lines 13–25 and includes `assets/skills/fbk-council/SKILL.md` at line 19. Add three lines to that array, immediately after the `assets/skills/fbk-council/SKILL.md` line, with the same indentation and quoting style:

   ```
     "$PROJECT_ROOT/assets/fbk-docs/fbk-council/consensus-failure.md"
     "$PROJECT_ROOT/assets/fbk-docs/fbk-council/compaction-recovery.md"
     "$PROJECT_ROOT/assets/fbk-docs/fbk-council/ralph-integration.md"
   ```

2. Do not change Tests 1–4 themselves; the `files=()` extension automatically extends each test's grep target. Do not add new tests in this file. Do not change `set -e`, the `fail_count` accumulator, or the exit logic.

3. Verify task-01's file `tests/sdl-workflow/test-council-skill-structure.sh` exists and contains assertions covering literal `session-manager` and literal `session-logger` against the SKILL (these are task-01's assertions 15 and 16). If not present, stop and report — do not proceed to step 4. This confirms assertions (1) and (2) of the deleted file have been migrated before deletion.

4. After step 3 confirms migration, delete `tests/sdl-workflow/test-council-skill-references.sh` from the repository. Use `git rm tests/sdl-workflow/test-council-skill-references.sh` so the deletion is staged.

5. Verify the completion gate: run `bash tests/sdl-workflow/test-no-old-path-patterns.sh`. Note: the test uses `set -e`; if the new leaf files do not exist on `main`, the embedded `grep -r ... "${files[@]}"` will silently produce zero matches for non-existent files (grep stderr is suppressed via `2>/dev/null`), so the test should exit 0 today. Confirm exit code 0. After implementation tasks land and the leaf files exist with valid content, the test still exits 0 (because no leaf will contain a legacy path substring). Then run `ls tests/sdl-workflow/test-council-skill-references.sh 2>&1 | grep -c 'No such file'` — must return `1`, confirming the deletion landed.

## 4. Files to create/modify

- **Modify**: `tests/sdl-workflow/test-no-old-path-patterns.sh`
- **Delete**: `tests/sdl-workflow/test-council-skill-references.sh`

## 5. Test requirements

| # | Change | Method | AC |
|---|--------|--------|----|
| 1 | Add `consensus-failure.md` to `files=()` | array-element insertion | AC-10 |
| 2 | Add `compaction-recovery.md` to `files=()` | array-element insertion | AC-10 |
| 3 | Add `ralph-integration.md` to `files=()` | array-element insertion | AC-10 |
| 4 | Delete `tests/sdl-workflow/test-council-skill-references.sh` | `git rm` | AC-10 |

The four legacy path-pattern checks (Test 1: `hooks/fbk-sdl-workflow`; Test 2: `scripts/fbk-pipeline`; Test 3: `uv run`; Test 4: `~/.claude/skills/fbk-council/`) automatically extend their coverage to the three new leaf paths via the `files=()` array additions. No new test cases needed.

## 6. Acceptance criteria

- The three new leaf paths appear in the `files=()` array of `test-no-old-path-patterns.sh` with consistent quoting and indentation.
- `tests/sdl-workflow/test-council-skill-references.sh` is removed from the repository.
- `bash tests/sdl-workflow/test-no-old-path-patterns.sh` exits 0 against current `main` and continues to exit 0 after the implementation tasks create the leaf files (because the leaves will not contain legacy path substrings).
- The CI glob `for test in tests/sdl-workflow/test-*.sh` no longer picks up `test-council-skill-references.sh` (because it is deleted).
- Covers AC-10 in conjunction with task-02 (which covers the new-location existence side) and task-01 (which absorbs the dispatcher-reference assertions).

## 7. Model

Haiku

## 8. Wave

Wave 1
