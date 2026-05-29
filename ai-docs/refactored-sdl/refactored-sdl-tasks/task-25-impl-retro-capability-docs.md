---
id: task-25
type: implementation
wave: 1
covers: [AC-20, AC-12]
files_to_create:
  - assets/fbk-docs/fbk-sdl-workflow/capability-entry.md
  - assets/fbk-scripts/fbk/retro.py
files_to_modify:
  - assets/fbk-docs/fbk-sdl-workflow/retrospective-guide.md
test_tasks: [task-05, task-06]
dependencies: []
completion_gate: "the referenced test tasks pass"
---

## 1. Objective

Adds intent and design stage sections (with an append-reads-before-write convention) to the retrospective guide, produces the importable `fbk/retro.py` append mechanism the phase skills call, and produces the `capability-entry.md` leaf the phase skills' mid-pipeline-entry step routes to.

## 2. Context

Two doc changes plus one small module that complete the cross-cutting work for capability-entry and the two-phase retrospective preservation:

0. **Retrospective append module** (`assets/fbk-scripts/fbk/retro.py`, new): an importable `append_section(retrospective_path, stage_name, content)` that the phase skills call to add a stage section. It reads the retrospective file before writing (read-before-write) and appends the new stage section so prior stage sections survive — it never truncates or overwrites. If the file does not exist yet it creates it. This is the mechanism that backs the append convention the retrospective guide documents, and is exactly what task-05's `test_retro.py` imports and verifies (appending stage section A then stage section B leaves both present).

1. **Retrospective guide** (`assets/fbk-docs/fbk-sdl-workflow/retrospective-guide.md`): the current guide lists numbered stage sections for Spec (Stage 1), Spec Review (Stage 2), Breakdown (Stage 3), Implementation (Stage 4), Code Review (Stage 5). Add stage sections for the two new phases — **Intent** and **Design** — placed before Spec, giving a seven-stage list: Intent, Design, Spec, Spec Review, Breakdown, Implementation, Code Review. The existing Spec Review stage is kept (it records real activity — council review findings — and the guide must keep a place for it); no existing stage's content is dropped or folded. Number the list 1–7 consistently, or use named (unnumbered) section headers — whichever reads cleanly — but do not leave unnumbered Intent/Design bullets sitting above an unchanged "Stage 1: Spec". Intent and Design precede Spec in the new pipeline. Also make the append-reads-before-write convention explicit: each stage reads the retrospective file before writing so prior stages survive (the current guide's top line already says "Read the file before writing to preserve existing content from prior stages" — reinforce that every new and reshaped phase appends rather than overwrites, via `fbk.retro.append_section`). The two-phase preservation test (task-05's `test_retro.py`) imports `fbk.retro.append_section` and verifies that appending stage section A then stage section B leaves both present — so the retro module this task creates is what makes that test pass; this doc change is the instruction that makes the phase skills follow the append convention (AC-20).

2. **Capability-entry leaf** (`assets/fbk-docs/fbk-sdl-workflow/capability-entry.md`, new): the doc the phase skills route to for mid-pipeline entry. It states: each phase is independently invocable; before proceeding, a directly-invoked phase checks its prior gate is satisfiable (via the `fbk/precheck.py` probe from task-23, function `check_prerequisites`); if a prerequisite is missing, the phase names the specific missing artifact and the upstream phase, and offers to run that upstream phase rather than hard-blocking. List the four upstream-missing cases (design needs prd.md from intent; spec needs design-manifest.md from design; breakdown needs the spec from spec; code-review needs implementation/ from implement). Reference the probe by its installed path form `.claude/fbk-scripts/precheck.py` (or by the command/library call the skills use) — not `assets/...` (AC-22). This is a referenced leaf: give it a one-line load condition (`Load condition: routed by a phase skill's mid-pipeline-entry step when the phase is invoked directly.`).

This task's two test_tasks are task-05 (retrospective preservation — its `test_retro.py` imports the `fbk.retro.append_section` this task creates) and task-06 (precheck — the capability-entry doc routes to the probe that task-06 covers; task-23 implements the probe, this task documents how phase skills use it). The capability-entry test in task-13's UV maps to the skills wiring; this doc supplies the routed instruction.

## 3. Instructions

1. Create `assets/fbk-scripts/fbk/retro.py` with an importable `append_section(retrospective_path, stage_name, content)`:
   - Read the existing file content first if the file exists (read-before-write); start from empty content if it does not.
   - Compose the new stage section (a `## ` heading derived from `stage_name`, followed by `content`) and append it to the prior content — never truncate or overwrite the prior content.
   - Write the combined content back. Prior stage sections must survive a subsequent append.
   - Keep it small and dependency-free (stdlib only), matching the style of the other `fbk/` utility modules.
   Completion: `python3 -c "from fbk.retro import append_section"` succeeds from `assets/fbk-scripts`, and task-05's `python3 -m pytest tests/test_retro.py -q` passes (appending stage A then stage B leaves both present).

2. In `assets/fbk-docs/fbk-sdl-workflow/retrospective-guide.md`, add Intent and Design stage sections before Spec and reshape the "Stage sections" list to the seven stages below, in this order, losing no existing content. Do NOT prepend unnumbered Intent/Design bullets ahead of an unchanged "Stage 1: Spec" (which would leave the guide reading Intent, Design, "Stage 1: Spec", … with mismatched numbering). The current list is `Stage 1: Spec`, `Stage 2: Spec Review`, `Stage 3: Breakdown`, `Stage 4: Implementation`, `Stage 5: Code Review`. Reshape it to these seven stages in pipeline order:
   - **Intent** — clarifying questions that revealed what the work is and why, the PRD/inventory produced, open questions deferred
   - **Design** — the module shape and contracts proposed, the decisions appended to the durable decisions log, the decomposition rationale
   - **Spec** — (the existing Spec stage content, unchanged)
   - **Spec Review** — (the existing Spec Review stage content, unchanged — keep it; it records real activity, the council review findings)
   - **Breakdown** — (the existing Breakdown stage content, unchanged)
   - **Implementation** — (the existing Implementation stage content, unchanged)
   - **Code Review** — (the existing Code Review stage content, unchanged)

   Add Intent and Design before Spec; keep all five existing stage sections (Spec, Spec Review, Breakdown, Implementation, Code Review) with their content intact — none is dropped or folded into another. Number the seven stages 1–7 consistently (Stage 1 Intent … Stage 7 Code Review), OR drop the "Stage N:" numbering entirely and use plain named section headers (`**Intent**`, `**Design**`, …) — choose whichever reads cleanly, but do not leave a half-numbered list with a stale "Stage 1: Spec" still in it. Completion: each of `Intent`, `Design`, `Spec`, `Spec Review`, `Breakdown`, `Implementation`, `Code Review` appears as a stage-section header in the guide (`for s in Intent Design Spec "Spec Review" Breakdown Implementation "Code Review"; do grep -qi "$s" assets/fbk-docs/fbk-sdl-workflow/retrospective-guide.md; done`); if numbered, the headers run 1–7 with no gaps or duplicates and no leftover "Stage 1: Spec"; the guide still states the read-before-write/append convention.

3. Reinforce the append convention: ensure the guide states that each new and reshaped phase appends its stage section and reads the file first so prior stages survive, and that the append is performed via `fbk.retro.append_section`. Completion: `grep -qi 'read the file before writing\|append' assets/fbk-docs/fbk-sdl-workflow/retrospective-guide.md` succeeds.

4. Create `assets/fbk-docs/fbk-sdl-workflow/capability-entry.md` as a referenced leaf with a one-line load condition, then the capability-entry model: phases are independently invocable; a directly-invoked phase runs the prerequisite probe; on a missing prerequisite it names the missing artifact + upstream phase and offers the upstream phase, never hard-blocking. Enumerate the four upstream-missing cases. Reference the probe by its installed path form. Completion: `[ -s assets/fbk-docs/fbk-sdl-workflow/capability-entry.md ]` and `grep -qi 'upstream' assets/fbk-docs/fbk-sdl-workflow/capability-entry.md` succeed; the file contains no `assets/` path prefix (`grep -c '\bassets/' assets/fbk-docs/fbk-sdl-workflow/capability-entry.md` returns 0).

5. Run the paired tests: from `assets/fbk-scripts`, `python3 -m pytest tests/test_retro.py -q` (task-05's retrospective-preservation test against `fbk.retro.append_section`, must pass) and confirm the precheck unit test still passes (`python3 -m pytest tests/test_precheck.py -q`, owned by task-23/task-06).

## 4. Files to create/modify

- `assets/fbk-docs/fbk-sdl-workflow/capability-entry.md` (create)
- `assets/fbk-scripts/fbk/retro.py` (create)
- `assets/fbk-docs/fbk-sdl-workflow/retrospective-guide.md` (modify)

## 5. Test requirements

- New tests: none authored here. The retrospective-preservation test (task-05's `test_retro.py`) imports `fbk.retro.append_section` — this task creates that module so the test passes — and this task also supplies the doc instruction that makes the phase skills honor the append convention. The precheck test (task-06) is satisfied by task-23; this task documents the probe's use.
- Existing tests impacted: search `tests/sdl-workflow/` for any test enumerating the retrospective stage list; if one hard-codes the stage set, the phase-skill-modifications slice (task-31/task-32) re-sentinels prose tests — do not modify such a test here unless it asserts content this task changed.

## 6. Acceptance criteria

- AC-20: `fbk.retro.append_section` reads-before-writes and preserves prior stage sections, and the retrospective guide carries Intent and Design stage sections and states the append-reads-before-write convention, so two phases running in sequence preserve both stage sections.
- AC-12: the capability-entry leaf routes to the prerequisite probe and documents the four upstream-missing cases with the name-and-offer (non-blocking) behavior.
- Primary criterion: the task-05 and task-06 tests pass.

## 7. Model

Sonnet

## 8. Wave

Wave 1
