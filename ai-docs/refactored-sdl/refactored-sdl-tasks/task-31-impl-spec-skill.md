---
id: task-31
type: implementation
wave: 2
covers: [AC-04]
files_to_modify:
  - assets/skills/fbk-spec/SKILL.md
  - assets/fbk-docs/fbk-sdl-workflow/feature-spec-guide.md
test_tasks: [task-10]
dependencies: []
completion_gate: "the referenced test tasks pass"
---

## 1. Objective

Refactors `assets/skills/fbk-spec/SKILL.md` to consume intent + design inputs, compose `fbk-grilling` narrowed to "how" questions, and author the `## Slices` block; and adds the `## Slices` format and narrow-grilling guidance to `feature-spec-guide.md`.

## 2. Context

The spec phase narrows to "how." After this change the spec consumes the upstream PRD + behavior inventory + design pages + manifest, records only tech choices / file organization / integration / testing strategy / module-touch policy / slice declarations, grills only on "how," and bounces back to design if the design under-specifies. This is a refactor-then-extend of the skill body (read the current `assets/skills/fbk-spec/SKILL.md`).

Three behavioral additions:
1. **Consume intent + design**: the skill's entry/inputs note that the spec builds on `ai-docs/<feature>/prd.md`, `behavior-inventory.yaml`, the `design/` pages, and `design-manifest.md`. (Mid-pipeline entry / prerequisite handling is owned by the capability-entry wiring; this skill only states the inputs.)
2. **Compose `fbk-grilling` narrowed to "how"**: the current `## Closing ambiguity` section hand-rolls the grilling loop. Re-point it to compose the `fbk-grilling` technique skill, narrowed to "how" questions (tech/organization/integration), instead of inline grilling prose. Reference `fbk-grilling` by name.
3. **Author the `## Slices` block**: the skill instructs authoring a `## Slices` block per the slice-declaration format (one entry per slice with `name`, `description`, `test-discipline` from the four-shape taxonomy, `contract` pointer, and `retired-tests` for contract-evolving). The spec gate validates this block (task-29).

The guide (`assets/fbk-docs/fbk-sdl-workflow/feature-spec-guide.md`) gets: the `## Slices` declaration format (the YAML block shape with the four `test-discipline` values) and narrowed grilling guidance ("how" questions only, composed via the grilling technique).

**Prose-sentinel awareness.** `tests/sdl-workflow/test-skill-guide-dedup.sh` greps `fbk-spec/SKILL.md` and `feature-spec-guide.md` for exact strings. Read that test before editing. This task only ADDS content (slice authoring, grilling composition) and re-points the Closing-ambiguity section — it must not delete a string the dedup sentinel asserts. If a sentinel asserts a phrase in the `## Closing ambiguity` section that the re-point removes, update that sentinel in `test-skill-guide-dedup.sh` to match the new composed-grilling wording (sentinels are updated in place, not removed — this is the `phase-skill-modifications` slice's "re-sentinel the prose-anchored tests" work). The task-10 paired test is the spec-gate unit test (it does not grep the skill body); the skill/guide edits here are validated by the dedup sentinel and the cross-cutting reference-integrity/e2e in wave 4.

## 3. Instructions

1. Read the current `assets/skills/fbk-spec/SKILL.md`, `assets/fbk-docs/fbk-sdl-workflow/feature-spec-guide.md`, and `tests/sdl-workflow/test-skill-guide-dedup.sh`.

2. In `assets/skills/fbk-spec/SKILL.md`, state the upstream inputs (PRD, behavior inventory, design pages, design manifest) the spec consumes. Use installed path forms where a path is referenced.

3. Re-point the `## Closing ambiguity` section to compose `fbk-grilling` narrowed to "how" questions (tech choices, file organization, integration). Reference `fbk-grilling` by name. Completion: `grep -q 'fbk-grilling' assets/skills/fbk-spec/SKILL.md` succeeds.

4. Add a `## Slices` authoring instruction to the skill: author a `## Slices` block per the slice-declaration format (one entry per slice with `name`, `description`, `test-discipline`, `contract`, and `retired-tests` for contract-evolving). Note the spec gate validates it. Completion: `grep -qi 'slice' assets/skills/fbk-spec/SKILL.md` and `grep -q 'test-discipline' assets/skills/fbk-spec/SKILL.md` succeed.

5. In `assets/fbk-docs/fbk-sdl-workflow/feature-spec-guide.md`, add a `## Slices` declaration-format subsection showing the YAML block (the `slices:` list with `name`, `description`, `test-discipline` enumerating the four values, `contract`, `retired-tests`) and add narrowed-grilling guidance (the spec grills only on "how," composed via the grilling technique). Completion: `grep -q 'test-discipline' assets/fbk-docs/fbk-sdl-workflow/feature-spec-guide.md` and `grep -qi 'slices' assets/fbk-docs/fbk-sdl-workflow/feature-spec-guide.md` succeed.

6. If `test-skill-guide-dedup.sh` greps a string in the Closing-ambiguity section that the re-point removed, update that sentinel string in the test to match the new wording (update in place; do not delete the assertion). Completion: `bash tests/sdl-workflow/test-skill-guide-dedup.sh` exits 0.

7. Run the paired unit test (regression confirmation that the spec gate still behaves): from `assets/fbk-scripts`, `python3 -m pytest tests/test_gates_spec.py -q`, and run `bash tests/sdl-workflow/test-skill-guide-dedup.sh`.

## 4. Files to create/modify

- `assets/skills/fbk-spec/SKILL.md` (modify)
- `assets/fbk-docs/fbk-sdl-workflow/feature-spec-guide.md` (modify)

## 5. Test requirements

- New tests: none authored here. The paired task-10 test is the spec-gate unit test (satisfied by task-29's code); this task's skill/guide edits are validated by the dedup sentinel test and the wave-4 cross-cutting e2e.
- Existing tests impacted: `tests/sdl-workflow/test-skill-guide-dedup.sh` greps this skill and guide — update its sentinels in place if the re-point changes an asserted string; do not remove assertions.

## 6. Acceptance criteria

- AC-04: the spec skill consumes intent + design, composes grilling narrowed to "how," and authors the `## Slices` block; the guide documents the format. (The gate enforcement of the block is task-29.)
- Primary criterion: the dedup sentinel test stays green and the spec-gate unit test (task-10) passes.

## 7. Model

Sonnet

## 8. Wave

Wave 2
