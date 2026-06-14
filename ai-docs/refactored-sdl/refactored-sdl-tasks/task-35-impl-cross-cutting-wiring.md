---
id: task-35
type: implementation
wave: 4
covers: [AC-22]
files_to_modify:
  - assets/fbk-docs/fbk-sdl-workflow.md
  - assets/skills/fbk-spec-review/SKILL.md
  - assets/skills/fbk-implement/SKILL.md
  # Plus any tests/sdl-workflow/ files surfaced by the step-8 enumeration audit
  # (likely candidates: test-no-old-path-patterns.sh, test-implementation-pipeline.sh,
  # test-orchestrator-pipeline-integration.sh, test-orchestration-extensions.sh,
  # test-reference-integrity.sh, plus any others found via the grep -lr in step 8).
  # Each test the audit actually edits MUST be appended here at edit time.
test_tasks: [task-13]
dependencies: []
completion_gate: "the referenced test tasks pass"
---

## 1. Objective

Wires the two new phases into the SDL index (`assets/fbk-docs/fbk-sdl-workflow.md`) — adding intent and design to the pipeline description and routing to the new leaves — so the assembled chain is navigable and every new asset is reachable from the index.

## 2. Context

`fbk-sdl-workflow.md` is the SDL index. Today it describes a 4-stage pipeline (Spec → Review → Breakdown → Implement) and carries a "Stage Guides" routing table that points each phase to its guide leaf. The refactoring adds two front-of-pipeline phases — **intent** and **design** — and several new routed leaves; this task wires them into the index so the new assets are reachable (the integration wiring that makes the assembled chain navigable).

What to add (read the current `assets/fbk-docs/fbk-sdl-workflow.md` first):
1. Update the pipeline description so it names the new phase order — intent → design → spec → (review) → breakdown → code-review → implement (the refactoring's six-phase shape; keep the existing review and implement phases). State that intent and design precede spec.
2. Add Stage-Guides routing rows for the new phases and leaves:
   - When co-authoring intent → `/fbk-intent` loads `fbk-sdl-workflow/intent-guide.md`
   - When co-authoring a design → `/fbk-design` loads `fbk-sdl-workflow/design-guide.md`
   - When identifying slices during breakdown → `fbk-sdl-workflow/slice-shapes.md` (which routes to the four shape leaves)
   - When a phase is invoked directly (mid-pipeline entry) → `fbk-sdl-workflow/capability-entry.md`
3. Keep the existing rows (spec, review, breakdown, implement, code-review, corrective, retrospective) intact.

**Doc-only reframes (NO behavioral change).** Two existing skills are reframed in docs only — one-line framing notes, no change to their behavior, gates, agents, or routing:
- `assets/skills/fbk-spec-review/SKILL.md` — add a one-line framing note that it produces the spec gate's semantic anchor (its review artifact is the semantic-anchor input the spec gate reads). This is purely a framing note; do NOT change what the skill does. The spec keeps `review.py`/`review-gate`/`validate_review` untouched (the code-review gate is a separate new module), so this reframe must not touch any gate call, agent spawn, or routing line.
- `assets/skills/fbk-implement/SKILL.md` — add a one-line framing note that it is phase five of the six-phase refactored SDL (intent → design → spec → breakdown → code-review → implement). Framing note only; no behavioral change.

Use installed path forms throughout (the index is an installed asset — AC-22 path class 1; no `assets/` prefix in its body). The per-asset installed-path compliance of the new leaves themselves is honored by the authoring tasks (task-25, task-27, task-28, task-33) — this task wires the index and must not introduce an `assets/` prefix.

The paired test (task-13, wave 4) is the cross-cutting verification: the installer e2e (`test-refactored-sdl-install.sh`) asserts the new skills/agents/docs install under `~/.claude/` (including `intent-guide.md`, `design-guide.md`, `capability-entry.md`), and the reference-integrity extension (`test-reference-integrity.sh`) asserts no installed-asset body contains the `assets/` path prefix. This index-wiring task ensures the new leaves are reachable from the index (reference-integrity routed-paths-resolve check) and that the index itself carries no `assets/` prefix.

## 3. Instructions

1. Read the current `assets/fbk-docs/fbk-sdl-workflow.md` (the pipeline description and the "Stage Guides" routing list).

2. Update the pipeline description (the opening line and any pipeline summary) to include intent and design as the first two phases, preceding spec, and keep review/breakdown/code-review/implement. Completion: `grep -qi 'intent' assets/fbk-docs/fbk-sdl-workflow.md` and `grep -qi 'design' assets/fbk-docs/fbk-sdl-workflow.md` succeed in the pipeline-description context.

3. Add the four new routing rows to the "Stage Guides" section (intent-guide, design-guide, slice-shapes, capability-entry) using installed path forms (`fbk-sdl-workflow/...`). Keep all existing rows. Completion: `grep -q 'intent-guide.md' assets/fbk-docs/fbk-sdl-workflow.md`, `grep -q 'design-guide.md' ...`, `grep -q 'slice-shapes.md' ...`, and `grep -q 'capability-entry.md' ...` all succeed.

4. In `assets/skills/fbk-spec-review/SKILL.md`, add a one-line framing note that the skill produces the spec gate's semantic anchor (its review artifact is the semantic-anchor input the spec gate reads). Doc-only: do NOT change any behavior, gate call, agent spawn, or routing line. Completion: `grep -qi 'semantic anchor' assets/skills/fbk-spec-review/SKILL.md` succeeds and no gate/agent/routing line was modified.

5. In `assets/skills/fbk-implement/SKILL.md`, add a one-line framing note that the skill is phase five of the six-phase refactored SDL (intent → design → spec → breakdown → code-review → implement). Doc-only: no behavioral change. Completion: `grep -qi 'phase five' assets/skills/fbk-implement/SKILL.md` succeeds and no behavioral line was modified.

6. Confirm both reframed skill bodies carry no `assets/` path prefix: `grep -c '\bassets/' assets/skills/fbk-spec-review/SKILL.md` and `grep -c '\bassets/' assets/skills/fbk-implement/SKILL.md` each return 0.

7. Confirm the index body carries no `assets/` path prefix: `grep -c '\bassets/' assets/fbk-docs/fbk-sdl-workflow.md` returns 0.

8. Audit and update hard-coded SDL enumerations in `tests/sdl-workflow/`. Several shell tests enumerate the SDL phases or the asset list (skills, agents, docs) with literal lists — when the refactoring adds the two new phases (intent, design) or the new skills/agents/docs to a list a test enumerates, that test's expected list silently drifts out of date and either misses the new items or rejects them. Locate the candidates and update each one that names a list this refactoring grew:
   - Likely candidates to read first: `tests/sdl-workflow/test-no-old-path-patterns.sh`, `test-implementation-pipeline.sh`, `test-orchestrator-pipeline-integration.sh`, `test-orchestration-extensions.sh`, `test-reference-integrity.sh`.
   - Discover any others via: `grep -lr 'fbk-spec\|fbk-breakdown\|fbk-code-review\|fbk-implement' tests/sdl-workflow/` — every match is a file that names a current SDL skill and may carry an enumeration that needs the two new skills (`fbk-intent`, `fbk-design`) and any new technique skills / docs added by this refactoring.
   - For each candidate: open it, look for arrays/loops/`for X in ...` constructs that enumerate the SDL phase set or the SDL asset set. Where the rewrite added items to that list, update the literal to match the new full list. Where a test enumerates the four current SDL skills, add `fbk-intent` and `fbk-design` (and any other new skills/agents/docs the rewrite adds to that enumeration's scope).
   - Do not weaken assertions to skip the new items — the goal is the test enumerates the now-complete set. Do not edit tests whose enumeration is intentional (e.g. tests that specifically assert legacy behavior over the pre-refactor list); for those, report and leave alone.
   - Add every file you actually edit to `files_to_modify` in this task's frontmatter at edit time. The list of candidates above is not exhaustive — `files_to_modify` may grow as the audit finds more enumerations.

9. Run the paired tests: `bash tests/installer/test-refactored-sdl-install.sh` (requires all new skills/agents/docs to exist — they are produced by waves 1–2 tasks; this index wiring makes the docs reachable and T12–T14 for the routed docs pass once those leaves exist and install) and `bash tests/sdl-workflow/test-reference-integrity.sh` (routed paths resolve; no `assets/` prefix). Both must pass once all upstream slices are complete. Run any audited shell tests from step 8 to confirm they now pass against the new enumerations.

## 4. Files to create/modify

- `assets/fbk-docs/fbk-sdl-workflow.md` (modify)
- `assets/skills/fbk-spec-review/SKILL.md` (modify — one-line doc-only framing note; no behavioral change)
- `assets/skills/fbk-implement/SKILL.md` (modify — one-line doc-only framing note; no behavioral change)

File-scope justification: this is the cross-cutting integration-wiring task. The two skill edits are each a single one-line framing note (no behavioral change, no new hunks of logic), so they sit naturally alongside the index wiring rather than warranting their own tasks — splitting a one-line doc note into a separate task would be an artificial boundary. The step-8 enumeration-audit edits over `tests/sdl-workflow/` are each a literal-list update sized like the framing notes (extend an existing list, no new logic); they belong with the index-wiring because the index changes and the test-enumeration changes are the same cross-cutting question — "which lists name the full SDL asset set after this refactoring." Total change is well under the lines/hunks budget even with the audited files added.

## 5. Test requirements

This task is the integration-wiring half of the cross-cutting verification slice. Its paired test (task-13) is the installer e2e + reference-integrity extension. This task makes the index navigable so the routed-path-resolution and reachability assertions pass; the installer assertions for the new leaves pass once the leaf-producing tasks (waves 1–2) are complete. No new tests are written here. Do not edit the test files.

## 6. Acceptance criteria

- AC-22: the SDL index names the two new phases and routes to the new leaves so every new asset is reachable from the index; the index body uses installed path forms (no `assets/` prefix). Per-asset installed-path compliance of the leaves is honored by their authoring tasks.
- Primary criterion: the task-13 installer e2e and reference-integrity tests pass once all upstream slices are complete.

## 7. Model

Sonnet

## 8. Wave

Wave 4
