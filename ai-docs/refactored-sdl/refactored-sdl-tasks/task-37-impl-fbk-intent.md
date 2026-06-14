---
id: task-37
type: implementation
wave: 2
covers: [AC-01]
files_to_create:
  - assets/skills/fbk-intent/SKILL.md
test_tasks: [task-36]
dependencies: [task-21, task-23]
completion_gate: "task-36 tests pass"
---

## 1. Objective

Produces the `fbk-intent` phase skill (`assets/skills/fbk-intent/SKILL.md`) — the first SDL phase — which opens an interview, delegates PRD drafting to the product-author agent, composes the grilling and fresh-eyes technique skills, reads/updates the durable architecture/intent overview, produces the intent artifacts, and runs the intent gate.

## 2. Context

`fbk-intent` is the front-of-pipeline phase skill — the new SDL entry point. It is a thin routing/orchestration skill following the established skill shape (existing `fbk-*/SKILL.md`): frontmatter `description:` + `argument-hint:`, a thin body that routes to a `.claude/fbk-docs/...` leaf and runs its gate via `python3 "$HOME"/.claude/fbk-scripts/fbk.py <gate>`. The skill orchestrates; the agent drafts; the guide leaf carries the detailed instructions.

The behavioral contract the skill body must encode (from spec §New skills "fbk-intent" and design/fbk-intent.md):

1. **Interview-first entry.** Invoked with a feature name and a terse description: `/fbk-intent <name> <terse description>`. It opens an interview to draw out what the work is and why. For an established project it first reads the durable architecture/intent overview and asks only about the delta.

2. **Routes to the phase guide.** Routes to `fbk-sdl-workflow/intent-guide.md` (the leaf authored by task-27) for the detailed phase instructions — the 10 required PRD sections, the artifacts, and the read-the-overview-first behavior.

3. **Composes the two technique skills.** Composes `fbk-grilling` (invoked when product-level ambiguity surfaces that the agent cannot close by inference — behavior-inventory completeness, user-flow edge cases, acceptance-criteria boundaries) and `fbk-fresh-eyes` (invoked at gate closure on the PRD + behavior inventory). The phase skill compares the fresh-eyes raw report against the grilling log and removes observations that map to grilling-log resolutions before the gate consumes the reduced report.

4. **Delegates PRD drafting to the product-author agent.** The operator interview runs in the skill's own context; PRD drafting is delegated to the context-isolated `fbk-product-author` agent (authored by task-21) so the draft is produced cold. The agent returns PRD prose; the skill owns the file write (the agent has no Write tool — matching `fbk-spec-author`).

5. **Produces the intent artifacts** in the feature directory `ai-docs/<feature>/`: `prd.md` (behavioral content only — no implementation details, no file targets, no code paths), `behavior-inventory.yaml` (structured behavior list with IDs), and `grilling-log-intent.md` (the grilling decision log, with a reflect-back `Confirmed:` line per decision).

6. **Reads and (when intent shifts) updates the durable architecture/intent overview** at `docs/architecture-overview.md` — a project-relative durable doc (path class 3). Before drafting, read the overview to inherit what the project already is/wants; when the feature shifts project intent (a convention, direction, or constraint), update the overview in the feature branch so the change merges with the code.

7. **Runs the intent gate.** Runs `python3 "$HOME"/.claude/fbk-scripts/fbk.py intent-gate <feature-dir>` as the phase gate (the gate module is task-27; this skill calls it by command — a pinned-contract reference).

8. **Stage transition to fbk-design.** Follows the stage-transition protocol: write artifacts → update the overview if intent shifted → append the intent stage section to the feature retrospective → summarize → compact → invoke `/fbk-design <feature-name>` with operator approval.

**Intent is the FIRST phase — it does NOT call the prerequisite probe.** There is no upstream phase, so `fbk-intent` must not call `fbk.precheck.check_prerequisites` and must not check a prior gate. (Intent does check its own gate as a precondition to advancing, but that is the intent gate, not an upstream prerequisite.) Capability-entry still applies in the other direction: work that establishes no new project intent may skip intent and enter downstream — but that is the operator's choice, not a probe the intent skill runs.

**Installed paths.** Reference installed forms in the skill body — `.claude/fbk-docs/fbk-sdl-workflow/intent-guide.md`, `python3 "$HOME"/.claude/fbk-scripts/fbk.py intent-gate` — never the source `assets/...` form (AC-22 path class 1). The durable doc `docs/architecture-overview.md` and the feature artifacts under `ai-docs/<feature>/` are project-relative (path classes 2 and 3) and are referenced as-is.

The paired test (`tests/sdl-workflow/test-phase-skills-intent-design.sh`, task-36) asserts for `fbk-intent`: the file exists non-empty, has `description:` and `argument-hint:` frontmatter, and the body references `intent-guide.md`, `fbk-grilling`, `fbk-fresh-eyes`, `fbk-product-author`, `intent-gate`, and `architecture-overview.md`.

## 3. Instructions

1. Read an existing phase skill for the shape — `assets/skills/fbk-spec/SKILL.md` (frontmatter, thin routing body, gate invocation form) — and the routed guide `assets/fbk-docs/fbk-sdl-workflow/intent-guide.md` (task-27 produces it; if it does not yet exist at execution time, follow the spec's described intent-guide content). Read `tests/sdl-workflow/test-phase-skills-intent-design.sh` (task-36) for the exact sentinel strings the body must contain.

2. Create the directory `assets/skills/fbk-intent/` and `assets/skills/fbk-intent/SKILL.md` with YAML frontmatter: a `description:` (trigger: starting the SDL / opening an intent interview / co-authoring a PRD for a new feature) and an `argument-hint:` (e.g. `"<feature-name> <terse description>"`). Completion: `frontmatter assets/skills/fbk-intent/SKILL.md | grep -q 'description:'` and `... grep -q 'argument-hint:'` succeed.

3. In the skill body, encode the interview-first entry and route to the phase guide `intent-guide.md` for the detailed instructions. Completion: `grep -q 'intent-guide.md' assets/skills/fbk-intent/SKILL.md` succeeds.

4. In the body, compose the two technique skills by name: `fbk-grilling` (for product-level ambiguity) and `fbk-fresh-eyes` (at gate closure), and state the dedup step that reduces the fresh-eyes report against the grilling log before the gate. Completion: `grep -q 'fbk-grilling' ...` and `grep -q 'fbk-fresh-eyes' ...` succeed.

5. In the body, state that PRD drafting is delegated to the `fbk-product-author` agent (context-isolated; the skill owns the file write). Completion: `grep -q 'fbk-product-author' assets/skills/fbk-intent/SKILL.md` succeeds.

6. In the body, name the three produced artifacts (`prd.md`, `behavior-inventory.yaml`, `grilling-log-intent.md` under `ai-docs/<feature>/`) and state that PRD content is behavioral-only.

7. In the body, state that the skill reads (and, when project intent shifts, updates) the durable architecture/intent overview `docs/architecture-overview.md` — referenced as a project-relative path. Completion: `grep -q 'architecture-overview.md' assets/skills/fbk-intent/SKILL.md` succeeds.

8. In the body, run the gate via the installed form: `python3 "$HOME"/.claude/fbk-scripts/fbk.py intent-gate <feature-dir>`. Completion: `grep -q 'intent-gate' assets/skills/fbk-intent/SKILL.md` succeeds.

9. In the body, encode the stage transition (write artifacts → update overview if intent shifted → append the intent retrospective section → summarize → compact → invoke `/fbk-design`). Do NOT add a prerequisite-probe / `check_prerequisites` call — intent is the first phase with no upstream. Completion: `grep -q 'fbk-design' assets/skills/fbk-intent/SKILL.md` succeeds and `grep -c 'check_prerequisites' assets/skills/fbk-intent/SKILL.md` returns 0.

10. Confirm the body carries no source `assets/` path prefix: `grep -c '\bassets/' assets/skills/fbk-intent/SKILL.md` returns 0 (use installed `.claude/...` forms).

11. Run the paired test: `bash tests/sdl-workflow/test-phase-skills-intent-design.sh`. The `fbk-intent` assertions (T1–T9) must pass.

## 4. Files to create/modify

- `assets/skills/fbk-intent/SKILL.md` (create)

## 5. Test requirements

This task makes the `fbk-intent` half of `tests/sdl-workflow/test-phase-skills-intent-design.sh` (task-36) pass — T1–T9 (existence, frontmatter, intent-guide route, grilling + fresh-eyes composition, product-author delegation, intent-gate, architecture-overview). No new tests are written here. Do not edit the test file.

## 6. Acceptance criteria

- AC-01: `fbk-intent` exists, opens an interview, produces `prd.md` + `behavior-inventory.yaml` + `grilling-log-intent.md`, and runs `intent-gate` (the gate's registration and behavior are task-22/task-27; this skill calls it by command).
- The skill composes `fbk-grilling` + `fbk-fresh-eyes`, delegates PRD drafting to `fbk-product-author`, and reads/updates `docs/architecture-overview.md`.
- Intent is the first phase: the skill does not call the prerequisite probe.
- The body uses installed path forms (no `assets/` prefix).
- Primary criterion: the task-36 `fbk-intent` assertions pass.

## 7. Model

Sonnet

## 8. Wave

Wave 2
