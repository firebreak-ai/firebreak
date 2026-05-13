---
id: task-01
type: test
wave: 1
covers: [AC-01, AC-02, AC-03, AC-04, AC-06, AC-07, AC-09, AC-10, AC-11, AC-12, AC-13, AC-14]
files_to_create:
  - tests/sdl-workflow/test-council-skill-structure.sh
completion_gate: "test compiles, is executable, and exits non-zero when run against current main (because the rewritten SKILL and the three leaves do not yet exist)"
---

## 1. Objective

Adds `tests/sdl-workflow/test-council-skill-structure.sh` — a TAP-format structural smoke test that asserts the rewritten council SKILL and its three conditional leaves contain the required content and omit banned content, and that fails today against current `main` because the implementation work has not yet happened.

## 2. Context

The `/fbk-council` skill is being decomposed: a substantial body rewrite of `assets/skills/fbk-council/SKILL.md` plus extraction of three conditional leaves to `assets/fbk-docs/fbk-council/` (`consensus-failure.md`, `compaction-recovery.md`, `ralph-integration.md`). The Quick/Full tier prescription is replaced with a judgment-based council-sizing instruction; quick-mode triggers (`/fbk-qcouncil`, `/fbk-council quick`) carry a soft default to a 3-agent Architect+Builder+Guardian council with the Phase 1 alignment round skipped.

This task authors the structural smoke test that proves the rewrite happened correctly. The test must FAIL when run today against `main` — that is the completion gate. It will pass after the implementation tasks (compiled in a later wave) finish. The test runs from the existing CI glob `for test in tests/sdl-workflow/test-*.sh`; no CI changes required.

The test follows the TAP format used by `tests/sdl-workflow/test-council-skill-references.sh` and `tests/sdl-workflow/test-review-integration.sh`: emit `TAP version 13`, increment a TOTAL counter, emit `ok N - <name>` or `not ok N - <name>` per assertion, emit `1..N` summary, exit non-zero on any failure. Use `set -uo pipefail` (NOT `set -e`) so individual `grep` failures do not abort the whole script. Compute `SCRIPT_DIR` and `PROJECT_ROOT` via the standard idiom at the top of the existing council-test files.

This task also absorbs assertions (1) and (2) from `tests/sdl-workflow/test-council-skill-references.sh` (which is being deleted in task-03): the SKILL must contain a `session-manager` dispatcher reference and a `session-logger` dispatcher reference. Both ports are inline in the structure test as assertions 5 and 6 below.

Each assertion is a single grep or file-test call — fast (sub-second), deterministic, no LLM invocation. Total: 68 assertions; the file is roughly 110 lines plus boilerplate.

## 3. Instructions

1. Create `tests/sdl-workflow/test-council-skill-structure.sh` with the standard TAP header: shebang `#!/usr/bin/env bash`, `set -uo pipefail`, the `PASS`/`FAIL`/`TOTAL` counters, the `ok` and `not_ok` helper functions, and `SCRIPT_DIR` / `PROJECT_ROOT` resolution as in `test-council-skill-references.sh`. Define the path constants at the top: `SKILL="$PROJECT_ROOT/assets/skills/fbk-council/SKILL.md"`, `LEAF_DIR="$PROJECT_ROOT/assets/fbk-docs/fbk-council"`, `CONSENSUS="$LEAF_DIR/consensus-failure.md"`, `RECOVERY="$LEAF_DIR/compaction-recovery.md"`, `RALPH="$LEAF_DIR/ralph-integration.md"`. Emit `TAP version 13` once.

2. Implement each assertion below as one block: a single `grep -F` (or `grep -c` / file test) followed by an `if`/`else` calling `ok` or `not_ok`. Use `grep -F` (fixed string) for literal-substring assertions and `grep -E` only when a regex is required. Suppress grep stdout with `>/dev/null 2>&1` for boolean checks.

3. Emit `1..$TOTAL` after the last assertion, and `exit 1` when `$FAIL -gt 0`, otherwise `exit 0`. Make the file executable: `chmod +x tests/sdl-workflow/test-council-skill-structure.sh`.

4. Verify completion gate: run `bash tests/sdl-workflow/test-council-skill-structure.sh` against current `main`. Confirm it exits non-zero and at least the leaf-existence and banned-header assertions fail. Do not modify the SKILL or create the leaves to make it pass — that is the implementation tasks' job.

## 4. Files to create/modify

- **Create**: `tests/sdl-workflow/test-council-skill-structure.sh`

## 5. Test requirements

The test file performs these assertions in order. Each numbered item is one `ok`/`not_ok` line; sub-items expanded inline are also one assertion each. Total: ~50 assertions.

**SKILL existence and frontmatter (AC-01):**

1. `[ -s "$SKILL" ]` — `assets/skills/fbk-council/SKILL.md` exists and is non-empty.
2. SKILL frontmatter contains `name: fbk-council`. (`grep -F 'name: fbk-council' "$SKILL"`)
3. SKILL description contains literal substring `selected per task`. (`grep -F 'selected per task' "$SKILL"`)
4. SKILL description contains literal substring `architect, builder, guardian, security, advocate, analyst`. (`grep -F 'architect, builder, guardian, security, advocate, analyst' "$SKILL"`)
5. SKILL description does NOT contain literal substring `team of 6` (negative — verifies the literal "6" was removed). (`! grep -F 'team of 6' "$SKILL"`)

**Trigger phrases verbatim (AC-11):** one assertion per phrase, all using `grep -F`.

6. SKILL contains `/fbk-council`.
7. SKILL contains `/fbk-council quick`.
8. SKILL contains `/fbk-qcouncil`.
9. SKILL contains `/fbk-council --no-log`.
10. SKILL contains `/fbk-council quick --no-log`.
11. SKILL contains `/fbk-assemble`.
12. SKILL contains `assemble the team`.
13. SKILL contains `convene the council`.
14. SKILL contains `quick council`.

**Default-dispatcher references (AC-01 part (h); ported from deleted `test-council-skill-references.sh` assertions 1–2):**

15. SKILL contains literal `session-manager`. (`grep -F 'session-manager' "$SKILL"`)
16. SKILL contains literal `session-logger`. (`grep -F 'session-logger' "$SKILL"`)
17. SKILL contains literal `--no-log` (FIND-013 anti-typo guard; AC-01 part (i)).
18. SKILL contains literal `session-state checkpoint` (per-phase checkpoint trigger inline; AC-01 part (j); FIND-002 anti-regression).

**Required section headers (AC-01 parts (c)–(g)):** one assertion per header.

19. SKILL contains header `Council Members`. (`grep -F 'Council Members' "$SKILL"`)
20. SKILL contains header `Phase 5: Consensus Output`.
21. SKILL contains header `Phase 5.5`.
22. SKILL contains header `Immutable Core`.
23. SKILL contains header `Trigger Phrases`.

**Banned headers absent (AC-02):** one negative assertion per header.

24. SKILL does NOT contain header `Quick Council`. (`! grep -F 'Quick Council' "$SKILL"`)
25. SKILL does NOT contain header `Full Council`.
26. SKILL does NOT contain header `Tier Selection Heuristics`.
27. SKILL does NOT contain header `Auto-escalation`.

**Dispatch references to each conditional leaf (AC-09 reachability):**

28. SKILL contains dispatch path `assets/fbk-docs/fbk-council/consensus-failure.md`.
29. SKILL contains dispatch path `assets/fbk-docs/fbk-council/compaction-recovery.md`.
30. SKILL contains dispatch path `assets/fbk-docs/fbk-council/ralph-integration.md`.

**Leaf files exist at expected paths (AC-09 link resolution):**

31. `[ -s "$CONSENSUS" ]` — `consensus-failure.md` exists and is non-empty.
32. `[ -s "$RECOVERY" ]` — `compaction-recovery.md` exists and is non-empty.
33. `[ -s "$RALPH" ]` — `ralph-integration.md` exists and is non-empty.

**`consensus-failure.md` content (AC-04):** one assertion per term.

34. `consensus-failure.md` contains `Weighted Voting`.
35. `consensus-failure.md` contains `Evidence-Based Consensus`.
36. `consensus-failure.md` contains `Reasoning`.
37. `consensus-failure.md` contains `Knowledge`.
38. `consensus-failure.md` contains `Technical Disagreement`.
39. `consensus-failure.md` contains `Security vs Usability`.
40. `consensus-failure.md` contains `Quality vs Speed`.
41. `consensus-failure.md` contains `Feature Scope`.
42. `consensus-failure.md` contains `Deadlock`.

**`compaction-recovery.md` content (AC-06):** one assertion per term.

43. `compaction-recovery.md` contains `Recovery Protocol`.
44. `compaction-recovery.md` contains `Session State Footer`.
45. `compaction-recovery.md` contains `COUNCIL_STATUS: CONTINUE`.
46. `compaction-recovery.md` contains `COUNCIL_STATUS: COUNCIL_COMPLETE`.

**`ralph-integration.md` content (AC-07):** one assertion per term.

47. `ralph-integration.md` contains `What is Ralph Wiggum`.
48. `ralph-integration.md` contains `Guardrails`.
49. `ralph-integration.md` contains `Escape Hatches`.
50. `ralph-integration.md` contains `When to Use Ralph`.

**Sizing-instruction soft-default phrases (AC-03 + AC-13):** one assertion per phrase. Verifies AC-03 (single sizing instruction present) via the AC-13 phrases that uniquely identify it.

51. SKILL contains `Architect + Builder + Guardian`.
52. SKILL contains `substitute Security`.
53. SKILL contains `substitute Advocate`.
54. SKILL contains `substitute Analyst`.
55. SKILL contains `skipping the Phase 1 alignment round`.

**Modified existing tests + deleted reference test (AC-10):** verifies the test-infrastructure modifications by tasks 02 and 03 landed correctly.

56. `test-old-locations-empty.sh` contains the literal substring `assets/fbk-docs/fbk-council` (assertion the directory existence check was added by task-02).
57. `test-no-old-path-patterns.sh` contains the literal substring `assets/fbk-docs/fbk-council/consensus-failure.md` (assertion the new leaf paths were added to the files=() array by task-03).
58. `test-no-old-path-patterns.sh` contains the literal substring `assets/fbk-docs/fbk-council/compaction-recovery.md`.
59. `test-no-old-path-patterns.sh` contains the literal substring `assets/fbk-docs/fbk-council/ralph-integration.md`.
60. `tests/sdl-workflow/test-council-skill-references.sh` does NOT exist (asserts `! -e` on the path; verifies task-03's deletion).

**Downstream caller integrity (AC-12):** verifies the SKILL refactor did not break callers that reference `/fbk-council`.

61. `assets/skills/fbk-spec-review/SKILL.md` contains the literal substring `/fbk-council` (asserts caller still invokes the trigger).
62. `assets/fbk-docs/fbk-sdl-workflow/review-perspectives.md` contains the literal substring `/fbk-council` (asserts cross-doc reference preserved).

**CHANGELOG and README post-refactor content (AC-14):** verifies task-08 landed the documentation updates correctly.

63. `CHANGELOG.md` contains the literal substring `Decomposed the` (capital D — leads the new bullet per task-08 entry text).
64. `CHANGELOG.md` contains the literal substring `/fbk-council`.
65. `README.md` contains the literal substring `Assemble specialized agents`.
66. `README.md` does NOT contain the literal substring `Assemble 6 agents` (negative assertion — old wording removed).

**Ralph stale-state guard (AC-07 reinforcement; closes CP2 Finding 1):** verifies the SKILL inline Ralph dispatch instruction includes the negative-trigger guard text.

67. SKILL contains the literal substring `does NOT activate Ralph mode` (asserts the §4.2 item 16 stale-state exclusion clause survives the rewrite; prevents silent regression where the dispatch instruction loses the negative guard).

**Tier argument value (AC-01 reinforcement; closes CP2 Finding 3):** verifies the literal `--tier full` appears in the SKILL's logging command context per spec §4.7.

68. SKILL contains the literal substring `--tier full` (asserts the tier argument value is the literal `full` per spec §4.2 item 17 and §4.7; prevents regression to the old `[quick|full]` placeholder).

After all assertions, emit `1..$TOTAL` then `exit 1` if `$FAIL -gt 0`, else `exit 0`.

## 6. Acceptance criteria

- File `tests/sdl-workflow/test-council-skill-structure.sh` exists, is executable, follows TAP format.
- Running `bash tests/sdl-workflow/test-council-skill-structure.sh` against current `main` exits non-zero (because leaf files do not exist, banned headers are still in SKILL, dispatch references are absent, etc.). This is the completion gate.
- Each assertion enumerated in section 5 is implemented as one TAP line.
- After the implementation tasks (later waves) complete, the same test command exits 0 with all `ok` lines.
- AC coverage: AC-01 (assertions 1–5, 15–23, 68), AC-02 (assertions 24–27), AC-03 (assertions 51–55), AC-04 (assertions 34–42), AC-06 (assertions 43–46), AC-07 (assertions 47–50, 67), AC-09 (assertions 28–33), AC-10 (assertions 56–60), AC-11 (assertions 6–14), AC-12 (assertions 61–62), AC-13 (assertions 51–55), AC-14 (assertions 63–66).

## 7. Model

Sonnet

## 8. Wave

Wave 1
