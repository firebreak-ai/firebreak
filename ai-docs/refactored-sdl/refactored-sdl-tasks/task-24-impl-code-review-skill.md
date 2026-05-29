---
id: task-24
type: implementation
wave: 1
covers: [AC-08]
files_to_modify:
  - assets/skills/fbk-code-review/SKILL.md
  - assets/fbk-docs/fbk-sdl-workflow/code-review-guide.md
  # Conditional — re-sentineled only if the skill/guide edits break a sentinel
  # (this task owns the edits, so it owns the re-sentinel). If a test still passes
  # after the edits, do not modify it. See step 6.
  - tests/sdl-workflow/test-code-review-skill.sh
  - tests/sdl-workflow/test-code-review-guide-extensions.sh
  - tests/sdl-workflow/test-code-review-integration.sh
test_tasks: [task-05]
dependencies: []
completion_gate: "the referenced test tasks pass"
---

## 1. Objective

Extends `assets/skills/fbk-code-review/SKILL.md` so that after the existing bug-finding pass it invokes `fbk-quality-scan`, then `fbk-test-review` (final pass), then the `code-review-gate`, in that exact order, and adds the matching passes to the code-review guide.

## 2. Context

The code-review phase gains two additive passes after its preserved bug-finding loop. The order is a sequencing contract (AC-08): the existing bug-finding loop runs first (unchanged), then `fbk-quality-scan`, then `fbk-test-review` (final), then the new `code-review-gate`. The bug-finding loop itself is untouched.

The ordering test (`tests/sdl-workflow/test-code-review-ordering.sh`, task-05) greps `fbk-code-review/SKILL.md` for the line numbers of four sentinels and asserts they appear in this sequence:
1. the bug-finding sentinel — the test anchors on the verbatim invocation string `Spawn Detector with:` (the exact detector-invocation step in the current skill body; task-05 uses this exact string, a string that cannot survive removal of the bug-finding loop — do NOT use a bare word like `Detector`)
2. `fbk-quality-scan`
3. `fbk-test-review`
4. `code-review-gate`

So the three new sentinel strings (`fbk-quality-scan`, `fbk-test-review`, `code-review-gate`) must appear in the body in that order, all AFTER the `Spawn Detector with:` invocation step in the Detection-Verification Loop. The current skill (read it) has the `## Detection-Verification Loop` section (which carries the `Spawn Detector with:` step), then `## Post-Fix Verification`, then `## Broad-Scope Reviews`, etc., and ends with `## Retrospective`. Insert the two technique invocations and the gate call as a new section placed AFTER the Detection-Verification Loop and AFTER Post-Fix Verification, and BEFORE the Retrospective section (so the gate runs on a settled change set). The `Spawn Detector with:` step is near the top, so any placement after the loop satisfies the ordering.

The skill invokes the technique skills by name (they are composed) and runs the gate via the standard form `python3 "$HOME"/.claude/fbk-scripts/fbk.py code-review-gate <args>`. Use the installed path form, not `assets/...` (AC-22). The `code-review-gate` itself is implemented by task-34 (wave 3); this skill only needs to call it by command name — the call is a pinned-contract reference, not a build-order dependency.

The code-review guide (`assets/fbk-docs/fbk-sdl-workflow/code-review-guide.md`) gets a matching section documenting the two additive passes after the bug-finding pass and the gate, so the skill's routing target stays consistent.

**Mid-pipeline-entry prerequisite probe (the impl-missing-at-code-review case of AC-12).** The reshaped `fbk-code-review` skill is independently invocable; when invoked directly it must check that its upstream artifact (the implementation) is present before running. At mid-pipeline entry the skill calls the capability-entry prerequisite probe `fbk.precheck.check_prerequisites("code-review", <feature_dir>)` (the `precheck` module created by task-23). If the implementation artifact is missing, the skill names what's missing and offers to run the upstream phase (implement) — non-blocking, never a hard block. This is the `code-review` case of the four upstream-missing cases the probe handles. (`check_prerequisites` for `code-review` looks for an `implementation/` directory under the feature dir; if absent it returns the missing artifact + the upstream phase to run.)

## 3. Instructions

1. Read the current `assets/skills/fbk-code-review/SKILL.md` to locate the `## Detection-Verification Loop`, `## Post-Fix Verification`, and `## Retrospective` sections.

2. In `assets/skills/fbk-code-review/SKILL.md`, add a mid-pipeline-entry instruction near the top of the skill's flow (before the bug-finding pass runs): when invoked directly, call the capability-entry prerequisite probe `fbk.precheck.check_prerequisites("code-review", <feature_dir>)`; if the implementation artifact is missing, name what's missing and offer to run the upstream phase (implement), non-blocking — never hard-block. This is the impl-missing-at-code-review case of AC-12. Completion: `grep -q 'check_prerequisites' assets/skills/fbk-code-review/SKILL.md` and the body mentions the upstream phase to run when the implementation is missing.

3. In `assets/skills/fbk-code-review/SKILL.md`, add a new section after `## Post-Fix Verification` and before `## Retrospective` titled e.g. `## Quality scan, final test-review, and gate`. In it, in order:
   - Invoke `fbk-quality-scan` on the change set (compose the technique skill); it writes `ai-docs/<feature>/quality-scan.md`.
   - Then invoke `fbk-test-review` in its final mode over the tests covering the changed module; it writes the final test-review verdict artifact.
   - Then run the gate: `python3 "$HOME"/.claude/fbk-scripts/fbk.py code-review-gate ai-docs/<feature>` (use the feature directory path; match the arg shape the gate expects per task-34 — a single feature-dir path).
   Completion: in the file, the first line matching `fbk-quality-scan` comes before the first line matching `fbk-test-review`, which comes before the first line matching `code-review-gate`, and all three come after the first line matching `Spawn Detector with:`.

4. In `assets/fbk-docs/fbk-sdl-workflow/code-review-guide.md`, add a section documenting that after the detection-verification loop terminates, code review runs a top-five quality scan (via `fbk-quality-scan`, surface-only) and a final test-review pass (via `fbk-test-review`, flagging drifted tests), then runs `code-review-gate`. Keep the existing bug-finding methodology sections unchanged. Completion: `grep -q 'fbk-quality-scan' assets/fbk-docs/fbk-sdl-workflow/code-review-guide.md` and `grep -q 'code-review-gate' assets/fbk-docs/fbk-sdl-workflow/code-review-guide.md` succeed.

5. Run the paired ordering test: `bash tests/sdl-workflow/test-code-review-ordering.sh`. T1–T5 must pass (T2–T5 are the ordering assertions).

6. Re-sentinel the three code-review-path shell tests if (and only if) the skill/guide edits break their existing sentinels. This task owns the skill and guide edits, so it owns the re-sentineling triggered by those edits. The three tests to run after the edits:
   - `tests/sdl-workflow/test-code-review-skill.sh`
   - `tests/sdl-workflow/test-code-review-guide-extensions.sh`
   - `tests/sdl-workflow/test-code-review-integration.sh`

   For each, after applying the edits in steps 2–4:
   - Run `bash tests/sdl-workflow/<test>.sh`.
   - If it still passes, do not edit it (the edit's additions did not disturb existing sentinels).
   - If a sentinel fails because this task moved or renamed the prose it anchored on, update that sentinel in place to anchor on the new prose marker for the same load-bearing content. Keep the assertion load-bearing — anchor on the new verbatim string that carries the same meaning, never weaken to a trivially-passing form (no bare-word matches that survive deletion of the section, no `grep -q .` placeholders).
   - If a sentinel fails because this task genuinely removed a string a sentinel asserts (this task only adds, so this should be rare), report it rather than weakening the test.

   Append every test file you actually edit to this task's `files_to_modify`. The three test paths above are listed conditionally in `files_to_modify` — edit only the ones the run actually breaks.

## 4. Files to create/modify

- `assets/skills/fbk-code-review/SKILL.md` (modify)
- `assets/fbk-docs/fbk-sdl-workflow/code-review-guide.md` (modify)

## 5. Test requirements

- New tests: none authored here. Make `tests/sdl-workflow/test-code-review-ordering.sh` (task-05) assertions T2–T6 pass (T6 — the `check_prerequisites` sentinel — is satisfied by step 2's mid-pipeline-entry wiring).
- Existing tests impacted: the code-review path sentinel tests (`test-code-review-skill.sh`, `test-code-review-guide-extensions.sh`, `test-code-review-integration.sh`) grep this skill and guide. This task only adds content, so they should generally not break — but where an addition lands in a section whose prose-shape a sentinel anchored on, the sentinel may need re-anchoring. Re-sentinel in place per step 6 (anchor on the new verbatim string for the same load-bearing content; never weaken to a trivially-passing form). Edit only tests whose run actually fails after the edits.

## 6. Acceptance criteria

- AC-08: the skill runs the bug-finding pass first, then `fbk-quality-scan`, then `fbk-test-review` (final), then `code-review-gate`, in that order.
- Primary criterion: the task-05 ordering assertions pass.

## 7. Model

Sonnet

## 8. Wave

Wave 1
