---
id: task-24
type: implementation
wave: 1
covers: [AC-08]
files_to_modify:
  - assets/skills/fbk-code-review/SKILL.md
  - assets/fbk-docs/fbk-sdl-workflow/code-review-guide.md
test_tasks: [task-05]
dependencies: []
completion_gate: "the referenced test tasks pass"
---

## 1. Objective

Extends `assets/skills/fbk-code-review/SKILL.md` so that after the existing bug-finding pass it invokes `fbk-quality-scan`, then `fbk-test-review` (final pass), then the `code-review-gate`, in that exact order, and adds the matching passes to the code-review guide.

## 2. Context

The code-review phase gains two additive passes after its preserved bug-finding loop. The order is a sequencing contract (AC-08): the existing bug-finding loop runs first (unchanged), then `fbk-quality-scan`, then `fbk-test-review` (final), then the new `code-review-gate`. The bug-finding loop itself is untouched.

The ordering test (`tests/sdl-workflow/test-code-review-ordering.sh`, task-05) greps `fbk-code-review/SKILL.md` for the line numbers of four sentinels and asserts they appear in this sequence:
1. the bug-finding sentinel — the test matches `Detector\|Detection-Verification` (both already present in the current skill body)
2. `fbk-quality-scan`
3. `fbk-test-review`
4. `code-review-gate`

So the three new sentinel strings (`fbk-quality-scan`, `fbk-test-review`, `code-review-gate`) must appear in the body in that order, all AFTER the existing Detection-Verification Loop section. The current skill (read it) has the `## Detection-Verification Loop` section, then `## Post-Fix Verification`, then `## Broad-Scope Reviews`, etc., and ends with `## Retrospective`. Insert the two technique invocations and the gate call as a new section placed AFTER the Detection-Verification Loop and AFTER Post-Fix Verification, and BEFORE the Retrospective section (so the gate runs on a settled change set). The first occurrence of `Detector`/`Detection-Verification` is near the top, so any placement after the loop satisfies the ordering.

The skill invokes the technique skills by name (they are composed) and runs the gate via the standard form `python3 "$HOME"/.claude/fbk-scripts/fbk.py code-review-gate <args>`. Use the installed path form, not `assets/...` (AC-22). The `code-review-gate` itself is implemented by task-34 (wave 3); this skill only needs to call it by command name — the call is a pinned-contract reference, not a build-order dependency.

The code-review guide (`assets/fbk-docs/fbk-sdl-workflow/code-review-guide.md`) gets a matching section documenting the two additive passes after the bug-finding pass and the gate, so the skill's routing target stays consistent.

## 3. Instructions

1. Read the current `assets/skills/fbk-code-review/SKILL.md` to locate the `## Detection-Verification Loop`, `## Post-Fix Verification`, and `## Retrospective` sections.

2. In `assets/skills/fbk-code-review/SKILL.md`, add a new section after `## Post-Fix Verification` and before `## Retrospective` titled e.g. `## Quality scan, final test-review, and gate`. In it, in order:
   - Invoke `fbk-quality-scan` on the change set (compose the technique skill); it writes `ai-docs/<feature>/quality-scan.md`.
   - Then invoke `fbk-test-review` in its final mode over the tests covering the changed module; it writes the final test-review verdict artifact.
   - Then run the gate: `python3 "$HOME"/.claude/fbk-scripts/fbk.py code-review-gate ai-docs/<feature>` (use the feature directory path; match the arg shape the gate expects per task-34 — a single feature-dir path).
   Completion: in the file, the first line matching `fbk-quality-scan` comes before the first line matching `fbk-test-review`, which comes before the first line matching `code-review-gate`, and all three come after the first line matching `Detector`/`Detection-Verification`.

3. In `assets/fbk-docs/fbk-sdl-workflow/code-review-guide.md`, add a section documenting that after the detection-verification loop terminates, code review runs a top-five quality scan (via `fbk-quality-scan`, surface-only) and a final test-review pass (via `fbk-test-review`, flagging drifted tests), then runs `code-review-gate`. Keep the existing bug-finding methodology sections unchanged. Completion: `grep -q 'fbk-quality-scan' assets/fbk-docs/fbk-sdl-workflow/code-review-guide.md` and `grep -q 'code-review-gate' assets/fbk-docs/fbk-sdl-workflow/code-review-guide.md` succeed.

4. Run the paired ordering test: `bash tests/sdl-workflow/test-code-review-ordering.sh`. T1–T5 must pass (T2–T5 are the ordering assertions).

5. Verify the existing code-review path sentinel tests still pass (the prose this work touches is grepped by them): run `bash tests/sdl-workflow/test-code-review-skill.sh`, `bash tests/sdl-workflow/test-code-review-guide-extensions.sh`, and `bash tests/sdl-workflow/test-code-review-integration.sh` if present, and fix only newly-broken sentinels that assert content this task changed. If a sentinel asserts a string this task removed (it should not — this task only adds), report it rather than weakening the test.

## 4. Files to create/modify

- `assets/skills/fbk-code-review/SKILL.md` (modify)
- `assets/fbk-docs/fbk-sdl-workflow/code-review-guide.md` (modify)

## 5. Test requirements

- New tests: none authored here. Make `tests/sdl-workflow/test-code-review-ordering.sh` (task-05) assertions T2–T5 pass.
- Existing tests impacted: the code-review path sentinel tests (`test-code-review-skill.sh`, `test-code-review-guide-extensions.sh`, `test-code-review-integration.sh`) grep this skill and guide; they must stay green. This task only adds content, so they should not break. Do not edit those tests.

## 6. Acceptance criteria

- AC-08: the skill runs the bug-finding pass first, then `fbk-quality-scan`, then `fbk-test-review` (final), then `code-review-gate`, in that order.
- Primary criterion: the task-05 ordering assertions pass.

## 7. Model

Sonnet

## 8. Wave

Wave 1
