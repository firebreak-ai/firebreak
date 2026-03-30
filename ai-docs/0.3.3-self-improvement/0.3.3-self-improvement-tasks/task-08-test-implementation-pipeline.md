---
id: task-08
type: test
wave: 1
covers: [AC-01, AC-02, AC-03, AC-05, AC-06, AC-07, AC-08]
files_to_create:
  - tests/sdl-workflow/test-implementation-pipeline.sh
completion_gate: "tests compile and fail before implementation"
---

## Objective

Creates `tests/sdl-workflow/test-implementation-pipeline.sh` — a structural test suite validating the implementation pipeline improvements across implementation-guide.md, task-compilation.md, and test-authoring.md.

## Context

Three files receive additions:

`implementation-guide.md` (`assets/fbk-docs/fbk-sdl-workflow/implementation-guide.md`):
- AC-01: Hook-rejection retry cap — 3 retries, then team lead intervenes. The current escalation protocol (lines 156-166) has a 2-attempt cap for task escalation. AC-01 adds a separate cap for hook rejection retries within a single task attempt.
- AC-02: Fresh agent per task — do not reuse workers across tasks. Prevents context pollution. The current "Task Isolation" section (lines 66-69) describes file-scope isolation but not agent-instance isolation.
- AC-03: Foreground execution for all verification and hook commands — background execution can produce empty output. The current hook section (lines 109-123) does not specify foreground/background.

`task-compilation.md` (`assets/fbk-docs/fbk-sdl-workflow/task-compilation.md`):
- AC-05: E2E harness exception — combine test+impl into a single task when the task creates an E2E test harness. The current "Test/Implementation Task Separation" section (lines 157-167) mandates separate tasks with no exception for E2E harnesses.
- AC-06: Per-site completion conditions — tasks with multiple mutation sites must have numbered steps with per-site completion conditions. The current "Instructions" section (step 3 in task structure) requires numbered steps but not per-site conditions.

`test-authoring.md` (`assets/fbk-docs/fbk-design-guidelines/test-authoring.md`):
- AC-07: Assertion specificity rule — assertions must check specific values, not just truthiness or type.
- AC-08: Test name accuracy rule — test names must describe the behavior being verified, not the implementation mechanism.

Follow the TAP format from existing test files.

## Instructions

1. Create `tests/sdl-workflow/test-implementation-pipeline.sh` with shebang and `set -uo pipefail`.

2. Add standard boilerplate. Define:
   - `IMPL_GUIDE="$PROJECT_ROOT/assets/fbk-docs/fbk-sdl-workflow/implementation-guide.md"`
   - `TASK_COMP="$PROJECT_ROOT/assets/fbk-docs/fbk-sdl-workflow/task-compilation.md"`
   - `TEST_AUTH="$PROJECT_ROOT/assets/fbk-docs/fbk-design-guidelines/test-authoring.md"`

3. Add the following tests:

   **Test 1: Implementation guide contains hook retry cap (AC-01)**
   Grep for `retry cap\|3 retries\|retry.*3\|hook.*rejection.*cap\|hook.*retry` in `$IMPL_GUIDE`. Use: `grep -qiE 'retry.*(cap|limit|3)|hook.*reject.*retry|3.*retries' "$IMPL_GUIDE"`. Test name: "Implementation guide contains hook retry cap".

   **Test 2: Implementation guide contains fresh agent per task rule (AC-02)**
   Grep for `fresh.*agent\|agent.*per.*task\|no.*reuse\|do not reuse\|context.*pollution` in `$IMPL_GUIDE`. Use: `grep -qiE 'fresh.*agent|agent.*per.*task|do not reuse|no.*worker.*reuse|context.*pollution' "$IMPL_GUIDE"`. Test name: "Implementation guide contains fresh agent per task rule".

   **Test 3: Implementation guide contains foreground execution rule (AC-03)**
   Grep for `foreground.*execut\|foreground.*verif\|foreground.*hook\|background.*empty` in `$IMPL_GUIDE`. Use: `grep -qiE 'foreground|background.*empty' "$IMPL_GUIDE"`. Test name: "Implementation guide contains foreground execution rule".

   **Test 4: Task compilation contains E2E harness exception (AC-05)**
   Grep for `E2E.*harness\|e2e.*harness\|harness.*exception\|combine.*test.*impl\|single.*task.*harness` in `$TASK_COMP`. Use: `grep -qiE 'e2e.*harness|harness.*exception|combine.*(test|impl)' "$TASK_COMP"`. Test name: "Task compilation contains E2E harness exception".

   **Test 5: Task compilation contains per-site completion conditions (AC-06)**
   Grep for `per.site.*completion\|completion.*condition.*per.site\|mutation.*site\|numbered.*step.*per.*site` in `$TASK_COMP`. Use: `grep -qiE 'per.site|mutation site|completion.*condition.*site' "$TASK_COMP"`. Test name: "Task compilation contains per-site completion conditions".

   **Test 6: Test authoring contains assertion specificity rule (AC-07)**
   Grep for `assertion.*specific\|specific.*assert\|specific.*value\|not.*truthi\|not.*type.*only` in `$TEST_AUTH`. Use: `grep -qiE 'assertion.*specific|specific.*value|truthi|specificity' "$TEST_AUTH"`. Test name: "Test authoring contains assertion specificity rule".

   **Test 7: Test authoring contains test name accuracy rule (AC-08)**
   Grep for `test.*name.*accura\|name.*accura\|name.*describe.*behavior\|name.*match.*behavior` in `$TEST_AUTH`. Use: `grep -qiE 'test.*name.*(accura|descri)|name.*(accura|match).*behavior' "$TEST_AUTH"`. Test name: "Test authoring contains test name accuracy rule".

4. Add standard summary footer.

5. Make the file executable.

## Files to create/modify

- `tests/sdl-workflow/test-implementation-pipeline.sh` (create)

## Test requirements

7 structural tests covering AC-01, AC-02, AC-03, AC-05, AC-06, AC-07, AC-08. Tests must fail before implementation.

## Acceptance criteria

- AC-01: Test 1 verifies hook retry cap keyword.
- AC-02: Test 2 verifies fresh agent per task keyword.
- AC-03: Test 3 verifies foreground execution keyword.
- AC-05: Test 4 verifies E2E harness exception keyword.
- AC-06: Test 5 verifies per-site completion conditions keyword.
- AC-07: Test 6 verifies assertion specificity rule keyword.
- AC-08: Test 7 verifies test name accuracy rule keyword.

## Model

Haiku

## Wave

Wave 1
