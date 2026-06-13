---
id: task-04
type: implementation
wave: 1
covers: [AC-14]
files_to_create:
  - assets/fbk-docs/fbk-sdl-workflow/design-contracts-standard.md
files_to_modify:
  - assets/fbk-docs/fbk-sdl-workflow/design-guide.md
test_tasks: [task-03]
completion_gate: "task-03 tests pass"
---

# task-04 — Author the design contracts-standard leaf and route from design-guide

## 1. Objective

Produces the new routed leaf `assets/fbk-docs/fbk-sdl-workflow/design-contracts-standard.md` (the normative `design/contracts.md` schema) and an edit to `assets/fbk-docs/fbk-sdl-workflow/design-guide.md` adding the always-true required-page note plus a conditional route to the leaf.

## 2. Context

Implementation task for the `design-contracts-standard-leaf` slice (new-contract discipline). The paired test task (task-03) wrote a shell test that greps these two files for structural markers; your edits make it pass. The behavioral intent: the design phase must now always produce a `design/contracts.md`, but the detailed entry schema only matters when the feature actually has contracts — so the always-true minimal instruction lives in the guide (loads every design run) and the full schema lives in a separately-routed leaf (loads only when the author has contracts to write). This is the progressive-disclosure discipline: every instruction in a loaded asset must apply every time the asset loads.

The normative content for the leaf is already worked out in the design — reproduce its schema faithfully. The leaf must carry:

- The two document forms: the no-contracts form (a single sentence) and the entry form (a sequence of `## IF-D-NN` entries).
- The two-namespace identifier scheme: `IF-D-NN` for design-originated contracts (minted at design, live in `design/contracts.md`) and `IF-S-NN` for spec-originated contracts (minted at spec for blast-radius and spec-discovered entries). `NN` is zero-padded, minimum two digits. The carry rule: when the spec carries a design contract forward it copies the `IF-D-NN` id verbatim.
- The entry schema: the heading form `## IF-D-NN — <name>` followed by four fields each on its own line — `signature`, `invariants`, `consumed-by`, `produced-by` — with each field's rule (signature implementable by two independent implementers; invariants name at least one pre/post and at least one error condition, never "None"; consumed-by names at least one consumer and supplies the candidates the spec gate's seam heuristic matches; produced-by names exactly one producer).
- The exact no-contracts sentence: `No new or changed contracts in this feature.`
- The gate parse rule: the design-anchor walk identifies entries with `^## (IF-D-[0-9]{2,})` under `re.MULTILINE` — line-start, level-two heading, `IF-D-` prefix, two-or-more digits — and prose mentions do not match because `^##` anchors to line start.

**Path-class rule (load-bearing).** You are creating a SOURCE file under `assets/`, but the leaf BODY is an installed asset an agent reads at `.claude/fbk-docs/fbk-sdl-workflow/...`. Any path the leaf instructs an agent to read or run must be an INSTALLED path (`.claude/fbk-docs/...`, `python3 "$HOME"/.claude/fbk-scripts/fbk.py ...`) — never an `assets/` source-path prefix. Task-03's reference-integrity assertion fails the build if the leaf body contains the literal `assets/`. The leaf is mostly schema, so this is easy to honor: refer to `design/contracts.md` (the feature-relative artifact path) and to the gate's parse rule, not to source files.

**Where in `design-guide.md` to add the note.** Read the guide first. The "What the Design Phase Produces" section already lists `contracts.md` as a typical design page (under "Design pages"). The natural anchor is that section — promote `contracts.md` from "typical" to "required on every feature" and add the conditional route there. Do not invent a new top-level section; extend the existing one.

## 3. Instructions

1. Create `assets/fbk-docs/fbk-sdl-workflow/design-contracts-standard.md`. Reproduce the normative schema from §2: document forms, identifier scheme, entry schema with the four fields and their rules, the exact no-contracts sentence, and the parse rule. Use the heading-form token `## IF-D-NN — <name>` literally in the schema so task-03's grep for `## IF-D-NN` matches. Include the four field names `signature`, `invariants`, `consumed-by`, `produced-by` literally. Include the parse-rule regex as the literal fixed string `^## (IF-D-` (task-03 greps for it with `grep -qF`). Completion: the file exists; `grep -q '## IF-D-NN' "$LEAF"`, `grep -qF '^## (IF-D-' "$LEAF"`, and a grep for each of the four field names all succeed.

2. Verify the leaf body contains no `assets/` source-path prefix. If you reference any installed asset, use `.claude/fbk-docs/...`. Completion: `grep -q 'assets/' "$LEAF"` returns non-zero (no match).

3. Edit `assets/fbk-docs/fbk-sdl-workflow/design-guide.md`: in the "What the Design Phase Produces" section, change the `contracts.md` description so it states `contracts.md` is required on every feature — a feature that changes no contracts writes one sentence. Completion: the guide contains an anchored statement naming `contracts.md` as required (task-03 greps for `contracts.md` paired with a required-marker term).

4. In the same guide section, add a conditional route to the leaf: state that WHEN the feature introduces or changes contracts, the author reads `design-contracts-standard.md` for the entry schema and identifier scheme. The route must be conditional (gated on the feature having contracts), not unconditional. Completion: the guide contains a reference to `design-contracts-standard.md` with a conditional clause near it (task-03 greps for both the leaf filename and a conditional clause).

5. Run `bash tests/sdl-workflow/test-design-contracts-standard-leaf.sh` from the repo root and confirm it passes (green phase).

## 4. Files to create/modify

- Create: `assets/fbk-docs/fbk-sdl-workflow/design-contracts-standard.md`
- Modify: `assets/fbk-docs/fbk-sdl-workflow/design-guide.md`

Do not touch any other file. The spec-side format leaf and the glossary terms are task-06; the reviewer brief is task-08.

## 5. Test requirements

This task writes no tests. It must make task-03's `tests/sdl-workflow/test-design-contracts-standard-leaf.sh` pass — the instruction-hygiene assertions (guide names `contracts.md` required, guide routes conditionally to the leaf, leaf carries the `## IF-D-NN` schema with all four fields and the `^## (IF-D-` parse rule) and the reference-integrity assertions (leaf exists, leaf body has no `assets/` prefix). Re-read task-03 §5 for the exact greps.

## 6. Acceptance criteria

- Primary: task-03's tests pass (green phase).
- Covers AC-14.
- The guide states `contracts.md` is required on every feature and routes to the leaf only when the feature has contracts.
- The leaf carries the `IF-D-NN` entry schema (four fields) and the design-page parse rule.
- The leaf body uses installed paths only — no `assets/` source prefix.

## 7. Model

Sonnet

Rationale: this is prose authoring against a normative schema plus a precise edit to a loaded guide, requiring progressive-disclosure judgment (always-true note vs. conditional route) and path-class discipline. Two files with judgment about phrasing the route correctly — above Haiku's bounded-mechanical comfort zone. Sonnet.

## 8. Wave

Wave 1
