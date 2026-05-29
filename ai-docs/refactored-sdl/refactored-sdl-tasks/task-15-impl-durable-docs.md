---
id: task-15
type: implementation
wave: 1
covers: [AC-19]
files_to_create:
  - docs/decisions-log.md
  - docs/architecture-overview.md
files_to_modify:
  - GLOSSARY.md
test_tasks: [task-01]
dependencies: []
completion_gate: "the referenced test tasks pass"
---

## 1. Objective

Produces the two durable operator-project docs (`docs/decisions-log.md` and `docs/architecture-overview.md`), seeded for this repo, and updates `GLOSSARY.md` with the new durable-artifact and SDL terms while removing cut terms.

## 2. Context

The durable-artifact discipline establishes a small curated set of git-tracked markdown that outlives a feature: the glossary, a decisions log, and an architecture/intent overview. These are **path class 3** (operator-project durable docs) — project-relative, never installed to `~/.claude/`, referenced by the intent/design skills as project-relative paths. The installed-path constraint does NOT apply to them.

The governing conventions for durable docs (which the overview or a doc it references must state): plain markdown, bounded length, in-branch updates that merge with the change. The test greps the overview for at least one of the phrases "plain markdown", "bounded length", or "in-branch".

The decisions log is append-only, chronological, with status-bearing entries: each records what was decided, the alternatives, the rationale, and what it constrains. Seed it with the resolved scoping decisions already recorded in this feature's spec (`ai-docs/refactored-sdl/refactored-sdl-spec.md` §"Decisions resolved during scoping") so the log is non-empty and demonstrates the entry shape — in particular the `fbk-architect` author-only decision (the future council-architect collapse is recorded here, not built).

The architecture overview is living, onboarding-length: what this project is and how it works now. Seed it from the current SDL's shape (the six-phase pipeline the refactoring produces — intent, design, spec, breakdown, code-review, implement — described at onboarding depth) and fold in the unrouted concept material (hybrid-gate pattern, technique-skills layer, design-manifest, durable-artifact discipline) so future intent phases have something to inherit. It must be non-empty.

GLOSSARY changes (the glossary already exists with most SDL terms — confirm presence, add only what is missing, remove cut terms):
- ADD if absent: capability-entry, durable-artifact discipline, architecture/intent overview, decisions log, slice shape (and the four shape names: new-contract, contract-preserving, contract-evolving, cross-cutting), fresh-eyes, quality scan. Confirm technique skill (`technique-skill`) is present.
- REMOVE if present: project-memory, capture gate (capture-gate), mutation sampling.

Note: reading the current GLOSSARY.md shows most of these terms (capability-entry, durable-artifact discipline, architecture/intent overview, decisions log, slice shape, the four shapes, technique-skill, the technique entries) already exist. The remaining gap to confirm is the standalone `fresh-eyes` and `quality scan` short-form entries — they exist as "fresh-eyes technique" and "quality scan technique". Add short alias entries or confirm the technique entries satisfy the requirement. The cut terms (project-memory, capture gate, mutation sampling) are not present in the current file — confirm their absence; do not add them.

## 3. Instructions

1. Create the `docs/` directory if it does not exist. Completion: `[ -d docs ]` succeeds.

2. Create `docs/architecture-overview.md`. Author it as a living, onboarding-length overview of this project (the firebreak SDL): a short "What this is" paragraph, a "How the pipeline works" section naming the six phases in order (intent, design, spec, breakdown, code-review, implement) with one line each, a "Gates" section summarizing the hybrid-gate pattern (mechanical anchor + semantic anchor on a technique-skill artifact), a "Technique skills" section (grilling, fresh-eyes, quality scan, test review as the capability layer), a "Durable docs" section stating the governing conventions verbatim: durable docs are **plain markdown**, kept to **bounded length**, and updated **in-branch** so they merge with the change. Completion: `[ -s docs/architecture-overview.md ]` and `grep -qiE 'plain markdown|bounded length|in-branch' docs/architecture-overview.md` both succeed.

3. Create `docs/decisions-log.md`. Author it as an append-only, chronological, status-bearing log. Add a short header stating the log is append-only and that a new entry supersedes rather than rewriting an old one. Seed it with at least two entries drawn from `ai-docs/refactored-sdl/refactored-sdl-spec.md` §"Decisions resolved during scoping": one for the `fbk-architect` author-only scoping (recording that the future council-architect collapse is deferred, not built this cycle) and one for the code-review gate landing in a new `code_review.py` module. Each entry carries: a date (use 2026-05-29), a status (e.g., `Status: accepted`), what was decided, the alternative considered, and what it constrains. Completion: `[ -f docs/decisions-log.md ]` and `[ -s docs/decisions-log.md ]` both succeed.

4. In `GLOSSARY.md`, confirm the required terms are present. The current file already contains: capability-entry, durable-artifact discipline, architecture/intent overview, decisions log, slice shape, new-contract, contract-preserving, contract-evolving, cross-cutting, technique-skill, fresh-eyes technique, quality scan technique. Verify each by reading; if any is genuinely absent, add a glossary entry following the file's `### term` + `**Definition**:` + `**LLM priors activated**:` format. Add short-form `### fresh-eyes` and `### quality scan` cross-reference stub entries that point to the existing "fresh-eyes technique" and "quality scan technique" entries, so the bare terms resolve. Completion: `grep -q 'fresh-eyes' GLOSSARY.md` and `grep -qi 'quality scan' GLOSSARY.md` succeed.

5. In `GLOSSARY.md`, confirm the cut terms are absent: `grep -iE 'project-memory|capture.gate|mutation sampling' GLOSSARY.md` should print nothing. If any cut term is present as a term entry, remove its entry. (The current file does not contain them — this step is a verification, not an edit, unless they appear.)

6. Run the paired test and confirm assertions T12–T15 pass: `bash tests/sdl-workflow/test-always-on-and-durable-docs.sh`.

## 4. Files to create/modify

- `docs/decisions-log.md` (create)
- `docs/architecture-overview.md` (create)
- `GLOSSARY.md` (modify)

File-scope justification: three files for one cohesive durable-artifact change. The two durable docs and the glossary together constitute "establishing the durable-artifact discipline" (AC-19); they share the same governing conventions and must be created together for the discipline to be coherent.

## 5. Test requirements

This task makes assertions T12–T15 of `tests/sdl-workflow/test-always-on-and-durable-docs.sh` pass (the disciplines assertions T1–T11 are owned by task-14). No new tests are written here. Do not edit the test file.

## 6. Acceptance criteria

- AC-19: `docs/decisions-log.md` and `docs/architecture-overview.md` exist; the overview is non-empty and states at least one governing convention; the glossary carries the durable-artifact and SDL terms with cut terms absent (T12–T15 pass).
- Primary criterion: the task-01 assertions T12–T15 pass.

## 7. Model

Sonnet

## 8. Wave

Wave 1
