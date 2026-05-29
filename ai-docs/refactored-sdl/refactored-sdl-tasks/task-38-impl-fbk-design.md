---
id: task-38
type: implementation
wave: 2
covers: [AC-03, AC-12]
files_to_create:
  - assets/skills/fbk-design/SKILL.md
test_tasks: [task-36]
dependencies: [task-21, task-23]
completion_gate: "task-36 tests pass"
---

## 1. Objective

Produces the `fbk-design` phase skill (`assets/skills/fbk-design/SKILL.md`) — the second SDL phase — which composes the grilling and fresh-eyes technique skills, delegates design authoring to the architect agent, writes design pages + a manifest to the feature directory, appends enduring decisions to the durable decisions log, runs the design gate, and at mid-pipeline entry calls the prerequisite probe to handle the intent-missing-at-design case non-blockingly.

## 2. Context

`fbk-design` is the second phase skill, between intent and spec. It is a thin routing/orchestration skill following the established skill shape (existing `fbk-*/SKILL.md`): frontmatter `description:` + `argument-hint:`, a thin body routing to a `.claude/fbk-docs/...` leaf and running its gate via `python3 "$HOME"/.claude/fbk-scripts/fbk.py <gate>`. The skill orchestrates; the architect agent drafts; the guide leaf carries the detailed instructions.

The behavioral contract the skill body must encode (from spec §New skills "fbk-design" and design/fbk-design.md):

1. **Takes intent inputs.** Consumes the PRD + behavior inventory from `fbk-intent` and produces design artifacts — module list, dependency graph, schemas, interface contracts, decomposition rationale, decision records.

2. **Routes to the phase guide.** Routes to `fbk-sdl-workflow/design-guide.md` (the leaf authored by task-28) for the detailed phase instructions.

3. **Composes the two technique skills.** Composes `fbk-grilling` (invoked when a design choice has multiple reasonable options — the technique surfaces each choice with recommendation and tradeoff, the operator decides) and `fbk-fresh-eyes` (invoked at gate closure on the design pages + manifest).

4. **Delegates to the architect agent.** Drafting is delegated to the context-isolated `fbk-architect` agent in authoring mode (authored by task-21) — the skill orchestrates, the agent drafts. The architect has no Write tool; the skill owns the file writes. (The design gate's own review is fresh-eyes, not the architect.)

5. **Writes design pages + a manifest to the feature directory.** Design pages under `ai-docs/<feature>/design/` (one page per capability — shape, contracts, decomposition rationale) and the `ai-docs/<feature>/design-manifest.md` indexing every page. The manifest's "Decisions recorded" count line points to the durable decisions log and is what the design gate checks is non-zero.

6. **Appends enduring decisions to the durable decisions log** at `docs/decisions-log.md` — append-only, status-bearing entries, written in the feature branch and merged with the change (project-relative durable doc, path class 3). The manifest carries the count and points to the durable log; it never duplicates the log.

7. **Runs the design gate.** Runs `python3 "$HOME"/.claude/fbk-scripts/fbk.py design-gate <feature-dir>` (the gate module is task-28; this skill calls it by command — a pinned-contract reference). The gate performs the bidirectional manifest↔directory check, the decomposition-rationale check, the non-zero "Decisions recorded" check, the injection scan, and the no-open-critical fresh-eyes semantic anchor.

8. **Mid-pipeline-entry prerequisite probe (AC-12 / UV-8 — the intent-missing-at-design case).** When invoked directly, `fbk-design` checks that its upstream (the intent phase) is satisfiable before proceeding. At mid-pipeline entry it calls the capability-entry prerequisite probe `fbk.precheck.check_prerequisites("design", <feature_dir>)` (the `precheck` module from task-23). If the intent artifact (`prd.md`) is missing, the skill names what's missing and offers to run the upstream phase (`/fbk-intent`) — non-blocking, never a hard block. This is the `design` case of the four upstream-missing cases the probe handles (it checks for `prd.md`; if absent it returns the missing artifact + `intent` as the upstream phase). The reverse capability-entry also holds: an operator with a clear enough idea may skip design and start at spec — design is a capability, not a forced step.

9. **Stage transition to fbk-spec.** Follows the stage-transition protocol: write design pages + manifest to the feature dir, enduring decisions to the decisions log, any shape change to the architecture/intent overview → append the design stage section to the feature retrospective → summarize → compact → invoke `/fbk-spec <feature-name>` with operator approval.

**Installed paths.** Reference installed forms in the skill body — `.claude/fbk-docs/fbk-sdl-workflow/design-guide.md`, `python3 "$HOME"/.claude/fbk-scripts/fbk.py design-gate` — never the source `assets/...` form (AC-22 path class 1). The durable doc `docs/decisions-log.md` and the feature artifacts under `ai-docs/<feature>/` are project-relative (path classes 2 and 3) and referenced as-is.

The paired test (`tests/sdl-workflow/test-phase-skills-intent-design.sh`, task-36) asserts for `fbk-design`: the file exists non-empty, has `description:` and `argument-hint:` frontmatter, and the body references `design-guide.md`, `fbk-grilling`, `fbk-fresh-eyes`, `fbk-architect`, `design-gate`, `decisions-log.md`, and `check_prerequisites`.

## 3. Instructions

1. Read an existing phase skill for the shape — `assets/skills/fbk-spec/SKILL.md` (frontmatter, thin routing body, gate invocation form) — and the routed guide `assets/fbk-docs/fbk-sdl-workflow/design-guide.md` (task-28 produces it; if it does not yet exist at execution time, follow the spec's described design-guide content). Read `tests/sdl-workflow/test-phase-skills-intent-design.sh` (task-36) for the exact sentinel strings, and read the precheck contract in task-23 (`check_prerequisites(phase, feature_dir)` — the `design` case checks for `prd.md`).

2. Create the directory `assets/skills/fbk-design/` and `assets/skills/fbk-design/SKILL.md` with YAML frontmatter: a `description:` (trigger: designing a feature's module shape and contracts after intent / co-authoring a design) and an `argument-hint:` (e.g. `"<feature-name>"`). Completion: `frontmatter assets/skills/fbk-design/SKILL.md | grep -q 'description:'` and `... grep -q 'argument-hint:'` succeed.

3. In the body, add the mid-pipeline-entry step FIRST (before design authoring): when invoked directly, call `fbk.precheck.check_prerequisites("design", <feature_dir>)`; if the intent artifact (`prd.md`) is missing, name what's missing and offer to run `/fbk-intent`, non-blocking — never hard-block. This is the intent-missing-at-design case (AC-12 / UV-8). Completion: `grep -q 'check_prerequisites' assets/skills/fbk-design/SKILL.md` succeeds and the body mentions offering to run intent when the PRD is missing.

4. In the body, route to the phase guide `design-guide.md` for the detailed instructions. Completion: `grep -q 'design-guide.md' assets/skills/fbk-design/SKILL.md` succeeds.

5. In the body, compose the two technique skills by name: `fbk-grilling` (for multi-option design choices) and `fbk-fresh-eyes` (at gate closure). Completion: `grep -q 'fbk-grilling' ...` and `grep -q 'fbk-fresh-eyes' ...` succeed.

6. In the body, state that design authoring is delegated to the `fbk-architect` agent in authoring mode (context-isolated; the skill owns the file writes). Completion: `grep -q 'fbk-architect' assets/skills/fbk-design/SKILL.md` succeeds.

7. In the body, state the produced artifacts: design pages under `ai-docs/<feature>/design/`, the `design-manifest.md` indexing them (with the non-zero "Decisions recorded" count line), and the enduring-decisions append to `docs/decisions-log.md` (project-relative durable doc; the manifest points to it and never duplicates it). Completion: `grep -q 'decisions-log.md' assets/skills/fbk-design/SKILL.md` succeeds.

8. In the body, run the gate via the installed form: `python3 "$HOME"/.claude/fbk-scripts/fbk.py design-gate <feature-dir>`. Completion: `grep -q 'design-gate' assets/skills/fbk-design/SKILL.md` succeeds.

9. In the body, encode the stage transition (write artifacts + decisions-log append → append the design retrospective section → summarize → compact → invoke `/fbk-spec`). Completion: `grep -q 'fbk-spec' assets/skills/fbk-design/SKILL.md` succeeds.

10. Confirm the body carries no source `assets/` path prefix: `grep -c '\bassets/' assets/skills/fbk-design/SKILL.md` returns 0 (use installed `.claude/...` forms).

11. Run the paired test: `bash tests/sdl-workflow/test-phase-skills-intent-design.sh`. The `fbk-design` assertions (T10–T19) must pass.

## 4. Files to create/modify

- `assets/skills/fbk-design/SKILL.md` (create)

## 5. Test requirements

This task makes the `fbk-design` half of `tests/sdl-workflow/test-phase-skills-intent-design.sh` (task-36) pass — T10–T19 (existence, frontmatter, design-guide route, grilling + fresh-eyes composition, architect delegation, design-gate, decisions-log append, the `check_prerequisites` probe). No new tests are written here. Do not edit the test file.

## 6. Acceptance criteria

- AC-03: `fbk-design` exists, produces `design/` pages + `design-manifest.md` and appends a status-bearing entry to `docs/decisions-log.md`, and runs `design-gate` (the gate's behavior is task-28; this skill calls it by command).
- AC-12: when invoked without intent artifacts, the skill calls the prerequisite probe, names the missing `prd.md`, and offers to run `/fbk-intent` without hard-blocking (the intent-missing-at-design case / UV-8).
- The skill composes `fbk-grilling` + `fbk-fresh-eyes` and delegates authoring to `fbk-architect`.
- The body uses installed path forms (no `assets/` prefix).
- Primary criterion: the task-36 `fbk-design` assertions pass.

## 7. Model

Sonnet

## 8. Wave

Wave 2
