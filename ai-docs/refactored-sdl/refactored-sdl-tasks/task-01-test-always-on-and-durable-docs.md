---
id: task-01
type: test
wave: 1
covers: [AC-17, AC-18, AC-19]
files_to_create:
  - tests/sdl-workflow/test-always-on-and-durable-docs.sh
completion_gate: "tests compile and fail before implementation"
---

## 1. Objective

Creates `tests/sdl-workflow/test-always-on-and-durable-docs.sh`, a TAP-format shell integration test that asserts the five always-on disciplines are present in both `.claude/CLAUDE.md` and the authoring rules, and that the two durable docs exist and are properly seeded.

## 2. Context

The spec adds five named always-on disciplines to the project: "simple language," "descriptions over identifiers," "capability framing," "interview before drafting," and "structural-principles awareness." These must appear as one-liners with routing in `.claude/CLAUDE.md` (AC-17) and as instructions in the asset-authoring rules at `assets/fbk-docs/fbk-context-assets.md` (AC-18).

Two durable docs must also exist (AC-19): `docs/decisions-log.md` (append-only decisions log) and `docs/architecture-overview.md` (living architecture/intent overview seeded for this repo). The spec requires that the overview be non-empty and that authoring docs state the governing conventions (plain markdown, bounded length, in-branch updates that merge with the change).

The test is a presence/content sentinel, not a behavioral test. Follow the TAP pattern in `tests/sdl-workflow/test-code-review-structural.sh`: `PASS`/`FAIL` counters, `ok`/`not_ok` helpers, `echo "TAP version 13"` at top, `echo "1..$TOTAL"` at end, exit 1 on any failure.

Before implementation, all assertions will fail because the disciplines do not yet exist in those files and the durable docs do not yet exist. That is the intended red state.

## 3. Instructions

1. Create `tests/sdl-workflow/test-always-on-and-durable-docs.sh` with the shebang `#!/usr/bin/env bash` and `set -uo pipefail`.

2. Add the standard TAP boilerplate: `PASS=0`, `FAIL=0`, `TOTAL=0`, `ok()` and `not_ok()` helper functions, `SCRIPT_DIR` and `PROJECT_ROOT` derived the same way as `test-code-review-structural.sh` (using `cd "$(dirname "$0")" && pwd` and `cd "$SCRIPT_DIR/../.." && pwd`).

3. Define these path variables at the top of the assertion block:
   - `CLAUDE_MD="$PROJECT_ROOT/.claude/CLAUDE.md"`
   - `AUTHORING_RULES="$PROJECT_ROOT/assets/fbk-docs/fbk-context-assets.md"`
   - `DECISIONS_LOG="$PROJECT_ROOT/docs/decisions-log.md"`
   - `ARCH_OVERVIEW="$PROJECT_ROOT/docs/architecture-overview.md"`

4. Write exactly these assertions for AC-17 (`.claude/CLAUDE.md` surfaces all five disciplines):
   - T1: `grep -qiF 'simple language' "$CLAUDE_MD"` — discipline "simple language" present in `.claude/CLAUDE.md`
   - T2: `grep -qiF 'descriptions over identifiers' "$CLAUDE_MD"` — discipline "descriptions over identifiers" present
   - T3: `grep -qiF 'capability framing' "$CLAUDE_MD"` — discipline "capability framing" present
   - T4: `grep -qiF 'interview before drafting' "$CLAUDE_MD"` — discipline "interview before drafting" present
   - T5: `grep -qiF 'structural-principles awareness' "$CLAUDE_MD"` — discipline "structural-principles awareness" present
   - T6: `grep -qE 'fbk-context-assets|always-on' "$CLAUDE_MD"` — `.claude/CLAUDE.md` routes to the authoring rules (the route must reference either the `fbk-context-assets` filename or the phrase `always-on`)

5. Write exactly these assertions for AC-18 (authoring rules contain all five disciplines):
   - T7: `grep -qiF 'simple language' "$AUTHORING_RULES"` — authoring rules contain "simple language"
   - T8: `grep -qiF 'descriptions over identifiers' "$AUTHORING_RULES"` — authoring rules contain "descriptions over identifiers"
   - T9: `grep -qiF 'capability framing' "$AUTHORING_RULES"` — authoring rules contain "capability framing"
   - T10: `grep -qiF 'interview before drafting' "$AUTHORING_RULES"` — authoring rules contain "interview before drafting"
   - T11: `grep -qiF 'structural-principles awareness' "$AUTHORING_RULES"` — authoring rules contain "structural-principles awareness"

6. Write exactly these assertions for AC-19 (durable-artifact discipline established):
   - T12: `[ -f "$DECISIONS_LOG" ]` — `docs/decisions-log.md` exists
   - T13: `[ -f "$ARCH_OVERVIEW" ]` — `docs/architecture-overview.md` exists
   - T14: `[ -s "$ARCH_OVERVIEW" ]` — `docs/architecture-overview.md` is non-empty (use `-s` to check size > 0)
   - T15: Check that the authoring conventions are stated in either the overview or a doc it references. Use `grep -qiE 'plain markdown|bounded length|in-branch' "$ARCH_OVERVIEW"` — the overview contains at least one of the three governing convention phrases.

7. Add the TAP summary block at the end:
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

8. Make the file executable: `chmod +x tests/sdl-workflow/test-always-on-and-durable-docs.sh`. (State this as a step; the implementing agent performs it.)

## 4. Files to create/modify

- `tests/sdl-workflow/test-always-on-and-durable-docs.sh` (create)

## 5. Test requirements

All 15 assertions are shell integration tests (grep/file-existence checks). They are:
- T1–T6: Unit level, `.claude/CLAUDE.md` presence checks (AC-17)
- T7–T11: Unit level, `assets/fbk-docs/fbk-context-assets.md` presence checks (AC-18)
- T12–T15: Unit level, file existence and content checks for the two durable docs (AC-19)

Expected state before implementation: all 15 assertions fire `not_ok` because the disciplines have not been added to the files and the durable docs do not exist. That is the correct red state.

## 6. Acceptance criteria

- The five always-on disciplines appear in `.claude/CLAUDE.md` (T1–T5 pass after implementation of the foundation-disciplines-durable-docs slice).
- `.claude/CLAUDE.md` routes to the authoring rule that carries them (T6 passes).
- All five disciplines appear in `assets/fbk-docs/fbk-context-assets.md` (T7–T11 pass).
- `docs/decisions-log.md` and `docs/architecture-overview.md` exist (T12–T13 pass).
- The overview is non-empty (T14 passes) and states at least one governing convention (T15 passes).

## 7. Model

Haiku

## 8. Wave

Wave 1
