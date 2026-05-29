---
id: task-35
type: implementation
wave: 4
covers: [AC-22]
files_to_modify:
  - assets/fbk-docs/fbk-sdl-workflow.md
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

Use installed path forms throughout (the index is an installed asset — AC-22 path class 1; no `assets/` prefix in its body). The per-asset installed-path compliance of the new leaves themselves is honored by the authoring tasks (task-25, task-27, task-28, task-33) — this task wires the index and must not introduce an `assets/` prefix.

The paired test (task-13, wave 4) is the cross-cutting verification: the installer e2e (`test-refactored-sdl-install.sh`) asserts the new skills/agents/docs install under `~/.claude/` (including `intent-guide.md`, `design-guide.md`, `capability-entry.md`), and the reference-integrity extension (`test-reference-integrity.sh`) asserts no installed-asset body contains the `assets/` path prefix. This index-wiring task ensures the new leaves are reachable from the index (reference-integrity routed-paths-resolve check) and that the index itself carries no `assets/` prefix.

## 3. Instructions

1. Read the current `assets/fbk-docs/fbk-sdl-workflow.md` (the pipeline description and the "Stage Guides" routing list).

2. Update the pipeline description (the opening line and any pipeline summary) to include intent and design as the first two phases, preceding spec, and keep review/breakdown/code-review/implement. Completion: `grep -qi 'intent' assets/fbk-docs/fbk-sdl-workflow.md` and `grep -qi 'design' assets/fbk-docs/fbk-sdl-workflow.md` succeed in the pipeline-description context.

3. Add the four new routing rows to the "Stage Guides" section (intent-guide, design-guide, slice-shapes, capability-entry) using installed path forms (`fbk-sdl-workflow/...`). Keep all existing rows. Completion: `grep -q 'intent-guide.md' assets/fbk-docs/fbk-sdl-workflow.md`, `grep -q 'design-guide.md' ...`, `grep -q 'slice-shapes.md' ...`, and `grep -q 'capability-entry.md' ...` all succeed.

4. Confirm the index body carries no `assets/` path prefix: `grep -c '\bassets/' assets/fbk-docs/fbk-sdl-workflow.md` returns 0.

5. Run the paired tests: `bash tests/installer/test-refactored-sdl-install.sh` (requires all new skills/agents/docs to exist — they are produced by waves 1–2 tasks; this index wiring makes the docs reachable and T12–T14 for the routed docs pass once those leaves exist and install) and `bash tests/sdl-workflow/test-reference-integrity.sh` (routed paths resolve; no `assets/` prefix). Both must pass once all upstream slices are complete.

## 4. Files to create/modify

- `assets/fbk-docs/fbk-sdl-workflow.md` (modify)

## 5. Test requirements

This task is the integration-wiring half of the cross-cutting verification slice. Its paired test (task-13) is the installer e2e + reference-integrity extension. This task makes the index navigable so the routed-path-resolution and reachability assertions pass; the installer assertions for the new leaves pass once the leaf-producing tasks (waves 1–2) are complete. No new tests are written here. Do not edit the test files.

## 6. Acceptance criteria

- AC-22: the SDL index names the two new phases and routes to the new leaves so every new asset is reachable from the index; the index body uses installed path forms (no `assets/` prefix). Per-asset installed-path compliance of the leaves is honored by their authoring tasks.
- Primary criterion: the task-13 installer e2e and reference-integrity tests pass once all upstream slices are complete.

## 7. Model

Sonnet

## 8. Wave

Wave 4
