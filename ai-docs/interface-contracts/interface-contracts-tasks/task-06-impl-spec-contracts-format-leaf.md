---
id: task-06
type: implementation
wave: 1
covers: [AC-15]
files_to_create:
  - assets/fbk-docs/fbk-sdl-workflow/interface-contracts-format.md
files_to_modify:
  - assets/fbk-docs/fbk-sdl-workflow/feature-spec-guide.md
  - GLOSSARY.md
test_tasks: [task-05]
completion_gate: "task-05 tests pass"
---

# task-06 — Author the spec interface-contracts-format leaf, route from feature-spec-guide, and add glossary terms

## 1. Objective

Produces the new routed leaf `assets/fbk-docs/fbk-sdl-workflow/interface-contracts-format.md` (the three spec-side section shapes plus the blast-radius derivation step), an edit to `assets/fbk-docs/fbk-sdl-workflow/feature-spec-guide.md` adding the always-true required-section note plus a conditional route, and new entries in `GLOSSARY.md` for the vocabulary this feature introduces.

## 2. Context

Implementation task for the `spec-contracts-format-leaf` slice (new-contract discipline). The paired test task (task-05) wrote a shell test that greps the leaf and the guide for structural markers; your edits make it pass. The behavioral intent mirrors the design-side split: the always-true minimal instruction (`## Interface contracts` is a required section; no-contracts is one sentence) lives in the guide and loads on every spec run, while the full section schema loads only when the author actually has contracts to write — the progressive-disclosure discipline.

The normative content for the leaf is worked out in the design — reproduce it faithfully. The leaf must carry:

- The three spec-side section shapes, each with its exact heading: `## Interface contracts`, `## Excluded contracts`, `## Uncovered acceptance criteria`.
- The `## Interface contracts` field rules for an entry: `id` (two forms — `IF-D-NN` carried verbatim from design, or `IF-S-NN` minted by the spec author; `NN` zero-padded, min two digits), `name`, `signature`, `invariants` (at least one condition and one error condition), `covers` (non-empty YAML inline list whose values each match an `AC-NN` in `## Acceptance criteria`), and `design-ref`. Entries are YAML-block list items inside the single section body — there is no `## IF-D-NN` heading per entry on the spec side (a heading per entry would make the section parser terminate at the first entry).
- The three valid `design-ref` forms: a path/anchor into `design/contracts.md` (for carried `IF-D-NN` entries, e.g. `design/contracts.md#if-d-01`), the literal `pre-existing` (for blast-radius entries — pre-existing contracts on touched modules, always paired with an `IF-S-NN` id), and the literal `none` (for spec-discovered new contracts with no design reference, always paired with an `IF-S-NN` id).
- The no-contracts form: the body is the single sentence `No new or changed contracts in this feature.`
- The `## Excluded contracts` shape (each entry an `IF-D-NN` id plus a non-empty `rationale`) and the `## Uncovered acceptance criteria` shape (each entry an `AC-NN` id plus a non-empty `rationale`).
- The section ordering: `## Acceptance criteria` (existing) → `## Interface contracts` (required) → `## Excluded contracts` (conditional) → `## Uncovered acceptance criteria` (conditional) → `## Open questions` (existing) → `## Dependencies` (existing).
- The blast-radius derivation step: to populate pre-existing entries, derive the dependent set with the project's reference tooling run against the modules the spec declares changed, and mint an `IF-S-NN` id for each pre-existing entry found.

**Path-class rule (load-bearing).** The leaf is an installed asset read at `.claude/fbk-docs/fbk-sdl-workflow/...`. Any path the leaf body instructs an agent to read or run must be an INSTALLED path (`.claude/fbk-docs/...`, `python3 "$HOME"/.claude/fbk-scripts/fbk.py ...`) — never an `assets/` source prefix. Task-05's reference-integrity assertion fails if the leaf body contains the literal `assets/`. Refer to the feature-relative artifact path `design/contracts.md`, not source files.

**Where in `feature-spec-guide.md` to add the note.** Read the guide first. The "Feature-Level Spec (9 Required Sections)" block enumerates the required sections, and "Section ordering" detail belongs near §7 Acceptance criteria. Add the always-true note (a `## Interface contracts` section is required; no-contracts is one sentence) into that required-sections enumeration, and add the conditional route adjacent to it. Do not invent a new top-level section — extend the existing required-sections list.

**GLOSSARY conventions.** Read `GLOSSARY.md` first. Each entry follows the house format: `### <term>`, then a `**Definition**:` line, then a `**LLM priors activated**:` line, separated by `---`. New entries append under `## Entries` before the closing `*(Additional entries accrete...)*` line. Match the existing voice. Confirm **integration seam** — verify whether it already has an entry; the design lists it as "confirm already present." (At compilation time `GLOSSARY.md` has no `integration seam` entry — so add one too, defining it as a declared pair of interacting components in `## Technical approach` plus the convention both sides honor.)

The terms to add: **interface contract**, **design contracts page** (`design/contracts.md`), the **IF-D-NN / IF-S-NN** two-namespace identifier scheme, **blast radius** (the dependent set of a changed module), **design-anchor check**, **contract drift**, and **integration seam** (confirm/add).

## 3. Instructions

1. Create `assets/fbk-docs/fbk-sdl-workflow/interface-contracts-format.md`. Reproduce the three section shapes, field rules, the three `design-ref` forms, the no-contracts form, the section ordering, and the blast-radius derivation step from §2. Use the three section headings literally — `## Interface contracts`, `## Excluded contracts`, `## Uncovered acceptance criteria` — so task-05's three heading greps match. Include the blast-radius derivation instruction using the word `blast` and include the `IF-S-` token where you describe minting ids for pre-existing entries (task-05 greps for both `blast` and `IF-S-`). Completion: the file exists; greps for the three headings, for `blast`, and for `IF-S-` all succeed.

2. Verify the leaf body contains no `assets/` source-path prefix. Completion: `grep -q 'assets/' "$LEAF"` returns non-zero.

3. Edit `assets/fbk-docs/fbk-sdl-workflow/feature-spec-guide.md`: in the required-sections enumeration, add the always-true note that `## Interface contracts` is a required section (a no-contracts feature writes one sentence). Completion: the guide contains the anchored heading token `## Interface contracts` paired with a required-marker term (task-05 greps for both).

4. In the same guide location, add a conditional route to the leaf: state that WHEN the author enumerates contracts, excludes one, or leaves an acceptance criterion uncovered, they read `interface-contracts-format.md`. The route is conditional, not unconditional. Completion: the guide references `interface-contracts-format.md` with a conditional clause near it (task-05 greps for both).

5. Edit `GLOSSARY.md`: append entries (house format: `### term`, `**Definition**:`, `**LLM priors activated**:`, `---`) for **interface contract**, **design contracts page**, **IF-D-NN / IF-S-NN identifier scheme**, **blast radius**, **design-anchor check**, **contract drift**, and **integration seam** (add — it is not present at compilation time). Place them under `## Entries`, before the closing `*(Additional entries accrete...)*` line. Completion: each new term has a `###` heading with the two required sub-lines.

6. Run `bash tests/sdl-workflow/test-spec-contracts-format-leaf.sh` from the repo root and confirm it passes (green phase). (The glossary edit is not directly asserted by task-05; it is required by the slice description and the spec's Documentation impact — verify the entries read cleanly against the house format.)

## 4. Files to create/modify

- Create: `assets/fbk-docs/fbk-sdl-workflow/interface-contracts-format.md`
- Modify: `assets/fbk-docs/fbk-sdl-workflow/feature-spec-guide.md`
- Modify: `GLOSSARY.md`

Do not touch any other file. The design-side leaf and design-guide edit are task-04; the reviewer brief is task-08.

### File-scope justification (three files in one task)

This task touches three files, above the 1-2 target. The split is not artificial: the leaf, its route in the guide, and the vocabulary it introduces are one cohesive authoring unit per the slice description (`spec-contracts-format-leaf` explicitly bundles "new leaf; feature-spec-guide.md gains the route; GLOSSARY terms added"). The glossary terms (interface contract, blast radius, design-anchor check, contract drift) are exactly the vocabulary the leaf uses — authoring them apart from the leaf would split a definition from its first use. Keeping them together lets one agent hold the vocabulary consistent across the leaf body, the guide note, and the glossary definitions.

## 5. Test requirements

This task writes no tests. It must make task-05's `tests/sdl-workflow/test-spec-contracts-format-leaf.sh` pass — the guide-names-section-required and conditional-route assertions, the three section-heading greps on the leaf, the `blast` and `IF-S-` greps, and the no-`assets/`-prefix reference-integrity assertion. Re-read task-05 §5 for the exact greps. The glossary edit has no shell-test assertion but is a required work item.

## 6. Acceptance criteria

- Primary: task-05's tests pass (green phase).
- Covers AC-15.
- The guide states `## Interface contracts` is a required section and routes to the leaf conditionally.
- The leaf carries the three section shapes and the blast-radius derivation instruction.
- The leaf body uses installed paths only — no `assets/` source prefix.
- `GLOSSARY.md` carries entries for the new terms in house format; `integration seam` is present.

## 7. Model

Sonnet

Rationale: three files, prose authoring against a normative schema, progressive-disclosure judgment for the guide route, glossary entries that must capture activated LLM priors in the house voice, and path-class discipline. Clearly above the bounded single-file Haiku zone. Sonnet.

## 8. Wave

Wave 1
