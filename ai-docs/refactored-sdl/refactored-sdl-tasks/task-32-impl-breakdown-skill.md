---
id: task-32
type: implementation
wave: 2
covers: [AC-05]
files_to_modify:
  - assets/skills/fbk-breakdown/SKILL.md
  - assets/fbk-docs/fbk-sdl-workflow/task-compilation.md
test_tasks: [task-11]
dependencies: []
completion_gate: "the referenced test tasks pass"
---

## 1. Objective

Refactors `assets/skills/fbk-breakdown/SKILL.md` into slice-identification then per-slice work-unit authoring, gating lock application on a pre-lock `fbk-test-review` verdict and adding bounce-back-to-spec; and adds slice-then-pair guidance plus four-shape routing to `task-compilation.md`.

## 2. Context

Breakdown is reshaped from a single-pass decomposition into two steps: (1) **slice identification** — read each `## Slices` entry from the spec plus its contract pointer; (2) **per-slice work-unit authoring** — for each slice, per its declared `test-discipline`, produce the matching work-unit shape, loading only that one shape leaf (progressive disclosure). This is a refactor-then-extend of the skill body (read the current `assets/skills/fbk-breakdown/SKILL.md`).

Behavioral additions:
1. **Mid-pipeline-entry prerequisite probe (the spec-missing-at-breakdown case of AC-12)**: the reshaped `fbk-breakdown` skill is independently invocable; when invoked directly it calls the capability-entry prerequisite probe `fbk.precheck.check_prerequisites("breakdown", <feature_dir>)` (the `precheck` module created by task-23) at mid-pipeline entry. If the spec artifact (the `<feature>-spec.md` file) is missing, the skill names the missing artifact and offers to run the upstream phase (spec) — non-blocking, never a hard block. This is the `breakdown` case of the four upstream-missing cases the probe handles. (This is distinct from the preserved prior-stage `review-gate` call, which remains.)
2. **Slice-then-pair**: identify slices first, then author work units per slice (test task + impl task pairs, shaped by the slice's discipline). Route to the four shape leaves under `fbk-sdl-workflow/slice-shapes/` (created by task-33) via the `slice-shapes.md` index — load only the leaf for the current slice's `test-discipline`.
3. **Pre-lock `fbk-test-review` gates lock**: before hash-locking a slice's tests, invoke `fbk-test-review` in pre-lock mode over the full set of tests covering the changed module (including pre-existing tests a contract-preserving slice locks). Only an `accepted` verdict triggers `test-hash-gate` manifest population. Reference `fbk-test-review` by name and `test-hash-gate` by command.
4. **Bounce-back-to-spec**: if breakdown cannot write a work unit a less-familiar agent could execute, it names the specific spec gap and bounces back to spec (emit a `BOUNCE-BACK:` marker / report) rather than producing oversized work units. The breakdown gate fails on an unresolved bounce-back marker (task-30).

Preserve: the existing prior-stage `review-gate` call (breakdown invokes `review-gate` today as its prior-stage check — keep it). Preserve the existing test-task-agent / impl-task-agent / task.json assembly / task-review / breakdown-gate structure; layer the slice-shaped work on top.

The guide (`assets/fbk-docs/fbk-sdl-workflow/task-compilation.md`) gets: slice-identification-then-pairing guidance replacing the single-pass framing, and routing to the four shape leaves (the four shapes: new-contract, contract-preserving, contract-evolving, cross-cutting), with a one-line routing rule per shape.

**Prose-sentinel awareness.** Read `tests/sdl-workflow/test-skill-guide-dedup.sh` (it greps `feature-spec-guide.md`; check whether it also greps `task-compilation.md` or the breakdown skill) and any `tests/sdl-workflow/*` test enumerating the skill/phase set. This task ADDS content; if a sentinel asserts a string this task's edits move or remove, update that sentinel in place (do not delete assertions). The paired task-11 test is the breakdown-gate unit test (it does not grep the skill body); these skill/guide edits are validated by the sentinel tests and the wave-4 cross-cutting e2e.

## 3. Instructions

1. Read the current `assets/skills/fbk-breakdown/SKILL.md`, `assets/fbk-docs/fbk-sdl-workflow/task-compilation.md`, and `tests/sdl-workflow/test-skill-guide-dedup.sh`.

2. In `assets/skills/fbk-breakdown/SKILL.md`, add a mid-pipeline-entry instruction (near the top of the skill's flow, before slice identification): when invoked directly, call the capability-entry prerequisite probe `fbk.precheck.check_prerequisites("breakdown", <feature_dir>)`; if the spec artifact (the `<feature>-spec.md` file) is missing, name what's missing and offer to run the upstream phase (spec), non-blocking — never hard-block. This is the spec-missing-at-breakdown case of AC-12, distinct from the preserved prior-stage `review-gate` call. Completion: `grep -q 'check_prerequisites' assets/skills/fbk-breakdown/SKILL.md` and the body mentions offering to run spec when the spec file is missing.

3. In `assets/skills/fbk-breakdown/SKILL.md`, add a slice-identification step before work-unit authoring: read each `## Slices` entry from the spec plus its contract pointer. Then add per-slice authoring that routes to `slice-shapes.md` and loads only the leaf for the slice's `test-discipline`. Keep the existing prior-stage `review-gate` invocation. Completion: `grep -q 'slice' assets/skills/fbk-breakdown/SKILL.md` and `grep -q 'review-gate' assets/skills/fbk-breakdown/SKILL.md` both succeed.

4. Add the pre-lock test-review gating: before populating the test-lock manifest, invoke `fbk-test-review` (pre-lock mode) over the full test set for the changed module; only an `accepted` verdict triggers `test-hash-gate` manifest population. Completion: `grep -q 'fbk-test-review' assets/skills/fbk-breakdown/SKILL.md` and `grep -q 'test-hash-gate' assets/skills/fbk-breakdown/SKILL.md` succeed.

5. Add the bounce-back-to-spec instruction: when a work unit cannot be written for a less-familiar agent, name the specific spec gap and emit a `BOUNCE-BACK:` marker rather than producing oversized units. Completion: `grep -q 'BOUNCE-BACK\|bounce' assets/skills/fbk-breakdown/SKILL.md` succeeds.

6. In `assets/fbk-docs/fbk-sdl-workflow/task-compilation.md`, add slice-identification-then-pairing guidance and a four-shape routing table/section (one routing line per shape to its leaf under `slice-shapes/`). Completion: `grep -qi 'slice' assets/fbk-docs/fbk-sdl-workflow/task-compilation.md` and the four shape names each appear.

7. If any sentinel test asserts a string this task moved/removed, update it in place. Completion: `bash tests/sdl-workflow/test-skill-guide-dedup.sh` exits 0.

8. Run the paired unit test (regression confirmation): from `assets/fbk-scripts`, `python3 -m pytest tests/test_gates_breakdown.py -q`, and run `bash tests/sdl-workflow/test-skill-guide-dedup.sh`.

## 4. Files to create/modify

- `assets/skills/fbk-breakdown/SKILL.md` (modify)
- `assets/fbk-docs/fbk-sdl-workflow/task-compilation.md` (modify)

## 5. Test requirements

- New tests: none authored here. The paired task-11 test is the breakdown-gate unit test (satisfied by task-30's code); these skill/guide edits are validated by the sentinel tests and the wave-4 cross-cutting e2e.
- Existing tests impacted: `tests/sdl-workflow/test-skill-guide-dedup.sh` and any phase-set-enumerating sentinel — update in place if a moved/removed asserted string requires it; do not delete assertions.

## 6. Acceptance criteria

- AC-05: the breakdown skill identifies slices then authors per-slice work units shaped by `test-discipline`, gates lock on a pre-lock `accepted` test-review verdict, and bounces back to spec on an unwritable work unit; the guide documents slice-then-pair and the four shapes.
- Primary criterion: the breakdown-gate unit test (task-11) passes and the sentinel tests stay green.

## 7. Model

Sonnet

## 8. Wave

Wave 2
