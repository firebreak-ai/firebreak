---
id: task-14
type: implementation
wave: 1
covers: [AC-17, AC-18]
files_to_create:
  - assets/fbk-docs/fbk-context-assets/always-on-disciplines.md
files_to_modify:
  - .claude/CLAUDE.md
  - assets/fbk-docs/fbk-context-assets.md
test_tasks: [task-01]
dependencies: []
completion_gate: "the referenced test tasks pass"
---

## 1. Objective

Produces the always-on-disciplines authoring leaf (`assets/fbk-docs/fbk-context-assets/always-on-disciplines.md`), surfaces the five disciplines as one-liners with a route in the project `.claude/CLAUDE.md`, and adds the disciplines as instructions in the asset-authoring rules at `assets/fbk-docs/fbk-context-assets.md`.

## 2. Context

This work codifies five always-on authoring disciplines — the habits that produced clean remediation code — so they apply at every session and inform every asset the team authors. The five disciplines, with their exact names (which the test greps for, case-insensitively):

1. **simple language** — write every artifact and every question as if for a smart non-engineer; minimize jargon.
2. **descriptions over identifiers** — in dialogue and prose, refer to items by name or short description, never by bare identifier (no "AC-1", "F-02", "B-NNN").
3. **capability framing** — describe what a thing is and what it does (its capability), not what it forbids or what it is not.
4. **interview before drafting** — surface the open decisions to the operator and get answers before producing an artifact, rather than drafting around an assumed answer.
5. **structural-principles awareness** — keep the asset-authoring structural principles (necessity test, progressive disclosure, separation of concerns, trust-the-agent, objectives-over-steps) in mind whenever authoring or modifying a context asset.

The three-file scope is one cohesive disciplines change, justified below.

Constraints and invariants:
- The five discipline phrases must appear verbatim (case-insensitive match is what the test uses, but write them lowercase as listed): "simple language", "descriptions over identifiers", "capability framing", "interview before drafting", "structural-principles awareness". Each must appear in BOTH `.claude/CLAUDE.md` and `assets/fbk-docs/fbk-context-assets.md`.
- `.claude/CLAUDE.md` must route to the rule that carries the disciplines. The route must reference either the filename token `fbk-context-assets` or the phrase `always-on` (the test accepts either). Reference the rule by its installed path form, not the source `assets/...` form (AC-22 path-class-1 constraint).
- The new leaf is a referenced doc (a "leaf"): it loads only when a skill or the authoring-rules index routes to it. Follow the established leaf style in the sibling files under `assets/fbk-docs/fbk-context-assets/` (imperative, direct-address, one verifiable constraint per instruction — the principles stated in `fbk-context-assets.md` §"Write for Agents, Not Humans").

Existing patterns to follow:
- `assets/fbk-docs/fbk-context-assets.md` already has a `## Routing Table` (around the section titled "Routing Table") listing "When you are... / Read" rows that point to leaves under `fbk-context-assets/`. Add a row routing to the new always-on-disciplines leaf.
- The project `.claude/CLAUDE.md` is currently a short routing file. Its first line already points to the authoring principles doc. Add the five discipline one-liners and a route to the rule.

## 3. Instructions

1. Create `assets/fbk-docs/fbk-context-assets/always-on-disciplines.md`. Author it as a referenced leaf with a one-line load condition at the top (`Load condition: routed from the asset-authoring rules and from session start via CLAUDE.md when authoring or conversing on any firebreak work.`), then a short heading and the five disciplines, each as a named bolded item followed by one imperative instruction. Use the exact discipline names. Completion: `grep -qiF 'structural-principles awareness' assets/fbk-docs/fbk-context-assets/always-on-disciplines.md` succeeds, and the same for the other four names.

2. In `assets/fbk-docs/fbk-context-assets.md`, add the five disciplines as instructions. Place them under a new top-level section `## Always-on disciplines` near the top of the file (before the `## The Necessity Test` section), with each discipline as a bolded name plus one imperative sentence. Each of the five exact phrases ("simple language", "descriptions over identifiers", "capability framing", "interview before drafting", "structural-principles awareness") must appear in this file. Completion: `for p in 'simple language' 'descriptions over identifiers' 'capability framing' 'interview before drafting' 'structural-principles awareness'; do grep -qiF "$p" assets/fbk-docs/fbk-context-assets.md || echo MISSING "$p"; done` prints nothing.

3. In `assets/fbk-docs/fbk-context-assets.md`, add a row to the `## Routing Table` that routes to the new leaf: `| Reviewing the always-on authoring disciplines | `fbk-context-assets/always-on-disciplines.md` |`. Completion: `grep -q 'always-on-disciplines.md' assets/fbk-docs/fbk-context-assets.md` succeeds.

4. In `.claude/CLAUDE.md`, add a section listing the five disciplines as one-liners and a route to the rule that carries them. The five exact discipline phrases must each appear. The route must reference either `fbk-context-assets` or `always-on`. Reference the rule using the installed path form `.claude/fbk-docs/fbk-context-assets/always-on-disciplines.md` (not `assets/...`). Completion: each of the five phrases is grep-findable case-insensitively in `.claude/CLAUDE.md`, and `grep -qE 'fbk-context-assets|always-on' .claude/CLAUDE.md` succeeds.

5. Run the paired test and confirm assertions T1–T11 pass: `bash tests/sdl-workflow/test-always-on-and-durable-docs.sh` (T1–T6 cover CLAUDE.md, T7–T11 cover the authoring rules; T12–T15 are the durable-docs assertions delivered by task-15).

## 4. Files to create/modify

- `assets/fbk-docs/fbk-context-assets/always-on-disciplines.md` (create)
- `assets/fbk-docs/fbk-context-assets.md` (modify)
- `.claude/CLAUDE.md` (modify)

File-scope justification: three files for one cohesive disciplines change. The leaf carries the canonical instruction text; the authoring-rules file makes it an authoring instruction and routes to the leaf; CLAUDE.md surfaces the same five disciplines at session start. Splitting these would create artificial boundaries — the disciplines must be consistent across all three or the routing breaks.

## 5. Test requirements

This task makes assertions T1–T11 of `tests/sdl-workflow/test-always-on-and-durable-docs.sh` pass (the durable-docs assertions T12–T15 are owned by task-15). No new tests are written here. Do not edit the test file.

## 6. Acceptance criteria

- AC-17: `.claude/CLAUDE.md` surfaces all five named always-on disciplines and routes to the rule that carries them (T1–T6 pass).
- AC-18: the asset-authoring rules contain all five always-on disciplines as instructions (T7–T11 pass).
- Primary criterion: the task-01 assertions T1–T11 pass.

## 7. Model

Sonnet

## 8. Wave

Wave 1
